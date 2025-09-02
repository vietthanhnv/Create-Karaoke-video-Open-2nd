"""
Unit tests for core data models.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import os

from src.core.models import (
    VideoFile, AudioFile, ImageFile, SubtitleFile, SubtitleLine, SubtitleStyle,
    Effect, ExportSettings, Project, MediaType, VideoFormat, AudioFormat,
    ImageFormat, SubtitleFormat
)


class TestVideoFile:
    """Test cases for VideoFile data model."""
    
    def test_video_file_creation(self):
        """Test basic VideoFile creation."""
        video = VideoFile(path="/test/video.mp4")
        assert video.path == str(Path("/test/video.mp4").resolve())
        assert video.duration == 0.0
        assert video.resolution == {"width": 0, "height": 0}
        assert video.format == ""
        assert video.frame_rate == 0.0
        assert video.file_size == 0
    
    def test_video_file_with_metadata(self):
        """Test VideoFile creation with metadata."""
        video = VideoFile(
            path="/test/video.mp4",
            duration=120.5,
            resolution={"width": 1920, "height": 1080},
            format="mp4",
            frame_rate=30.0,
            file_size=1024000
        )
        assert video.duration == 120.5
        assert video.resolution["width"] == 1920
        assert video.resolution["height"] == 1080
        assert video.format == "mp4"
        assert video.frame_rate == 30.0
        assert video.file_size == 1024000
    
    def test_video_file_path_normalization(self):
        """Test that file paths are normalized."""
        video = VideoFile(path="./test/../video.mp4")
        # Path should be resolved to absolute path
        assert Path(video.path).is_absolute()


class TestAudioFile:
    """Test cases for AudioFile data model."""
    
    def test_audio_file_creation(self):
        """Test basic AudioFile creation."""
        audio = AudioFile(path="/test/audio.mp3")
        assert audio.path == str(Path("/test/audio.mp3").resolve())
        assert audio.duration == 0.0
        assert audio.format == ""
        assert audio.sample_rate == 0
        assert audio.channels == 0
        assert audio.bitrate == 0
        assert audio.file_size == 0
    
    def test_audio_file_with_metadata(self):
        """Test AudioFile creation with metadata."""
        audio = AudioFile(
            path="/test/audio.mp3",
            duration=180.0,
            format="mp3",
            sample_rate=44100,
            channels=2,
            bitrate=320,
            file_size=512000
        )
        assert audio.duration == 180.0
        assert audio.format == "mp3"
        assert audio.sample_rate == 44100
        assert audio.channels == 2
        assert audio.bitrate == 320
        assert audio.file_size == 512000


class TestImageFile:
    """Test cases for ImageFile data model."""
    
    def test_image_file_creation(self):
        """Test basic ImageFile creation."""
        image = ImageFile(path="/test/image.jpg")
        assert image.path == str(Path("/test/image.jpg").resolve())
        assert image.resolution == {"width": 0, "height": 0}
        assert image.format == ""
        assert image.file_size == 0
    
    def test_image_file_with_metadata(self):
        """Test ImageFile creation with metadata."""
        image = ImageFile(
            path="/test/image.jpg",
            resolution={"width": 1920, "height": 1080},
            format="jpg",
            file_size=256000
        )
        assert image.resolution["width"] == 1920
        assert image.resolution["height"] == 1080
        assert image.format == "jpg"
        assert image.file_size == 256000


class TestSubtitleLine:
    """Test cases for SubtitleLine data model."""
    
    def test_subtitle_line_creation(self):
        """Test basic SubtitleLine creation."""
        line = SubtitleLine(
            start_time=10.0,
            end_time=15.0,
            text="Hello world"
        )
        assert line.start_time == 10.0
        assert line.end_time == 15.0
        assert line.text == "Hello world"
        assert line.style == "Default"
    
    def test_subtitle_line_with_style(self):
        """Test SubtitleLine creation with custom style."""
        line = SubtitleLine(
            start_time=10.0,
            end_time=15.0,
            text="Hello world",
            style="CustomStyle"
        )
        assert line.style == "CustomStyle"
    
    def test_subtitle_line_negative_start_time(self):
        """Test that negative start time raises ValueError."""
        with pytest.raises(ValueError, match="Start time cannot be negative"):
            SubtitleLine(start_time=-1.0, end_time=5.0, text="Test")
    
    def test_subtitle_line_invalid_timing(self):
        """Test that end time <= start time raises ValueError."""
        with pytest.raises(ValueError, match="End time must be greater than start time"):
            SubtitleLine(start_time=10.0, end_time=10.0, text="Test")
        
        with pytest.raises(ValueError, match="End time must be greater than start time"):
            SubtitleLine(start_time=15.0, end_time=10.0, text="Test")


class TestSubtitleStyle:
    """Test cases for SubtitleStyle data model."""
    
    def test_subtitle_style_defaults(self):
        """Test SubtitleStyle creation with default values."""
        style = SubtitleStyle()
        assert style.name == "Default"
        assert style.font_name == "Arial"
        assert style.font_size == 20
        assert style.primary_color == "&H00FFFFFF"
        assert style.bold is False
        assert style.italic is False
        assert style.scale_x == 100.0
        assert style.alignment == 2
    
    def test_subtitle_style_custom(self):
        """Test SubtitleStyle creation with custom values."""
        style = SubtitleStyle(
            name="CustomStyle",
            font_name="Times New Roman",
            font_size=24,
            bold=True,
            italic=True
        )
        assert style.name == "CustomStyle"
        assert style.font_name == "Times New Roman"
        assert style.font_size == 24
        assert style.bold is True
        assert style.italic is True


class TestSubtitleFile:
    """Test cases for SubtitleFile data model."""
    
    def test_subtitle_file_creation(self):
        """Test basic SubtitleFile creation."""
        subtitle = SubtitleFile(path="/test/subtitle.ass")
        assert subtitle.path == str(Path("/test/subtitle.ass").resolve())
        assert subtitle.format == "ass"
        assert subtitle.lines == []
        assert len(subtitle.styles) == 0  # No default style added automatically
        assert subtitle.file_size == 0
    
    def test_subtitle_file_with_content(self):
        """Test SubtitleFile creation with content."""
        lines = [
            SubtitleLine(0.0, 5.0, "First line"),
            SubtitleLine(5.0, 10.0, "Second line")
        ]
        styles = [SubtitleStyle(name="CustomStyle")]
        
        subtitle = SubtitleFile(
            path="/test/subtitle.ass",
            lines=lines,
            styles=styles
        )
        assert len(subtitle.lines) == 2
        assert len(subtitle.styles) == 1
        assert subtitle.styles[0].name == "CustomStyle"


class TestEffect:
    """Test cases for Effect data model."""
    
    def test_effect_creation(self):
        """Test basic Effect creation."""
        effect = Effect(
            id="effect1",
            name="Glow Effect",
            type="glow"
        )
        assert effect.id == "effect1"
        assert effect.name == "Glow Effect"
        assert effect.type == "glow"
        assert effect.parameters == {}
        assert effect.enabled is True
    
    def test_effect_with_parameters(self):
        """Test Effect creation with parameters."""
        effect = Effect(
            id="effect1",
            name="Glow Effect",
            type="glow",
            parameters={"radius": 5, "color": "#FF0000"},
            enabled=False
        )
        assert effect.parameters["radius"] == 5
        assert effect.parameters["color"] == "#FF0000"
        assert effect.enabled is False


class TestExportSettings:
    """Test cases for ExportSettings data model."""
    
    def test_export_settings_defaults(self):
        """Test ExportSettings creation with default values."""
        settings = ExportSettings()
        assert settings.resolution == {"width": 1920, "height": 1080}
        assert settings.bitrate == 5000
        assert settings.format == "mp4"
        assert settings.quality == "high"
        assert settings.frame_rate == 30.0
        assert settings.audio_bitrate == 192
        assert settings.output_directory == "output"
    
    def test_export_settings_custom(self):
        """Test ExportSettings creation with custom values."""
        settings = ExportSettings(
            resolution={"width": 1280, "height": 720},
            bitrate=3000,
            quality="medium",
            frame_rate=24.0
        )
        assert settings.resolution["width"] == 1280
        assert settings.resolution["height"] == 720
        assert settings.bitrate == 3000
        assert settings.quality == "medium"
        assert settings.frame_rate == 24.0


class TestProject:
    """Test cases for Project data model."""
    
    def test_project_creation(self):
        """Test basic Project creation."""
        project = Project(id="proj1", name="Test Project")
        assert project.id == "proj1"
        assert project.name == "Test Project"
        assert project.video_file is None
        assert project.image_file is None
        assert project.audio_file is None
        assert project.subtitle_file is None
        assert project.effects == []
        assert isinstance(project.export_settings, ExportSettings)
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.modified_at, datetime)
    
    def test_project_empty_name(self):
        """Test that empty project name raises ValueError."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            Project(id="proj1", name="")
    
    def test_project_with_media_files(self):
        """Test Project creation with media files."""
        video = VideoFile(path="/test/video.mp4")
        audio = AudioFile(path="/test/audio.mp3")
        subtitle = SubtitleFile(path="/test/subtitle.ass")
        
        project = Project(
            id="proj1",
            name="Test Project",
            video_file=video,
            audio_file=audio,
            subtitle_file=subtitle
        )
        assert project.video_file == video
        assert project.audio_file == audio
        assert project.subtitle_file == subtitle
    
    def test_project_has_video_background(self):
        """Test has_video_background method."""
        project = Project(id="proj1", name="Test")
        assert not project.has_video_background()
        
        project.video_file = VideoFile(path="/test/video.mp4")
        assert project.has_video_background()
    
    def test_project_has_image_background(self):
        """Test has_image_background method."""
        project = Project(id="proj1", name="Test")
        assert not project.has_image_background()
        
        project.image_file = ImageFile(path="/test/image.jpg")
        assert project.has_image_background()
    
    def test_project_has_audio(self):
        """Test has_audio method."""
        project = Project(id="proj1", name="Test")
        assert not project.has_audio()
        
        project.audio_file = AudioFile(path="/test/audio.mp3")
        assert project.has_audio()
    
    def test_project_has_subtitles(self):
        """Test has_subtitles method."""
        project = Project(id="proj1", name="Test")
        assert not project.has_subtitles()
        
        project.subtitle_file = SubtitleFile(path="/test/subtitle.ass")
        assert project.has_subtitles()
    
    def test_project_is_ready_for_export(self):
        """Test is_ready_for_export method."""
        project = Project(id="proj1", name="Test")
        assert not project.is_ready_for_export()
        
        # Add video background, audio, and subtitles
        project.video_file = VideoFile(path="/test/video.mp4")
        project.audio_file = AudioFile(path="/test/audio.mp3")
        project.subtitle_file = SubtitleFile(path="/test/subtitle.ass")
        assert project.is_ready_for_export()
        
        # Test with image background instead of video
        project.video_file = None
        project.image_file = ImageFile(path="/test/image.jpg")
        assert project.is_ready_for_export()
        
        # Remove audio - should not be ready
        project.audio_file = None
        assert not project.is_ready_for_export()
    
    def test_project_update_modified_time(self):
        """Test update_modified_time method."""
        project = Project(id="proj1", name="Test")
        original_time = project.modified_at
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        project.update_modified_time()
        assert project.modified_at > original_time


class TestEnums:
    """Test cases for enum classes."""
    
    def test_media_type_enum(self):
        """Test MediaType enum values."""
        assert MediaType.VIDEO.value == "video"
        assert MediaType.AUDIO.value == "audio"
        assert MediaType.IMAGE.value == "image"
        assert MediaType.SUBTITLE.value == "subtitle"
    
    def test_video_format_enum(self):
        """Test VideoFormat enum values."""
        assert VideoFormat.MP4.value == "mp4"
        assert VideoFormat.MOV.value == "mov"
        assert VideoFormat.AVI.value == "avi"
    
    def test_audio_format_enum(self):
        """Test AudioFormat enum values."""
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.WAV.value == "wav"
        assert AudioFormat.AAC.value == "aac"
    
    def test_image_format_enum(self):
        """Test ImageFormat enum values."""
        assert ImageFormat.JPG.value == "jpg"
        assert ImageFormat.JPEG.value == "jpeg"
        assert ImageFormat.PNG.value == "png"
        assert ImageFormat.BMP.value == "bmp"
    
    def test_subtitle_format_enum(self):
        """Test SubtitleFormat enum values."""
        assert SubtitleFormat.ASS.value == "ass"