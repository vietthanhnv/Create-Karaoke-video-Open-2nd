"""
Core module for the Karaoke Video Creator application.

This module provides the fundamental data models and validation utilities
used throughout the application.
"""

from .models import (
    # Data models
    VideoFile,
    AudioFile,
    ImageFile,
    SubtitleFile,
    SubtitleLine,
    SubtitleStyle,
    Effect,
    ExportSettings,
    Project,
    
    # Enums
    MediaType,
    VideoFormat,
    AudioFormat,
    ImageFormat,
    SubtitleFormat
)

from .validation import (
    FileValidator,
    ValidationError,
    validate_project_requirements
)

__all__ = [
    # Data models
    'VideoFile',
    'AudioFile',
    'ImageFile',
    'SubtitleFile',
    'SubtitleLine',
    'SubtitleStyle',
    'Effect',
    'ExportSettings',
    'Project',
    
    # Enums
    'MediaType',
    'VideoFormat',
    'AudioFormat',
    'ImageFormat',
    'SubtitleFormat',
    
    # Validation
    'FileValidator',
    'ValidationError',
    'validate_project_requirements'
]