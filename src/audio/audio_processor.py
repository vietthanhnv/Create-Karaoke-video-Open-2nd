"""
Audio processing and synchronization module for the Karaoke Video Creator.

This module provides functionality for:
- Audio file loading and metadata extraction
- Audio-subtitle timing synchronization
- Audio duration validation against subtitle timing
- Audio embedding pipeline for FFmpeg export
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import logging

from ..core.models import AudioFile, SubtitleFile
from ..core.validation import ValidationError


logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Detailed audio metadata extracted from file."""
    duration: float
    sample_rate: int
    channels: int
    bitrate: int
    codec: str
    format: str
    file_size: int


@dataclass
class TimingSyncResult:
    """Result of audio-subtitle timing synchronization."""
    is_synchronized: bool
    audio_duration: float
    subtitle_duration: float
    timing_offset: float
    warnings: List[str]
    errors: List[str]


class AudioProcessor:
    """Handles audio file processing and synchronization operations."""
    
    def __init__(self):
        """Initialize the audio processor."""
        self.supported_formats = {'.mp3', '.wav', '.flac', '.aac', '.m4a'}
        
    def load_audio_file(self, file_path: str) -> AudioFile:
        """
        Load an audio file and extract its metadata.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioFile object with extracted metadata
            
        Raises:
            ValidationError: If file is invalid or unsupported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        if path.suffix.lower() not in self.supported_formats:
            raise ValidationError(
                f"Unsupported audio format: {path.suffix}. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )
        
        try:
            metadata = self.extract_metadata(file_path)
            
            audio_file = AudioFile(
                path=str(path.resolve()),
                file_path=str(path.resolve()),
                duration=metadata.duration,
                sample_rate=metadata.sample_rate,
                channels=metadata.channels,
                format=metadata.format,
                file_size=metadata.file_size,
                bitrate=metadata.bitrate
            )
            
            logger.info(f"Successfully loaded audio file: {file_path}")
            logger.debug(f"Audio metadata: {metadata}")
            
            return audio_file
            
        except Exception as e:
            logger.error(f"Failed to load audio file {file_path}: {e}")
            raise ValidationError(f"Failed to load audio file: {e}")
    
    def extract_metadata(self, file_path: str) -> AudioMetadata:
        """
        Extract detailed metadata from an audio file using FFprobe.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioMetadata object with extracted information
            
        Raises:
            ValidationError: If metadata extraction fails
        """
        try:
            # Use ffprobe to get detailed audio metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                '-select_streams', 'a:0',  # Select first audio stream
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            data = json.loads(result.stdout)
            
            # Find audio stream
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ValidationError("No audio stream found in file")
            
            format_info = data.get('format', {})
            
            metadata = AudioMetadata(
                duration=float(format_info.get('duration', 0)),
                sample_rate=int(audio_stream.get('sample_rate', 0)),
                channels=int(audio_stream.get('channels', 0)),
                bitrate=int(audio_stream.get('bit_rate', 0)) or 
                        int(format_info.get('bit_rate', 0)),
                codec=audio_stream.get('codec_name', ''),
                format=format_info.get('format_name', ''),
                file_size=int(format_info.get('size', 0))
            )
            
            return metadata
            
        except subprocess.TimeoutExpired:
            raise ValidationError("Timeout while extracting audio metadata")
        except subprocess.CalledProcessError as e:
            raise ValidationError(f"FFprobe failed: {e.stderr}")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON response from FFprobe")
        except Exception as e:
            raise ValidationError(f"Failed to extract metadata: {e}")
    
    def validate_audio_duration(self, audio_file: AudioFile, 
                              subtitle_file: Optional[SubtitleFile] = None) -> TimingSyncResult:
        """
        Validate audio duration against subtitle timing.
        
        Args:
            audio_file: Audio file to validate
            subtitle_file: Optional subtitle file for timing comparison
            
        Returns:
            TimingSyncResult with validation results
        """
        warnings = []
        errors = []
        timing_offset = 0.0
        is_synchronized = True
        
        audio_duration = audio_file.duration
        subtitle_duration = 0.0
        
        if subtitle_file:
            # Calculate subtitle duration from timing data
            if hasattr(subtitle_file, 'lines') and subtitle_file.lines:
                # Find the last subtitle end time
                last_end_time = 0.0
                for line in subtitle_file.lines:
                    if hasattr(line, 'end_time'):
                        last_end_time = max(last_end_time, line.end_time)
                subtitle_duration = last_end_time
            
            # Check duration compatibility
            duration_diff = abs(audio_duration - subtitle_duration)
            
            if duration_diff > 5.0:  # More than 5 seconds difference
                errors.append(
                    f"Significant duration mismatch: audio={audio_duration:.2f}s, "
                    f"subtitles={subtitle_duration:.2f}s (diff={duration_diff:.2f}s)"
                )
                is_synchronized = False
            elif duration_diff > 1.0:  # More than 1 second difference
                warnings.append(
                    f"Minor duration mismatch: audio={audio_duration:.2f}s, "
                    f"subtitles={subtitle_duration:.2f}s (diff={duration_diff:.2f}s)"
                )
            
            # Calculate timing offset (positive if audio is longer)
            timing_offset = audio_duration - subtitle_duration
        else:
            # No subtitle file provided, no offset calculation
            timing_offset = 0.0
        
        # Validate audio file properties
        if audio_duration <= 0:
            errors.append("Audio duration is zero or negative")
            is_synchronized = False
        
        if audio_file.sample_rate < 8000:
            warnings.append(f"Low sample rate: {audio_file.sample_rate}Hz")
        
        if audio_file.channels == 0:
            errors.append("No audio channels detected")
            is_synchronized = False
        elif audio_file.channels > 2:
            warnings.append(f"Multi-channel audio: {audio_file.channels} channels")
        
        return TimingSyncResult(
            is_synchronized=is_synchronized,
            audio_duration=audio_duration,
            subtitle_duration=subtitle_duration,
            timing_offset=timing_offset,
            warnings=warnings,
            errors=errors
        )
    
    def synchronize_timing(self, audio_file: AudioFile, 
                          subtitle_file: SubtitleFile,
                          target_offset: float = 0.0) -> TimingSyncResult:
        """
        Synchronize audio and subtitle timing.
        
        Args:
            audio_file: Audio file for synchronization
            subtitle_file: Subtitle file to synchronize
            target_offset: Target timing offset in seconds
            
        Returns:
            TimingSyncResult with synchronization results
        """
        # First validate current timing
        sync_result = self.validate_audio_duration(audio_file, subtitle_file)
        
        # Apply timing offset if needed
        if target_offset != 0.0 and hasattr(subtitle_file, 'lines'):
            for line in subtitle_file.lines:
                if hasattr(line, 'start_time'):
                    line.start_time += target_offset
                if hasattr(line, 'end_time'):
                    line.end_time += target_offset
            
            sync_result.timing_offset = target_offset
            sync_result.warnings.append(f"Applied timing offset: {target_offset:.2f}s")
        
        return sync_result
    
    def create_ffmpeg_audio_args(self, audio_file: AudioFile, 
                                output_settings: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Create FFmpeg arguments for audio embedding in video export.
        
        Args:
            audio_file: Audio file to embed
            output_settings: Optional output settings
            
        Returns:
            List of FFmpeg arguments for audio processing
        """
        args = []
        
        # Input audio file
        args.extend(['-i', audio_file.path])
        
        # Audio codec settings
        if output_settings:
            audio_codec = output_settings.get('audio_codec', 'aac')
            audio_bitrate = output_settings.get('audio_bitrate', '128k')
            audio_sample_rate = output_settings.get('audio_sample_rate')
            audio_channels = output_settings.get('audio_channels')
        else:
            audio_codec = 'aac'
            audio_bitrate = '128k'
            audio_sample_rate = None
            audio_channels = None
        
        # Audio encoding options
        args.extend(['-c:a', audio_codec])
        args.extend(['-b:a', audio_bitrate])
        
        if audio_sample_rate:
            args.extend(['-ar', str(audio_sample_rate)])
        
        if audio_channels:
            args.extend(['-ac', str(audio_channels)])
        
        # Audio quality settings
        args.extend(['-q:a', '2'])  # High quality
        
        return args
    
    def get_audio_stream_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get detailed audio stream information for FFmpeg processing.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio stream information
        """
        try:
            metadata = self.extract_metadata(file_path)
            
            return {
                'duration': metadata.duration,
                'sample_rate': metadata.sample_rate,
                'channels': metadata.channels,
                'bitrate': metadata.bitrate,
                'codec': metadata.codec,
                'format': metadata.format,
                'compatible_with_h264': metadata.codec in ['aac', 'mp3'],
                'needs_conversion': metadata.codec not in ['aac', 'mp3']
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio stream info: {e}")
            return {}