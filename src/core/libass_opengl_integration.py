"""
Libass-OpenGL Texture Integration System

This module provides the integration layer between libass bitmap output and OpenGL textures,
implementing texture streaming for animated subtitle effects, texture caching for performance
optimization, and karaoke timing data integration.
"""

import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from threading import Lock
import logging

# Configure logging
logger = logging.getLogger(__name__)

try:
    from .libass_integration import LibassContext, LibassImage, LibassIntegration
    from .opengl_context import OpenGLContext, OpenGLTexture
    from .models import SubtitleFile, SubtitleLine, KaraokeTimingInfo
except ImportError:
    from libass_integration import LibassContext, LibassImage, LibassIntegration
    from opengl_context import OpenGLContext, OpenGLTexture
    from models import SubtitleFile, SubtitleLine, KaraokeTimingInfo

# Try to import OpenGL libraries
try:
    import OpenGL.GL as gl
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    logger.warning("OpenGL not available, using mock implementation")


@dataclass
class TextureStreamFrame:
    """Represents a single frame in a texture stream"""
    timestamp: float
    texture: Optional[OpenGLTexture]
    libass_images: List[LibassImage]
    karaoke_data: Optional[KaraokeTimingInfo]
    is_cached: bool = False
    last_access_time: float = field(default_factory=time.time)


@dataclass
class TextureStreamConfig:
    """Configuration for texture streaming"""
    max_cache_size: int = 100
    preload_frames: int = 5
    cache_timeout: float = 30.0  # seconds
    texture_format: int = gl.GL_RGBA if OPENGL_AVAILABLE else 0x1908
    enable_compression: bool = False
    enable_mipmaps: bool = False


class TextureCache:
    """High-performance texture cache with LRU eviction"""
    
    def __init__(self, max_size: int = 100, timeout: float = 30.0):
        self.max_size = max_size
        self.timeout = timeout
        self.cache: Dict[str, TextureStreamFrame] = {}
        self.access_order: List[str] = []
        self.lock = Lock()
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_cache_key(self, timestamp: float, subtitle_hash: str, 
                          viewport_size: Tuple[int, int]) -> str:
        """Generate cache key for texture"""
        return f"{subtitle_hash}_{timestamp:.3f}_{viewport_size[0]}x{viewport_size[1]}"
    
    def get(self, cache_key: str) -> Optional[TextureStreamFrame]:
        """Get cached texture frame"""
        with self.lock:
            if cache_key in self.cache:
                frame = self.cache[cache_key]
                
                # Check if frame has expired
                if time.time() - frame.last_access_time > self.timeout:
                    self._remove_frame(cache_key)
                    self.miss_count += 1
                    return None
                
                # Update access time and order
                frame.last_access_time = time.time()
                if cache_key in self.access_order:
                    self.access_order.remove(cache_key)
                self.access_order.append(cache_key)
                
                self.hit_count += 1
                return frame
            
            self.miss_count += 1
            return None
    
    def put(self, cache_key: str, frame: TextureStreamFrame):
        """Store texture frame in cache"""
        with self.lock:
            # Remove existing entry if present
            if cache_key in self.cache:
                self._remove_frame(cache_key)
            
            # Evict oldest entries if cache is full
            while len(self.cache) >= self.max_size:
                if self.access_order:
                    oldest_key = self.access_order.pop(0)
                    self._remove_frame(oldest_key)
                else:
                    break
            
            # Add new frame
            frame.is_cached = True
            frame.last_access_time = time.time()
            self.cache[cache_key] = frame
            self.access_order.append(cache_key)
    
    def _remove_frame(self, cache_key: str):
        """Remove frame from cache and cleanup texture"""
        if cache_key in self.cache:
            frame = self.cache[cache_key]
            if frame.texture and hasattr(frame.texture, 'destroy'):
                frame.texture.destroy()
            del self.cache[cache_key]
        
        if cache_key in self.access_order:
            self.access_order.remove(cache_key)
    
    def clear(self):
        """Clear all cached textures"""
        with self.lock:
            for frame in self.cache.values():
                if frame.texture and hasattr(frame.texture, 'destroy'):
                    frame.texture.destroy()
            
            self.cache.clear()
            self.access_order.clear()
            self.hit_count = 0
            self.miss_count = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate': hit_rate,
                'timeout': self.timeout
            }
    
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, frame in self.cache.items():
                if current_time - frame.last_access_time > self.timeout:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_frame(key)


class TextureStreamer:
    """Manages texture streaming for animated subtitle effects"""
    
    def __init__(self, config: TextureStreamConfig):
        self.config = config
        self.cache = TextureCache(config.max_cache_size, config.cache_timeout)
        self.preloaded_frames: Dict[float, TextureStreamFrame] = {}
        self.current_subtitle_file: Optional[SubtitleFile] = None
        self.current_karaoke_data: List[KaraokeTimingInfo] = []
        self.lock = Lock()
    
    def set_subtitle_data(self, subtitle_file: SubtitleFile, karaoke_data: List[KaraokeTimingInfo]):
        """Set current subtitle file and karaoke data"""
        with self.lock:
            self.current_subtitle_file = subtitle_file
            self.current_karaoke_data = karaoke_data
            self.preloaded_frames.clear()
    
    def preload_frames(self, timestamps: List[float], libass_context: LibassContext,
                      opengl_context: OpenGLContext, viewport_size: Tuple[int, int]):
        """Preload texture frames for specified timestamps"""
        if not self.current_subtitle_file:
            return
        
        subtitle_hash = self._compute_subtitle_hash(self.current_subtitle_file)
        
        for timestamp in timestamps:
            cache_key = self.cache._generate_cache_key(timestamp, subtitle_hash, viewport_size)
            
            # Skip if already cached
            if self.cache.get(cache_key):
                continue
            
            # Render frame
            frame = self._render_frame(timestamp, libass_context, opengl_context, 
                                     viewport_size, subtitle_hash)
            if frame:
                self.cache.put(cache_key, frame)
    
    def get_frame(self, timestamp: float, libass_context: LibassContext,
                  opengl_context: OpenGLContext, viewport_size: Tuple[int, int]) -> Optional[TextureStreamFrame]:
        """Get texture frame for specified timestamp"""
        if not self.current_subtitle_file:
            return None
        
        subtitle_hash = self._compute_subtitle_hash(self.current_subtitle_file)
        cache_key = self.cache._generate_cache_key(timestamp, subtitle_hash, viewport_size)
        
        # Try cache first
        cached_frame = self.cache.get(cache_key)
        if cached_frame:
            return cached_frame
        
        # Render new frame
        frame = self._render_frame(timestamp, libass_context, opengl_context, 
                                 viewport_size, subtitle_hash)
        if frame:
            self.cache.put(cache_key, frame)
        
        return frame
    
    def _render_frame(self, timestamp: float, libass_context: LibassContext,
                     opengl_context: OpenGLContext, viewport_size: Tuple[int, int],
                     subtitle_hash: str) -> Optional[TextureStreamFrame]:
        """Render a single texture frame"""
        try:
            # Render libass frame
            timestamp_ms = int(timestamp * 1000)
            libass_images = libass_context.render_frame(timestamp_ms)
            
            if not libass_images:
                return None
            
            # Find matching karaoke data
            karaoke_data = self._find_karaoke_data(timestamp)
            
            # Create OpenGL texture from libass images
            texture = self._create_texture_from_libass_images(
                libass_images, opengl_context, viewport_size
            )
            
            return TextureStreamFrame(
                timestamp=timestamp,
                texture=texture,
                libass_images=libass_images,
                karaoke_data=karaoke_data
            )
            
        except Exception as e:
            logger.error(f"Failed to render frame at {timestamp}s: {e}")
            return None
    
    def _create_texture_from_libass_images(self, libass_images: List[LibassImage],
                                         opengl_context: OpenGLContext,
                                         viewport_size: Tuple[int, int]) -> Optional[OpenGLTexture]:
        """Create OpenGL texture from libass bitmap images"""
        if not libass_images:
            return None
        
        try:
            # For now, handle single image (can be extended for multiple images)
            image = libass_images[0]
            
            # Convert libass bitmap to RGBA format
            rgba_data = image.to_rgba_bytes()
            
            # Create numpy array
            rgba_array = np.frombuffer(rgba_data, dtype=np.uint8)
            rgba_array = rgba_array.reshape((image.height, image.width, 4))
            
            # Create OpenGL texture
            texture = opengl_context.create_texture_from_data(
                rgba_array, self.config.texture_format
            )
            
            return texture
            
        except Exception as e:
            logger.error(f"Failed to create texture from libass images: {e}")
            return None
    
    def _find_karaoke_data(self, timestamp: float) -> Optional[KaraokeTimingInfo]:
        """Find karaoke timing data for timestamp"""
        for karaoke_info in self.current_karaoke_data:
            if karaoke_info.start_time <= timestamp <= karaoke_info.end_time:
                return karaoke_info
        return None
    
    def _compute_subtitle_hash(self, subtitle_file: SubtitleFile) -> str:
        """Compute hash for subtitle file content"""
        import hashlib
        content = f"{subtitle_file.file_path}_{len(subtitle_file.lines)}"
        for line in subtitle_file.lines[:10]:  # Sample first 10 lines
            content += f"_{line.text}_{line.start_time}_{line.end_time}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get texture streaming statistics"""
        return {
            'cache_stats': self.cache.get_stats(),
            'preloaded_frames': len(self.preloaded_frames),
            'config': {
                'max_cache_size': self.config.max_cache_size,
                'preload_frames': self.config.preload_frames,
                'cache_timeout': self.config.cache_timeout
            }
        }
    
    def cleanup(self):
        """Clean up texture streamer resources"""
        self.cache.clear()
        self.preloaded_frames.clear()


class KaraokeTextureRenderer:
    """Specialized renderer for karaoke timing effects"""
    
    def __init__(self, opengl_context: OpenGLContext):
        self.opengl_context = opengl_context
        self.syllable_textures: Dict[str, List[OpenGLTexture]] = {}
        self.timing_cache: Dict[str, List[Tuple[float, float]]] = {}
    
    def render_karaoke_frame(self, karaoke_data: KaraokeTimingInfo, current_time: float,
                           viewport_size: Tuple[int, int]) -> List[OpenGLTexture]:
        """Render karaoke frame with syllable-level timing"""
        if not karaoke_data or not karaoke_data.syllable_timings:
            return []
        
        textures = []
        syllable_start_time = karaoke_data.start_time
        
        for i, syllable_duration in enumerate(karaoke_data.syllable_timings):
            syllable_end_time = syllable_start_time + syllable_duration
            
            # Check if this syllable should be highlighted
            is_active = syllable_start_time <= current_time <= syllable_end_time
            
            # Create texture for syllable (simplified - would need actual text rendering)
            texture = self._create_syllable_texture(
                karaoke_data.text, i, is_active, viewport_size
            )
            
            if texture:
                textures.append(texture)
            
            syllable_start_time = syllable_end_time
        
        return textures
    
    def _create_syllable_texture(self, text: str, syllable_index: int, is_active: bool,
                               viewport_size: Tuple[int, int]) -> Optional[OpenGLTexture]:
        """Create texture for individual syllable"""
        # This is a simplified implementation
        # In practice, this would render individual syllables with different colors/effects
        
        # Create mock texture data for testing
        width, height = 100, 50
        channels = 4
        
        # Create RGBA data
        rgba_data = np.zeros((height, width, channels), dtype=np.uint8)
        
        if is_active:
            # Active syllable - bright color
            rgba_data[:, :, 0] = 255  # Red
            rgba_data[:, :, 1] = 255  # Green
            rgba_data[:, :, 2] = 0    # Blue
            rgba_data[:, :, 3] = 255  # Alpha
        else:
            # Inactive syllable - dim color
            rgba_data[:, :, 0] = 128  # Red
            rgba_data[:, :, 1] = 128  # Green
            rgba_data[:, :, 2] = 128  # Blue
            rgba_data[:, :, 3] = 255  # Alpha
        
        return self.opengl_context.create_texture_from_data(rgba_data)
    
    def update_karaoke_progress(self, karaoke_data: KaraokeTimingInfo, current_time: float) -> float:
        """Calculate karaoke progress for current time"""
        if not karaoke_data:
            return 0.0
        
        if current_time < karaoke_data.start_time:
            return 0.0
        elif current_time > karaoke_data.end_time:
            return 1.0
        else:
            duration = karaoke_data.end_time - karaoke_data.start_time
            elapsed = current_time - karaoke_data.start_time
            return elapsed / duration if duration > 0 else 0.0


class LibassOpenGLIntegration:
    """Main integration class for libass-OpenGL texture system"""
    
    def __init__(self, opengl_context: OpenGLContext, 
                 config: Optional[TextureStreamConfig] = None):
        self.opengl_context = opengl_context
        self.config = config or TextureStreamConfig()
        
        # Initialize components
        self.libass_integration = LibassIntegration()
        self.texture_streamer = TextureStreamer(self.config)
        self.karaoke_renderer = KaraokeTextureRenderer(opengl_context)
        
        # State
        self.current_subtitle_file: Optional[SubtitleFile] = None
        self.current_karaoke_data: List[KaraokeTimingInfo] = []
        self.viewport_size = (1920, 1080)
        
        logger.info("Libass-OpenGL integration initialized")
    
    def load_subtitle_file(self, file_path: str) -> bool:
        """Load subtitle file and prepare for rendering"""
        try:
            # Load file using libass integration
            subtitle_file, karaoke_data = self.libass_integration.load_and_parse_subtitle_file(file_path)
            
            # Set data in texture streamer
            self.texture_streamer.set_subtitle_data(subtitle_file, karaoke_data)
            
            # Store current data
            self.current_subtitle_file = subtitle_file
            self.current_karaoke_data = karaoke_data
            
            logger.info(f"Loaded subtitle file: {file_path}")
            if hasattr(subtitle_file, 'lines'):
                logger.info(f"Found {len(subtitle_file.lines)} subtitle lines")
            if hasattr(karaoke_data, '__len__'):
                logger.info(f"Found {len(karaoke_data)} karaoke timing entries")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load subtitle file {file_path}: {e}")
            return False
    
    def set_viewport_size(self, width: int, height: int):
        """Set viewport size for texture rendering"""
        self.viewport_size = (width, height)
    
    def render_frame(self, timestamp: float) -> Optional[TextureStreamFrame]:
        """Render subtitle frame at specified timestamp"""
        if not self.current_subtitle_file or not self.libass_integration.context.is_available():
            return None
        
        return self.texture_streamer.get_frame(
            timestamp,
            self.libass_integration.context,
            self.opengl_context,
            self.viewport_size
        )
    
    def render_karaoke_frame(self, timestamp: float) -> Tuple[Optional[TextureStreamFrame], List[OpenGLTexture]]:
        """Render frame with karaoke timing effects"""
        # Get base subtitle frame
        base_frame = self.render_frame(timestamp)
        
        # Get karaoke-specific textures
        karaoke_textures = []
        if base_frame and base_frame.karaoke_data:
            karaoke_textures = self.karaoke_renderer.render_karaoke_frame(
                base_frame.karaoke_data, timestamp, self.viewport_size
            )
        
        return base_frame, karaoke_textures
    
    def preload_frames_for_range(self, start_time: float, end_time: float, fps: float = 30.0):
        """Preload texture frames for time range"""
        if not self.current_subtitle_file or not self.libass_integration.context.is_available():
            return
        
        # Generate timestamps
        frame_duration = 1.0 / fps
        timestamps = []
        current_time = start_time
        
        while current_time <= end_time:
            timestamps.append(current_time)
            current_time += frame_duration
        
        # Preload frames
        self.texture_streamer.preload_frames(
            timestamps,
            self.libass_integration.context,
            self.opengl_context,
            self.viewport_size
        )
        
        logger.info(f"Preloaded {len(timestamps)} frames for range {start_time:.2f}s - {end_time:.2f}s")
    
    def get_karaoke_progress(self, timestamp: float) -> float:
        """Get karaoke progress for current timestamp"""
        # Find active karaoke data
        for karaoke_data in self.current_karaoke_data:
            if karaoke_data.start_time <= timestamp <= karaoke_data.end_time:
                return self.karaoke_renderer.update_karaoke_progress(karaoke_data, timestamp)
        
        return 0.0
    
    def get_active_subtitles(self, timestamp: float) -> List[SubtitleLine]:
        """Get subtitle lines active at specified timestamp"""
        if not self.current_subtitle_file:
            return []
        
        active_subtitles = []
        for line in self.current_subtitle_file.lines:
            if line.start_time <= timestamp <= line.end_time:
                active_subtitles.append(line)
        
        return active_subtitles
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'texture_streaming': self.texture_streamer.get_cache_stats(),
            'libass_available': self.libass_integration.context.is_available(),
            'opengl_context': self.opengl_context.backend.value if self.opengl_context else None,
            'viewport_size': self.viewport_size,
            'subtitle_file_loaded': self.current_subtitle_file is not None,
            'karaoke_data_count': len(self.current_karaoke_data)
        }
    
    def cleanup(self):
        """Clean up all resources"""
        if self.texture_streamer:
            self.texture_streamer.cleanup()
        
        if self.libass_integration:
            self.libass_integration.cleanup()
        
        logger.info("Libass-OpenGL integration cleaned up")


# Convenience functions
def create_libass_opengl_integration(opengl_context: OpenGLContext,
                                   cache_size: int = 100,
                                   preload_frames: int = 5) -> LibassOpenGLIntegration:
    """Create libass-OpenGL integration with specified configuration"""
    config = TextureStreamConfig(
        max_cache_size=cache_size,
        preload_frames=preload_frames
    )
    
    return LibassOpenGLIntegration(opengl_context, config)


def load_and_render_subtitle(file_path: str, timestamp: float,
                           opengl_context: OpenGLContext,
                           viewport_size: Tuple[int, int] = (1920, 1080)) -> Optional[TextureStreamFrame]:
    """Load subtitle file and render frame at specified timestamp"""
    integration = create_libass_opengl_integration(opengl_context)
    
    try:
        integration.set_viewport_size(*viewport_size)
        
        if integration.load_subtitle_file(file_path):
            return integration.render_frame(timestamp)
        
        return None
        
    finally:
        integration.cleanup()


if __name__ == "__main__":
    print("Testing Libass-OpenGL Integration...")
    
    # This would normally require actual OpenGL context and libass library
    # For testing, we'll use mock implementations
    from opengl_context import create_offscreen_context
    
    context = create_offscreen_context(1920, 1080)
    if context:
        integration = create_libass_opengl_integration(context)
        print("Integration created successfully")
        print("Performance stats:", integration.get_performance_stats())
        integration.cleanup()
        context.cleanup()
    else:
        print("Failed to create OpenGL context")