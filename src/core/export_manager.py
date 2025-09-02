"""
Export Manager

Manages the video export process using the unified OpenGL export system.
Integrates with the UI and provides progress tracking and error handling.
"""

import os
import shutil
import tempfile
import time
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

try:
    from .models import Project
    from .opengl_export_renderer import OpenGLExportRenderer, ExportSettings, ExportProgress
    from .validation import ValidationResult, ValidationLevel
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from models import Project
    from opengl_export_renderer import OpenGLExportRenderer, ExportSettings, ExportProgress
    from validation import ValidationResult, ValidationLevel


class ExportStatus(Enum):
    """Export status enumeration."""
    IDLE = "idle"
    VALIDATING = "validating"
    PREPARING = "preparing"
    RENDERING = "rendering"
    ENCODING = "encoding"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportProgressInfo:
    """Detailed export progress information."""
    status: ExportStatus = ExportStatus.IDLE
    current_frame: int = 0
    total_frames: int = 0
    progress_percent: float = 0.0
    
    # Time tracking
    start_time: float = field(default_factory=time.time)
    elapsed_time: float = 0.0
    estimated_remaining: float = 0.0
    estimated_total: float = 0.0
    
    # Performance metrics
    fps: float = 0.0
    frames_per_second: float = 0.0
    
    # Status information
    current_operation: str = ""
    detailed_status: str = ""
    
    # Error information
    last_error: Optional[str] = None
    error_suggestions: List[str] = field(default_factory=list)
    
    def update_timing(self):
        """Update timing calculations."""
        current_time = time.time()
        self.elapsed_time = current_time - self.start_time
        
        # Calculate progress percentage
        if self.total_frames > 0:
            self.progress_percent = (self.current_frame / self.total_frames) * 100.0
        
        # Calculate performance metrics
        if self.current_frame > 0 and self.elapsed_time > 0:
            self.frames_per_second = self.current_frame / self.elapsed_time
            
            if self.total_frames > 0:
                remaining_frames = self.total_frames - self.current_frame
                if self.frames_per_second > 0:
                    self.estimated_remaining = remaining_frames / self.frames_per_second
                    self.estimated_total = self.total_frames / self.frames_per_second
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for signal emission."""
        return {
            'status': self.status.value,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'progress_percent': self.progress_percent,
            'elapsed_time': self.elapsed_time,
            'estimated_remaining': self.estimated_remaining,
            'estimated_total': self.estimated_total,
            'fps': self.fps,
            'frames_per_second': self.frames_per_second,
            'current_operation': self.current_operation,
            'detailed_status': self.detailed_status,
            'last_error': self.last_error,
            'error_suggestions': self.error_suggestions
        }


@dataclass
class ExportConfiguration:
    """Complete export configuration including UI settings."""
    # Video settings
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    bitrate: int = 8000  # kbps
    
    # Output settings
    output_dir: str = "./output/"
    filename: str = "karaoke_video.mp4"
    format: str = "MP4 (H.264)"
    
    # Processing options
    cleanup_temp: bool = True
    overwrite_existing: bool = True
    
    # Quality presets
    quality_preset: str = "Medium (1080p)"
    
    def to_export_settings(self) -> ExportSettings:
        """Convert to OpenGL export settings."""
        output_path = os.path.join(self.output_dir, self.filename)
        
        # Map format to codec
        codec_map = {
            "MP4 (H.264)": "libx264",
            "MP4 (H.265)": "libx265"
        }
        codec = codec_map.get(self.format, "libx264")
        
        return ExportSettings(
            output_path=output_path,
            width=self.width,
            height=self.height,
            fps=self.fps,
            bitrate=self.bitrate,
            codec=codec,
            cleanup_temp=self.cleanup_temp
        )


class ExportManager(QObject):
    """
    Manages the complete video export process.
    
    Handles validation, progress tracking, error handling, and cleanup.
    Integrates the OpenGL export renderer with the UI.
    """
    
    # Progress and status signals
    export_started = pyqtSignal()
    export_progress = pyqtSignal(dict)  # Progress information
    export_completed = pyqtSignal(str)  # Output file path
    export_failed = pyqtSignal(str)  # Error message
    export_cancelled = pyqtSignal()
    
    # Validation signals
    validation_completed = pyqtSignal(list)  # List of ValidationResult
    
    # Enhanced progress signals
    status_changed = pyqtSignal(str)  # Status updates
    detailed_progress = pyqtSignal(dict)  # Detailed progress info
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.opengl_renderer: Optional[OpenGLExportRenderer] = None
        self.current_project: Optional[Project] = None
        self.export_config: Optional[ExportConfiguration] = None
        
        # Enhanced state tracking
        self.is_exporting = False
        self.export_status = ExportStatus.IDLE
        self.temp_dir: Optional[str] = None
        self.cancel_requested = False
        
        # Enhanced progress tracking
        self.progress_info = ExportProgressInfo()
        self.progress_timer: Optional[QTimer] = None
        self.progress_update_interval = 100  # ms
        
        # Error tracking
        self.error_history: List[str] = []
        self.retry_count = 0
        self.max_retries = 3
        
        # Initialize OpenGL renderer
        self._initialize_renderer()
    
    def _initialize_renderer(self):
        """Initialize the OpenGL export renderer."""
        try:
            from .opengl_export_renderer import create_export_renderer
            self.opengl_renderer = create_export_renderer()
            
            if hasattr(self.opengl_renderer, 'progress_updated'):
                self.opengl_renderer.progress_updated.connect(self._on_progress_updated)
            if hasattr(self.opengl_renderer, 'export_completed'):
                self.opengl_renderer.export_completed.connect(self._on_export_completed)
            if hasattr(self.opengl_renderer, 'export_failed'):
                self.opengl_renderer.export_failed.connect(self._on_export_failed)
            
            print("Export renderer initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize export renderer: {e}")
            self.opengl_renderer = None
    
    def set_project(self, project: Project):
        """Set the current project for export."""
        self.current_project = project
        print(f"Project set for export: {project.name if project else 'None'}")
    
    def validate_export_requirements(self, config: ExportConfiguration) -> List[ValidationResult]:
        """Validate that all requirements for export are met."""
        results = []
        
        # Check if project is loaded
        if not self.current_project:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="No project loaded",
                suggestion="Load a project with media files before exporting"
            ))
            return results
        
        # Check required media files
        if not self.current_project.audio_file:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="No audio file in project",
                suggestion="Add an audio file to the project"
            ))
        
        if not self.current_project.video_file and not self.current_project.image_file:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="No video or image background in project",
                suggestion="Add either a video file or image background"
            ))
        
        if not self.current_project.subtitle_file or not self.current_project.subtitle_file.lines:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message="No subtitles in project",
                suggestion="Add subtitle file for karaoke text overlay"
            ))
        
        # Validate output settings
        output_dir = Path(config.output_dir)
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    message=f"Created output directory: {output_dir}",
                    suggestion=""
                ))
            except Exception as e:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    message=f"Cannot create output directory: {e}",
                    suggestion="Choose a different output directory or check permissions"
                ))
        
        # Check if output file already exists
        output_path = output_dir / config.filename
        if output_path.exists() and not config.overwrite_existing:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message=f"Output file already exists: {output_path}",
                suggestion="Enable overwrite or choose a different filename"
            ))
        
        # Check available disk space
        try:
            free_space = shutil.disk_usage(output_dir).free
            estimated_size = self._estimate_output_size(config)
            
            if free_space < estimated_size * 2:  # 2x safety margin
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    message=f"Low disk space. Available: {free_space // (1024**3)}GB, Estimated: {estimated_size // (1024**3)}GB",
                    suggestion="Free up disk space or choose a different output location"
                ))
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                message=f"Could not check disk space: {e}",
                suggestion=""
            ))
        
        # Validate FFmpeg availability
        if not self._check_ffmpeg_available():
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                message="FFmpeg not found",
                suggestion="Install FFmpeg and ensure it's in your system PATH"
            ))
        
        # Validate OpenGL renderer (allow mock export for testing)
        if not self.opengl_renderer:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                message="OpenGL export renderer not available - will use mock export",
                suggestion="Install PyQt6 and ensure OpenGL support for production use"
            ))
        
        return results
    
    def _estimate_output_size(self, config: ExportConfiguration) -> int:
        """Estimate output file size in bytes."""
        if not self.current_project:
            return 0
        
        # Get duration from project
        duration = 0.0
        if self.current_project.audio_file:
            duration = self.current_project.audio_file.duration
        elif self.current_project.video_file:
            duration = self.current_project.video_file.duration
        else:
            duration = 60.0  # Default 1 minute
        
        # Estimate size based on bitrate
        video_bits = config.bitrate * 1000 * duration  # Video bitrate in bps
        audio_bits = 128 * 1000 * duration  # Audio bitrate in bps (128 kbps default)
        total_bits = video_bits + audio_bits
        
        return int(total_bits / 8)  # Convert to bytes
    
    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available in system PATH."""
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_error_suggestions(self, error_message: str) -> List[str]:
        """Get suggested solutions for common export errors."""
        suggestions = []
        error_lower = error_message.lower()
        
        # FFmpeg related errors
        if "ffmpeg" in error_lower:
            if "not found" in error_lower or "no such file" in error_lower:
                suggestions.extend([
                    "Install FFmpeg from https://ffmpeg.org/download.html",
                    "Ensure FFmpeg is added to your system PATH",
                    "Restart the application after installing FFmpeg"
                ])
            elif "permission denied" in error_lower:
                suggestions.extend([
                    "Run the application as administrator",
                    "Check file permissions in the output directory",
                    "Ensure FFmpeg executable has proper permissions"
                ])
            elif "codec" in error_lower:
                suggestions.extend([
                    "Try a different video codec (H.264 vs H.265)",
                    "Update FFmpeg to the latest version",
                    "Check if your FFmpeg build supports the selected codec"
                ])
        
        # File system errors
        if "disk" in error_lower or "space" in error_lower:
            suggestions.extend([
                "Free up disk space on the output drive",
                "Choose a different output directory",
                "Reduce video quality settings to decrease file size"
            ])
        
        if "permission" in error_lower or "access" in error_lower:
            suggestions.extend([
                "Check write permissions for the output directory",
                "Close any applications that might be using the output file",
                "Try running the application as administrator"
            ])
        
        # Memory errors
        if "memory" in error_lower or "allocation" in error_lower:
            suggestions.extend([
                "Close other applications to free up memory",
                "Reduce video resolution or quality settings",
                "Process shorter video segments if possible"
            ])
        
        # OpenGL errors
        if "opengl" in error_lower or "gpu" in error_lower:
            suggestions.extend([
                "Update your graphics drivers",
                "Try reducing video resolution",
                "Check if your GPU supports the required OpenGL version"
            ])
        
        # Generic suggestions if no specific ones found
        if not suggestions:
            suggestions.extend([
                "Check the application logs for more details",
                "Try exporting with different quality settings",
                "Restart the application and try again",
                "Ensure all input files are accessible and not corrupted"
            ])
        
        return suggestions
    
    def _handle_export_error(self, error_message: str, context: str = ""):
        """Handle export errors with detailed logging and suggestions."""
        full_error = f"{context}: {error_message}" if context else error_message
        
        # Add to error history
        self.error_history.append(full_error)
        
        # Get suggestions
        suggestions = self._get_error_suggestions(error_message)
        
        # Update progress info
        self.progress_info.last_error = full_error
        self.progress_info.error_suggestions = suggestions
        self.progress_info.status = ExportStatus.FAILED
        
        # Log error details
        print(f"Export Error: {full_error}")
        print(f"Suggestions: {suggestions}")
        
        # Emit detailed error information
        error_details = {
            'error': full_error,
            'suggestions': suggestions,
            'context': context,
            'retry_count': self.retry_count,
            'can_retry': self.retry_count < self.max_retries
        }
        
        self.detailed_progress.emit(error_details)
        self.export_failed.emit(full_error)
    
    def _update_status(self, status: ExportStatus, operation: str = "", details: str = ""):
        """Update export status with detailed information."""
        self.export_status = status
        self.progress_info.status = status
        self.progress_info.current_operation = operation
        self.progress_info.detailed_status = details
        
        # Emit status updates
        self.status_changed.emit(status.value)
        self.detailed_progress.emit(self.progress_info.to_dict())
        
        print(f"Export Status: {status.value} - {operation} - {details}")
    
    def _start_progress_monitoring(self):
        """Start progress monitoring timer."""
        if not PYQT_AVAILABLE:
            return
        
        if self.progress_timer:
            self.progress_timer.stop()
        
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress_display)
        self.progress_timer.start(self.progress_update_interval)
    
    def _stop_progress_monitoring(self):
        """Stop progress monitoring timer."""
        if self.progress_timer:
            self.progress_timer.stop()
            self.progress_timer = None
    
    def _update_progress_display(self):
        """Update progress display with current information."""
        if not self.is_exporting:
            return
        
        # Update timing calculations
        self.progress_info.update_timing()
        
        # Emit progress updates
        self.export_progress.emit(self.progress_info.to_dict())
        self.detailed_progress.emit(self.progress_info.to_dict())
    
    def start_export(self, config: ExportConfiguration) -> bool:
        """Start the export process with the given configuration."""
        if self.is_exporting:
            print("Export already in progress")
            return False
        
        # Reset state
        self.cancel_requested = False
        self.retry_count = 0
        self.error_history.clear()
        self.progress_info = ExportProgressInfo()
        
        # Store configuration
        self.export_config = config
        
        # Update status
        self._update_status(ExportStatus.VALIDATING, "Validating export requirements", "Checking project and system requirements...")
        
        # Validate requirements
        validation_results = self.validate_export_requirements(config)
        self.validation_completed.emit(validation_results)
        
        # Check for blocking errors
        has_errors = any(r.level == ValidationLevel.ERROR for r in validation_results)
        if has_errors:
            error_messages = [r.message for r in validation_results if r.level == ValidationLevel.ERROR]
            error_text = "Export validation failed:\n" + "\n".join(error_messages)
            self._handle_export_error(error_text, "Validation")
            return False
        
        # Update status
        self._update_status(ExportStatus.PREPARING, "Setting up export", "Preparing temporary files and renderer...")
        
        # Set up export
        if not self._setup_export():
            self._handle_export_error("Failed to set up export environment", "Setup")
            return False
        
        # Calculate total frames for progress tracking
        self._calculate_total_frames()
        
        # Start export process
        try:
            self.is_exporting = True
            self.progress_info.start_time = time.time()
            
            # Start progress monitoring
            self._start_progress_monitoring()
            
            # Update status
            self._update_status(ExportStatus.RENDERING, "Starting export", "Initializing video rendering...")
            
            # Emit export started signal
            self.export_started.emit()
            
            if self.opengl_renderer and hasattr(self.opengl_renderer, 'start_export_async'):
                success = self.opengl_renderer.start_export_async()
                if not success:
                    self._handle_export_error("Failed to start OpenGL export renderer", "Renderer")
                    self.is_exporting = False
                    return False
            else:
                # Mock export for testing
                self._start_mock_export()
            
            return True
            
        except Exception as e:
            self.is_exporting = False
            self._handle_export_error(f"Export start failed: {e}", "Initialization")
            return False
    
    def _calculate_total_frames(self):
        """Calculate total number of frames for progress tracking."""
        if not self.current_project or not self.export_config:
            return
        
        # Get duration from project
        duration = 0.0
        if self.current_project.audio_file:
            duration = self.current_project.audio_file.duration
        elif self.current_project.video_file:
            duration = self.current_project.video_file.duration
        else:
            duration = 60.0  # Default 1 minute
        
        # Calculate total frames
        self.progress_info.total_frames = int(duration * self.export_config.fps)
        print(f"Calculated total frames: {self.progress_info.total_frames} (duration: {duration}s, fps: {self.export_config.fps})")
    
    def retry_export(self) -> bool:
        """Retry the export process after a failure."""
        if self.retry_count >= self.max_retries:
            self._handle_export_error(f"Maximum retry attempts ({self.max_retries}) exceeded", "Retry")
            return False
        
        if not self.export_config:
            self._handle_export_error("No export configuration available for retry", "Retry")
            return False
        
        self.retry_count += 1
        print(f"Retrying export (attempt {self.retry_count}/{self.max_retries})")
        
        # Wait a moment before retrying
        if PYQT_AVAILABLE:
            QTimer.singleShot(1000, lambda: self.start_export(self.export_config))
        else:
            time.sleep(1)
            return self.start_export(self.export_config)
        
        return True
    
    def _setup_export(self) -> bool:
        """Set up export environment and renderer."""
        if not self.current_project or not self.export_config:
            return False
        
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="karaoke_export_")
            print(f"Created temp directory: {self.temp_dir}")
            
            # Convert configuration to export settings
            export_settings = self.export_config.to_export_settings()
            
            # Set up OpenGL renderer
            if self.opengl_renderer and hasattr(self.opengl_renderer, 'setup_export'):
                success = self.opengl_renderer.setup_export(self.current_project, export_settings)
                if not success:
                    print("Failed to set up OpenGL renderer")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Export setup failed: {e}")
            return False
    
    def cancel_export(self):
        """Cancel the ongoing export process."""
        if not self.is_exporting:
            print("No export in progress to cancel")
            return
        
        print("Cancelling export...")
        self.cancel_requested = True
        
        # Update status
        self._update_status(ExportStatus.CANCELLED, "Cancelling export", "Stopping export process and cleaning up...")
        
        # Cancel OpenGL renderer
        if self.opengl_renderer and hasattr(self.opengl_renderer, 'cancel_export'):
            try:
                self.opengl_renderer.cancel_export()
                print("OpenGL renderer cancellation requested")
            except Exception as e:
                print(f"Error cancelling OpenGL renderer: {e}")
        
        # Stop progress monitoring
        self._stop_progress_monitoring()
        
        # Clean up resources
        self._cleanup_export()
        
        # Update state
        self.is_exporting = False
        self.progress_info.status = ExportStatus.CANCELLED
        
        # Emit cancellation signal
        self.export_cancelled.emit()
        self.detailed_progress.emit(self.progress_info.to_dict())
        
        print("Export cancellation completed")
    
    def force_cancel_export(self):
        """Force cancel export process (for emergency situations)."""
        print("Force cancelling export...")
        
        # Immediately stop everything
        self.cancel_requested = True
        self.is_exporting = False
        
        # Stop timers
        self._stop_progress_monitoring()
        
        # Force cleanup
        try:
            self._cleanup_export()
        except Exception as e:
            print(f"Error during force cleanup: {e}")
        
        # Update status
        self.export_status = ExportStatus.CANCELLED
        self.progress_info.status = ExportStatus.CANCELLED
        self.progress_info.detailed_status = "Export force cancelled"
        
        # Emit signals
        self.export_cancelled.emit()
        self.detailed_progress.emit(self.progress_info.to_dict())
        
        print("Force cancellation completed")
    
    def _cleanup_export(self):
        """Clean up temporary files and resources."""
        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                print(f"Failed to clean up temp directory: {e}")
            finally:
                self.temp_dir = None
    
    def _start_mock_export(self):
        """Start mock export for testing without OpenGL."""
        print("Starting mock export...")
        
        # Set up mock progress
        self.progress_info.total_frames = 100
        self.progress_info.current_frame = 0
        
        # Update status
        self._update_status(ExportStatus.RENDERING, "Mock export", "Simulating video rendering...")
        
        # Simulate export progress
        self.mock_progress = 0
        mock_timer = QTimer() if PYQT_AVAILABLE else None
        
        def update_mock_progress():
            if self.cancel_requested:
                if mock_timer:
                    mock_timer.stop()
                return
            
            self.mock_progress += 5
            self.progress_info.current_frame = self.mock_progress
            self.progress_info.update_timing()
            
            # Update status based on progress
            if self.mock_progress < 80:
                operation = f"Rendering frame {self.mock_progress}/100"
                self._update_status(ExportStatus.RENDERING, operation, f"Mock export progress: {self.mock_progress}%")
            elif self.mock_progress < 95:
                self._update_status(ExportStatus.ENCODING, "Encoding video", "Finalizing mock export...")
            else:
                self._update_status(ExportStatus.FINALIZING, "Completing export", "Saving final video file...")
            
            # Emit progress
            self.export_progress.emit(self.progress_info.to_dict())
            self.detailed_progress.emit(self.progress_info.to_dict())
            
            if self.mock_progress >= 100:
                if mock_timer:
                    mock_timer.stop()
                
                # Create mock output file for testing
                output_path = self.export_config.to_export_settings().output_path
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'w') as f:
                        f.write("Mock export file")
                except Exception as e:
                    self._handle_export_error(f"Failed to create mock output file: {e}", "Mock Export")
                    return
                
                self._on_export_completed(output_path)
        
        if mock_timer:
            mock_timer.timeout.connect(update_mock_progress)
            mock_timer.start(200)  # Update every 200ms
        else:
            # Immediate completion for non-PyQt environments
            for i in range(0, 101, 5):
                if self.cancel_requested:
                    break
                self.mock_progress = i
                update_mock_progress()
                time.sleep(0.1)
    
    def _on_progress_updated(self, progress: ExportProgress):
        """Handle progress updates from OpenGL renderer."""
        if self.cancel_requested:
            return
        
        # Update progress info
        self.progress_info.current_frame = progress.current_frame
        self.progress_info.total_frames = max(progress.total_frames, self.progress_info.total_frames)
        self.progress_info.fps = progress.fps
        
        # Update timing
        self.progress_info.update_timing()
        
        # Update status based on progress
        if progress.current_frame == 0:
            self._update_status(ExportStatus.RENDERING, "Starting render", progress.status)
        elif progress.current_frame >= self.progress_info.total_frames:
            self._update_status(ExportStatus.ENCODING, "Finalizing video", "Encoding final video file...")
        else:
            operation = f"Rendering frame {progress.current_frame}/{self.progress_info.total_frames}"
            self._update_status(ExportStatus.RENDERING, operation, progress.status)
        
        # Emit progress signals
        self.export_progress.emit(self.progress_info.to_dict())
        self.detailed_progress.emit(self.progress_info.to_dict())
    
    def _on_export_completed(self, output_path: str):
        """Handle export completion."""
        print(f"Export completed: {output_path}")
        
        # Update status
        self._update_status(ExportStatus.COMPLETED, "Export completed", f"Video saved to: {output_path}")
        
        # Update progress to 100%
        self.progress_info.current_frame = self.progress_info.total_frames
        self.progress_info.progress_percent = 100.0
        self.progress_info.update_timing()
        
        # Stop progress monitoring
        self._stop_progress_monitoring()
        
        # Update state
        self.is_exporting = False
        
        # Verify output file exists and get size
        try:
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                size_mb = file_size / (1024 * 1024)
                self.progress_info.detailed_status = f"Export completed successfully. File size: {size_mb:.1f} MB"
                print(f"Output file size: {size_mb:.1f} MB")
            else:
                self._handle_export_error(f"Output file not found: {output_path}", "Completion")
                return
        except Exception as e:
            print(f"Error checking output file: {e}")
        
        # Clean up if requested
        if self.export_config and self.export_config.cleanup_temp:
            self._cleanup_export()
        
        # Emit completion signals
        self.export_completed.emit(output_path)
        self.detailed_progress.emit(self.progress_info.to_dict())
    
    def _on_export_failed(self, error_message: str):
        """Handle export failure."""
        print(f"Export failed: {error_message}")
        
        # Stop progress monitoring
        self._stop_progress_monitoring()
        
        # Update state
        self.is_exporting = False
        
        # Clean up resources
        self._cleanup_export()
        
        # Handle error with suggestions
        self._handle_export_error(error_message, "Export Process")
    
    def get_export_status(self) -> Dict[str, Any]:
        """Get current export status information."""
        return {
            'is_exporting': self.is_exporting,
            'export_status': self.export_status.value,
            'has_project': self.current_project is not None,
            'renderer_available': self.opengl_renderer is not None,
            'temp_dir': self.temp_dir,
            'cancel_requested': self.cancel_requested,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_count': len(self.error_history),
            'progress_percent': self.progress_info.progress_percent,
            'estimated_remaining': self.progress_info.estimated_remaining
        }
    
    def get_detailed_progress(self) -> Dict[str, Any]:
        """Get detailed progress information."""
        return self.progress_info.to_dict()
    
    def get_error_history(self) -> List[str]:
        """Get history of export errors."""
        return self.error_history.copy()
    
    def clear_error_history(self):
        """Clear the error history."""
        self.error_history.clear()
        self.retry_count = 0
    
    def can_retry(self) -> bool:
        """Check if export can be retried."""
        return (not self.is_exporting and 
                self.export_config is not None and 
                self.retry_count < self.max_retries)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get export performance metrics."""
        return {
            'frames_per_second': self.progress_info.frames_per_second,
            'elapsed_time': self.progress_info.elapsed_time,
            'estimated_total': self.progress_info.estimated_total,
            'current_fps': self.progress_info.fps,
            'progress_percent': self.progress_info.progress_percent,
            'total_frames': self.progress_info.total_frames,
            'current_frame': self.progress_info.current_frame
        }
    
    def get_quality_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get available quality presets."""
        return {
            "Low (720p)": {
                "width": 1280,
                "height": 720,
                "bitrate": 4000,
                "description": "720p resolution, good for web sharing"
            },
            "Medium (1080p)": {
                "width": 1920,
                "height": 1080,
                "bitrate": 8000,
                "description": "1080p resolution, balanced quality and size"
            },
            "High (1080p HQ)": {
                "width": 1920,
                "height": 1080,
                "bitrate": 15000,
                "description": "1080p high quality, larger file size"
            },
            "4K (2160p)": {
                "width": 3840,
                "height": 2160,
                "bitrate": 25000,
                "description": "4K resolution, maximum quality"
            }
        }
    
    def apply_quality_preset(self, preset_name: str, config: ExportConfiguration) -> ExportConfiguration:
        """Apply a quality preset to the export configuration."""
        presets = self.get_quality_presets()
        
        if preset_name in presets:
            preset = presets[preset_name]
            config.width = preset["width"]
            config.height = preset["height"]
            config.bitrate = preset["bitrate"]
            config.quality_preset = preset_name
        
        return config


if __name__ == "__main__":
    print("Testing Export Manager...")
    
    try:
        # Test basic functionality
        manager = ExportManager()
        print("Export manager created successfully")
        
        # Test quality presets
        presets = manager.get_quality_presets()
        print(f"Available quality presets: {list(presets.keys())}")
        
        # Test configuration
        config = ExportConfiguration()
        config = manager.apply_quality_preset("High (1080p HQ)", config)
        print(f"Applied preset - Resolution: {config.width}x{config.height}, Bitrate: {config.bitrate}")
        
        # Test status
        status = manager.get_export_status()
        print(f"Export status: {status}")
        
        # Test enhanced features
        print(f"Can retry: {manager.can_retry()}")
        print(f"Error history count: {len(manager.get_error_history())}")
        
        # Test progress info
        progress = manager.get_detailed_progress()
        print(f"Progress status: {progress['status']}")
        
        # Test performance metrics
        metrics = manager.get_performance_metrics()
        print(f"Performance metrics: {metrics}")
        
        print("Export Manager test completed successfully")
        
    except Exception as e:
        print(f"Export Manager test failed: {e}")
        import traceback
        traceback.print_exc()