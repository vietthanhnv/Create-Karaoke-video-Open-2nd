"""
Enhanced FFmpeg Integration and Optimization

This module provides enhanced FFmpeg process management with better error handling,
optimized raw frame data streaming pipeline, improved progress tracking,
and advanced export settings configuration.
"""

import os
import subprocess
import threading
import queue
import time
import re
import json
import tempfile
import shutil
from typing import Optional, Dict, List, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QProcess, QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

import numpy as np

try:
    from .frame_capture_system import CapturedFrame, PixelFormat
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from frame_capture_system import CapturedFrame, PixelFormat


class FFmpegPreset(Enum):
    """FFmpeg encoding presets for different quality/speed tradeoffs"""
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"


class VideoCodec(Enum):
    """Supported video codecs"""
    H264 = "libx264"
    H265 = "libx265"
    VP9 = "libvpx-vp9"
    AV1 = "libaom-av1"


class AudioCodec(Enum):
    """Supported audio codecs"""
    AAC = "aac"
    MP3 = "libmp3lame"
    OPUS = "libopus"
    VORBIS = "libvorbis"


class ContainerFormat(Enum):
    """Supported container formats"""
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"


@dataclass
class FFmpegCapabilities:
    """FFmpeg installation capabilities"""
    version: str = ""
    available: bool = False
    supported_codecs: List[str] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=list)
    supported_filters: List[str] = field(default_factory=list)
    hardware_acceleration: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class EnhancedExportSettings:
    """Enhanced export settings with advanced options"""
    # Basic settings
    output_path: str = "output.mp4"
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    
    # Video codec settings
    video_codec: VideoCodec = VideoCodec.H264
    preset: FFmpegPreset = FFmpegPreset.MEDIUM
    crf: Optional[int] = 23  # Constant Rate Factor (0-51, lower = better quality)
    bitrate: Optional[int] = None  # kbps, if None uses CRF
    max_bitrate: Optional[int] = None  # Maximum bitrate for VBR
    buffer_size: Optional[int] = None  # Buffer size for rate control
    
    # Audio settings
    audio_codec: AudioCodec = AudioCodec.AAC
    audio_bitrate: int = 128  # kbps
    audio_sample_rate: int = 44100
    audio_channels: int = 2
    
    # Container and format
    container_format: ContainerFormat = ContainerFormat.MP4
    pixel_format: str = "yuv420p"
    
    # Advanced options
    two_pass_encoding: bool = False
    hardware_acceleration: Optional[str] = None  # e.g., "nvenc", "qsv", "vaapi"
    custom_filters: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    
    # Performance settings
    threads: Optional[int] = None  # Number of encoding threads
    thread_type: str = "frame"  # "frame" or "slice"
    
    # Quality settings
    tune: Optional[str] = None  # e.g., "film", "animation", "grain"
    profile: Optional[str] = None  # e.g., "baseline", "main", "high"
    level: Optional[str] = None  # e.g., "3.1", "4.0", "4.1"


@dataclass
class FFmpegProgress:
    """FFmpeg encoding progress information"""
    frame: int = 0
    fps: float = 0.0
    bitrate: str = ""
    total_size: str = ""
    out_time: str = ""
    dup_frames: int = 0
    drop_frames: int = 0
    speed: str = ""
    progress: str = ""
    
    # Calculated fields
    progress_percent: float = 0.0
    estimated_remaining: float = 0.0
    elapsed_time: float = 0.0


class EnhancedFFmpegProcessor(QObject):
    """
    Enhanced FFmpeg processor with optimized streaming and advanced features
    """
    
    # Progress signals
    progress_updated = pyqtSignal(dict)  # FFmpegProgress as dict
    encoding_started = pyqtSignal()
    encoding_completed = pyqtSignal(str)  # output_path
    encoding_failed = pyqtSignal(str)  # error_message
    
    # Status signals
    status_changed = pyqtSignal(str)  # Status message
    
    def __init__(self):
        super().__init__()
        
        # FFmpeg process management
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.ffmpeg_qprocess: Optional[QProcess] = None  # For PyQt6 integration
        
        # Threading for frame streaming
        self.frame_queue: Optional[queue.Queue] = None
        self.frame_writer_thread: Optional[threading.Thread] = None
        self.progress_monitor_thread: Optional[threading.Thread] = None
        
        # State management
        self.is_encoding = False
        self.should_cancel = False
        self.start_time = 0.0
        self.total_frames = 0
        self.current_frame = 0
        
        # Settings and capabilities
        self.export_settings: Optional[EnhancedExportSettings] = None
        self.capabilities: Optional[FFmpegCapabilities] = None
        
        # Progress tracking
        self.progress_info = FFmpegProgress()
        
        # Frame streaming optimization
        self.frame_buffer_size = 10  # Number of frames to buffer
        self.streaming_chunk_size = 1024 * 1024  # 1MB chunks
        
        # Check FFmpeg capabilities on initialization
        self._detect_capabilities()
    
    def _detect_capabilities(self) -> FFmpegCapabilities:
        """Detect FFmpeg installation and capabilities"""
        capabilities = FFmpegCapabilities()
        
        try:
            # Check FFmpeg version
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                capabilities.available = True
                
                # Parse version
                version_match = re.search(r'ffmpeg version (\S+)', result.stdout)
                if version_match:
                    capabilities.version = version_match.group(1)
                
                # Get supported codecs
                capabilities.supported_codecs = self._get_supported_codecs()
                
                # Get supported formats
                capabilities.supported_formats = self._get_supported_formats()
                
                # Get supported filters
                capabilities.supported_filters = self._get_supported_filters()
                
                # Detect hardware acceleration
                capabilities.hardware_acceleration = self._detect_hardware_acceleration()
                
            else:
                capabilities.error_message = f"FFmpeg returned error code {result.returncode}"
        
        except FileNotFoundError:
            capabilities.error_message = "FFmpeg not found in system PATH"
        except subprocess.TimeoutExpired:
            capabilities.error_message = "FFmpeg command timed out"
        except Exception as e:
            capabilities.error_message = f"Error detecting FFmpeg: {e}"
        
        self.capabilities = capabilities
        return capabilities
    
    def _get_supported_codecs(self) -> List[str]:
        """Get list of supported video and audio codecs"""
        codecs = []
        
        try:
            # Get encoders list which is more reliable
            result = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse encoder list
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('-') or line.startswith('Encoders:'):
                        continue
                    
                    # Look for common codecs we support
                    if any(codec in line for codec in ['libx264', 'libx265', 'h264_', 'h265_', 
                                                      'aac', 'libmp3lame', 'libopus', 'libvorbis']):
                        # Extract codec name (usually the first word after the type indicators)
                        parts = line.split()
                        if len(parts) >= 2:
                            # Skip the type indicators (V/A/S and encoding type)
                            codec_name = parts[1]
                            if codec_name not in codecs:
                                codecs.append(codec_name)
            
            # Add common codecs that should be available
            common_codecs = ['libx264', 'libx265', 'aac', 'libmp3lame', 'libopus']
            for codec in common_codecs:
                if codec not in codecs:
                    # Test if codec is actually available
                    if self._test_codec_availability(codec):
                        codecs.append(codec)
        
        except Exception as e:
            print(f"Error getting supported codecs: {e}")
        
        return codecs
    
    def _test_codec_availability(self, codec_name: str) -> bool:
        """Test if a specific codec is available by trying to use it"""
        try:
            # Try to get help for the codec
            result = subprocess.run(
                ["ffmpeg", "-h", f"encoder={codec_name}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _get_supported_formats(self) -> List[str]:
        """Get list of supported container formats"""
        formats = []
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-formats"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse format list
                for line in result.stdout.split('\n'):
                    # Look for muxer lines (contain 'E' or 'DE')
                    if (' E ' in line or 'DE ' in line) and line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            format_name = parts[1]
                            # Handle comma-separated formats
                            if ',' in format_name:
                                formats.extend(format_name.split(','))
                            else:
                                formats.append(format_name)
        
        except Exception as e:
            print(f"Error getting supported formats: {e}")
        
        return formats
    
    def _get_supported_filters(self) -> List[str]:
        """Get list of supported video filters"""
        filters = []
        
        try:
            result = subprocess.run(
                ["ffmpeg", "-filters"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse filter list
                for line in result.stdout.split('\n'):
                    if line.strip() and not line.startswith(' '):
                        parts = line.split()
                        if len(parts) >= 2:
                            filter_name = parts[1]
                            filters.append(filter_name)
        
        except Exception as e:
            print(f"Error getting supported filters: {e}")
        
        return filters
    
    def _detect_hardware_acceleration(self) -> List[str]:
        """Detect available hardware acceleration options"""
        hw_accel = []
        
        # Check for NVIDIA NVENC
        if self._check_codec_support("h264_nvenc"):
            hw_accel.append("nvenc")
        
        # Check for Intel Quick Sync
        if self._check_codec_support("h264_qsv"):
            hw_accel.append("qsv")
        
        # Check for VAAPI (Linux)
        if self._check_codec_support("h264_vaapi"):
            hw_accel.append("vaapi")
        
        # Check for VideoToolbox (macOS)
        if self._check_codec_support("h264_videotoolbox"):
            hw_accel.append("videotoolbox")
        
        return hw_accel
    
    def _check_codec_support(self, codec_name: str) -> bool:
        """Check if a specific codec is supported"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return codec_name in result.stdout
        
        except Exception:
            return False
    
    def get_capabilities(self) -> FFmpegCapabilities:
        """Get FFmpeg capabilities"""
        return self.capabilities or FFmpegCapabilities()
    
    def validate_settings(self, settings: EnhancedExportSettings) -> List[str]:
        """Validate export settings against FFmpeg capabilities with enhanced checks"""
        errors = []
        warnings = []
        
        if not self.capabilities or not self.capabilities.available:
            errors.append("FFmpeg is not available")
            return errors
        
        # Check video codec support
        codec_name = settings.video_codec.value
        if codec_name not in self.capabilities.supported_codecs:
            errors.append(f"Video codec '{codec_name}' is not supported")
        
        # Check audio codec support
        audio_codec_name = settings.audio_codec.value
        if audio_codec_name not in self.capabilities.supported_codecs:
            errors.append(f"Audio codec '{audio_codec_name}' is not supported")
        
        # Check container format support
        format_name = settings.container_format.value
        if format_name not in self.capabilities.supported_formats:
            errors.append(f"Container format '{format_name}' is not supported")
        
        # Check hardware acceleration
        if settings.hardware_acceleration:
            if settings.hardware_acceleration not in self.capabilities.hardware_acceleration:
                errors.append(f"Hardware acceleration '{settings.hardware_acceleration}' is not available")
        
        # Validate resolution
        if settings.width <= 0 or settings.height <= 0:
            errors.append("Invalid resolution: width and height must be positive")
        elif settings.width % 2 != 0 or settings.height % 2 != 0:
            warnings.append("Resolution should be even numbers for better codec compatibility")
        
        # Check for common resolution limits
        if settings.width > 7680 or settings.height > 4320:
            warnings.append("Very high resolution (>8K) may cause performance issues")
        elif settings.width < 64 or settings.height < 64:
            warnings.append("Very low resolution may cause encoding issues")
        
        # Validate frame rate
        if settings.fps <= 0:
            errors.append("Invalid frame rate: must be positive")
        elif settings.fps > 120:
            warnings.append("Very high frame rate (>120fps) may cause performance issues")
        elif settings.fps < 1:
            warnings.append("Very low frame rate (<1fps) may cause playback issues")
        
        # Validate CRF value
        if settings.crf is not None:
            if settings.crf < 0 or settings.crf > 51:
                errors.append("Invalid CRF value: must be between 0 and 51")
            elif settings.crf < 10:
                warnings.append("Very low CRF (<10) results in very large files")
            elif settings.crf > 35:
                warnings.append("High CRF (>35) may result in poor quality")
        
        # Validate bitrate
        if settings.bitrate is not None:
            if settings.bitrate <= 0:
                errors.append("Invalid bitrate: must be positive")
            elif settings.bitrate < 100:
                warnings.append("Very low bitrate (<100kbps) may result in poor quality")
            elif settings.bitrate > 50000:
                warnings.append("Very high bitrate (>50Mbps) may be unnecessary")
        
        # Validate audio settings
        if settings.audio_bitrate <= 0:
            errors.append("Invalid audio bitrate: must be positive")
        elif settings.audio_bitrate < 64:
            warnings.append("Low audio bitrate (<64kbps) may result in poor audio quality")
        elif settings.audio_bitrate > 320:
            warnings.append("High audio bitrate (>320kbps) may be unnecessary")
        
        if settings.audio_sample_rate not in [8000, 11025, 16000, 22050, 44100, 48000, 96000]:
            warnings.append("Non-standard audio sample rate may cause compatibility issues")
        
        if settings.audio_channels not in [1, 2, 6, 8]:
            warnings.append("Non-standard channel count may cause compatibility issues")
        
        # Check codec and container compatibility
        codec_container_compatibility = {
            VideoCodec.H264: [ContainerFormat.MP4, ContainerFormat.MKV, ContainerFormat.AVI],
            VideoCodec.H265: [ContainerFormat.MP4, ContainerFormat.MKV],
            VideoCodec.VP9: [ContainerFormat.WEBM, ContainerFormat.MKV],
            VideoCodec.AV1: [ContainerFormat.MP4, ContainerFormat.MKV, ContainerFormat.WEBM]
        }
        
        if settings.video_codec in codec_container_compatibility:
            compatible_formats = codec_container_compatibility[settings.video_codec]
            if settings.container_format not in compatible_formats:
                warnings.append(f"Video codec {settings.video_codec.value} may not be optimal for {settings.container_format.value} container")
        
        # Check preset and quality settings compatibility
        if settings.crf is not None and settings.bitrate is not None:
            warnings.append("Both CRF and bitrate specified; bitrate will take precedence")
        
        if settings.preset == FFmpegPreset.ULTRAFAST and settings.crf is not None and settings.crf < 20:
            warnings.append("Ultrafast preset with low CRF may not provide expected quality benefits")
        
        # Validate threading settings
        if settings.threads is not None:
            if settings.threads <= 0:
                errors.append("Invalid thread count: must be positive")
            elif settings.threads > 32:
                warnings.append("Very high thread count (>32) may not improve performance")
        
        # Check for potentially problematic combinations
        if settings.hardware_acceleration and settings.preset in [FFmpegPreset.VERYSLOW, FFmpegPreset.SLOWER]:
            warnings.append("Hardware acceleration with slow presets may not provide expected speed benefits")
        
        # Add warnings to errors list with warning prefix
        for warning in warnings:
            errors.append(f"Warning: {warning}")
        
        return errors
    
    def build_ffmpeg_command(self, settings: EnhancedExportSettings, 
                           input_audio: Optional[str] = None) -> List[str]:
        """Build FFmpeg command line arguments"""
        cmd = ["ffmpeg"]
        
        # Global options
        cmd.extend(["-hide_banner", "-y"])  # Hide banner, overwrite output
        
        # Threading
        if settings.threads:
            cmd.extend(["-threads", str(settings.threads)])
        
        # Hardware acceleration
        if settings.hardware_acceleration:
            if settings.hardware_acceleration == "nvenc":
                cmd.extend(["-hwaccel", "cuda"])
            elif settings.hardware_acceleration == "qsv":
                cmd.extend(["-hwaccel", "qsv"])
            elif settings.hardware_acceleration == "vaapi":
                cmd.extend(["-hwaccel", "vaapi"])
        
        # Input: raw video from stdin
        cmd.extend([
            "-f", "rawvideo",
            "-pix_fmt", "rgba",
            "-s", f"{settings.width}x{settings.height}",
            "-r", str(settings.fps),
            "-i", "pipe:0"
        ])
        
        # Input: audio file (if provided)
        if input_audio and os.path.exists(input_audio):
            cmd.extend(["-i", input_audio])
        
        # Video encoding options
        cmd.extend(["-c:v", settings.video_codec.value])
        
        # Video quality settings
        if settings.crf is not None and settings.bitrate is None:
            # Use CRF (Constant Rate Factor) for quality-based encoding
            cmd.extend(["-crf", str(settings.crf)])
        elif settings.bitrate is not None:
            # Use bitrate-based encoding
            cmd.extend(["-b:v", f"{settings.bitrate}k"])
            
            if settings.max_bitrate:
                cmd.extend(["-maxrate", f"{settings.max_bitrate}k"])
            
            if settings.buffer_size:
                cmd.extend(["-bufsize", f"{settings.buffer_size}k"])
        
        # Preset and tuning
        cmd.extend(["-preset", settings.preset.value])
        
        if settings.tune:
            cmd.extend(["-tune", settings.tune])
        
        if settings.profile:
            cmd.extend(["-profile:v", settings.profile])
        
        if settings.level:
            cmd.extend(["-level", settings.level])
        
        # Pixel format
        cmd.extend(["-pix_fmt", settings.pixel_format])
        
        # Audio encoding (if audio input is provided)
        if input_audio and os.path.exists(input_audio):
            cmd.extend([
                "-c:a", settings.audio_codec.value,
                "-b:a", f"{settings.audio_bitrate}k",
                "-ar", str(settings.audio_sample_rate),
                "-ac", str(settings.audio_channels)
            ])
        else:
            # No audio
            cmd.extend(["-an"])
        
        # Custom filters
        if settings.custom_filters:
            filter_string = ",".join(settings.custom_filters)
            cmd.extend(["-vf", filter_string])
        
        # Metadata
        for key, value in settings.metadata.items():
            cmd.extend(["-metadata", f"{key}={value}"])
        
        # Output format
        cmd.extend(["-f", settings.container_format.value])
        
        # Progress reporting
        cmd.extend(["-progress", "pipe:2"])
        
        # Output file
        cmd.append(settings.output_path)
        
        return cmd
    
    def start_encoding(self, settings: EnhancedExportSettings, 
                      frame_source: Callable[[], Optional[CapturedFrame]],
                      total_frames: int,
                      input_audio: Optional[str] = None) -> bool:
        """Start FFmpeg encoding process with frame streaming"""
        
        if self.is_encoding:
            print("Encoding already in progress")
            return False
        
        # Validate settings
        validation_errors = self.validate_settings(settings)
        if validation_errors:
            error_msg = "Settings validation failed:\n" + "\n".join(validation_errors)
            self.encoding_failed.emit(error_msg)
            return False
        
        self.export_settings = settings
        self.total_frames = total_frames
        self.current_frame = 0
        self.should_cancel = False
        self.start_time = time.time()
        
        try:
            # Build FFmpeg command
            cmd = self.build_ffmpeg_command(settings, input_audio)
            print(f"FFmpeg command: {' '.join(cmd)}")
            
            # Start FFmpeg process
            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered for real-time streaming
            )
            
            # Create frame queue for streaming
            self.frame_queue = queue.Queue(maxsize=self.frame_buffer_size)
            
            # Start frame writer thread
            self.frame_writer_thread = threading.Thread(
                target=self._frame_writer_worker,
                args=(frame_source,),
                daemon=True
            )
            
            # Start progress monitor thread
            self.progress_monitor_thread = threading.Thread(
                target=self._progress_monitor_worker,
                daemon=True
            )
            
            self.is_encoding = True
            
            # Start threads
            self.frame_writer_thread.start()
            self.progress_monitor_thread.start()
            
            # Emit started signal
            if PYQT_AVAILABLE:
                self.encoding_started.emit()
            
            print("FFmpeg encoding started")
            return True
            
        except Exception as e:
            error_msg = f"Failed to start FFmpeg encoding: {e}"
            print(error_msg)
            if PYQT_AVAILABLE:
                self.encoding_failed.emit(error_msg)
            return False
    
    def _frame_writer_worker(self, frame_source: Callable[[], Optional[CapturedFrame]]):
        """Worker thread for writing frames to FFmpeg stdin with optimized streaming"""
        try:
            frame_count = 0
            consecutive_failures = 0
            max_consecutive_failures = 5
            write_buffer = bytearray()
            buffer_flush_threshold = self.streaming_chunk_size
            
            while not self.should_cancel and frame_count < self.total_frames:
                try:
                    # Get next frame
                    frame = frame_source()
                    
                    if frame is None:
                        print(f"No more frames available at frame {frame_count}")
                        break
                    
                    # Convert frame data to the format expected by FFmpeg
                    frame_data = self._prepare_frame_for_ffmpeg(frame)
                    
                    if frame_data is not None:
                        # Add frame data to buffer for optimized streaming
                        write_buffer.extend(frame_data)
                        frame_count += 1
                        self.current_frame = frame_count
                        consecutive_failures = 0  # Reset failure counter
                        
                        # Flush buffer when it reaches threshold or on last frame
                        if len(write_buffer) >= buffer_flush_threshold or frame_count >= self.total_frames:
                            try:
                                self.ffmpeg_process.stdin.write(write_buffer)
                                self.ffmpeg_process.stdin.flush()
                                write_buffer.clear()
                                
                            except BrokenPipeError:
                                print("FFmpeg process closed stdin pipe")
                                break
                            except OSError as e:
                                if e.errno == 32:  # Broken pipe
                                    print("FFmpeg process terminated unexpectedly")
                                    break
                                else:
                                    raise
                        
                        # Update progress less frequently for better performance
                        if frame_count % 30 == 0:  # Update every 30 frames
                            progress_percent = (frame_count / self.total_frames) * 100
                            print(f"Streamed frame {frame_count}/{self.total_frames} ({progress_percent:.1f}%)")
                        
                    else:
                        consecutive_failures += 1
                        print(f"Failed to prepare frame {frame_count} for FFmpeg (failure {consecutive_failures})")
                        
                        if consecutive_failures >= max_consecutive_failures:
                            error_msg = f"Too many consecutive frame preparation failures ({consecutive_failures})"
                            print(error_msg)
                            if PYQT_AVAILABLE:
                                self.encoding_failed.emit(error_msg)
                            break
                
                except Exception as e:
                    consecutive_failures += 1
                    print(f"Error processing frame {frame_count}: {e}")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        error_msg = f"Too many consecutive frame processing errors: {e}"
                        print(error_msg)
                        if PYQT_AVAILABLE:
                            self.encoding_failed.emit(error_msg)
                        break
            
            # Flush any remaining data in buffer
            if write_buffer and self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    self.ffmpeg_process.stdin.write(write_buffer)
                    self.ffmpeg_process.stdin.flush()
                except Exception as e:
                    print(f"Error flushing final buffer: {e}")
            
            # Close stdin to signal end of input
            if self.ffmpeg_process and self.ffmpeg_process.stdin:
                try:
                    self.ffmpeg_process.stdin.close()
                except Exception as e:
                    print(f"Error closing FFmpeg stdin: {e}")
            
            print(f"Frame writer completed: {frame_count} frames written")
            
        except Exception as e:
            error_msg = f"Frame writer thread error: {e}"
            print(error_msg)
            if PYQT_AVAILABLE:
                self.encoding_failed.emit(f"Frame writing failed: {e}")
    
    def _prepare_frame_for_ffmpeg(self, frame: CapturedFrame) -> Optional[bytes]:
        """Prepare frame data for FFmpeg input"""
        try:
            # Ensure frame data is in the correct format (RGBA)
            if frame.pixel_format == PixelFormat.RGBA8:
                # Frame is already in RGBA format
                frame_data = frame.data
            else:
                # Convert to RGBA if needed
                print(f"Warning: Frame format {frame.pixel_format} may need conversion")
                frame_data = frame.data
            
            # Ensure data is contiguous and in the right shape
            if frame_data.ndim == 3:
                # Flatten to 1D array for FFmpeg
                frame_bytes = frame_data.astype(np.uint8).tobytes()
            else:
                # Data is already flattened
                frame_bytes = frame_data.astype(np.uint8).tobytes()
            
            return frame_bytes
            
        except Exception as e:
            print(f"Error preparing frame for FFmpeg: {e}")
            return None
    
    def _progress_monitor_worker(self):
        """Worker thread for monitoring FFmpeg progress with enhanced stderr parsing"""
        try:
            if not self.ffmpeg_process or not self.ffmpeg_process.stderr:
                return
            
            stderr_buffer = ""
            error_lines = []
            warning_lines = []
            
            # Read progress from FFmpeg stderr
            for line in iter(self.ffmpeg_process.stderr.readline, b''):
                if self.should_cancel:
                    break
                
                try:
                    line_str = line.decode('utf-8', errors='replace').strip()
                    
                    if line_str:
                        # Collect stderr output for error analysis
                        stderr_buffer += line_str + "\n"
                        
                        # Categorize different types of output
                        if line_str.startswith('frame=') or '=' in line_str:
                            # Progress information
                            self._parse_progress_line(line_str)
                        elif any(keyword in line_str.lower() for keyword in ['error', 'failed', 'cannot', 'invalid']):
                            # Error messages
                            error_lines.append(line_str)
                            print(f"FFmpeg Error: {line_str}")
                        elif any(keyword in line_str.lower() for keyword in ['warning', 'deprecated']):
                            # Warning messages
                            warning_lines.append(line_str)
                            print(f"FFmpeg Warning: {line_str}")
                        elif 'configuration:' in line_str.lower():
                            # Configuration info (usually at start)
                            continue
                        elif line_str.startswith('Input #') or line_str.startswith('Output #'):
                            # Stream information
                            print(f"FFmpeg Info: {line_str}")
                        elif 'Stream mapping:' in line_str:
                            # Stream mapping info
                            print(f"FFmpeg Info: {line_str}")
                        
                except UnicodeDecodeError:
                    # Skip lines that can't be decoded
                    continue
                except Exception as e:
                    print(f"Error parsing progress line: {e}")
            
            # Wait for process to complete
            if self.ffmpeg_process:
                return_code = self.ffmpeg_process.wait()
                
                if return_code == 0 and not self.should_cancel:
                    print("FFmpeg encoding completed successfully")
                    if warning_lines:
                        print(f"Encoding completed with {len(warning_lines)} warnings")
                    if PYQT_AVAILABLE:
                        self.encoding_completed.emit(self.export_settings.output_path)
                elif self.should_cancel:
                    print("FFmpeg encoding was cancelled")
                else:
                    # Analyze error output for better error reporting
                    error_msg = self._analyze_ffmpeg_errors(return_code, error_lines, stderr_buffer)
                    print(error_msg)
                    if PYQT_AVAILABLE:
                        self.encoding_failed.emit(error_msg)
            
        except Exception as e:
            error_msg = f"Progress monitor thread error: {e}"
            print(error_msg)
            if PYQT_AVAILABLE:
                self.encoding_failed.emit(f"Progress monitoring failed: {e}")
        
        finally:
            self.is_encoding = False
    
    def _analyze_ffmpeg_errors(self, return_code: int, error_lines: List[str], stderr_output: str) -> str:
        """Analyze FFmpeg errors and provide helpful error messages"""
        if return_code == 0:
            return "Encoding completed successfully"
        
        # Common error patterns and their explanations
        error_patterns = {
            'No such file or directory': 'Input file not found or output directory does not exist',
            'Permission denied': 'Insufficient permissions to read input or write output file',
            'Invalid data found': 'Input file is corrupted or in an unsupported format',
            'Encoder not found': 'Requested video/audio encoder is not available',
            'Unknown encoder': 'Specified encoder is not supported by this FFmpeg build',
            'Invalid argument': 'Invalid encoding parameters or command line arguments',
            'Conversion failed': 'General encoding failure, check input format and parameters',
            'No space left on device': 'Insufficient disk space for output file',
            'Broken pipe': 'Input stream was interrupted or closed unexpectedly',
            'Protocol not found': 'Network protocol not supported (for streaming)',
            'Server returned 404': 'Remote file not found (for network inputs)',
            'Connection refused': 'Cannot connect to remote server (for streaming)',
            'Immediate exit requested': 'FFmpeg was terminated by user or system'
        }
        
        # Look for specific error patterns
        for pattern, explanation in error_patterns.items():
            if any(pattern.lower() in line.lower() for line in error_lines):
                return f"FFmpeg encoding failed (code {return_code}): {explanation}"
        
        # Check for codec-specific errors
        if any('codec' in line.lower() for line in error_lines):
            return f"FFmpeg encoding failed (code {return_code}): Codec-related error. Check that the specified video/audio codecs are supported."
        
        # Check for format-specific errors
        if any('format' in line.lower() for line in error_lines):
            return f"FFmpeg encoding failed (code {return_code}): Format-related error. Check input file format and output container compatibility."
        
        # Generic error with the most relevant error line
        if error_lines:
            most_relevant_error = error_lines[-1]  # Usually the last error is most relevant
            return f"FFmpeg encoding failed (code {return_code}): {most_relevant_error}"
        
        # Fallback error message
        return f"FFmpeg encoding failed with return code {return_code}. Check FFmpeg output for details."
    
    def _parse_progress_line(self, line: str):
        """Parse FFmpeg progress line and update progress info"""
        try:
            # FFmpeg progress format: key=value
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Update progress info based on key
                if key == 'frame':
                    self.progress_info.frame = int(value)
                elif key == 'fps':
                    self.progress_info.fps = float(value)
                elif key == 'bitrate':
                    self.progress_info.bitrate = value
                elif key == 'total_size':
                    self.progress_info.total_size = value
                elif key == 'out_time':
                    self.progress_info.out_time = value
                elif key == 'dup_frames':
                    self.progress_info.dup_frames = int(value)
                elif key == 'drop_frames':
                    self.progress_info.drop_frames = int(value)
                elif key == 'speed':
                    self.progress_info.speed = value
                elif key == 'progress':
                    self.progress_info.progress = value
                
                # Calculate derived values
                if self.total_frames > 0:
                    self.progress_info.progress_percent = (self.progress_info.frame / self.total_frames) * 100
                
                self.progress_info.elapsed_time = time.time() - self.start_time
                
                # Estimate remaining time
                if self.progress_info.frame > 0 and self.total_frames > 0:
                    frames_remaining = self.total_frames - self.progress_info.frame
                    if self.progress_info.fps > 0:
                        self.progress_info.estimated_remaining = frames_remaining / self.progress_info.fps
                
                # Emit progress update
                if PYQT_AVAILABLE:
                    progress_dict = {
                        'frame': self.progress_info.frame,
                        'fps': self.progress_info.fps,
                        'bitrate': self.progress_info.bitrate,
                        'total_size': self.progress_info.total_size,
                        'out_time': self.progress_info.out_time,
                        'speed': self.progress_info.speed,
                        'progress_percent': self.progress_info.progress_percent,
                        'estimated_remaining': self.progress_info.estimated_remaining,
                        'elapsed_time': self.progress_info.elapsed_time
                    }
                    self.progress_updated.emit(progress_dict)
        
        except Exception as e:
            print(f"Error parsing progress line '{line}': {e}")
    
    def cancel_encoding(self):
        """Cancel ongoing encoding process"""
        if not self.is_encoding:
            return
        
        print("Cancelling FFmpeg encoding...")
        self.should_cancel = True
        
        # Terminate FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                
                # Wait for graceful termination
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print("FFmpeg did not terminate gracefully, killing...")
                    self.ffmpeg_process.kill()
                    try:
                        self.ffmpeg_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        print("FFmpeg process could not be killed")
                
            except Exception as e:
                print(f"Error terminating FFmpeg process: {e}")
        
        # Wait for threads to finish
        if self.frame_writer_thread and self.frame_writer_thread.is_alive():
            self.frame_writer_thread.join(timeout=5)
        
        if self.progress_monitor_thread and self.progress_monitor_thread.is_alive():
            self.progress_monitor_thread.join(timeout=5)
        
        self.is_encoding = False
        print("FFmpeg encoding cancelled")
    
    def get_progress_info(self) -> FFmpegProgress:
        """Get current progress information"""
        return self.progress_info
    
    def cleanup(self):
        """Clean up resources"""
        if self.is_encoding:
            self.cancel_encoding()
        
        # Clear queues
        if self.frame_queue:
            try:
                while not self.frame_queue.empty():
                    self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        
        # Reset state
        self.ffmpeg_process = None
        self.frame_queue = None
        self.frame_writer_thread = None
        self.progress_monitor_thread = None


# Convenience functions
def create_enhanced_ffmpeg_processor() -> EnhancedFFmpegProcessor:
    """Create an enhanced FFmpeg processor"""
    return EnhancedFFmpegProcessor()


def get_ffmpeg_capabilities() -> FFmpegCapabilities:
    """Get FFmpeg capabilities"""
    processor = EnhancedFFmpegProcessor()
    return processor.get_capabilities()


def create_optimized_export_settings(
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    quality: str = "high",
    hardware_acceleration: Optional[str] = None
) -> EnhancedExportSettings:
    """Create optimized export settings for different quality levels"""
    
    settings = EnhancedExportSettings(
        output_path=output_path,
        width=width,
        height=height,
        fps=fps,
        hardware_acceleration=hardware_acceleration
    )
    
    # Optimize settings based on quality level
    if quality == "high":
        settings.crf = 18
        settings.preset = FFmpegPreset.SLOW
        settings.audio_bitrate = 192
        settings.tune = "film"
        settings.profile = "high"
    elif quality == "medium":
        settings.crf = 23
        settings.preset = FFmpegPreset.MEDIUM
        settings.audio_bitrate = 128
        settings.profile = "main"
    elif quality == "low":
        settings.crf = 28
        settings.preset = FFmpegPreset.FAST
        settings.audio_bitrate = 96
        settings.profile = "baseline"
    elif quality == "ultrafast":
        settings.bitrate = 2000  # Use bitrate instead of CRF for speed
        settings.crf = None
        settings.preset = FFmpegPreset.ULTRAFAST
        settings.audio_bitrate = 128
        settings.profile = "baseline"
    elif quality == "lossless":
        settings.crf = 0
        settings.preset = FFmpegPreset.MEDIUM
        settings.audio_bitrate = 320
        settings.pixel_format = "yuv444p"
    
    # Adjust for hardware acceleration
    if hardware_acceleration:
        if hardware_acceleration == "nvenc":
            settings.preset = FFmpegPreset.FAST  # NVENC presets are different
        elif hardware_acceleration in ["qsv", "vaapi"]:
            settings.preset = FFmpegPreset.MEDIUM
    
    return settings


def create_web_optimized_settings(
    output_path: str,
    width: int = 1280,
    height: int = 720,
    fps: float = 30.0
) -> EnhancedExportSettings:
    """Create web-optimized export settings"""
    settings = EnhancedExportSettings(
        output_path=output_path,
        width=width,
        height=height,
        fps=fps,
        video_codec=VideoCodec.H264,
        container_format=ContainerFormat.MP4,
        crf=23,
        preset=FFmpegPreset.MEDIUM,
        profile="main",
        level="3.1",
        pixel_format="yuv420p",
        audio_codec=AudioCodec.AAC,
        audio_bitrate=128,
        audio_sample_rate=44100,
        audio_channels=2
    )
    
    # Add web-specific metadata
    settings.metadata = {
        "title": "Web Video",
        "encoder": "Enhanced FFmpeg Integration"
    }
    
    return settings


def create_mobile_optimized_settings(
    output_path: str,
    width: int = 854,
    height: int = 480,
    fps: float = 30.0
) -> EnhancedExportSettings:
    """Create mobile-optimized export settings"""
    settings = EnhancedExportSettings(
        output_path=output_path,
        width=width,
        height=height,
        fps=fps,
        video_codec=VideoCodec.H264,
        container_format=ContainerFormat.MP4,
        crf=26,
        preset=FFmpegPreset.FAST,
        profile="baseline",
        level="3.0",
        pixel_format="yuv420p",
        audio_codec=AudioCodec.AAC,
        audio_bitrate=96,
        audio_sample_rate=44100,
        audio_channels=2
    )
    
    return settings


@dataclass
class BatchExportJob:
    """Individual job in a batch export operation"""
    job_id: str
    settings: EnhancedExportSettings
    frame_source: Callable[[], Optional[CapturedFrame]]
    total_frames: int
    input_audio: Optional[str] = None
    status: str = "pending"  # "pending", "running", "completed", "failed", "cancelled"
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    progress_percent: float = 0.0


class BatchFFmpegProcessor(QObject):
    """
    Batch processing system for multiple FFmpeg encoding jobs
    """
    
    # Batch progress signals
    batch_started = pyqtSignal(int)  # total_jobs
    batch_completed = pyqtSignal()
    batch_failed = pyqtSignal(str)  # error_message
    
    # Job progress signals
    job_started = pyqtSignal(str)  # job_id
    job_completed = pyqtSignal(str)  # job_id
    job_failed = pyqtSignal(str, str)  # job_id, error_message
    job_progress = pyqtSignal(str, dict)  # job_id, progress_dict
    
    # Overall progress
    overall_progress = pyqtSignal(dict)  # overall progress info
    
    def __init__(self, max_concurrent_jobs: int = 1):
        super().__init__()
        
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: List[BatchExportJob] = []
        self.active_processors: Dict[str, EnhancedFFmpegProcessor] = {}
        self.is_processing = False
        self.should_cancel = False
        
        # Statistics
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.cancelled_jobs = 0
        
        # Timing
        self.batch_start_time = 0.0
        self.batch_end_time = 0.0
    
    def add_job(self, job: BatchExportJob):
        """Add a job to the batch queue"""
        if self.is_processing:
            raise RuntimeError("Cannot add jobs while batch is processing")
        
        self.jobs.append(job)
        print(f"Added job {job.job_id} to batch queue")
    
    def add_export_job(self, job_id: str, settings: EnhancedExportSettings,
                      frame_source: Callable[[], Optional[CapturedFrame]],
                      total_frames: int, input_audio: Optional[str] = None) -> BatchExportJob:
        """Convenience method to add an export job"""
        job = BatchExportJob(
            job_id=job_id,
            settings=settings,
            frame_source=frame_source,
            total_frames=total_frames,
            input_audio=input_audio
        )
        self.add_job(job)
        return job
    
    def start_batch_processing(self) -> bool:
        """Start processing all jobs in the batch"""
        if self.is_processing:
            print("Batch processing already in progress")
            return False
        
        if not self.jobs:
            print("No jobs to process")
            return False
        
        print(f"Starting batch processing of {len(self.jobs)} jobs")
        
        self.is_processing = True
        self.should_cancel = False
        self.total_jobs = len(self.jobs)
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.cancelled_jobs = 0
        self.batch_start_time = time.time()
        
        # Emit batch started signal
        if PYQT_AVAILABLE:
            self.batch_started.emit(self.total_jobs)
        
        # Start processing jobs
        self._process_next_jobs()
        
        return True
    
    def _process_next_jobs(self):
        """Process the next available jobs up to max_concurrent_jobs"""
        # Find pending jobs
        pending_jobs = [job for job in self.jobs if job.status == "pending"]
        
        # Calculate how many new jobs we can start
        available_slots = self.max_concurrent_jobs - len(self.active_processors)
        jobs_to_start = min(available_slots, len(pending_jobs))
        
        # Start new jobs
        for i in range(jobs_to_start):
            job = pending_jobs[i]
            self._start_job(job)
        
        # Check if batch is complete
        if not self.active_processors and not pending_jobs:
            self._complete_batch()
    
    def _start_job(self, job: BatchExportJob):
        """Start processing a single job"""
        print(f"Starting job {job.job_id}")
        
        # Create processor for this job
        processor = EnhancedFFmpegProcessor()
        
        # Connect signals
        processor.encoding_started.connect(lambda: self._on_job_started(job.job_id))
        processor.encoding_completed.connect(lambda path: self._on_job_completed(job.job_id, path))
        processor.encoding_failed.connect(lambda error: self._on_job_failed(job.job_id, error))
        processor.progress_updated.connect(lambda progress: self._on_job_progress(job.job_id, progress))
        
        # Store processor
        self.active_processors[job.job_id] = processor
        
        # Update job status
        job.status = "running"
        job.start_time = time.time()
        
        # Start encoding
        success = processor.start_encoding(
            job.settings,
            job.frame_source,
            job.total_frames,
            job.input_audio
        )
        
        if not success:
            self._on_job_failed(job.job_id, "Failed to start encoding")
    
    def _on_job_started(self, job_id: str):
        """Handle job started event"""
        print(f"Job {job_id} started")
        if PYQT_AVAILABLE:
            self.job_started.emit(job_id)
    
    def _on_job_completed(self, job_id: str, output_path: str):
        """Handle job completed event"""
        print(f"Job {job_id} completed: {output_path}")
        
        # Find and update job
        job = self._find_job(job_id)
        if job:
            job.status = "completed"
            job.end_time = time.time()
            job.progress_percent = 100.0
        
        # Remove processor
        if job_id in self.active_processors:
            del self.active_processors[job_id]
        
        self.completed_jobs += 1
        
        # Emit signals
        if PYQT_AVAILABLE:
            self.job_completed.emit(job_id)
            self._emit_overall_progress()
        
        # Process next jobs
        if not self.should_cancel:
            self._process_next_jobs()
    
    def _on_job_failed(self, job_id: str, error_message: str):
        """Handle job failed event"""
        print(f"Job {job_id} failed: {error_message}")
        
        # Find and update job
        job = self._find_job(job_id)
        if job:
            job.status = "failed"
            job.end_time = time.time()
            job.error_message = error_message
        
        # Remove processor
        if job_id in self.active_processors:
            del self.active_processors[job_id]
        
        self.failed_jobs += 1
        
        # Emit signals
        if PYQT_AVAILABLE:
            self.job_failed.emit(job_id, error_message)
            self._emit_overall_progress()
        
        # Process next jobs
        if not self.should_cancel:
            self._process_next_jobs()
    
    def _on_job_progress(self, job_id: str, progress_dict: dict):
        """Handle job progress update"""
        # Update job progress
        job = self._find_job(job_id)
        if job:
            job.progress_percent = progress_dict.get('progress_percent', 0.0)
        
        # Emit signals
        if PYQT_AVAILABLE:
            self.job_progress.emit(job_id, progress_dict)
            self._emit_overall_progress()
    
    def _emit_overall_progress(self):
        """Emit overall batch progress"""
        if not PYQT_AVAILABLE:
            return
        
        # Calculate overall progress
        total_progress = 0.0
        for job in self.jobs:
            total_progress += job.progress_percent
        
        overall_percent = total_progress / len(self.jobs) if self.jobs else 0.0
        
        elapsed_time = time.time() - self.batch_start_time
        
        # Estimate remaining time
        estimated_remaining = 0.0
        if overall_percent > 0:
            estimated_total_time = elapsed_time / (overall_percent / 100.0)
            estimated_remaining = max(0, estimated_total_time - elapsed_time)
        
        progress_info = {
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'active_jobs': len(self.active_processors),
            'overall_percent': overall_percent,
            'elapsed_time': elapsed_time,
            'estimated_remaining': estimated_remaining
        }
        
        self.overall_progress.emit(progress_info)
    
    def _find_job(self, job_id: str) -> Optional[BatchExportJob]:
        """Find a job by ID"""
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        return None
    
    def _complete_batch(self):
        """Complete the batch processing"""
        self.is_processing = False
        self.batch_end_time = time.time()
        
        total_time = self.batch_end_time - self.batch_start_time
        
        print(f"Batch processing completed in {total_time:.2f} seconds")
        print(f"Completed: {self.completed_jobs}, Failed: {self.failed_jobs}, Cancelled: {self.cancelled_jobs}")
        
        if PYQT_AVAILABLE:
            if self.failed_jobs == 0 and self.cancelled_jobs == 0:
                self.batch_completed.emit()
            else:
                error_msg = f"Batch completed with {self.failed_jobs} failures and {self.cancelled_jobs} cancellations"
                self.batch_failed.emit(error_msg)
    
    def cancel_batch(self):
        """Cancel all jobs in the batch"""
        print("Cancelling batch processing...")
        self.should_cancel = True
        
        # Cancel all active processors
        for job_id, processor in self.active_processors.items():
            processor.cancel_encoding()
            
            # Update job status
            job = self._find_job(job_id)
            if job and job.status == "running":
                job.status = "cancelled"
                job.end_time = time.time()
                self.cancelled_jobs += 1
        
        # Mark pending jobs as cancelled
        for job in self.jobs:
            if job.status == "pending":
                job.status = "cancelled"
                self.cancelled_jobs += 1
        
        # Clear active processors
        self.active_processors.clear()
        
        # Complete batch
        self._complete_batch()
    
    def get_batch_status(self) -> dict:
        """Get current batch status"""
        return {
            'is_processing': self.is_processing,
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'cancelled_jobs': self.cancelled_jobs,
            'active_jobs': len(self.active_processors),
            'pending_jobs': len([job for job in self.jobs if job.status == "pending"]),
            'elapsed_time': time.time() - self.batch_start_time if self.is_processing else 0.0
        }
    
    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get status of a specific job"""
        job = self._find_job(job_id)
        if not job:
            return None
        
        return {
            'job_id': job.job_id,
            'status': job.status,
            'progress_percent': job.progress_percent,
            'error_message': job.error_message,
            'start_time': job.start_time,
            'end_time': job.end_time,
            'duration': (job.end_time - job.start_time) if job.start_time and job.end_time else None
        }
    
    def clear_completed_jobs(self):
        """Remove completed and failed jobs from the queue"""
        if self.is_processing:
            raise RuntimeError("Cannot clear jobs while batch is processing")
        
        self.jobs = [job for job in self.jobs if job.status in ["pending", "running"]]
        print(f"Cleared completed jobs, {len(self.jobs)} jobs remaining")


def create_batch_processor(max_concurrent_jobs: int = 1) -> BatchFFmpegProcessor:
    """Create a batch FFmpeg processor"""
    return BatchFFmpegProcessor(max_concurrent_jobs)


if __name__ == "__main__":
    # Test the enhanced FFmpeg integration
    print("Testing Enhanced FFmpeg Integration...")
    
    # Check capabilities
    capabilities = get_ffmpeg_capabilities()
    print(f"FFmpeg available: {capabilities.available}")
    
    if capabilities.available:
        print(f"Version: {capabilities.version}")
        print(f"Supported codecs: {len(capabilities.supported_codecs)}")
        print(f"Supported formats: {len(capabilities.supported_formats)}")
        print(f"Hardware acceleration: {capabilities.hardware_acceleration}")
    else:
        print(f"Error: {capabilities.error_message}")
    
    print("Enhanced FFmpeg integration test completed")