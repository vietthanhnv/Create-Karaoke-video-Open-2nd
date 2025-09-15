"""
Unit tests for audio processing functionality.
"""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from src.audio.audio_processor import AudioProcessor, AudioMetadata, TimingSyncResult
from src.core.models import AudioFile, SubtitleFile
from src.core.validation import ValidationError


class TestAudioProcessor:
    """Test cases for AudioProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = AudioProcessor()
        self.test_audio_path = "test_audio.mp3"
        
    def test_init(self):
        """Test AudioProcessor initialization."""
        processor = AudioProcessor()
        assert processor.supported_formats == {'.mp3', '.wav', '.flac', '.aac', '.m4a'}
    
    def test_load_audio_file_not_found(self):
        """Test loading non-existent audio file."""
        with pytest.raises(FileNotFoundError):
            self.processor.load_audio_file("nonexistent.mp3")
    
    def test_load_audio_file_unsupported_format(self):
        """Test loading unsupported audio format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            with pytest.raises(ValidationError) as exc_info:
                self.processor.load_audio_file(tmp_path)
            assert "Unsupported audio format" in str(exc_info.value)
        finally:
            os.unlink(tmp_path)
    
    @patch('src.audio.audio_processor.AudioProcessor.extract_metadata')
    def test_load_audio_file_success(self, mock_extract):
        """Test successful audio file loading."""
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Mock metadata extraction
            mock_metadata = AudioMetadata(
                duration=180.5,
                sample_rate=44100,
                channels=2,
                bitrate=128000,
                codec='mp3',
                format='mp3',
                file_size=2304000
            )
            mock_extract.return_value = mock_metadata
            
            # Load audio file
            audio_file = self.processor.load_audio_file(tmp_path)
            
            # Verify results
            assert isinstance(audio_file, AudioFile)
            assert audio_file.duration == 180.5
            assert audio_file.sample_rate == 44100
            assert audio_file.channels == 2
            assert audio_file.bitrate == 128000
            assert audio_file.format == 'mp3'
            assert audio_file.file_size == 2304000
            assert Path(audio_file.path).resolve() == Path(tmp_path).resolve()
            
        finally:
            os.unlink(tmp_path)
    
    @patch('subprocess.run')
    def test_extract_metadata_success(self, mock_run):
        """Test successful metadata extraction."""
        # Mock ffprobe output
        mock_output = {
            "streams": [{
                "codec_type": "audio",
                "codec_name": "mp3",
                "sample_rate": "44100",
                "channels": 2,
                "bit_rate": "128000"
            }],
            "format": {
                "duration": "180.5",
                "format_name": "mp3",
                "size": "2304000",
                "bit_rate": "128000"
            }
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_output),
            returncode=0
        )
        
        metadata = self.processor.extract_metadata("test.mp3")
        
        assert metadata.duration == 180.5
        assert metadata.sample_rate == 44100
        assert metadata.channels == 2
        assert metadata.bitrate == 128000
        assert metadata.codec == "mp3"
        assert metadata.format == "mp3"
        assert metadata.file_size == 2304000
    
    @patch('subprocess.run')
    def test_extract_metadata_no_audio_stream(self, mock_run):
        """Test metadata extraction with no audio stream."""
        mock_output = {
            "streams": [{
                "codec_type": "video",
                "codec_name": "h264"
            }],
            "format": {}
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(mock_output),
            returncode=0
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.processor.extract_metadata("test.mp4")
        assert "No audio stream found" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_extract_metadata_ffprobe_error(self, mock_run):
        """Test metadata extraction with ffprobe error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffprobe', stderr='Error message'
        )
        
        with pytest.raises(ValidationError) as exc_info:
            self.processor.extract_metadata("test.mp3")
        assert "FFprobe failed" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_extract_metadata_timeout(self, mock_run):
        """Test metadata extraction timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ffprobe', 30)
        
        with pytest.raises(ValidationError) as exc_info:
            self.processor.extract_metadata("test.mp3")
        assert "Timeout while extracting" in str(exc_info.value)
    
    def test_validate_audio_duration_no_subtitle(self):
        """Test audio duration validation without subtitle file."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        
        result = self.processor.validate_audio_duration(audio_file)
        
        assert isinstance(result, TimingSyncResult)
        assert result.is_synchronized == True
        assert result.audio_duration == 180.0
        assert result.subtitle_duration == 0.0
        assert result.timing_offset == 0.0
        assert len(result.errors) == 0
    
    def test_validate_audio_duration_with_subtitle(self):
        """Test audio duration validation with subtitle file."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        
        # Mock subtitle file with lines
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0),
            Mock(start_time=10.0, end_time=15.0),
            Mock(start_time=170.0, end_time=175.0)
        ]
        
        result = self.processor.validate_audio_duration(audio_file, subtitle_file)
        
        assert result.is_synchronized == True
        assert result.audio_duration == 180.0
        assert result.subtitle_duration == 175.0
        assert result.timing_offset == 5.0
        assert len(result.errors) == 0
    
    def test_validate_audio_duration_mismatch(self):
        """Test audio duration validation with significant mismatch."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        
        # Mock subtitle file with much shorter duration
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0),
            Mock(start_time=10.0, end_time=15.0),
            Mock(start_time=20.0, end_time=25.0)
        ]
        
        result = self.processor.validate_audio_duration(audio_file, subtitle_file)
        
        assert result.is_synchronized == False
        assert result.audio_duration == 180.0
        assert result.subtitle_duration == 25.0
        assert len(result.errors) > 0
        assert "Significant duration mismatch" in result.errors[0]
    
    def test_validate_audio_duration_invalid_audio(self):
        """Test validation with invalid audio properties."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=0.0,  # Invalid duration
            sample_rate=44100,
            channels=0  # Invalid channels
        )
        
        result = self.processor.validate_audio_duration(audio_file)
        
        assert result.is_synchronized == False
        assert "Audio duration is zero or negative" in result.errors
        assert "No audio channels detected" in result.errors
    
    def test_synchronize_timing(self):
        """Test timing synchronization."""
        audio_file = AudioFile(
            path="test.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2
        )
        
        # Mock subtitle file
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0),
            Mock(start_time=10.0, end_time=15.0)
        ]
        
        result = self.processor.synchronize_timing(
            audio_file, subtitle_file, target_offset=2.0
        )
        
        # Check that timing was adjusted
        assert subtitle_file.lines[0].start_time == 2.0
        assert subtitle_file.lines[0].end_time == 7.0
        assert subtitle_file.lines[1].start_time == 12.0
        assert subtitle_file.lines[1].end_time == 17.0
        
        assert result.timing_offset == 2.0
        assert any("Applied timing offset" in warning for warning in result.warnings)
    
    def test_create_ffmpeg_audio_args_default(self):
        """Test FFmpeg audio arguments creation with defaults."""
        audio_file = AudioFile(path="/path/to/audio.mp3")
        
        args = self.processor.create_ffmpeg_audio_args(audio_file)
        
        expected_args = [
            '-i', audio_file.path,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-q:a', '2'
        ]
        
        assert args == expected_args
    
    def test_create_ffmpeg_audio_args_custom(self):
        """Test FFmpeg audio arguments creation with custom settings."""
        audio_file = AudioFile(path="/path/to/audio.mp3")
        
        output_settings = {
            'audio_codec': 'mp3',
            'audio_bitrate': '192k',
            'audio_sample_rate': 48000,
            'audio_channels': 2
        }
        
        args = self.processor.create_ffmpeg_audio_args(audio_file, output_settings)
        
        expected_args = [
            '-i', audio_file.path,
            '-c:a', 'mp3',
            '-b:a', '192k',
            '-ar', '48000',
            '-ac', '2',
            '-q:a', '2'
        ]
        
        assert args == expected_args
    
    @patch('src.audio.audio_processor.AudioProcessor.extract_metadata')
    def test_get_audio_stream_info_success(self, mock_extract):
        """Test getting audio stream information."""
        mock_metadata = AudioMetadata(
            duration=180.5,
            sample_rate=44100,
            channels=2,
            bitrate=128000,
            codec='aac',
            format='m4a',
            file_size=2304000
        )
        mock_extract.return_value = mock_metadata
        
        info = self.processor.get_audio_stream_info("test.m4a")
        
        expected_info = {
            'duration': 180.5,
            'sample_rate': 44100,
            'channels': 2,
            'bitrate': 128000,
            'codec': 'aac',
            'format': 'm4a',
            'compatible_with_h264': True,
            'needs_conversion': False
        }
        
        assert info == expected_info
    
    @patch('src.audio.audio_processor.AudioProcessor.extract_metadata')
    def test_get_audio_stream_info_needs_conversion(self, mock_extract):
        """Test getting audio stream info for format needing conversion."""
        mock_metadata = AudioMetadata(
            duration=180.5,
            sample_rate=44100,
            channels=2,
            bitrate=128000,
            codec='flac',
            format='flac',
            file_size=2304000
        )
        mock_extract.return_value = mock_metadata
        
        info = self.processor.get_audio_stream_info("test.flac")
        
        assert info['compatible_with_h264'] == False
        assert info['needs_conversion'] == True
    
    @patch('src.audio.audio_processor.AudioProcessor.extract_metadata')
    def test_get_audio_stream_info_error(self, mock_extract):
        """Test getting audio stream info with error."""
        mock_extract.side_effect = ValidationError("Test error")
        
        info = self.processor.get_audio_stream_info("test.mp3")
        
        assert info == {}


class TestAudioMetadata:
    """Test cases for AudioMetadata dataclass."""
    
    def test_audio_metadata_creation(self):
        """Test AudioMetadata creation."""
        metadata = AudioMetadata(
            duration=180.5,
            sample_rate=44100,
            channels=2,
            bitrate=128000,
            codec='mp3',
            format='mp3',
            file_size=2304000
        )
        
        assert metadata.duration == 180.5
        assert metadata.sample_rate == 44100
        assert metadata.channels == 2
        assert metadata.bitrate == 128000
        assert metadata.codec == 'mp3'
        assert metadata.format == 'mp3'
        assert metadata.file_size == 2304000


class TestTimingSyncResult:
    """Test cases for TimingSyncResult dataclass."""
    
    def test_timing_sync_result_creation(self):
        """Test TimingSyncResult creation."""
        result = TimingSyncResult(
            is_synchronized=True,
            audio_duration=180.0,
            subtitle_duration=175.0,
            timing_offset=5.0,
            warnings=["Minor timing issue"],
            errors=[]
        )
        
        assert result.is_synchronized == True
        assert result.audio_duration == 180.0
        assert result.subtitle_duration == 175.0
        assert result.timing_offset == 5.0
        assert result.warnings == ["Minor timing issue"]
        assert result.errors == []