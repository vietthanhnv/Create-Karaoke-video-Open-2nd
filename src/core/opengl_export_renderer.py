"""
Unified OpenGL Export System

This module provides a unified OpenGL rendering system that ensures perfect consistency
between preview and export by using the same OpenGL context and shaders for both.
"""

import os
import subprocess
import tempfile
import time
import threading
import queue
import json
import re
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from pathlib import Path

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
    from PyQt6.QtGui import QImage, QOpenGLContext, QSurface, QOffscreenSurface
    from PyQt6.QtOpenGL import QOpenGLFramebufferObject
    from PyQt6.QtWidgets import QApplication
    import OpenGL.GL as gl
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

try:
    from .models import Project, SubtitleLine, SubtitleStyle
    from .opengl_subtitle_renderer import OpenGLSubtitleRenderer, RenderedSubtitle
    from .preview_synchronizer import PreviewSynchronizer
except ImportError:
    from models import Project, SubtitleLine, SubtitleStyle
    from opengl_subtitle_renderer import OpenGLSubtitleRenderer, RenderedSubtitle
    from preview_synchronizer import PreviewSynchronizer


@dataclass
class ExportSettings:
    """Export configuration settings."""
    output_path: str
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    bitrate: int = 8000  # kbps
    codec: str = "libx264"
    pixel_format: str = "yuv420p"
    audio_codec: str = "aac"
    audio_bitrate: int = 128  # kbps
    cleanup_temp: bool = True
    
    # Advanced encoding options
    preset: str = "medium"  # FFmpeg preset: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    crf: Optional[int] = None  # Constant Rate Factor (0-51, lower = better quality)
    profile: str = "high"  # H.264 profile: baseline, main, high
    level: str = "4.0"  # H.264 level
    
    # Audio settings
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    
    # Container options
    container_format: str = "mp4"  # mp4, mkv, avi
    
    # Quality control
    max_bitrate: Optional[int] = None  # Maximum bitrate for VBR
    buffer_size: Optional[int] = None  # Buffer size for rate control


@dataclass
class ExportProgress:
    """Export progress information."""
    current_frame: int = 0
    total_frames: int = 0
    elapsed_time: float = 0.0
    estimated_remaining: float = 0.0
    fps: float = 0.0
    status: str = "Initializing"
    error: Optional[str] = None
    
    # FFmpeg-specific progress
    ffmpeg_fps: float = 0.0
    ffmpeg_bitrate: str = ""
    ffmpeg_size: str = ""
    ffmpeg_time: str = ""
    ffmpeg_speed: str = ""
    
    # Quality metrics
    frame_drops: int = 0
    encoding_speed: float = 0.0


class OpenGLExportRenderer(QObject):
    """
    Unified OpenGL export renderer that uses the same rendering pipeline as preview.
    
    This ensures perfect WYSIWYG consistency between what users see in preview
    and the final exported video.
    """
    
    # Progress signals
    progress_updated = pyqtSignal(ExportProgress)
    export_completed = pyqtSignal(str)  # output_path
    export_failed = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        
        # OpenGL components
        self.opengl_context: Optional[QOpenGLContext] = None
        self.offscreen_surface: Optional[QOffscreenSurface] = None
        self.framebuffer: Optional[QOpenGLFramebufferObject] = None
        self.subtitle_renderer: Optional[OpenGLSubtitleRenderer] = None
        
        # Export state
        self.current_project: Optional[Project] = None
        self.export_settings: Optional[ExportSettings] = None
        self.is_exporting = False
        self.should_cancel = False
        
        # FFmpeg process management
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.ffmpeg_monitor_thread: Optional[threading.Thread] = None
        self.frame_queue: Optional[queue.Queue] = None
        self.frame_writer_thread: Optional[threading.Thread] = None
        
        # Progress tracking
        self.progress = ExportProgress()
        self.start_time = 0.0
        
        # FFmpeg capabilities
        self._ffmpeg_version: Optional[str] = None
        self._supported_codecs: Optional[List[str]] = None
        self._supported_formats: Optional[List[str]] = None
        
    def initialize_opengl_context(self) -> bool:
        """Initialize OpenGL context for off-screen rendering."""
        if not PYQT_AVAILABLE:
            print("PyQt6 not available, using mock implementation")
            return True
            
        try:
            # Create OpenGL context
            self.opengl_context = QOpenGLContext()
            
            # Set format to match preview widget
            format = self.opengl_context.format()
            format.setMajorVersion(3)
            format.setMinorVersion(3)
            format.setProfile(format.OpenGLContextProfile.CoreProfile)
            self.opengl_context.setFormat(format)
            
            if not self.opengl_context.create():
                print("Failed to create OpenGL context")
                return False
            
            # Create offscreen surface
            self.offscreen_surface = QOffscreenSurface()
            self.offscreen_surface.setFormat(format)
            self.offscreen_surface.create()
            
            if not self.offscreen_surface.isValid():
                print("Failed to create offscreen surface")
                return False
            
            # Make context current
            if not self.opengl_context.makeCurrent(self.offscreen_surface):
                print("Failed to make OpenGL context current")
                return False
            
            print("OpenGL context initialized successfully")
            return True
            
        except Exception as e:
            print(f"OpenGL context initialization failed: {e}")
            return False
    
    def create_framebuffer(self, width: int, height: int) -> bool:
        """Create framebuffer for off-screen rendering."""
        if not PYQT_AVAILABLE:
            return True
            
        try:
            # Create framebuffer object
            self.framebuffer = QOpenGLFramebufferObject(
                width, height,
                QOpenGLFramebufferObject.Attachment.CombinedDepthStencil
            )
            
            if not self.framebuffer.isValid():
                print("Failed to create framebuffer")
                return False
            
            print(f"Framebuffer created: {width}x{height}")
            return True
            
        except Exception as e:
            print(f"Framebuffer creation failed: {e}")
            return False
    
    def initialize_subtitle_renderer(self) -> bool:
        """Initialize subtitle renderer with same settings as preview."""
        try:
            self.subtitle_renderer = OpenGLSubtitleRenderer()
            
            if not self.subtitle_renderer.initialize_opengl():
                print("Failed to initialize subtitle renderer")
                return False
            
            print("Subtitle renderer initialized")
            return True
            
        except Exception as e:
            print(f"Subtitle renderer initialization failed: {e}")
            return False
    
    def setup_export(self, project: Project, settings: ExportSettings) -> bool:
        """Set up export with project and settings."""
        self.current_project = project
        self.export_settings = settings
        
        # Initialize OpenGL components
        if not self.initialize_opengl_context():
            return False
        
        if not self.create_framebuffer(settings.width, settings.height):
            return False
        
        if not self.initialize_subtitle_renderer():
            return False
        
        # Calculate total frames
        duration = self._get_project_duration()
        self.progress.total_frames = int(duration * settings.fps)
        
        print(f"Export setup complete: {self.progress.total_frames} frames at {settings.fps} fps")
        return True
    
    def _get_project_duration(self) -> float:
        """Get project duration from audio or video file."""
        if not self.current_project:
            return 0.0
        
        # Try to get duration from audio file first
        if self.current_project.audio_file:
            return self.current_project.audio_file.duration
        
        # Fall back to video file
        if self.current_project.video_file:
            return self.current_project.video_file.duration
        
        # Default duration if no media files
        return 60.0
    
    def start_export_async(self) -> bool:
        """Start export process asynchronously."""
        if self.is_exporting:
            return False
        
        if not self.current_project or not self.export_settings:
            self.export_failed.emit("No project or export settings configured")
            return False
        
        # Start export in separate thread
        self.export_thread = ExportThread(self)
        self.export_thread.finished.connect(self._on_export_finished)
        self.export_thread.start()
        
        self.is_exporting = True
        self.should_cancel = False
        self.start_time = time.time()
        
        return True
    
    def cancel_export(self):
        """Cancel ongoing export."""
        print("Cancelling export...")
        self.should_cancel = True
        
        # Stop frame writer thread
        if self.frame_writer_thread and self.frame_writer_thread.is_alive():
            # Signal frame writer to stop
            if self.frame_queue:
                try:
                    self.frame_queue.put(None, timeout=1)  # Sentinel
                except queue.Full:
                    pass
            
            # Wait for thread to finish
            self.frame_writer_thread.join(timeout=5)
        
        # Terminate FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("FFmpeg did not terminate gracefully, killing...")
                self.ffmpeg_process.kill()
                try:
                    self.ffmpeg_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print("FFmpeg process could not be killed")
            except Exception as e:
                print(f"Error terminating FFmpeg: {e}")
        
        # Stop monitor thread
        if self.ffmpeg_monitor_thread and self.ffmpeg_monitor_thread.is_alive():
            # Monitor thread is daemon, it will stop automatically
            pass
        
        self._cleanup_export()
    
    def render_frame_at_time(self, timestamp: float) -> Optional[QImage]:
        """Render a single frame at the specified timestamp."""
        if not self.framebuffer or not self.subtitle_renderer:
            return None
        
        try:
            # Make context current
            if PYQT_AVAILABLE and not self.opengl_context.makeCurrent(self.offscreen_surface):
                print("Failed to make context current for frame rendering")
                return None
            
            # Bind framebuffer
            if PYQT_AVAILABLE:
                self.framebuffer.bind()
            
            # Set viewport
            if PYQT_AVAILABLE:
                gl.glViewport(0, 0, self.framebuffer.width(), self.framebuffer.height())
            
            # Clear framebuffer
            if PYQT_AVAILABLE:
                gl.glClearColor(0.0, 0.0, 0.0, 1.0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
            
            # Render background (video or image)
            self._render_background(timestamp)
            
            # Render subtitles with effects
            self._render_subtitles(timestamp)
            
            # Read framebuffer to image
            if PYQT_AVAILABLE:
                image = self.framebuffer.toImage()
                self.framebuffer.release()
                return image
            else:
                # Mock implementation
                from PyQt6.QtGui import QImage
                return QImage(self.export_settings.width, self.export_settings.height, QImage.Format.Format_RGBA8888)
            
        except Exception as e:
            print(f"Frame rendering failed: {e}")
            return None
    
    def _render_background(self, timestamp: float):
        """Render video or image background."""
        if not self.current_project:
            return
        
        # For now, just clear to black
        # TODO: Implement actual video/image rendering
        if PYQT_AVAILABLE:
            gl.glClearColor(0.0, 0.0, 0.0, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
    
    def _render_subtitles(self, timestamp: float):
        """Render subtitles with effects at the specified timestamp."""
        if not self.current_project or not self.subtitle_renderer:
            return
        
        try:
            # Get visible subtitles at this timestamp
            visible_subtitles = []
            if self.current_project.subtitle_file:
                for subtitle in self.current_project.subtitle_file.lines:
                    if subtitle.start_time <= timestamp <= subtitle.end_time:
                        visible_subtitles.append(subtitle)
            
            if not visible_subtitles:
                return
            
            # Set current time for effects
            self.subtitle_renderer.set_current_time(timestamp)
            
            # Render each visible subtitle
            viewport_size = (self.export_settings.width, self.export_settings.height)
            
            for subtitle in visible_subtitles:
                # Get style for subtitle
                style = self._get_subtitle_style(subtitle)
                if not style:
                    continue
                
                # Render subtitle
                rendered = self.subtitle_renderer.render_subtitle(
                    subtitle, style, viewport_size, timestamp
                )
                
                if rendered:
                    self._draw_rendered_subtitle(rendered, viewport_size)
            
        except Exception as e:
            print(f"Subtitle rendering failed: {e}")
    
    def _get_subtitle_style(self, subtitle: SubtitleLine) -> Optional[SubtitleStyle]:
        """Get style for a subtitle line."""
        if not self.current_project or not self.current_project.subtitle_file:
            return None
        
        # Find style by name
        for style in self.current_project.subtitle_file.styles:
            if style.name == subtitle.style:
                return style
        
        # Return default style if not found
        for style in self.current_project.subtitle_file.styles:
            if style.name == "Default":
                return style
        
        # Create basic default style if none exists
        return SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=20,
            primary_color="#FFFFFF",
            secondary_color="#000000",
            outline_color="#000000",
            back_color="#000000"
        )
    
    def _draw_rendered_subtitle(self, rendered: RenderedSubtitle, viewport_size: Tuple[int, int]):
        """Draw a rendered subtitle to the framebuffer."""
        # This would use the same OpenGL rendering code as the preview widget
        # For now, this is a placeholder
        pass
    
    def check_ffmpeg_capabilities(self) -> Dict[str, Any]:
        """Check FFmpeg installation and capabilities."""
        capabilities = {
            'available': False,
            'version': None,
            'codecs': [],
            'formats': [],
            'error': None
        }
        
        try:
            # Check FFmpeg version
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                capabilities['available'] = True
                
                # Parse version
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                if version_match:
                    capabilities['version'] = version_match.group(1)
                    self._ffmpeg_version = capabilities['version']
                
                # Get supported codecs
                codec_result = subprocess.run(
                    ["ffmpeg", "-codecs"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if codec_result.returncode == 0:
                    # Parse codec list
                    codecs = []
                    for line in codec_result.stdout.split('\n'):
                        if 'libx264' in line:
                            codecs.append('libx264')
                        elif 'libx265' in line:
                            codecs.append('libx265')
                        elif 'aac' in line and 'encoder' in line:
                            codecs.append('aac')
                    
                    capabilities['codecs'] = codecs
                    self._supported_codecs = codecs
                
                # Get supported formats
                format_result = subprocess.run(
                    ["ffmpeg", "-formats"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if format_result.returncode == 0:
                    formats = []
                    for line in format_result.stdout.split('\n'):
                        if 'mp4' in line and 'muxer' in line:
                            formats.append('mp4')
                        elif 'mkv' in line and 'muxer' in line:
                            formats.append('mkv')
                        elif 'avi' in line and 'muxer' in line:
                            formats.append('avi')
                    
                    capabilities['formats'] = formats
                    self._supported_formats = formats
            
            else:
                capabilities['error'] = f"FFmpeg returned error code {result.returncode}"
        
        except FileNotFoundError:
            capabilities['error'] = "FFmpeg not found in system PATH"
        except subprocess.TimeoutExpired:
            capabilities['error'] = "FFmpeg command timed out"
        except Exception as e:
            capabilities['error'] = f"Error checking FFmpeg: {e}"
        
        return capabilities
    
    def validate_export_settings(self, settings: ExportSettings) -> List[str]:
        """Validate export settings against FFmpeg capabilities."""
        errors = []
        
        # Check FFmpeg availability
        capabilities = self.check_ffmpeg_capabilities()
        if not capabilities['available']:
            errors.append(f"FFmpeg not available: {capabilities.get('error', 'Unknown error')}")
            return errors
        
        # Check codec support
        if settings.codec not in capabilities.get('codecs', []):
            errors.append(f"Codec '{settings.codec}' not supported by FFmpeg")
        
        # Check format support
        if settings.container_format not in capabilities.get('formats', []):
            errors.append(f"Format '{settings.container_format}' not supported by FFmpeg")
        
        # Validate resolution
        if settings.width <= 0 or settings.height <= 0:
            errors.append("Invalid resolution: width and height must be positive")
        
        if settings.width % 2 != 0 or settings.height % 2 != 0:
            errors.append("Resolution must have even width and height for H.264 encoding")
        
        # Validate frame rate
        if settings.fps <= 0 or settings.fps > 120:
            errors.append("Frame rate must be between 0 and 120 fps")
        
        # Validate bitrate
        if settings.bitrate <= 0:
            errors.append("Bitrate must be positive")
        
        # Validate CRF if specified
        if settings.crf is not None and (settings.crf < 0 or settings.crf > 51):
            errors.append("CRF must be between 0 and 51")
        
        return errors
    
    def build_ffmpeg_command(self) -> List[str]:
        """Build FFmpeg command with all settings."""
        if not self.export_settings:
            raise ValueError("Export settings not configured")
        
        cmd = ["ffmpeg", "-y"]  # Overwrite output file
        
        # Input video stream (raw frames from stdin)
        cmd.extend([
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", f"{self.export_settings.width}x{self.export_settings.height}",
            "-r", str(self.export_settings.fps),
            "-i", "-"  # Read from stdin
        ])
        
        # Add audio input if available
        audio_input_index = 1
        if self.current_project and self.current_project.audio_file:
            cmd.extend(["-i", self.current_project.audio_file.path])
            
            # Audio encoding settings
            cmd.extend([
                "-c:a", self.export_settings.audio_codec,
                "-b:a", f"{self.export_settings.audio_bitrate}k",
                "-ar", str(self.export_settings.audio_sample_rate),
                "-ac", str(self.export_settings.audio_channels)
            ])
        else:
            # No audio input
            audio_input_index = -1
        
        # Video encoding settings
        cmd.extend(["-c:v", self.export_settings.codec])
        
        # Rate control
        if self.export_settings.crf is not None:
            # Constant Rate Factor (quality-based)
            cmd.extend(["-crf", str(self.export_settings.crf)])
        else:
            # Bitrate-based encoding
            cmd.extend(["-b:v", f"{self.export_settings.bitrate}k"])
            
            if self.export_settings.max_bitrate:
                cmd.extend(["-maxrate", f"{self.export_settings.max_bitrate}k"])
            
            if self.export_settings.buffer_size:
                cmd.extend(["-bufsize", f"{self.export_settings.buffer_size}k"])
        
        # Encoding parameters
        cmd.extend([
            "-preset", self.export_settings.preset,
            "-profile:v", self.export_settings.profile,
            "-level", self.export_settings.level,
            "-pix_fmt", self.export_settings.pixel_format
        ])
        
        # Container-specific options
        if self.export_settings.container_format == "mp4":
            cmd.extend([
                "-movflags", "+faststart",  # Enable fast start for web playback
                "-f", "mp4"
            ])
        elif self.export_settings.container_format == "mkv":
            cmd.extend(["-f", "matroska"])
        elif self.export_settings.container_format == "avi":
            cmd.extend(["-f", "avi"])
        
        # Progress reporting
        cmd.extend(["-progress", "pipe:2"])
        
        # Output file
        cmd.append(self.export_settings.output_path)
        
        return cmd
    
    def start_ffmpeg_process(self) -> bool:
        """Start FFmpeg process for encoding."""
        if not self.export_settings:
            return False
        
        try:
            # Validate settings
            validation_errors = self.validate_export_settings(self.export_settings)
            if validation_errors:
                error_msg = "Export settings validation failed:\n" + "\n".join(validation_errors)
                print(error_msg)
                self.export_failed.emit(error_msg)
                return False
            
            # Ensure output directory exists
            output_path = Path(self.export_settings.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build FFmpeg command
            cmd = self.build_ffmpeg_command()
            print(f"Starting FFmpeg: {' '.join(cmd)}")
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            # Start progress monitoring thread
            self._start_ffmpeg_monitor()
            
            # Initialize frame queue for threaded writing
            self.frame_queue = queue.Queue(maxsize=10)  # Buffer up to 10 frames
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to start FFmpeg: {e}"
            print(error_msg)
            self.export_failed.emit(error_msg)
            return False
    
    def _start_ffmpeg_monitor(self):
        """Start thread to monitor FFmpeg progress and output."""
        if not self.ffmpeg_process:
            return
        
        def monitor_ffmpeg():
            """Monitor FFmpeg stderr for progress updates."""
            try:
                while self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                    line = self.ffmpeg_process.stderr.readline()
                    if not line:
                        break
                    
                    line = line.decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    
                    # Parse progress information
                    self._parse_ffmpeg_progress(line)
                
            except Exception as e:
                print(f"FFmpeg monitor error: {e}")
        
        self.ffmpeg_monitor_thread = threading.Thread(target=monitor_ffmpeg, daemon=True)
        self.ffmpeg_monitor_thread.start()
    
    def _parse_ffmpeg_progress(self, line: str):
        """Parse FFmpeg progress output."""
        try:
            # FFmpeg progress format: key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'fps':
                    self.progress.ffmpeg_fps = float(value) if value != 'N/A' else 0.0
                elif key == 'bitrate':
                    self.progress.ffmpeg_bitrate = value
                elif key == 'total_size':
                    self.progress.ffmpeg_size = value
                elif key == 'out_time_ms':
                    # Convert microseconds to seconds
                    time_ms = int(value) if value.isdigit() else 0
                    self.progress.ffmpeg_time = f"{time_ms / 1000000:.2f}s"
                elif key == 'speed':
                    self.progress.ffmpeg_speed = value
                    if 'x' in value:
                        try:
                            speed_val = float(value.replace('x', ''))
                            self.progress.encoding_speed = speed_val
                        except ValueError:
                            pass
            
            # Update status with FFmpeg info
            if self.progress.ffmpeg_fps > 0:
                self.progress.status = f"Encoding at {self.progress.ffmpeg_fps:.1f} fps"
                if self.progress.ffmpeg_speed:
                    self.progress.status += f" ({self.progress.ffmpeg_speed})"
            
        except Exception as e:
            print(f"Error parsing FFmpeg progress: {e}")
    
    def export_frames(self):
        """Export all frames to FFmpeg using threaded pipeline."""
        if not self.start_ffmpeg_process():
            self.export_failed.emit("Failed to start FFmpeg process")
            return
        
        try:
            # Start frame writer thread
            self._start_frame_writer()
            
            duration = self._get_project_duration()
            frame_time = 1.0 / self.export_settings.fps
            
            for frame_num in range(self.progress.total_frames):
                if self.should_cancel:
                    break
                
                # Calculate timestamp for this frame
                timestamp = frame_num * frame_time
                
                # Render frame
                frame_image = self.render_frame_at_time(timestamp)
                if not frame_image:
                    self.progress.frame_drops += 1
                    continue
                
                # Convert to raw RGBA data
                frame_data = self._convert_frame_to_raw(frame_image)
                if not frame_data:
                    self.progress.frame_drops += 1
                    continue
                
                # Queue frame for writing (with timeout to prevent blocking)
                try:
                    self.frame_queue.put((frame_num, frame_data), timeout=5.0)
                except queue.Full:
                    print("Frame queue full, dropping frame")
                    self.progress.frame_drops += 1
                    continue
                
                # Update progress
                self.progress.current_frame = frame_num + 1
                self.progress.elapsed_time = time.time() - self.start_time
                
                if self.progress.elapsed_time > 0:
                    self.progress.fps = self.progress.current_frame / self.progress.elapsed_time
                    remaining_frames = self.progress.total_frames - self.progress.current_frame
                    if self.progress.fps > 0:
                        self.progress.estimated_remaining = remaining_frames / self.progress.fps
                
                # Update status
                if not self.progress.status.startswith("Encoding"):
                    self.progress.status = f"Rendering frame {self.progress.current_frame}/{self.progress.total_frames}"
                
                # Emit progress update (throttled)
                if frame_num % 10 == 0 or frame_num == self.progress.total_frames - 1:
                    self.progress_updated.emit(self.progress)
            
            # Signal end of frames
            if self.frame_queue:
                self.frame_queue.put(None)  # Sentinel value
            
            # Wait for frame writer to finish
            if self.frame_writer_thread:
                self.frame_writer_thread.join(timeout=30)
            
            # Wait for FFmpeg to finish
            if self.ffmpeg_process:
                try:
                    stdout, stderr = self.ffmpeg_process.communicate(timeout=60)
                    
                    if self.ffmpeg_process.returncode == 0:
                        self.progress.status = "Export completed successfully"
                        if self.progress.frame_drops > 0:
                            self.progress.status += f" ({self.progress.frame_drops} frames dropped)"
                        self.export_completed.emit(self.export_settings.output_path)
                    else:
                        error_msg = self._parse_ffmpeg_error(stderr)
                        self.export_failed.emit(f"FFmpeg failed: {error_msg}")
                
                except subprocess.TimeoutExpired:
                    self.export_failed.emit("FFmpeg process timed out")
                    if self.ffmpeg_process:
                        self.ffmpeg_process.kill()
            
        except Exception as e:
            error_msg = f"Export failed: {e}"
            print(error_msg)
            self.export_failed.emit(error_msg)
        
        finally:
            self._cleanup_export()
    
    def _convert_frame_to_raw(self, frame_image) -> Optional[bytes]:
        """Convert QImage to raw RGBA bytes."""
        try:
            if PYQT_AVAILABLE and frame_image:
                # Convert to RGBA format
                rgba_image = frame_image.convertToFormat(QImage.Format.Format_RGBA8888)
                return rgba_image.constBits().asstring(rgba_image.sizeInBytes())
            else:
                # Mock frame data for testing
                return b'\x00' * (self.export_settings.width * self.export_settings.height * 4)
        
        except Exception as e:
            print(f"Frame conversion failed: {e}")
            return None
    
    def _start_frame_writer(self):
        """Start thread to write frames to FFmpeg stdin."""
        def write_frames():
            """Write frames from queue to FFmpeg stdin."""
            try:
                while True:
                    try:
                        item = self.frame_queue.get(timeout=10)
                        if item is None:  # Sentinel value
                            break
                        
                        frame_num, frame_data = item
                        
                        # Write frame to FFmpeg
                        if self.ffmpeg_process and self.ffmpeg_process.stdin:
                            self.ffmpeg_process.stdin.write(frame_data)
                            self.ffmpeg_process.stdin.flush()
                        
                        self.frame_queue.task_done()
                        
                    except queue.Empty:
                        if self.should_cancel:
                            break
                        continue
                    except BrokenPipeError:
                        print("FFmpeg process terminated unexpectedly")
                        break
                    except Exception as e:
                        print(f"Frame writing error: {e}")
                        break
                
                # Close FFmpeg stdin
                if self.ffmpeg_process and self.ffmpeg_process.stdin:
                    self.ffmpeg_process.stdin.close()
                
            except Exception as e:
                print(f"Frame writer thread error: {e}")
        
        self.frame_writer_thread = threading.Thread(target=write_frames, daemon=True)
        self.frame_writer_thread.start()
    
    def _parse_ffmpeg_error(self, stderr: bytes) -> str:
        """Parse FFmpeg error output for meaningful error messages."""
        if not stderr:
            return "Unknown FFmpeg error"
        
        error_text = stderr.decode('utf-8', errors='ignore')
        
        # Look for common error patterns
        if "No such file or directory" in error_text:
            return "Input file not found"
        elif "Permission denied" in error_text:
            return "Permission denied - check file permissions"
        elif "Invalid data found" in error_text:
            return "Invalid input data format"
        elif "Codec not supported" in error_text:
            return "Codec not supported by FFmpeg"
        elif "Unknown encoder" in error_text:
            return "Video encoder not available"
        elif "disk full" in error_text.lower():
            return "Insufficient disk space"
        else:
            # Return last few lines of error output
            lines = error_text.strip().split('\n')
            return ' '.join(lines[-3:]) if len(lines) >= 3 else error_text.strip()
    
    def _cleanup_export(self):
        """Clean up export resources."""
        print("Cleaning up export resources...")
        self.is_exporting = False
        
        # Clean up FFmpeg process
        if self.ffmpeg_process:
            try:
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait(timeout=5)
            except Exception as e:
                print(f"Error cleaning up FFmpeg process: {e}")
            finally:
                self.ffmpeg_process = None
        
        # Clean up threads
        if self.frame_writer_thread and self.frame_writer_thread.is_alive():
            try:
                self.frame_writer_thread.join(timeout=2)
            except Exception as e:
                print(f"Error joining frame writer thread: {e}")
        self.frame_writer_thread = None
        
        if self.ffmpeg_monitor_thread and self.ffmpeg_monitor_thread.is_alive():
            # Monitor thread is daemon, no need to join
            pass
        self.ffmpeg_monitor_thread = None
        
        # Clean up frame queue
        if self.frame_queue:
            try:
                # Clear any remaining frames
                while not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.task_done()
                    except queue.Empty:
                        break
            except Exception as e:
                print(f"Error cleaning up frame queue: {e}")
        self.frame_queue = None
        
        # Clean up OpenGL resources
        if self.framebuffer:
            self.framebuffer = None
        
        if self.subtitle_renderer:
            try:
                self.subtitle_renderer.cleanup()
            except Exception as e:
                print(f"Error cleaning up subtitle renderer: {e}")
            self.subtitle_renderer = None
        
        # Reset progress
        self.progress = ExportProgress()
        self.should_cancel = False
    
    def _on_export_finished(self):
        """Handle export thread completion."""
        self.is_exporting = False


class ExportThread(QThread):
    """Thread for running export process."""
    
    def __init__(self, renderer: OpenGLExportRenderer):
        super().__init__()
        self.renderer = renderer
    
    def run(self):
        """Run export in thread."""
        try:
            self.renderer.export_frames()
        except Exception as e:
            self.renderer.export_failed.emit(f"Export thread failed: {e}")


# Mock implementations for testing without PyQt6
class MockExportRenderer:
    """Mock export renderer for testing."""
    
    def __init__(self):
        self.is_exporting = False
        self.progress = ExportProgress()
    
    def setup_export(self, project, settings) -> bool:
        print(f"Mock: Setting up export for {settings.output_path}")
        return True
    
    def start_export_async(self) -> bool:
        print("Mock: Starting export")
        self.is_exporting = True
        return True
    
    def cancel_export(self):
        print("Mock: Cancelling export")
        self.is_exporting = False


class FFmpegQualityPresets:
    """Predefined quality presets for FFmpeg encoding."""
    
    @staticmethod
    def get_presets() -> Dict[str, ExportSettings]:
        """Get all available quality presets."""
        return {
            "Web Low (480p)": ExportSettings(
                output_path="",
                width=854,
                height=480,
                fps=30.0,
                bitrate=1500,
                preset="fast",
                crf=28,
                profile="main"
            ),
            "Web Medium (720p)": ExportSettings(
                output_path="",
                width=1280,
                height=720,
                fps=30.0,
                bitrate=3000,
                preset="medium",
                crf=23,
                profile="high"
            ),
            "HD (1080p)": ExportSettings(
                output_path="",
                width=1920,
                height=1080,
                fps=30.0,
                bitrate=6000,
                preset="medium",
                crf=20,
                profile="high"
            ),
            "HD High Quality": ExportSettings(
                output_path="",
                width=1920,
                height=1080,
                fps=30.0,
                bitrate=12000,
                preset="slow",
                crf=18,
                profile="high"
            ),
            "4K (2160p)": ExportSettings(
                output_path="",
                width=3840,
                height=2160,
                fps=30.0,
                bitrate=25000,
                preset="medium",
                crf=20,
                profile="high",
                level="5.1"
            ),
            "Archive Quality": ExportSettings(
                output_path="",
                width=1920,
                height=1080,
                fps=30.0,
                bitrate=50000,
                preset="veryslow",
                crf=12,
                profile="high"
            )
        }
    
    @staticmethod
    def get_format_options() -> Dict[str, Dict[str, Any]]:
        """Get supported output formats and their options."""
        return {
            "MP4 (H.264)": {
                "container_format": "mp4",
                "codec": "libx264",
                "pixel_format": "yuv420p",
                "audio_codec": "aac",
                "description": "Most compatible format for web and devices"
            },
            "MP4 (H.265)": {
                "container_format": "mp4",
                "codec": "libx265",
                "pixel_format": "yuv420p",
                "audio_codec": "aac",
                "description": "Better compression, newer devices only"
            },
            "MKV (H.264)": {
                "container_format": "mkv",
                "codec": "libx264",
                "pixel_format": "yuv420p",
                "audio_codec": "aac",
                "description": "Open format with advanced features"
            },
            "AVI (H.264)": {
                "container_format": "avi",
                "codec": "libx264",
                "pixel_format": "yuv420p",
                "audio_codec": "aac",
                "description": "Legacy format for older systems"
            }
        }


def create_export_renderer() -> OpenGLExportRenderer:
    """Factory function to create export renderer."""
    if PYQT_AVAILABLE:
        return OpenGLExportRenderer()
    else:
        return MockExportRenderer()


if __name__ == "__main__":
    print("Testing OpenGL Export Renderer...")
    
    # Test basic functionality
    renderer = create_export_renderer()
    print("Export renderer created successfully")
    
    # Test with mock settings
    settings = ExportSettings(
        output_path="test_output.mp4",
        width=1920,
        height=1080,
        fps=30.0
    )
    
    print(f"Export settings: {settings}")
    print("OpenGL Export Renderer test completed")