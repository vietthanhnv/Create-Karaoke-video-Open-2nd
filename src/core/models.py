"""
Core data models for the Karaoke Video Creator application.

This module defines the data structures used throughout the application
for representing projects, media files, and related metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class MediaType(Enum):
    """Enumeration of supported media types."""
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    SUBTITLE = "subtitle"


class VideoFormat(Enum):
    """Supported video file formats."""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"


class AudioFormat(Enum):
    """Supported audio file formats."""
    MP3 = "mp3"
    WAV = "wav"
    AAC = "aac"


class ImageFormat(Enum):
    """Supported image file formats."""
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"


class SubtitleFormat(Enum):
    """Supported subtitle file formats."""
    ASS = "ass"


@dataclass
class VideoFile:
    """Represents a video file with its metadata."""
    path: str
    duration: float = 0.0
    resolution: Dict[str, int] = field(default_factory=lambda: {"width": 0, "height": 0})
    format: str = ""
    frame_rate: float = 0.0
    file_size: int = 0
    
    def __post_init__(self):
        """Validate the video file after initialization."""
        if self.path:
            self.path = str(Path(self.path).resolve())


@dataclass
class AudioFile:
    """Represents an audio file with its metadata."""
    path: str
    duration: float = 0.0
    format: str = ""
    sample_rate: int = 0
    channels: int = 0
    bitrate: int = 0
    file_size: int = 0
    
    def __post_init__(self):
        """Validate the audio file after initialization."""
        if self.path:
            self.path = str(Path(self.path).resolve())


@dataclass
class ImageFile:
    """Represents an image file with its metadata."""
    path: str
    resolution: Dict[str, int] = field(default_factory=lambda: {"width": 0, "height": 0})
    format: str = ""
    file_size: int = 0
    
    def __post_init__(self):
        """Validate the image file after initialization."""
        if self.path:
            self.path = str(Path(self.path).resolve())


@dataclass
class WordTiming:
    """Represents timing for individual words in karaoke-style subtitles."""
    word: str
    start_time: float
    end_time: float
    
    def __post_init__(self):
        """Validate word timing."""
        if self.start_time < 0:
            raise ValueError("Word start time cannot be negative")
        if self.end_time <= self.start_time:
            raise ValueError("Word end time must be greater than start time")


@dataclass
class SubtitleLine:
    """Represents a single subtitle line with timing and content."""
    start_time: float
    end_time: float
    text: str
    style: str = "Default"
    word_timings: List['WordTiming'] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate subtitle line timing."""
        if self.start_time < 0:
            raise ValueError("Start time cannot be negative")
        if self.end_time <= self.start_time:
            raise ValueError("End time must be greater than start time")
    
    def get_active_words(self, current_time: float) -> List[str]:
        """Get words that should be highlighted at the current time."""
        if not self.word_timings:
            # If no word timings, return all words if line is active
            if self.start_time <= current_time <= self.end_time:
                return self.text.split()
            return []
        
        active_words = []
        for word_timing in self.word_timings:
            if word_timing.start_time <= current_time <= word_timing.end_time:
                active_words.append(word_timing.word)
        return active_words
    
    def get_progress_ratio(self, current_time: float) -> float:
        """Get progress ratio (0.0 to 1.0) for karaoke animation."""
        if current_time <= self.start_time:
            return 0.0
        if current_time >= self.end_time:
            return 1.0
        
        if self.word_timings:
            # Calculate based on word timings
            total_words = len(self.word_timings)
            completed_words = 0
            
            for word_timing in self.word_timings:
                if current_time >= word_timing.end_time:
                    completed_words += 1
                elif word_timing.start_time <= current_time <= word_timing.end_time:
                    # Partial completion of current word
                    word_progress = (current_time - word_timing.start_time) / (word_timing.end_time - word_timing.start_time)
                    return (completed_words + word_progress) / total_words
            
            return completed_words / total_words if total_words > 0 else 1.0
        else:
            # Linear progress based on line timing
            return (current_time - self.start_time) / (self.end_time - self.start_time)


@dataclass
class SubtitleStyle:
    """Represents subtitle styling information."""
    name: str = "Default"
    font_name: str = "Arial"
    font_size: int = 20
    primary_color: str = "&H00FFFFFF"  # White in ASS format
    secondary_color: str = "&H000000FF"  # Red in ASS format
    outline_color: str = "&H00000000"  # Black in ASS format
    back_color: str = "&H80000000"  # Semi-transparent black
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike_out: bool = False
    scale_x: float = 100.0
    scale_y: float = 100.0
    spacing: float = 0.0
    angle: float = 0.0
    border_style: int = 1
    outline: float = 2.0
    shadow: float = 0.0
    alignment: int = 2
    margin_l: int = 10
    margin_r: int = 10
    margin_v: int = 10


@dataclass
class SubtitleFile:
    """Represents a subtitle file with its content and metadata."""
    path: str
    format: str = "ass"
    lines: List[SubtitleLine] = field(default_factory=list)
    styles: List[SubtitleStyle] = field(default_factory=list)
    file_size: int = 0
    
    def __post_init__(self):
        """Validate the subtitle file after initialization."""
        if self.path:
            self.path = str(Path(self.path).resolve())


@dataclass
class Effect:
    """Represents a text effect that can be applied to subtitles."""
    id: str
    name: str
    type: str  # "fade", "glow", "outline", "shadow", "animation"
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ExportSettings:
    """Represents export configuration settings."""
    resolution: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    bitrate: int = 5000  # kbps
    format: str = "mp4"
    quality: str = "high"  # "low", "medium", "high", "custom"
    frame_rate: float = 30.0
    audio_bitrate: int = 192  # kbps
    output_directory: str = "output"


@dataclass
class Project:
    """Represents a complete karaoke video project."""
    id: str
    name: str
    video_file: Optional[VideoFile] = None
    image_file: Optional[ImageFile] = None
    audio_file: Optional[AudioFile] = None
    subtitle_file: Optional[SubtitleFile] = None
    effects: List[Effect] = field(default_factory=list)
    export_settings: ExportSettings = field(default_factory=ExportSettings)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate project after initialization."""
        if not self.name:
            raise ValueError("Project name cannot be empty")
        
        # Ensure we have either video or image file
        if not self.video_file and not self.image_file:
            # This is allowed during project creation, but will be validated later
            pass
    
    def has_video_background(self) -> bool:
        """Check if project has a video background."""
        return self.video_file is not None
    
    def has_image_background(self) -> bool:
        """Check if project has an image background."""
        return self.image_file is not None
    
    def has_audio(self) -> bool:
        """Check if project has audio."""
        return self.audio_file is not None
    
    def has_subtitles(self) -> bool:
        """Check if project has subtitles."""
        return self.subtitle_file is not None
    
    def is_ready_for_export(self) -> bool:
        """Check if project has all required components for export."""
        has_background = self.has_video_background() or self.has_image_background()
        return has_background and self.has_audio() and self.has_subtitles()
    
    def update_modified_time(self):
        """Update the modified timestamp."""
        self.modified_at = datetime.now()