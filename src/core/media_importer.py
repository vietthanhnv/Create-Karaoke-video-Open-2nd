"""
Media Import System for the Karaoke Video Creator application.

This module provides the MediaImporter class for importing media files with
file selection dialogs, format filtering, drag-and-drop support, and metadata
extraction using FFmpeg probe.
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from PyQt6.QtWidgets import QFileDialog, QWidget
from PyQt6.QtCore import QObject, pyqtSignal

from .models import VideoFile, AudioFile, ImageFile, SubtitleFile, MediaType
from .validation import FileValidator, ValidationError


class MediaImportError(Exception):
    """Custom exception for media import errors."""
    pass


class MediaImporter(QObject):
    """
    Handles media file import with file dialogs, validation, and metadata extraction.
    
    Provides file selection dialogs with format filtering, drag-and-drop support,
    and FFmpeg-based metadata extraction for imported media files.
    """
    
    # Signals for import events
    import_started = pyqtSignal(str)  # file_path
    import_completed = pyqtSignal(object)  # media_file_object
    import_failed = pyqtSignal(str, str)  # file_path, error_message
    metadata_extracted = pyqtSignal(str, dict)  # file_path, metadata
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the MediaImporter.
        
        Args:
            parent: Parent widget for file dialogs
        """
        super().__init__()
        self.parent = parent
        self._ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """
        Find FFmpeg executable in system PATH.
        
        Returns:
            Path to FFmpeg executable or None if not found
        """
        try:
            result = subprocess.run(
                ['where', 'ffmpeg'] if os.name == 'nt' else ['which', 'ffmpeg'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n')[0]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def import_video(self, file_path: Optional[str] = None) -> Optional[VideoFile]:
        """
        Import a video file with validation and metadata extraction.
        
        Args:
            file_path: Optional path to video file. If None, opens file dialog.
            
        Returns:
            VideoFile object with metadata or None if cancelled/failed
            
        Raises:
            MediaImportError: If import fails
        """
        if file_path is None:
            file_path = self._select_video_file()
            if not file_path:
                return None
        
        try:
            self.import_started.emit(file_path)
            
            # Validate file format
            video_file = FileValidator.validate_video_file(file_path)
            
            # Extract metadata using FFmpeg
            metadata = self._extract_video_metadata(file_path)
            if metadata:
                video_file.duration = metadata.get('duration', 0.0)
                video_file.resolution = {
                    'width': metadata.get('width', 0),
                    'height': metadata.get('height', 0)
                }
                video_file.frame_rate = metadata.get('frame_rate', 0.0)
                
                self.metadata_extracted.emit(file_path, metadata)
            
            self.import_completed.emit(video_file)
            return video_file
            
        except (ValidationError, MediaImportError) as e:
            error_msg = str(e)
            self.import_failed.emit(file_path, error_msg)
            raise MediaImportError(f"Failed to import video file: {error_msg}")
    
    def import_audio(self, file_path: Optional[str] = None) -> Optional[AudioFile]:
        """
        Import an audio file with validation and metadata extraction.
        
        Args:
            file_path: Optional path to audio file. If None, opens file dialog.
            
        Returns:
            AudioFile object with metadata or None if cancelled/failed
            
        Raises:
            MediaImportError: If import fails
        """
        if file_path is None:
            file_path = self._select_audio_file()
            if not file_path:
                return None
        
        try:
            self.import_started.emit(file_path)
            
            # Validate file format
            audio_file = FileValidator.validate_audio_file(file_path)
            
            # Extract metadata using FFmpeg
            metadata = self._extract_audio_metadata(file_path)
            if metadata:
                audio_file.duration = metadata.get('duration', 0.0)
                audio_file.sample_rate = metadata.get('sample_rate', 0)
                audio_file.channels = metadata.get('channels', 0)
                audio_file.bitrate = metadata.get('bitrate', 0)
                
                self.metadata_extracted.emit(file_path, metadata)
            
            self.import_completed.emit(audio_file)
            return audio_file
            
        except (ValidationError, MediaImportError) as e:
            error_msg = str(e)
            self.import_failed.emit(file_path, error_msg)
            raise MediaImportError(f"Failed to import audio file: {error_msg}")
    
    def import_image(self, file_path: Optional[str] = None) -> Optional[ImageFile]:
        """
        Import an image file with validation and metadata extraction.
        
        Args:
            file_path: Optional path to image file. If None, opens file dialog.
            
        Returns:
            ImageFile object with metadata or None if cancelled/failed
            
        Raises:
            MediaImportError: If import fails
        """
        if file_path is None:
            file_path = self._select_image_file()
            if not file_path:
                return None
        
        try:
            self.import_started.emit(file_path)
            
            # Validate file format
            image_file = FileValidator.validate_image_file(file_path)
            
            # Extract metadata using FFmpeg
            metadata = self._extract_image_metadata(file_path)
            if metadata:
                image_file.resolution = {
                    'width': metadata.get('width', 0),
                    'height': metadata.get('height', 0)
                }
                
                self.metadata_extracted.emit(file_path, metadata)
            
            self.import_completed.emit(image_file)
            return image_file
            
        except (ValidationError, MediaImportError) as e:
            error_msg = str(e)
            self.import_failed.emit(file_path, error_msg)
            raise MediaImportError(f"Failed to import image file: {error_msg}")
    
    def import_subtitles(self, file_path: Optional[str] = None) -> Optional[SubtitleFile]:
        """
        Import a subtitle file with validation and parsing.
        
        Args:
            file_path: Optional path to subtitle file. If None, opens file dialog.
            
        Returns:
            SubtitleFile object with parsed content or None if cancelled/failed
            
        Raises:
            MediaImportError: If import fails
        """
        if file_path is None:
            file_path = self._select_subtitle_file()
            if not file_path:
                return None
        
        try:
            self.import_started.emit(file_path)
            
            # Basic file validation (extension and existence)
            if not Path(file_path).exists():
                raise MediaImportError(f"File not found: {file_path}")
            
            if not file_path.lower().endswith('.ass'):
                raise MediaImportError(f"Invalid file extension. Expected .ass file")
            
            # Parse the ASS file using the subtitle parser
            from .subtitle_parser import parse_ass_file
            subtitle_file, errors, warnings = parse_ass_file(file_path)
            
            # Check for parsing errors
            if errors:
                error_messages = [f"Line {err.line_number}: {err.message}" for err in errors]
                raise MediaImportError(f"Subtitle parsing errors:\n" + "\n".join(error_messages))
            
            # Log warnings if any
            if warnings:
                warning_messages = [f"Line {warn.line_number}: {warn.message}" for warn in warnings]
                print(f"Subtitle parsing warnings:\n" + "\n".join(warning_messages))
            
            self.import_completed.emit(subtitle_file)
            return subtitle_file
            
        except MediaImportError:
            # Re-raise MediaImportError as-is
            raise
        except Exception as e:
            error_msg = f"Unexpected error during subtitle import: {str(e)}"
            self.import_failed.emit(file_path, error_msg)
            raise MediaImportError(error_msg)
    
    def validate_file(self, file_path: str, expected_type: MediaType) -> bool:
        """
        Validate if a file matches the expected media type.
        
        Args:
            file_path: Path to the file to validate
            expected_type: Expected MediaType enum value
            
        Returns:
            True if file is valid for the expected type
        """
        try:
            FileValidator.validate_media_file(file_path, expected_type)
            return True
        except ValidationError:
            return False
    
    def _select_video_file(self) -> Optional[str]:
        """
        Open file dialog to select a video file.
        
        Returns:
            Selected file path or None if cancelled
        """
        extensions = FileValidator.get_supported_extensions(MediaType.VIDEO)
        filter_str = self._create_file_filter("Video Files", extensions)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Video File",
            "",
            filter_str
        )
        
        return file_path if file_path else None
    
    def _select_audio_file(self) -> Optional[str]:
        """
        Open file dialog to select an audio file.
        
        Returns:
            Selected file path or None if cancelled
        """
        extensions = FileValidator.get_supported_extensions(MediaType.AUDIO)
        filter_str = self._create_file_filter("Audio Files", extensions)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Audio File",
            "",
            filter_str
        )
        
        return file_path if file_path else None
    
    def _select_image_file(self) -> Optional[str]:
        """
        Open file dialog to select an image file.
        
        Returns:
            Selected file path or None if cancelled
        """
        extensions = FileValidator.get_supported_extensions(MediaType.IMAGE)
        filter_str = self._create_file_filter("Image Files", extensions)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Image File",
            "",
            filter_str
        )
        
        return file_path if file_path else None
    
    def _select_subtitle_file(self) -> Optional[str]:
        """
        Open file dialog to select a subtitle file.
        
        Returns:
            Selected file path or None if cancelled
        """
        extensions = FileValidator.get_supported_extensions(MediaType.SUBTITLE)
        filter_str = self._create_file_filter("Subtitle Files", extensions)
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Subtitle File",
            "",
            filter_str
        )
        
        return file_path if file_path else None
    
    def _create_file_filter(self, description: str, extensions: List[str]) -> str:
        """
        Create a file filter string for QFileDialog.
        
        Args:
            description: Description of file type
            extensions: List of file extensions (with dots)
            
        Returns:
            File filter string for QFileDialog
        """
        # Convert extensions to uppercase patterns
        patterns = []
        for ext in extensions:
            patterns.append(f"*{ext}")
            patterns.append(f"*{ext.upper()}")
        
        pattern_str = " ".join(patterns)
        return f"{description} ({pattern_str});;All Files (*)"
    
    def _extract_video_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract video metadata using FFmpeg probe.
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary with metadata or None if extraction fails
        """
        if not self._ffmpeg_path:
            return None
        
        try:
            # Use ffprobe to get video metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return None
            
            # Extract relevant metadata
            metadata = {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'frame_rate': self._parse_frame_rate(video_stream.get('r_frame_rate', '0/1')),
                'codec': video_stream.get('codec_name', ''),
                'bitrate': int(data.get('format', {}).get('bit_rate', 0))
            }
            
            return metadata
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            return None
    
    def _extract_audio_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract audio metadata using FFmpeg probe.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with metadata or None if extraction fails
        """
        if not self._ffmpeg_path:
            return None
        
        try:
            # Use ffprobe to get audio metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # Find audio stream
            audio_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return None
            
            # Extract relevant metadata
            metadata = {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bitrate': int(audio_stream.get('bit_rate', 0)) or int(data.get('format', {}).get('bit_rate', 0)),
                'codec': audio_stream.get('codec_name', '')
            }
            
            return metadata
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            return None
    
    def _extract_image_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract image metadata using FFmpeg probe.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary with metadata or None if extraction fails
        """
        if not self._ffmpeg_path:
            return None
        
        try:
            # Use ffprobe to get image metadata
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # Find video stream (images are treated as single-frame video)
            stream = data.get('streams', [{}])[0]
            
            # Extract relevant metadata
            metadata = {
                'width': int(stream.get('width', 0)),
                'height': int(stream.get('height', 0)),
                'codec': stream.get('codec_name', ''),
                'pixel_format': stream.get('pix_fmt', '')
            }
            
            return metadata
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
            return None
    
    def _parse_frame_rate(self, frame_rate_str: str) -> float:
        """
        Parse frame rate from FFmpeg format (e.g., "30/1" -> 30.0).
        
        Args:
            frame_rate_str: Frame rate string from FFmpeg
            
        Returns:
            Frame rate as float
        """
        try:
            if '/' in frame_rate_str:
                numerator, denominator = frame_rate_str.split('/')
                return float(numerator) / float(denominator)
            else:
                return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get dictionary of supported formats for each media type.
        
        Returns:
            Dictionary mapping media type names to extension lists
        """
        return {
            'video': FileValidator.get_supported_extensions(MediaType.VIDEO),
            'audio': FileValidator.get_supported_extensions(MediaType.AUDIO),
            'image': FileValidator.get_supported_extensions(MediaType.IMAGE),
            'subtitle': FileValidator.get_supported_extensions(MediaType.SUBTITLE)
        }