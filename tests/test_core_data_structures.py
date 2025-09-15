"""
Unit tests for core data structures and file validation.

Tests the implementation of task 2: Implement core data structures and file validation
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.models import (
    ProjectConfig, AudioFile, SubtitleFile, EffectsConfig, ExportSettings,
    KaraokeTimingInfo, SubtitleLine, AudioFormat
)
from src.core.validation import FileValidator, ValidationError, ValidationResult, ValidationLevel


class TestProjectConfig:
    """Test ProjectConfig data structure."""
    
    def test_project_config_creation(self):
        """Test basic ProjectConfig creation."""
        config = ProjectConfig(
            audio_file="test.mp3",
            subtitle_file="test.ass",
            background_image="test.jpg",
            width=1920,
            height=1080,
            fps=30.0
        )
        
        assert config.audio_file == "test.mp3"
        assert config.subtitle_file == "test.ass"
        assert config.background_image == "test.jpg"
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 30.0
    
    def test_project_config_validation(self):
        """Test ProjectConfig validation."""
        # Test invalid width
        with pytest.raises(ValueError, match="Width and height must be positive"):
            ProjectConfig(width=0, height=1080)
        
        # Test invalid height
        with pytest.raises(ValueError, match="Width and height must be positive"):
            ProjectConfig(width=1920, height=-1)
        
        # Test invalid fps
        with pytest.raises(ValueError, match="FPS must be positive"):
            ProjectConfig(fps=0)
        
        # Test invalid duration
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            ProjectConfig(duration=-1.0)


class TestAudioFile:
    """Test AudioFile data structure."""
    
    def test_audio_file_creation(self):
        """Test basic AudioFile creation."""
        audio = AudioFile(
            file_path="test.mp3",
            duration=180.5,
            sample_rate=44100,
            channels=2,
            format="mp3"
        )
        
        assert audio.file_path.endswith("test.mp3")
        assert audio.duration == 180.5
        assert audio.sample_rate == 44100
        assert audio.channels == 2
        assert audio.format == "mp3"
        assert audio.path.endswith("test.mp3")  # Test backward compatibility
    
    def test_audio_file_validation(self):
        """Test AudioFile validation."""
        # Test invalid duration
        with pytest.raises(ValueError, match="Duration cannot be negative"):
            AudioFile(file_path="test.mp3", duration=-1.0)
        
        # Test invalid sample rate
        with pytest.raises(ValueError, match="Sample rate cannot be negative"):
            AudioFile(file_path="test.mp3", sample_rate=-1)
        
        # Test invalid channels
        with pytest.raises(ValueError, match="Channels cannot be negative"):
            AudioFile(file_path="test.mp3", channels=-1)


class TestKaraokeTimingInfo:
    """Test KaraokeTimingInfo data structure."""
    
    def test_karaoke_timing_creation(self):
        """Test basic KaraokeTimingInfo creation."""
        timing = KaraokeTimingInfo(
            start_time=10.0,
            end_time=15.0,
            text="Hello world",
            syllable_count=2,
            syllable_timings=[2.5, 2.5]
        )
        
        assert timing.start_time == 10.0
        assert timing.end_time == 15.0
        assert timing.text == "Hello world"
        assert timing.syllable_count == 2
        assert timing.syllable_timings == [2.5, 2.5]
    
    def test_karaoke_timing_validation(self):
        """Test KaraokeTimingInfo validation."""
        # Test invalid start time
        with pytest.raises(ValueError, match="Start time cannot be negative"):
            KaraokeTimingInfo(start_time=-1.0, end_time=5.0, text="test")
        
        # Test invalid end time
        with pytest.raises(ValueError, match="End time must be greater than start time"):
            KaraokeTimingInfo(start_time=5.0, end_time=3.0, text="test")
        
        # Test invalid syllable count
        with pytest.raises(ValueError, match="Syllable count cannot be negative"):
            KaraokeTimingInfo(start_time=0.0, end_time=5.0, text="test", syllable_count=-1)


class TestSubtitleFile:
    """Test SubtitleFile data structure."""
    
    def test_subtitle_file_creation(self):
        """Test basic SubtitleFile creation."""
        subtitle = SubtitleFile(
            file_path="test.ass",
            line_count=10,
            format="ass"
        )
        
        assert subtitle.file_path.endswith("test.ass")
        assert subtitle.line_count == 10
        assert subtitle.format == "ass"
        assert subtitle.path.endswith("test.ass")  # Test backward compatibility
    
    def test_subtitle_file_validation(self):
        """Test SubtitleFile validation."""
        # Test invalid line count
        with pytest.raises(ValueError, match="Line count cannot be negative"):
            SubtitleFile(file_path="test.ass", line_count=-1)
    
    def test_has_karaoke_timing(self):
        """Test karaoke timing detection."""
        # Test with karaoke data
        karaoke_data = [KaraokeTimingInfo(0.0, 5.0, "test", 1, [2.5])]
        subtitle = SubtitleFile(file_path="test.ass", karaoke_data=karaoke_data)
        assert subtitle.has_karaoke_timing() is True
        
        # Test without karaoke data
        subtitle = SubtitleFile(file_path="test.ass")
        assert subtitle.has_karaoke_timing() is False


class TestEffectsConfig:
    """Test EffectsConfig data structure."""
    
    def test_effects_config_creation(self):
        """Test basic EffectsConfig creation."""
        effects = EffectsConfig(
            glow_enabled=True,
            glow_intensity=1.5,
            particles_enabled=True,
            particle_count=100
        )
        
        assert effects.glow_enabled is True
        assert effects.glow_intensity == 1.5
        assert effects.particles_enabled is True
        assert effects.particle_count == 100
    
    def test_effects_config_defaults(self):
        """Test EffectsConfig default values."""
        effects = EffectsConfig()
        
        assert effects.glow_enabled is False
        assert effects.glow_intensity == 1.0
        assert effects.particles_enabled is False
        assert effects.particle_count == 50
        assert effects.text_animation_enabled is False
        assert effects.color_transition_enabled is False
        assert effects.background_blur_enabled is False


class TestExportSettings:
    """Test ExportSettings data structure."""
    
    def test_export_settings_creation(self):
        """Test basic ExportSettings creation."""
        settings = ExportSettings(
            output_width=1920,
            output_height=1080,
            output_fps=30.0,
            bitrate=5000
        )
        
        assert settings.output_width == 1920
        assert settings.output_height == 1080
        assert settings.output_fps == 30.0
        assert settings.bitrate == 5000
    
    def test_resolution_property(self):
        """Test resolution property for backward compatibility."""
        settings = ExportSettings(resolution={"width": 1280, "height": 720})
        
        assert settings.resolution["width"] == 1280
        assert settings.resolution["height"] == 720
        assert settings.output_width == 1280
        assert settings.output_height == 720


class TestFileValidator:
    """Test FileValidator functionality."""
    
    def test_supported_audio_formats(self):
        """Test supported audio format validation."""
        # Test MP3
        assert FileValidator.get_file_extension("test.mp3") == ".mp3"
        assert ".mp3" in FileValidator.AUDIO_EXTENSIONS
        
        # Test WAV
        assert FileValidator.get_file_extension("test.wav") == ".wav"
        assert ".wav" in FileValidator.AUDIO_EXTENSIONS
        
        # Test FLAC
        assert FileValidator.get_file_extension("test.flac") == ".flac"
        assert ".flac" in FileValidator.AUDIO_EXTENSIONS
        
        # Test unsupported format
        assert FileValidator.get_file_extension("test.ogg") == ".ogg"
        assert ".ogg" not in FileValidator.AUDIO_EXTENSIONS
    
    def test_supported_image_formats(self):
        """Test supported image format validation."""
        # Test JPG
        assert ".jpg" in FileValidator.IMAGE_EXTENSIONS
        
        # Test PNG
        assert ".png" in FileValidator.IMAGE_EXTENSIONS
        
        # Test BMP
        assert ".bmp" in FileValidator.IMAGE_EXTENSIONS
    
    def test_supported_video_formats(self):
        """Test supported video format validation."""
        # Test MP4
        assert ".mp4" in FileValidator.VIDEO_EXTENSIONS
        
        # Test MOV
        assert ".mov" in FileValidator.VIDEO_EXTENSIONS
        
        # Test AVI
        assert ".avi" in FileValidator.VIDEO_EXTENSIONS
    
    def test_supported_subtitle_formats(self):
        """Test supported subtitle format validation."""
        # Test ASS
        assert ".ass" in FileValidator.SUBTITLE_EXTENSIONS
    
    def test_file_exists_validation(self):
        """Test file existence validation."""
        # Test non-existent file
        with pytest.raises(ValidationError, match="File does not exist"):
            FileValidator.validate_file_exists("nonexistent.mp3")
    
    def test_parse_ass_time(self):
        """Test ASS time format parsing."""
        # Test valid time format
        assert FileValidator._parse_ass_time("0:01:30.50") == 90.5
        assert FileValidator._parse_ass_time("1:00:00.00") == 3600.0
        assert FileValidator._parse_ass_time("0:00:05.25") == 5.25
        
        # Test invalid time format
        with pytest.raises(ValueError, match="Invalid ASS time format"):
            FileValidator._parse_ass_time("invalid")
    
    @patch('builtins.open', new_callable=mock_open, read_data="""[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,{\\k50}Hello {\\k50}world
""")
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('os.access', return_value=True)
    @patch('pathlib.Path.stat')
    def test_karaoke_timing_extraction(self, mock_stat, mock_access, mock_is_file, mock_exists, mock_file):
        """Test karaoke timing extraction from ASS files."""
        mock_stat.return_value.st_size = 1000
        
        karaoke_data = FileValidator.extract_karaoke_timing("test.ass")
        
        assert len(karaoke_data) == 1
        assert karaoke_data[0].start_time == 1.0
        assert karaoke_data[0].end_time == 5.0
        assert karaoke_data[0].syllable_count == 2
        assert karaoke_data[0].syllable_timings == [0.5, 0.5]  # 50 centiseconds = 0.5 seconds
    
    @patch('builtins.open', new_callable=mock_open, read_data="""[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,{\\k-10}Invalid timing
""")
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.is_file', return_value=True)
    @patch('os.access', return_value=True)
    def test_invalid_karaoke_timing_validation(self, mock_access, mock_is_file, mock_exists, mock_file):
        """Test validation of invalid karaoke timing."""
        with pytest.raises(ValidationError, match="Timing value cannot be negative"):
            FileValidator._validate_ass_format("test.ass")
    
    def test_project_config_validation(self):
        """Test comprehensive project configuration validation."""
        # Create a valid config
        config = ProjectConfig(
            audio_file="test.mp3",
            subtitle_file="test.ass",
            background_image="test.jpg",
            width=1920,
            height=1080,
            fps=30.0
        )
        
        # Mock file validation to avoid actual file system access
        with patch.object(FileValidator, 'validate_audio_file') as mock_audio, \
             patch.object(FileValidator, 'validate_subtitle_file') as mock_subtitle, \
             patch.object(FileValidator, 'validate_image_file') as mock_image, \
             patch.object(FileValidator, 'extract_karaoke_timing') as mock_karaoke:
            
            # Setup mocks
            mock_audio.return_value = AudioFile(file_path="test.mp3", format="mp3")
            mock_subtitle.return_value = SubtitleFile(file_path="test.ass", format="ass")
            mock_image.return_value = type('ImageFile', (), {'format': 'jpg'})()
            mock_karaoke.return_value = [KaraokeTimingInfo(0.0, 5.0, "test", 1, [2.5])]
            
            results = FileValidator.validate_project_config(config)
            
            # Should have no errors for valid config
            error_results = [r for r in results if r.level == ValidationLevel.ERROR]
            assert len(error_results) == 0
    
    def test_project_config_validation_errors(self):
        """Test project configuration validation with errors."""
        # Create config with missing required files
        config = ProjectConfig(
            width=1920,
            height=1080,
            fps=30.0
        )
        
        results = FileValidator.validate_project_config(config)
        
        # Should have errors for missing audio and subtitle files
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        assert len(error_results) >= 3  # audio, subtitle, and background errors
        
        # Check specific error messages
        error_messages = [r.message for r in error_results]
        assert any("Audio file is required" in msg for msg in error_messages)
        assert any("Subtitle file is required" in msg for msg in error_messages)
        assert any("Either background image or background video is required" in msg for msg in error_messages)


if __name__ == "__main__":
    pytest.main([__file__])