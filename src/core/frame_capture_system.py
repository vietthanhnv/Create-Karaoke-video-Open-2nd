"""
Frame Capture and Rendering System

This module provides enhanced frame capture and rendering capabilities for the karaoke video creator.
It implements frame-by-frame rendering at specified timestamps, framebuffer capture to raw pixel data,
pixel format conversion for FFmpeg compatibility, and frame rate synchronization with audio timing.
"""

import os
import time
import threading
import queue
import struct
from typing import Optional, Tuple, List, Dict, Any, Callable, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    from PyQt6.QtGui import QImage
    import OpenGL.GL as gl
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

try:
    from .opengl_context import OpenGLContext, OpenGLFramebuffer, FramebufferConfig
    from .models import Project, SubtitleLine
    from .opengl_subtitle_renderer import OpenGLSubtitleRenderer
    from .effects_rendering_pipeline import EffectsRenderingPipeline
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from opengl_context import OpenGLContext, OpenGLFramebuffer, FramebufferConfig
    from models import Project, SubtitleLine
    from opengl_subtitle_renderer import OpenGLSubtitleRenderer
    from effects_rendering_pipeline import EffectsRenderingPipeline


class PixelFormat(Enum):
    """Supported pixel formats for frame capture"""
    RGBA8 = "rgba8"
    RGB8 = "rgb8"
    YUV420P = "yuv420p"
    YUV444P = "yuv444p"
    BGRA8 = "bgra8"
    BGR8 = "bgr8"


@dataclass
class FrameTimestamp:
    """Frame timing information"""
    frame_number: int
    timestamp: float
    duration: float
    fps: float
    
    @property
    def next_timestamp(self) -> float:
        """Get timestamp for next frame"""
        return self.timestamp + (1.0 / self.fps)
    
    @property
    def previous_timestamp(self) -> float:
        """Get timestamp for previous frame"""
        return max(0.0, self.timestamp - (1.0 / self.fps))


@dataclass
class CapturedFrame:
    """Captured frame data with metadata"""
    frame_number: int
    timestamp: float
    width: int
    height: int
    pixel_format: PixelFormat
    data: np.ndarray
    capture_time: float
    render_time: float
    
    @property
    def size_bytes(self) -> int:
        """Get frame size in bytes"""
        return self.data.nbytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'frame_number': self.frame_number,
            'timestamp': self.timestamp,
            'width': self.width,
            'height': self.height,
            'pixel_format': self.pixel_format.value,
            'size_bytes': self.size_bytes,
            'capture_time': self.capture_time,
            'render_time': self.render_time
        }


@dataclass
class FrameCaptureSettings:
    """Settings for frame capture"""
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    pixel_format: PixelFormat = PixelFormat.RGBA8
    quality: float = 1.0  # Quality factor (0.1 to 1.0)
    
    # Performance settings
    use_threading: bool = True
    buffer_size: int = 10  # Number of frames to buffer
    
    # Synchronization settings
    sync_with_audio: bool = True
    audio_offset: float = 0.0  # Audio offset in seconds
    
    # Output settings
    flip_vertically: bool = True  # OpenGL framebuffers are flipped
    premultiply_alpha: bool = False


class FrameRenderingEngine:
    """Core frame rendering engine with OpenGL integration"""
    
    def __init__(self, opengl_context: OpenGLContext):
        self.opengl_context = opengl_context
        self.framebuffer: Optional[OpenGLFramebuffer] = None
        self.subtitle_renderer: Optional[OpenGLSubtitleRenderer] = None
        self.effects_pipeline: Optional[EffectsRenderingPipeline] = None
        
        # Current project and settings
        self.current_project: Optional[Project] = None
        self.capture_settings: Optional[FrameCaptureSettings] = None
        
        # Performance tracking
        self.render_times: List[float] = []
        self.last_render_time = 0.0
        
        # Background rendering cache
        self.background_cache: Dict[float, np.ndarray] = {}
        self.cache_max_size = 50
    
    def initialize(self, project: Project, settings: FrameCaptureSettings) -> bool:
        """Initialize the rendering engine with project and settings"""
        self.current_project = project
        self.capture_settings = settings
        
        try:
            # Create framebuffer for rendering
            config = FramebufferConfig(
                width=settings.width,
                height=settings.height,
                use_depth=True,
                use_stencil=False
            )
            
            self.framebuffer = self.opengl_context.create_framebuffer("frame_capture", config)
            if not self.framebuffer:
                print("Failed to create framebuffer for frame capture")
                return False
            
            # Initialize subtitle renderer
            self.subtitle_renderer = OpenGLSubtitleRenderer()
            if not self.subtitle_renderer.initialize_opengl():
                print("Failed to initialize subtitle renderer")
                return False
            
            # Initialize effects pipeline
            self.effects_pipeline = EffectsRenderingPipeline(self.opengl_context)
            # Effects pipeline initializes itself in constructor, no need to call initialize()
            
            print(f"Frame rendering engine initialized: {settings.width}x{settings.height} @ {settings.fps}fps")
            return True
            
        except Exception as e:
            print(f"Failed to initialize frame rendering engine: {e}")
            return False
    
    def render_frame_at_timestamp(self, timestamp: float) -> Optional[CapturedFrame]:
        """Render a single frame at the specified timestamp"""
        if not self.framebuffer or not self.current_project or not self.capture_settings:
            return None
        
        start_time = time.time()
        
        try:
            # Make OpenGL context current
            if not self.opengl_context.make_current():
                print("Failed to make OpenGL context current")
                return None
            
            # Bind framebuffer for rendering
            self.framebuffer.bind()
            
            # Clear framebuffer
            self.framebuffer.clear((0.0, 0.0, 0.0, 1.0))
            
            # Render background (video or image)
            self._render_background(timestamp)
            
            # Render subtitles with effects
            self._render_subtitles(timestamp)
            
            # Capture framebuffer to pixel data
            pixel_data = self._capture_framebuffer()
            
            # Unbind framebuffer
            self.framebuffer.unbind()
            
            if pixel_data is None:
                return None
            
            # Convert pixel format if needed
            converted_data = self._convert_pixel_format(pixel_data, self.capture_settings.pixel_format)
            
            # Calculate frame number
            frame_number = int(timestamp * self.capture_settings.fps)
            
            # Record render time
            render_time = time.time() - start_time
            self.render_times.append(render_time)
            self.last_render_time = render_time
            
            # Keep only recent render times for performance tracking
            if len(self.render_times) > 100:
                self.render_times = self.render_times[-100:]
            
            return CapturedFrame(
                frame_number=frame_number,
                timestamp=timestamp,
                width=self.capture_settings.width,
                height=self.capture_settings.height,
                pixel_format=self.capture_settings.pixel_format,
                data=converted_data,
                capture_time=time.time(),
                render_time=render_time
            )
            
        except Exception as e:
            print(f"Frame rendering failed at timestamp {timestamp}: {e}")
            return None
    
    def _render_background(self, timestamp: float):
        """Render background (video frame or static image)"""
        if not self.current_project:
            return
        
        try:
            # Check cache first
            if timestamp in self.background_cache:
                cached_data = self.background_cache[timestamp]
                self._render_background_data(cached_data)
                return
            
            # Render based on project media
            if self.current_project.video_file:
                self._render_video_background(timestamp)
            elif self.current_project.image_file:
                self._render_image_background()
            else:
                # No background media - render solid color
                if PYQT_AVAILABLE:
                    gl.glClearColor(0.1, 0.1, 0.2, 1.0)  # Dark blue
                    gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
        except Exception as e:
            print(f"Background rendering failed: {e}")
            # Fallback to solid color
            if PYQT_AVAILABLE:
                gl.glClearColor(0.1, 0.1, 0.2, 1.0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    
    def _render_video_background(self, timestamp: float):
        """Render video frame at specified timestamp"""
        if not self.current_project.video_file:
            return
        
        try:
            # For now, render a time-based gradient as placeholder
            # In production, this would extract actual video frames
            progress = (timestamp % 10.0) / 10.0  # 10-second cycle
            
            if PYQT_AVAILABLE:
                # Create time-based color
                r = 0.2 + 0.3 * progress
                g = 0.3 + 0.2 * (1.0 - progress)
                b = 0.4 + 0.1 * progress
                
                gl.glClearColor(r, g, b, 1.0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
            # Cache this background for performance
            if len(self.background_cache) < self.cache_max_size:
                # In a real implementation, we'd cache the actual rendered data
                self.background_cache[timestamp] = np.array([r, g, b, 1.0], dtype=np.float32)
            
        except Exception as e:
            print(f"Video background rendering failed: {e}")
    
    def _render_image_background(self):
        """Render static image background"""
        if not self.current_project.image_file:
            return
        
        try:
            # For now, render a static gradient
            # In production, this would load and render the actual image
            if PYQT_AVAILABLE:
                gl.glClearColor(0.3, 0.5, 0.3, 1.0)  # Green tint
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            
        except Exception as e:
            print(f"Image background rendering failed: {e}")
    
    def _render_background_data(self, data: np.ndarray):
        """Render cached background data"""
        if PYQT_AVAILABLE and len(data) >= 3:
            gl.glClearColor(data[0], data[1], data[2], data[3] if len(data) > 3 else 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    
    def _render_subtitles(self, timestamp: float):
        """Render subtitles with effects at the specified timestamp"""
        if not self.current_project or not self.subtitle_renderer:
            return
        
        try:
            # Get visible subtitles at this timestamp
            visible_subtitles = self._get_visible_subtitles(timestamp)
            
            if not visible_subtitles:
                return
            
            # Set current time for effects
            self.subtitle_renderer.set_current_time(timestamp)
            
            # Render each visible subtitle
            viewport_size = (self.capture_settings.width, self.capture_settings.height)
            
            for subtitle in visible_subtitles:
                # Apply effects if pipeline is available
                if self.effects_pipeline:
                    self.effects_pipeline.set_current_time(timestamp)
                    # Effects would be applied here in production
                
                # Render subtitle (placeholder implementation)
                self._render_subtitle_placeholder(subtitle, timestamp, viewport_size)
            
        except Exception as e:
            print(f"Subtitle rendering failed: {e}")
    
    def _get_visible_subtitles(self, timestamp: float) -> List[SubtitleLine]:
        """Get subtitles visible at the specified timestamp"""
        if not self.current_project or not self.current_project.subtitle_file:
            return []
        
        visible = []
        for subtitle in self.current_project.subtitle_file.lines:
            if subtitle.start_time <= timestamp <= subtitle.end_time:
                visible.append(subtitle)
        
        return visible
    
    def _render_subtitle_placeholder(self, subtitle: SubtitleLine, timestamp: float, viewport_size: Tuple[int, int]):
        """Render subtitle placeholder (for testing without full libass integration)"""
        # This is a placeholder that would be replaced with actual subtitle rendering
        # For now, it just ensures the rendering pipeline is working
        pass
    
    def _capture_framebuffer(self) -> Optional[np.ndarray]:
        """Capture framebuffer contents to numpy array"""
        if not self.framebuffer:
            return None
        
        try:
            # Read pixels from framebuffer
            pixel_data = self.framebuffer.read_pixels()
            
            if pixel_data is None:
                return None
            
            # Apply quality scaling if needed
            if self.capture_settings.quality < 1.0:
                pixel_data = self._apply_quality_scaling(pixel_data)
            
            # Flip vertically if needed (OpenGL framebuffers are upside down)
            if self.capture_settings.flip_vertically:
                pixel_data = np.flipud(pixel_data)
            
            return pixel_data
            
        except Exception as e:
            print(f"Framebuffer capture failed: {e}")
            return None
    
    def _apply_quality_scaling(self, data: np.ndarray) -> np.ndarray:
        """Apply quality scaling to reduce data size"""
        if self.capture_settings.quality >= 1.0:
            return data
        
        try:
            # Simple quality reduction by scaling down and back up
            height, width = data.shape[:2]
            new_height = int(height * self.capture_settings.quality)
            new_width = int(width * self.capture_settings.quality)
            
            # This would use proper image scaling in production
            # For now, just return original data
            return data
            
        except Exception as e:
            print(f"Quality scaling failed: {e}")
            return data
    
    def _convert_pixel_format(self, data: np.ndarray, target_format: PixelFormat) -> np.ndarray:
        """Convert pixel data to target format"""
        if data is None:
            return None
        
        try:
            # Current data is assumed to be RGBA8
            if target_format == PixelFormat.RGBA8:
                return data
            elif target_format == PixelFormat.RGB8:
                return self._rgba_to_rgb(data)
            elif target_format == PixelFormat.YUV420P:
                return self._rgba_to_yuv420p(data)
            elif target_format == PixelFormat.YUV444P:
                return self._rgba_to_yuv444p(data)
            elif target_format == PixelFormat.BGRA8:
                return self._rgba_to_bgra(data)
            elif target_format == PixelFormat.BGR8:
                return self._rgba_to_bgr(data)
            else:
                print(f"Unsupported pixel format: {target_format}")
                return data
                
        except Exception as e:
            print(f"Pixel format conversion failed: {e}")
            return data
    
    def _rgba_to_rgb(self, data: np.ndarray) -> np.ndarray:
        """Convert RGBA to RGB by dropping alpha channel"""
        if data.shape[2] >= 3:
            return data[:, :, :3].copy()
        return data
    
    def _rgba_to_bgra(self, data: np.ndarray) -> np.ndarray:
        """Convert RGBA to BGRA by swapping red and blue channels"""
        if data.shape[2] >= 4:
            result = data.copy()
            result[:, :, [0, 2]] = result[:, :, [2, 0]]  # Swap R and B
            return result
        return data
    
    def _rgba_to_bgr(self, data: np.ndarray) -> np.ndarray:
        """Convert RGBA to BGR by swapping red and blue channels and dropping alpha"""
        if data.shape[2] >= 3:
            result = data[:, :, :3].copy()
            result[:, :, [0, 2]] = result[:, :, [2, 0]]  # Swap R and B
            return result
        return data
    
    def _rgba_to_yuv420p(self, data: np.ndarray) -> np.ndarray:
        """Convert RGBA to YUV420P format for FFmpeg compatibility"""
        if data.shape[2] < 3:
            return data
        
        try:
            # Extract RGB channels (ignore alpha)
            rgb = data[:, :, :3].astype(np.float32) / 255.0
            
            # Convert RGB to YUV using ITU-R BT.601 coefficients
            # Y = 0.299*R + 0.587*G + 0.114*B
            # U = -0.147*R - 0.289*G + 0.436*B + 0.5
            # V = 0.615*R - 0.515*G - 0.100*B + 0.5
            
            r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
            
            # Calculate Y (luma) - full resolution
            y = 0.299 * r + 0.587 * g + 0.114 * b
            
            # Calculate U and V (chroma) - subsampled to half resolution
            height, width = data.shape[:2]
            u_height, u_width = height // 2, width // 2
            v_height, v_width = height // 2, width // 2
            
            # Subsample by taking every other pixel
            r_sub = r[::2, ::2]
            g_sub = g[::2, ::2]
            b_sub = b[::2, ::2]
            
            u = -0.147 * r_sub - 0.289 * g_sub + 0.436 * b_sub + 0.5
            v = 0.615 * r_sub - 0.515 * g_sub - 0.100 * b_sub + 0.5
            
            # Convert to 8-bit and clamp
            y = np.clip(y * 255, 0, 255).astype(np.uint8)
            u = np.clip(u * 255, 0, 255).astype(np.uint8)
            v = np.clip(v * 255, 0, 255).astype(np.uint8)
            
            # Pack YUV420P format: Y plane, then U plane, then V plane
            yuv_size = height * width + 2 * u_height * u_width
            yuv_data = np.zeros(yuv_size, dtype=np.uint8)
            
            # Y plane (full resolution)
            yuv_data[:height * width] = y.flatten()
            
            # U plane (quarter resolution)
            u_start = height * width
            u_end = u_start + u_height * u_width
            yuv_data[u_start:u_end] = u.flatten()
            
            # V plane (quarter resolution)
            v_start = u_end
            yuv_data[v_start:] = v.flatten()
            
            return yuv_data.reshape(-1, 1)  # Return as column vector
            
        except Exception as e:
            print(f"RGBA to YUV420P conversion failed: {e}")
            return data
    
    def _rgba_to_yuv444p(self, data: np.ndarray) -> np.ndarray:
        """Convert RGBA to YUV444P format (full resolution chroma)"""
        if data.shape[2] < 3:
            return data
        
        try:
            # Extract RGB channels (ignore alpha)
            rgb = data[:, :, :3].astype(np.float32) / 255.0
            
            r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
            
            # Convert RGB to YUV
            y = 0.299 * r + 0.587 * g + 0.114 * b
            u = -0.147 * r - 0.289 * g + 0.436 * b + 0.5
            v = 0.615 * r - 0.515 * g - 0.100 * b + 0.5
            
            # Convert to 8-bit and clamp
            y = np.clip(y * 255, 0, 255).astype(np.uint8)
            u = np.clip(u * 255, 0, 255).astype(np.uint8)
            v = np.clip(v * 255, 0, 255).astype(np.uint8)
            
            # Pack YUV444P format: Y plane, then U plane, then V plane
            height, width = data.shape[:2]
            yuv_size = 3 * height * width
            yuv_data = np.zeros(yuv_size, dtype=np.uint8)
            
            # Y plane
            yuv_data[:height * width] = y.flatten()
            
            # U plane
            u_start = height * width
            u_end = u_start + height * width
            yuv_data[u_start:u_end] = u.flatten()
            
            # V plane
            v_start = u_end
            yuv_data[v_start:] = v.flatten()
            
            return yuv_data.reshape(-1, 1)  # Return as column vector
            
        except Exception as e:
            print(f"RGBA to YUV444P conversion failed: {e}")
            return data
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get rendering performance statistics"""
        if not self.render_times:
            return {
                'average_render_time': 0.0,
                'min_render_time': 0.0,
                'max_render_time': 0.0,
                'fps_estimate': 0.0,
                'frame_count': 0
            }
        
        avg_time = np.mean(self.render_times)
        min_time = np.min(self.render_times)
        max_time = np.max(self.render_times)
        fps_estimate = 1.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            'average_render_time': avg_time,
            'min_render_time': min_time,
            'max_render_time': max_time,
            'fps_estimate': fps_estimate,
            'frame_count': len(self.render_times)
        }
    
    def cleanup(self):
        """Clean up rendering resources"""
        if self.framebuffer:
            self.framebuffer.destroy()
            self.framebuffer = None
        
        if self.subtitle_renderer:
            self.subtitle_renderer.cleanup()
            self.subtitle_renderer = None
        
        if self.effects_pipeline:
            self.effects_pipeline.cleanup()
            self.effects_pipeline = None
        
        self.background_cache.clear()
        self.render_times.clear()


class FrameCaptureSystem(QObject):
    """
    High-level frame capture system with threading and synchronization support
    """
    
    # Signals for progress and status updates
    frame_captured = pyqtSignal(dict)  # Frame metadata
    capture_progress = pyqtSignal(float)  # Progress percentage
    capture_completed = pyqtSignal()
    capture_failed = pyqtSignal(str)  # Error message
    
    def __init__(self, opengl_context: OpenGLContext):
        super().__init__()
        
        self.opengl_context = opengl_context
        self.rendering_engine = FrameRenderingEngine(opengl_context)
        
        # Capture state
        self.is_capturing = False
        self.should_cancel = False
        
        # Threading support
        self.capture_thread: Optional[threading.Thread] = None
        self.frame_queue: Optional[queue.Queue] = None
        
        # Synchronization
        self.audio_sync_offset = 0.0
        self.frame_timestamps: List[FrameTimestamp] = []
        
        # Performance tracking
        self.capture_start_time = 0.0
        self.frames_captured = 0
        self.total_frames = 0
    
    def initialize(self, project: Project, settings: FrameCaptureSettings) -> bool:
        """Initialize the capture system"""
        return self.rendering_engine.initialize(project, settings)
    
    def generate_frame_timestamps(self, duration: float, fps: float, start_time: float = 0.0) -> List[FrameTimestamp]:
        """Generate frame timestamps for the specified duration and frame rate"""
        timestamps = []
        frame_duration = 1.0 / fps
        
        current_time = start_time
        frame_number = 0
        
        while current_time < duration:
            timestamps.append(FrameTimestamp(
                frame_number=frame_number,
                timestamp=current_time,
                duration=frame_duration,
                fps=fps
            ))
            
            current_time += frame_duration
            frame_number += 1
        
        return timestamps
    
    def capture_frame_sequence(self, timestamps: List[FrameTimestamp], 
                             progress_callback: Optional[Callable[[float], None]] = None) -> List[CapturedFrame]:
        """Capture a sequence of frames at the specified timestamps"""
        if self.is_capturing:
            print("Capture already in progress")
            return []
        
        self.is_capturing = True
        self.should_cancel = False
        self.frames_captured = 0
        self.total_frames = len(timestamps)
        self.capture_start_time = time.time()
        
        captured_frames = []
        
        try:
            for i, timestamp_info in enumerate(timestamps):
                if self.should_cancel:
                    print("Frame capture cancelled")
                    break
                
                # Capture frame at timestamp
                frame = self.rendering_engine.render_frame_at_timestamp(timestamp_info.timestamp)
                
                if frame:
                    captured_frames.append(frame)
                    self.frames_captured += 1
                    
                    # Emit frame captured signal
                    if PYQT_AVAILABLE:
                        self.frame_captured.emit(frame.to_dict())
                    
                    # Update progress
                    progress = (i + 1) / len(timestamps)
                    if progress_callback:
                        progress_callback(progress)
                    
                    if PYQT_AVAILABLE:
                        self.capture_progress.emit(progress * 100.0)
                    
                    # Print progress every 10 frames
                    if (i + 1) % 10 == 0 or i == len(timestamps) - 1:
                        elapsed = time.time() - self.capture_start_time
                        fps = self.frames_captured / elapsed if elapsed > 0 else 0
                        print(f"Captured frame {i + 1}/{len(timestamps)} ({progress*100:.1f}%) - {fps:.1f} fps")
                
                else:
                    print(f"Failed to capture frame at timestamp {timestamp_info.timestamp}")
            
            if not self.should_cancel:
                print(f"Frame capture completed: {len(captured_frames)} frames")
                if PYQT_AVAILABLE:
                    self.capture_completed.emit()
            
        except Exception as e:
            error_msg = f"Frame capture failed: {e}"
            print(error_msg)
            if PYQT_AVAILABLE:
                self.capture_failed.emit(error_msg)
        
        finally:
            self.is_capturing = False
        
        return captured_frames
    
    def capture_frame_sequence_async(self, timestamps: List[FrameTimestamp],
                                   completion_callback: Optional[Callable[[List[CapturedFrame]], None]] = None):
        """Capture frame sequence asynchronously in a separate thread"""
        if self.is_capturing:
            print("Capture already in progress")
            return
        
        def capture_worker():
            frames = self.capture_frame_sequence(timestamps)
            if completion_callback:
                completion_callback(frames)
        
        self.capture_thread = threading.Thread(target=capture_worker, daemon=True)
        self.capture_thread.start()
    
    def cancel_capture(self):
        """Cancel ongoing frame capture"""
        if self.is_capturing:
            print("Cancelling frame capture...")
            self.should_cancel = True
            
            # Wait for capture thread to finish
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=5.0)
    
    def synchronize_with_audio(self, audio_duration: float, audio_offset: float = 0.0):
        """Synchronize frame timestamps with audio timing"""
        self.audio_sync_offset = audio_offset
        
        # Adjust frame timestamps based on audio synchronization
        for timestamp in self.frame_timestamps:
            timestamp.timestamp += audio_offset
    
    def get_capture_statistics(self) -> Dict[str, Any]:
        """Get capture performance statistics"""
        if not self.is_capturing and self.frames_captured == 0:
            return {}
        
        elapsed_time = time.time() - self.capture_start_time
        capture_fps = self.frames_captured / elapsed_time if elapsed_time > 0 else 0.0
        
        # Get rendering engine stats
        render_stats = self.rendering_engine.get_performance_stats()
        
        return {
            'frames_captured': self.frames_captured,
            'total_frames': self.total_frames,
            'elapsed_time': elapsed_time,
            'capture_fps': capture_fps,
            'progress_percent': (self.frames_captured / self.total_frames * 100.0) if self.total_frames > 0 else 0.0,
            'render_stats': render_stats,
            'audio_sync_offset': self.audio_sync_offset
        }
    
    def cleanup(self):
        """Clean up capture system resources"""
        self.cancel_capture()
        self.rendering_engine.cleanup()


# Convenience functions for common operations
def create_frame_capture_system(opengl_context: OpenGLContext) -> FrameCaptureSystem:
    """Create a frame capture system with the given OpenGL context"""
    return FrameCaptureSystem(opengl_context)


def capture_video_frames(project: Project, settings: FrameCaptureSettings,
                        opengl_context: OpenGLContext) -> List[CapturedFrame]:
    """Capture all frames for a video project"""
    capture_system = create_frame_capture_system(opengl_context)
    
    if not capture_system.initialize(project, settings):
        print("Failed to initialize frame capture system")
        return []
    
    # Get project duration
    duration = 0.0
    if project.audio_file:
        duration = project.audio_file.duration
    elif project.video_file:
        duration = project.video_file.duration
    else:
        duration = 60.0  # Default 1 minute
    
    # Generate frame timestamps
    timestamps = capture_system.generate_frame_timestamps(duration, settings.fps)
    
    # Capture frames
    frames = capture_system.capture_frame_sequence(timestamps)
    
    # Cleanup
    capture_system.cleanup()
    
    return frames


if __name__ == "__main__":
    # Test the frame capture system
    print("Testing Frame Capture System...")
    
    # This would be run with actual OpenGL context and project in production
    print("Frame capture system module loaded successfully")