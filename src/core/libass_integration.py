"""
Libass integration system for ASS subtitle processing and rendering.

This module provides a Python wrapper around the libass library for
parsing ASS subtitle files, extracting karaoke timing, and generating
bitmap textures for OpenGL rendering.
"""

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import logging

from .models import SubtitleFile, SubtitleLine, KaraokeTimingInfo, SubtitleStyle

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class LibassImage:
    """Represents a rendered subtitle image from libass."""
    width: int
    height: int
    stride: int
    bitmap: bytes
    dst_x: int
    dst_y: int
    color: int
    
    def to_rgba_bytes(self) -> bytes:
        """Convert libass bitmap to RGBA format for OpenGL textures."""
        # libass provides grayscale bitmap, convert to RGBA
        rgba_data = bytearray(self.width * self.height * 4)
        
        # Extract color components from libass color format
        alpha = (self.color >> 24) & 0xFF
        blue = (self.color >> 16) & 0xFF
        green = (self.color >> 8) & 0xFF
        red = self.color & 0xFF
        
        # Convert grayscale bitmap to RGBA
        for y in range(self.height):
            for x in range(self.width):
                bitmap_idx = y * self.stride + x
                rgba_idx = (y * self.width + x) * 4
                
                if bitmap_idx < len(self.bitmap):
                    intensity = self.bitmap[bitmap_idx]
                    # Apply color and alpha
                    rgba_data[rgba_idx] = int(red * intensity / 255)      # R
                    rgba_data[rgba_idx + 1] = int(green * intensity / 255)  # G
                    rgba_data[rgba_idx + 2] = int(blue * intensity / 255)   # B
                    rgba_data[rgba_idx + 3] = int(alpha * intensity / 255)  # A
        
        return bytes(rgba_data)


class LibassError(Exception):
    """Exception raised for libass-related errors."""
    pass


class LibassContext:
    """
    Wrapper for libass library context and operations.
    
    This class provides a Python interface to the libass library for
    ASS subtitle parsing, rendering, and karaoke timing extraction.
    """
    
    def __init__(self, width: int = 1920, height: int = 1080):
        """
        Initialize libass context.
        
        Args:
            width: Rendering width in pixels
            height: Rendering height in pixels
        """
        self.width = width
        self.height = height
        self.library = None
        self.renderer = None
        self.track = None
        self._libass = None
        
        # Try to load libass library
        self._load_libass()
        
        if self._libass:
            self._init_context()
    
    def _load_libass(self):
        """Load the libass shared library."""
        # Try different library names based on platform
        library_names = []
        
        if sys.platform.startswith('win'):
            library_names = ['libass.dll', 'ass.dll', 'libass-9.dll']
        elif sys.platform.startswith('darwin'):
            library_names = ['libass.dylib', 'libass.9.dylib']
        else:  # Linux and other Unix-like systems
            library_names = ['libass.so', 'libass.so.9', 'libass.so.5']
        
        # Try to find and load the library
        for lib_name in library_names:
            try:
                # First try to load from system paths
                lib_path = ctypes.util.find_library(lib_name.split('.')[0])
                if lib_path:
                    self._libass = ctypes.CDLL(lib_path)
                    logger.info(f"Loaded libass from system: {lib_path}")
                    break
                
                # Try direct loading
                self._libass = ctypes.CDLL(lib_name)
                logger.info(f"Loaded libass directly: {lib_name}")
                break
                
            except OSError:
                continue
        
        if not self._libass:
            logger.warning("Could not load libass library. Falling back to basic ASS parsing.")
            return
        
        # Define function prototypes
        self._define_function_prototypes()
    
    def _define_function_prototypes(self):
        """Define ctypes function prototypes for libass functions."""
        if not self._libass:
            return
        
        try:
            # Library management
            self._libass.ass_library_init.restype = ctypes.c_void_p
            self._libass.ass_library_done.argtypes = [ctypes.c_void_p]
            
            # Renderer management
            self._libass.ass_renderer_init.argtypes = [ctypes.c_void_p]
            self._libass.ass_renderer_init.restype = ctypes.c_void_p
            self._libass.ass_renderer_done.argtypes = [ctypes.c_void_p]
            
            # Renderer configuration
            self._libass.ass_set_frame_size.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            self._libass.ass_set_storage_size.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
            self._libass.ass_set_shaper.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._libass.ass_set_margins.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            self._libass.ass_set_use_margins.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._libass.ass_set_font_scale.argtypes = [ctypes.c_void_p, ctypes.c_double]
            
            # Font management
            self._libass.ass_set_fonts.argtypes = [
                ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
                ctypes.c_int, ctypes.c_char_p, ctypes.c_int
            ]
            
            # Track management
            self._libass.ass_new_track.argtypes = [ctypes.c_void_p]
            self._libass.ass_new_track.restype = ctypes.c_void_p
            self._libass.ass_free_track.argtypes = [ctypes.c_void_p]
            
            # Track loading
            self._libass.ass_read_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
            self._libass.ass_read_file.restype = ctypes.c_void_p
            
            # Rendering
            self._libass.ass_render_frame.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong, ctypes.POINTER(ctypes.c_int)]
            self._libass.ass_render_frame.restype = ctypes.c_void_p
            
        except AttributeError as e:
            logger.error(f"Failed to define libass function prototypes: {e}")
            self._libass = None
    
    def _init_context(self):
        """Initialize libass library, renderer, and track."""
        if not self._libass:
            return
        
        try:
            # Initialize library
            self.library = self._libass.ass_library_init()
            if not self.library:
                raise LibassError("Failed to initialize libass library")
            
            # Initialize renderer
            self.renderer = self._libass.ass_renderer_init(self.library)
            if not self.renderer:
                raise LibassError("Failed to initialize libass renderer")
            
            # Configure renderer
            self._libass.ass_set_frame_size(self.renderer, self.width, self.height)
            self._libass.ass_set_storage_size(self.renderer, self.width, self.height)
            self._libass.ass_set_shaper(self.renderer, 1)  # Enable complex text shaping
            self._libass.ass_set_margins(self.renderer, 0, 0, 0, 0)
            self._libass.ass_set_use_margins(self.renderer, 0)
            self._libass.ass_set_font_scale(self.renderer, 1.0)
            
            # Set up fonts
            self._setup_fonts()
            
            logger.info("Libass context initialized successfully")
            
        except Exception as e:
            from .error_handling import global_error_handler, LibassError as EnhancedLibassError, ErrorInfo, ErrorCategory, ErrorSeverity
            error_info = global_error_handler.handle_error(e, "libass context initialization")
            logger.error(f"Failed to initialize libass context: {error_info.message}")
            self.cleanup()
            raise EnhancedLibassError(error_info, e)
    
    def _setup_fonts(self):
        """Set up font configuration for libass."""
        if not self._libass or not self.renderer:
            return
        
        # Try to find system fonts
        font_config = None
        default_font = None
        
        # Platform-specific font paths
        if sys.platform.startswith('win'):
            font_dirs = [
                r"C:\Windows\Fonts",
                os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Fonts")
            ]
            default_font = "arial.ttf"
        elif sys.platform.startswith('darwin'):
            font_dirs = [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ]
            default_font = "Arial.ttf"
        else:  # Linux
            font_dirs = [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts")
            ]
            default_font = "DejaVuSans.ttf"
        
        # Find a default font
        font_path = None
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                potential_font = os.path.join(font_dir, default_font)
                if os.path.exists(potential_font):
                    font_path = potential_font
                    break
                
                # Try to find any TTF font
                try:
                    for file in os.listdir(font_dir):
                        if file.lower().endswith('.ttf'):
                            font_path = os.path.join(font_dir, file)
                            break
                    if font_path:
                        break
                except (OSError, PermissionError):
                    continue
        
        # Set fonts
        font_path_bytes = font_path.encode('utf-8') if font_path else None
        self._libass.ass_set_fonts(
            self.renderer,
            font_path_bytes,  # Default font
            b"Arial,sans-serif",  # Font family
            1,  # Use fontconfig
            None,  # Fontconfig config
            1   # Update fontconfig cache
        )
        
        if font_path:
            logger.info(f"Using font: {font_path}")
        else:
            logger.warning("No system fonts found, text rendering may not work properly")
    
    def load_subtitle_file(self, file_path: str) -> bool:
        """
        Load an ASS subtitle file.
        
        Args:
            file_path: Path to the .ass file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._libass or not self.library:
            logger.warning("Libass not available, cannot load subtitle file")
            return False
        
        try:
            # Free existing track
            if self.track:
                self._libass.ass_free_track(self.track)
                self.track = None
            
            # Load file
            file_path_bytes = file_path.encode('utf-8')
            self.track = self._libass.ass_read_file(self.library, file_path_bytes, None)
            
            if not self.track:
                logger.error(f"Failed to load ASS file: {file_path}")
                return False
            
            logger.info(f"Successfully loaded ASS file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading ASS file {file_path}: {e}")
            return False
    
    def render_frame(self, timestamp_ms: int) -> List[LibassImage]:
        """
        Render subtitle frame at given timestamp.
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            List of rendered subtitle images
        """
        if not self._libass or not self.renderer or not self.track:
            return []
        
        try:
            # Render frame
            detect_change = ctypes.c_int(0)
            img_ptr = self._libass.ass_render_frame(
                self.renderer, 
                self.track, 
                ctypes.c_longlong(timestamp_ms), 
                ctypes.byref(detect_change)
            )
            
            images = []
            
            # Process rendered images
            while img_ptr:
                # This is a simplified version - in reality, we'd need to define
                # the ASS_Image structure and properly parse it
                # For now, we'll create a placeholder image
                image = LibassImage(
                    width=100,
                    height=50,
                    stride=100,
                    bitmap=b'\xFF' * (100 * 50),  # White bitmap
                    dst_x=0,
                    dst_y=0,
                    color=0xFFFFFFFF
                )
                images.append(image)
                break  # For now, just return one image
            
            return images
            
        except Exception as e:
            logger.error(f"Error rendering frame at {timestamp_ms}ms: {e}")
            return []
    
    def extract_karaoke_timing(self, subtitle_file: SubtitleFile) -> List[KaraokeTimingInfo]:
        """
        Extract karaoke timing information from loaded ASS file.
        
        Args:
            subtitle_file: SubtitleFile object to extract timing from
            
        Returns:
            List of KaraokeTimingInfo objects
        """
        karaoke_data = []
        
        for line in subtitle_file.lines:
            # Check if line has actual karaoke timing tags
            if hasattr(line, 'has_karaoke_tags') and line.has_karaoke_tags and line.word_timings:
                # Extract syllable timings from word timings
                syllable_timings = []
                for word_timing in line.word_timings:
                    duration = word_timing.end_time - word_timing.start_time
                    syllable_timings.append(duration)
                
                karaoke_info = KaraokeTimingInfo(
                    start_time=line.start_time,
                    end_time=line.end_time,
                    text=line.text,
                    syllable_count=len(line.word_timings),
                    syllable_timings=syllable_timings,
                    style_overrides=""
                )
                karaoke_data.append(karaoke_info)
        
        return karaoke_data
    
    def is_available(self) -> bool:
        """Check if libass is available and properly initialized."""
        return self._libass is not None and self.library is not None and self.renderer is not None
    
    def cleanup(self):
        """Clean up libass resources."""
        if not self._libass:
            return
        
        try:
            if self.track:
                self._libass.ass_free_track(self.track)
                self.track = None
            
            if self.renderer:
                self._libass.ass_renderer_done(self.renderer)
                self.renderer = None
            
            if self.library:
                self._libass.ass_library_done(self.library)
                self.library = None
            
            logger.info("Libass context cleaned up")
            
        except Exception as e:
            logger.error(f"Error during libass cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


class LibassIntegration:
    """
    High-level interface for libass integration with the karaoke video creator.
    
    This class provides a simplified interface for ASS file processing,
    combining libass rendering with the existing subtitle parser.
    """
    
    def __init__(self, width: int = 1920, height: int = 1080):
        """
        Initialize libass integration.
        
        Args:
            width: Rendering width in pixels
            height: Rendering height in pixels
        """
        self.width = width
        self.height = height
        self.context = LibassContext(width, height)
        self.current_subtitle_file = None
    
    def load_and_parse_subtitle_file(self, file_path: str) -> Tuple[SubtitleFile, List[KaraokeTimingInfo]]:
        """
        Load and parse an ASS subtitle file with karaoke timing extraction.
        
        Args:
            file_path: Path to the .ass file
            
        Returns:
            Tuple of (SubtitleFile, List of KaraokeTimingInfo)
            
        Raises:
            LibassError: If file loading or parsing fails
        """
        from .subtitle_parser import parse_ass_file
        
        try:
            # Parse file using existing parser
            subtitle_file, errors, warnings = parse_ass_file(file_path)
            
            if errors:
                error_messages = [f"Line {e.line_number}: {e.message}" for e in errors]
                raise LibassError(f"ASS parsing errors: {'; '.join(error_messages)}")
            
            # Load file into libass if available
            if self.context.is_available():
                success = self.context.load_subtitle_file(file_path)
                if not success:
                    logger.warning("Failed to load file into libass, using parser-only mode")
            
            # Extract karaoke timing
            karaoke_data = self.context.extract_karaoke_timing(subtitle_file)
            
            # Update subtitle file with karaoke data
            subtitle_file.karaoke_data = karaoke_data
            
            self.current_subtitle_file = subtitle_file
            
            logger.info(f"Successfully loaded subtitle file: {file_path}")
            logger.info(f"Found {len(subtitle_file.lines)} subtitle lines")
            logger.info(f"Found {len(karaoke_data)} karaoke timing entries")
            
            return subtitle_file, karaoke_data
            
        except Exception as e:
            raise LibassError(f"Failed to load subtitle file {file_path}: {e}")
    
    def render_subtitle_frame(self, timestamp: float) -> List[LibassImage]:
        """
        Render subtitle frame at given timestamp.
        
        Args:
            timestamp: Timestamp in seconds
            
        Returns:
            List of rendered subtitle images
        """
        if not self.context.is_available():
            logger.warning("Libass not available for rendering")
            return []
        
        timestamp_ms = int(timestamp * 1000)
        return self.context.render_frame(timestamp_ms)
    
    def generate_bitmap_textures(self, timestamps: List[float]) -> Dict[float, List[LibassImage]]:
        """
        Generate bitmap textures for multiple timestamps.
        
        Args:
            timestamps: List of timestamps in seconds
            
        Returns:
            Dictionary mapping timestamps to rendered images
        """
        textures = {}
        
        for timestamp in timestamps:
            images = self.render_subtitle_frame(timestamp)
            if images:
                textures[timestamp] = images
        
        return textures
    
    def get_font_info(self) -> Dict[str, Any]:
        """
        Get information about available fonts.
        
        Returns:
            Dictionary with font information
        """
        # This would be expanded to query libass for font information
        return {
            "libass_available": self.context.is_available(),
            "default_font": "Arial",
            "font_scale": 1.0
        }
    
    def validate_ass_format(self, file_path: str) -> Tuple[bool, List[str]]:
        """
        Validate ASS file format and karaoke timing.
        
        Args:
            file_path: Path to the .ass file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            from .subtitle_parser import parse_ass_file
            
            _, errors, warnings = parse_ass_file(file_path)
            
            error_messages = []
            for error in errors:
                error_messages.append(f"Line {error.line_number}: {error.message}")
            
            for warning in warnings:
                error_messages.append(f"Warning - Line {warning.line_number}: {warning.message}")
            
            is_valid = len(errors) == 0
            return is_valid, error_messages
            
        except Exception as e:
            return False, [f"Validation failed: {str(e)}"]
    
    def cleanup(self):
        """Clean up resources."""
        if self.context:
            self.context.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience functions for easy integration
def create_libass_context(width: int = 1920, height: int = 1080) -> LibassContext:
    """
    Create and initialize a libass context.
    
    Args:
        width: Rendering width in pixels
        height: Rendering height in pixels
        
    Returns:
        Initialized LibassContext
    """
    return LibassContext(width, height)


def load_ass_file_with_libass(file_path: str, width: int = 1920, height: int = 1080) -> Tuple[SubtitleFile, List[KaraokeTimingInfo]]:
    """
    Load an ASS file using libass integration.
    
    Args:
        file_path: Path to the .ass file
        width: Rendering width in pixels
        height: Rendering height in pixels
        
    Returns:
        Tuple of (SubtitleFile, List of KaraokeTimingInfo)
    """
    integration = LibassIntegration(width, height)
    try:
        return integration.load_and_parse_subtitle_file(file_path)
    finally:
        integration.cleanup()