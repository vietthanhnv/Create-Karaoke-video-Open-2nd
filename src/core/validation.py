"""
File validation utilities for the Karaoke Video Creator application.

This module provides functions to validate media file formats and integrity
according to the application's supported formats and requirements.
"""

import os
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass

from .models import (
    MediaType, VideoFormat, AudioFormat, ImageFormat, SubtitleFormat,
    VideoFile, AudioFile, ImageFile, SubtitleFile
)


class ValidationLevel(Enum):
    """Validation result severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Represents a validation result with level, message, and suggestion."""
    level: ValidationLevel
    message: str
    suggestion: str = ""


class ValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


class FileValidator:
    """Handles validation of media files for supported formats and integrity."""
    
    # Supported file extensions mapped to formats
    VIDEO_EXTENSIONS = {
        '.mp4': VideoFormat.MP4,
        '.mov': VideoFormat.MOV,
        '.avi': VideoFormat.AVI
    }
    
    AUDIO_EXTENSIONS = {
        '.mp3': AudioFormat.MP3,
        '.wav': AudioFormat.WAV,
        '.aac': AudioFormat.AAC
    }
    
    IMAGE_EXTENSIONS = {
        '.jpg': ImageFormat.JPG,
        '.jpeg': ImageFormat.JPEG,
        '.png': ImageFormat.PNG,
        '.bmp': ImageFormat.BMP
    }
    
    SUBTITLE_EXTENSIONS = {
        '.ass': SubtitleFormat.ASS
    }
    
    # MIME types for additional validation
    VIDEO_MIME_TYPES = {
        'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/avi'
    }
    
    AUDIO_MIME_TYPES = {
        'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/aac', 'audio/vnd.dlna.adts'
    }
    
    IMAGE_MIME_TYPES = {
        'image/jpeg', 'image/png', 'image/bmp', 'image/x-ms-bmp'
    }
    
    @classmethod
    def validate_file_exists(cls, file_path: str) -> bool:
        """
        Check if file exists and is accessible.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            True if file exists and is readable
            
        Raises:
            ValidationError: If file doesn't exist or isn't accessible
        """
        path = Path(file_path)
        
        if not path.exists():
            raise ValidationError(f"File does not exist: {file_path}")
        
        if not path.is_file():
            raise ValidationError(f"Path is not a file: {file_path}")
        
        if not os.access(path, os.R_OK):
            raise ValidationError(f"File is not readable: {file_path}")
        
        return True
    
    @classmethod
    def get_file_extension(cls, file_path: str) -> str:
        """
        Get the lowercase file extension from a file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Lowercase file extension including the dot (e.g., '.mp4')
        """
        return Path(file_path).suffix.lower()
    
    @classmethod
    def get_mime_type(cls, file_path: str) -> Optional[str]:
        """
        Get the MIME type of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string or None if cannot be determined
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type
    
    @classmethod
    def validate_video_file(cls, file_path: str) -> VideoFile:
        """
        Validate a video file and return VideoFile object.
        
        Args:
            file_path: Path to the video file
            
        Returns:
            VideoFile object with basic metadata
            
        Raises:
            ValidationError: If file is invalid or unsupported format
        """
        cls.validate_file_exists(file_path)
        
        extension = cls.get_file_extension(file_path)
        if extension not in cls.VIDEO_EXTENSIONS:
            supported = ', '.join(cls.VIDEO_EXTENSIONS.keys())
            raise ValidationError(
                f"Unsupported video format: {extension}. "
                f"Supported formats: {supported}"
            )
        
        # Additional MIME type validation
        mime_type = cls.get_mime_type(file_path)
        if mime_type and mime_type not in cls.VIDEO_MIME_TYPES:
            raise ValidationError(
                f"Invalid video file MIME type: {mime_type}"
            )
        
        # Get file size
        file_size = Path(file_path).stat().st_size
        
        return VideoFile(
            path=file_path,
            format=cls.VIDEO_EXTENSIONS[extension].value,
            file_size=file_size
        )
    
    @classmethod
    def validate_audio_file(cls, file_path: str) -> AudioFile:
        """
        Validate an audio file and return AudioFile object.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioFile object with basic metadata
            
        Raises:
            ValidationError: If file is invalid or unsupported format
        """
        cls.validate_file_exists(file_path)
        
        extension = cls.get_file_extension(file_path)
        if extension not in cls.AUDIO_EXTENSIONS:
            supported = ', '.join(cls.AUDIO_EXTENSIONS.keys())
            raise ValidationError(
                f"Unsupported audio format: {extension}. "
                f"Supported formats: {supported}"
            )
        
        # Additional MIME type validation
        mime_type = cls.get_mime_type(file_path)
        if mime_type and mime_type not in cls.AUDIO_MIME_TYPES:
            raise ValidationError(
                f"Invalid audio file MIME type: {mime_type}"
            )
        
        # Get file size
        file_size = Path(file_path).stat().st_size
        
        return AudioFile(
            path=file_path,
            format=cls.AUDIO_EXTENSIONS[extension].value,
            file_size=file_size
        )
    
    @classmethod
    def validate_image_file(cls, file_path: str) -> ImageFile:
        """
        Validate an image file and return ImageFile object.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            ImageFile object with basic metadata
            
        Raises:
            ValidationError: If file is invalid or unsupported format
        """
        cls.validate_file_exists(file_path)
        
        extension = cls.get_file_extension(file_path)
        if extension not in cls.IMAGE_EXTENSIONS:
            supported = ', '.join(cls.IMAGE_EXTENSIONS.keys())
            raise ValidationError(
                f"Unsupported image format: {extension}. "
                f"Supported formats: {supported}"
            )
        
        # Additional MIME type validation
        mime_type = cls.get_mime_type(file_path)
        if mime_type and mime_type not in cls.IMAGE_MIME_TYPES:
            raise ValidationError(
                f"Invalid image file MIME type: {mime_type}"
            )
        
        # Get file size
        file_size = Path(file_path).stat().st_size
        
        # Handle JPEG format mapping
        format_value = cls.IMAGE_EXTENSIONS[extension].value
        if format_value == "jpeg":
            format_value = "jpg"  # Normalize jpeg to jpg
        
        return ImageFile(
            path=file_path,
            format=format_value,
            file_size=file_size
        )
    
    @classmethod
    def validate_subtitle_file(cls, file_path: str) -> SubtitleFile:
        """
        Validate a subtitle file and return SubtitleFile object.
        
        Args:
            file_path: Path to the subtitle file
            
        Returns:
            SubtitleFile object with basic metadata
            
        Raises:
            ValidationError: If file is invalid or unsupported format
        """
        cls.validate_file_exists(file_path)
        
        extension = cls.get_file_extension(file_path)
        if extension not in cls.SUBTITLE_EXTENSIONS:
            supported = ', '.join(cls.SUBTITLE_EXTENSIONS.keys())
            raise ValidationError(
                f"Unsupported subtitle format: {extension}. "
                f"Supported formats: {supported}"
            )
        
        # Basic ASS file format validation
        if extension == '.ass':
            cls._validate_ass_format(file_path)
        
        # Get file size
        file_size = Path(file_path).stat().st_size
        
        return SubtitleFile(
            path=file_path,
            format=cls.SUBTITLE_EXTENSIONS[extension].value,
            file_size=file_size
        )
    
    @classmethod
    def _validate_ass_format(cls, file_path: str) -> None:
        """
        Validate basic ASS subtitle file format.
        
        Args:
            file_path: Path to the ASS file
            
        Raises:
            ValidationError: If ASS file format is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required ASS sections
            required_sections = ['[Script Info]', '[V4+ Styles]', '[Events]']
            for section in required_sections:
                if section not in content:
                    raise ValidationError(
                        f"Invalid ASS file: Missing required section '{section}'"
                    )
            
        except UnicodeDecodeError:
            raise ValidationError(
                "Invalid ASS file: File encoding is not UTF-8"
            )
        except Exception as e:
            raise ValidationError(f"Error reading ASS file: {str(e)}")
    
    @classmethod
    def validate_media_file(cls, file_path: str, expected_type: MediaType) -> Any:
        """
        Validate a media file based on expected type.
        
        Args:
            file_path: Path to the media file
            expected_type: Expected MediaType enum value
            
        Returns:
            Appropriate File object (VideoFile, AudioFile, etc.)
            
        Raises:
            ValidationError: If file is invalid or doesn't match expected type
        """
        if expected_type == MediaType.VIDEO:
            return cls.validate_video_file(file_path)
        elif expected_type == MediaType.AUDIO:
            return cls.validate_audio_file(file_path)
        elif expected_type == MediaType.IMAGE:
            return cls.validate_image_file(file_path)
        elif expected_type == MediaType.SUBTITLE:
            return cls.validate_subtitle_file(file_path)
        else:
            raise ValidationError(f"Unknown media type: {expected_type}")
    
    @classmethod
    def get_supported_extensions(cls, media_type: MediaType) -> List[str]:
        """
        Get list of supported file extensions for a media type.
        
        Args:
            media_type: MediaType enum value
            
        Returns:
            List of supported file extensions
        """
        if media_type == MediaType.VIDEO:
            return list(cls.VIDEO_EXTENSIONS.keys())
        elif media_type == MediaType.AUDIO:
            return list(cls.AUDIO_EXTENSIONS.keys())
        elif media_type == MediaType.IMAGE:
            return list(cls.IMAGE_EXTENSIONS.keys())
        elif media_type == MediaType.SUBTITLE:
            return list(cls.SUBTITLE_EXTENSIONS.keys())
        else:
            return []
    
    @classmethod
    def is_supported_format(cls, file_path: str, media_type: MediaType) -> bool:
        """
        Check if a file format is supported for the given media type.
        
        Args:
            file_path: Path to the file
            media_type: Expected MediaType
            
        Returns:
            True if format is supported, False otherwise
        """
        extension = cls.get_file_extension(file_path)
        supported_extensions = cls.get_supported_extensions(media_type)
        return extension in supported_extensions


def validate_project_requirements(project) -> List[str]:
    """
    Validate that a project meets all requirements for processing.
    
    Args:
        project: Project object to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check for required background (video or image)
    if not project.has_video_background() and not project.has_image_background():
        errors.append("Project must have either a video file or image background")
    
    # Check for required audio
    if not project.has_audio():
        errors.append("Project must have an audio file")
    
    # Check for required subtitles
    if not project.has_subtitles():
        errors.append("Project must have a subtitle file")
    
    # Validate file accessibility if files are present
    if project.video_file:
        try:
            FileValidator.validate_file_exists(project.video_file.path)
        except ValidationError as e:
            errors.append(str(e))
    
    if project.image_file:
        try:
            FileValidator.validate_file_exists(project.image_file.path)
        except ValidationError as e:
            errors.append(str(e))
    
    if project.audio_file:
        try:
            FileValidator.validate_file_exists(project.audio_file.path)
        except ValidationError as e:
            errors.append(str(e))
    
    if project.subtitle_file:
        try:
            FileValidator.validate_file_exists(project.subtitle_file.path)
        except ValidationError as e:
            errors.append(str(e))
    
    return errors