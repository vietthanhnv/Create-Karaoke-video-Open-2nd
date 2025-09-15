"""
Unit tests for file validation functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.validation import (
    FileValidator, ValidationError, validate_project_requirements
)
from src.core.models import (
    MediaType, VideoFile, AudioFile, ImageFile, SubtitleFile, Project
)


class TestFileValidator:
    """Test cases for FileValidator class."""
    
    def test_validate_file_exists_success(self):
        """Test successful file existence validation."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            result = FileValidator.validate_file_exists(tmp_path)
            assert result is True
        finally:
            os.unlink(tmp_path)
    
    def test_validate_file_exists_not_found(self):
        """Test file existence validation with non-existent file."""
        with pytest.raises(ValidationError, match="File does not exist"):
            FileValidator.validate_file_exists("/nonexistent/file.txt")
    
    def test_validate_file_exists_directory(self):
        """Test file existence validation with directory path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(ValidationError, match="Path is not a file"):
                FileValidator.validate_file_exists(tmp_dir)
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        assert FileValidator.get_file_extension("test.MP4") == ".mp4"
        assert FileValidator.get_file_extension("path/to/file.JPG") == ".jpg"
        assert FileValidator.get_file_extension("file.ass") == ".ass"
        assert FileValidator.get_file_extension("noextension") == ""
    
    def test_get_mime_type(self):
        """Test MIME type detection."""
        assert FileValidator.get_mime_type("test.mp4") == "video/mp4"
        assert FileValidator.get_mime_type("test.jpg") == "image/jpeg"
        assert FileValidator.get_mime_type("test.mp3") == "audio/mpeg"
        # Unknown extension should return None
        assert FileValidator.get_mime_type("test.unknown") is None


class TestVideoValidation:
    """Test cases for video file validation."""
    
    def test_validate_video_file_success(self):
        """Test successful video file validation."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(b"fake video content")
            tmp_path = tmp.name
        
        try:
            video = FileValidator.validate_video_file(tmp_path)
            assert isinstance(video, VideoFile)
            assert video.path == str(Path(tmp_path).resolve())
            assert video.format == "mp4"
            assert video.file_size > 0
        finally:
            os.unlink(tmp_path)
    
    def test_validate_video_file_unsupported_format(self):
        """Test video file validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            tmp.write(b"fake video content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Unsupported video format"):
                FileValidator.validate_video_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_video_file_supported_formats(self):
        """Test video file validation with all supported formats."""
        supported_formats = [".mp4", ".mov", ".avi"]
        
        for ext in supported_formats:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(b"fake video content")
                tmp_path = tmp.name
            
            try:
                video = FileValidator.validate_video_file(tmp_path)
                assert video.format == ext[1:]  # Remove the dot
            finally:
                os.unlink(tmp_path)


class TestAudioValidation:
    """Test cases for audio file validation."""
    
    def test_validate_audio_file_success(self):
        """Test successful audio file validation."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(b"fake audio content")
            tmp_path = tmp.name
        
        try:
            audio = FileValidator.validate_audio_file(tmp_path)
            assert isinstance(audio, AudioFile)
            assert audio.path == str(Path(tmp_path).resolve())
            assert audio.format == "mp3"
            assert audio.file_size > 0
        finally:
            os.unlink(tmp_path)
    
    def test_validate_audio_file_unsupported_format(self):
        """Test audio file validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(b"fake audio content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Unsupported audio format"):
                FileValidator.validate_audio_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_audio_file_supported_formats(self):
        """Test audio file validation with all supported formats."""
        supported_formats = [".mp3", ".wav", ".aac"]
        
        for ext in supported_formats:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(b"fake audio content")
                tmp_path = tmp.name
            
            try:
                audio = FileValidator.validate_audio_file(tmp_path)
                assert audio.format == ext[1:]  # Remove the dot
            finally:
                os.unlink(tmp_path)


class TestImageValidation:
    """Test cases for image file validation."""
    
    def test_validate_image_file_success(self):
        """Test successful image file validation."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(b"fake image content")
            tmp_path = tmp.name
        
        try:
            image = FileValidator.validate_image_file(tmp_path)
            assert isinstance(image, ImageFile)
            assert image.path == str(Path(tmp_path).resolve())
            assert image.format == "jpg"
            assert image.file_size > 0
        finally:
            os.unlink(tmp_path)
    
    def test_validate_image_file_unsupported_format(self):
        """Test image file validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as tmp:
            tmp.write(b"fake image content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Unsupported image format"):
                FileValidator.validate_image_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_image_file_supported_formats(self):
        """Test image file validation with all supported formats."""
        supported_formats = [".jpg", ".jpeg", ".png", ".bmp"]
        
        for ext in supported_formats:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(b"fake image content")
                tmp_path = tmp.name
            
            try:
                image = FileValidator.validate_image_file(tmp_path)
                # Both .jpg and .jpeg should result in "jpg" format
                expected_format = "jpg" if ext in [".jpg", ".jpeg"] else ext[1:]
                assert image.format == expected_format
            finally:
                os.unlink(tmp_path)


class TestSubtitleValidation:
    """Test cases for subtitle file validation."""
    
    def create_valid_ass_content(self):
        """Create valid ASS file content for testing."""
        return """[Script Info]
Title: Test Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,Test subtitle line
"""
    
    def test_validate_subtitle_file_success(self):
        """Test successful subtitle file validation."""
        content = self.create_valid_ass_content()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".ass", delete=False, encoding='utf-8') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            subtitle = FileValidator.validate_subtitle_file(tmp_path)
            assert isinstance(subtitle, SubtitleFile)
            assert subtitle.path == str(Path(tmp_path).resolve())
            assert subtitle.format == "ass"
            assert subtitle.file_size > 0
        finally:
            os.unlink(tmp_path)
    
    def test_validate_subtitle_file_unsupported_format(self):
        """Test subtitle file validation with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
            tmp.write(b"fake subtitle content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Unsupported subtitle format"):
                FileValidator.validate_subtitle_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_ass_format_missing_sections(self):
        """Test ASS format validation with missing required sections."""
        invalid_content = """[Script Info]
Title: Test Subtitle

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".ass", delete=False, encoding='utf-8') as tmp:
            tmp.write(invalid_content)
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Missing required section"):
                FileValidator.validate_subtitle_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_ass_format_invalid_encoding(self):
        """Test ASS format validation with invalid encoding."""
        # Create file with invalid UTF-8 content
        with tempfile.NamedTemporaryFile(mode='wb', suffix=".ass", delete=False) as tmp:
            tmp.write(b'\xff\xfe\x00\x00')  # Invalid UTF-8 bytes
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="File encoding is not UTF-8"):
                FileValidator.validate_subtitle_file(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestMediaFileValidation:
    """Test cases for generic media file validation."""
    
    def test_validate_media_file_video(self):
        """Test generic media file validation for video."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(b"fake video content")
            tmp_path = tmp.name
        
        try:
            result = FileValidator.validate_media_file(tmp_path, MediaType.VIDEO)
            assert isinstance(result, VideoFile)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_media_file_audio(self):
        """Test generic media file validation for audio."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(b"fake audio content")
            tmp_path = tmp.name
        
        try:
            result = FileValidator.validate_media_file(tmp_path, MediaType.AUDIO)
            assert isinstance(result, AudioFile)
        finally:
            os.unlink(tmp_path)
    
    def test_validate_media_file_unknown_type(self):
        """Test generic media file validation with unknown type."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(b"fake content")
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError, match="Unknown media type"):
                FileValidator.validate_media_file(tmp_path, "unknown_type")
        finally:
            os.unlink(tmp_path)


class TestSupportedExtensions:
    """Test cases for supported extensions functionality."""
    
    def test_get_supported_extensions_video(self):
        """Test getting supported video extensions."""
        extensions = FileValidator.get_supported_extensions(MediaType.VIDEO)
        assert ".mp4" in extensions
        assert ".mov" in extensions
        assert ".avi" in extensions
        assert len(extensions) == 3
    
    def test_get_supported_extensions_audio(self):
        """Test getting supported audio extensions."""
        extensions = FileValidator.get_supported_extensions(MediaType.AUDIO)
        assert ".mp3" in extensions
        assert ".wav" in extensions
        assert ".aac" in extensions
        assert ".flac" in extensions
        assert len(extensions) == 4
    
    def test_get_supported_extensions_image(self):
        """Test getting supported image extensions."""
        extensions = FileValidator.get_supported_extensions(MediaType.IMAGE)
        assert ".jpg" in extensions
        assert ".jpeg" in extensions
        assert ".png" in extensions
        assert ".bmp" in extensions
        assert len(extensions) == 4
    
    def test_get_supported_extensions_subtitle(self):
        """Test getting supported subtitle extensions."""
        extensions = FileValidator.get_supported_extensions(MediaType.SUBTITLE)
        assert ".ass" in extensions
        assert len(extensions) == 1
    
    def test_is_supported_format(self):
        """Test format support checking."""
        assert FileValidator.is_supported_format("test.mp4", MediaType.VIDEO)
        assert FileValidator.is_supported_format("test.MP4", MediaType.VIDEO)  # Case insensitive
        assert not FileValidator.is_supported_format("test.mkv", MediaType.VIDEO)
        
        assert FileValidator.is_supported_format("test.mp3", MediaType.AUDIO)
        assert not FileValidator.is_supported_format("test.ogg", MediaType.AUDIO)
        
        assert FileValidator.is_supported_format("test.jpg", MediaType.IMAGE)
        assert not FileValidator.is_supported_format("test.gif", MediaType.IMAGE)
        
        assert FileValidator.is_supported_format("test.ass", MediaType.SUBTITLE)
        assert not FileValidator.is_supported_format("test.srt", MediaType.SUBTITLE)


class TestProjectValidation:
    """Test cases for project validation."""
    
    def test_validate_project_requirements_empty_project(self):
        """Test project validation with empty project."""
        project = Project(id="test", name="Test Project")
        errors = validate_project_requirements(project)
        
        assert len(errors) == 3
        assert any("video file or image background" in error for error in errors)
        assert any("audio file" in error for error in errors)
        assert any("subtitle file" in error for error in errors)
    
    def test_validate_project_requirements_complete_project(self):
        """Test project validation with complete project."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_tmp:
            video_tmp.write(b"fake video")
            video_path = video_tmp.name
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_tmp:
            audio_tmp.write(b"fake audio")
            audio_path = audio_tmp.name
        
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as subtitle_tmp:
            subtitle_tmp.write(b"fake subtitle")
            subtitle_path = subtitle_tmp.name
        
        try:
            project = Project(
                id="test",
                name="Test Project",
                video_file=VideoFile(path=video_path),
                audio_file=AudioFile(path=audio_path),
                subtitle_file=SubtitleFile(path=subtitle_path)
            )
            
            errors = validate_project_requirements(project)
            assert len(errors) == 0
        finally:
            os.unlink(video_path)
            os.unlink(audio_path)
            os.unlink(subtitle_path)
    
    def test_validate_project_requirements_image_background(self):
        """Test project validation with image background instead of video."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image_tmp:
            image_tmp.write(b"fake image")
            image_path = image_tmp.name
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_tmp:
            audio_tmp.write(b"fake audio")
            audio_path = audio_tmp.name
        
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as subtitle_tmp:
            subtitle_tmp.write(b"fake subtitle")
            subtitle_path = subtitle_tmp.name
        
        try:
            project = Project(
                id="test",
                name="Test Project",
                image_file=ImageFile(path=image_path),
                audio_file=AudioFile(path=audio_path),
                subtitle_file=SubtitleFile(path=subtitle_path)
            )
            
            errors = validate_project_requirements(project)
            assert len(errors) == 0
        finally:
            os.unlink(image_path)
            os.unlink(audio_path)
            os.unlink(subtitle_path)
    
    def test_validate_project_requirements_missing_files(self):
        """Test project validation with missing files."""
        project = Project(
            id="test",
            name="Test Project",
            video_file=VideoFile(path="/nonexistent/video.mp4"),
            audio_file=AudioFile(path="/nonexistent/audio.mp3"),
            subtitle_file=SubtitleFile(path="/nonexistent/subtitle.ass")
        )
        
        errors = validate_project_requirements(project)
        assert len(errors) == 3  # Three file not found errors
        assert all("File does not exist" in error for error in errors)