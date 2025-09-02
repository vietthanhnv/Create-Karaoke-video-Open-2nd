"""
Unit tests for the MediaImporter class and import functionality.
"""

import unittest
import tempfile
import os
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.core.media_importer import MediaImporter, MediaImportError
from src.core.models import VideoFile, AudioFile, ImageFile, SubtitleFile, MediaType
from src.core.validation import ValidationError


class TestMediaImporter(unittest.TestCase):
    """Test cases for MediaImporter class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.importer = MediaImporter()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        self.test_audio_path = os.path.join(self.temp_dir, "test_audio.mp3")
        self.test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        self.test_subtitle_path = os.path.join(self.temp_dir, "test_subtitle.ass")
        
        # Create dummy files
        for path in [self.test_video_path, self.test_audio_path, 
                     self.test_image_path, self.test_subtitle_path]:
            with open(path, 'w') as f:
                f.write("dummy content")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test MediaImporter initialization"""
        importer = MediaImporter()
        self.assertIsNotNone(importer)
        self.assertIsNone(importer.parent)
    
    def test_init_with_parent(self):
        """Test MediaImporter initialization with parent widget"""
        parent = Mock()
        importer = MediaImporter(parent)
        self.assertEqual(importer.parent, parent)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_find_ffmpeg_success(self, mock_run):
        """Test successful FFmpeg detection"""
        mock_run.return_value.stdout = "C:\\ffmpeg\\bin\\ffmpeg.exe\n"
        mock_run.return_value.returncode = 0
        
        importer = MediaImporter()
        # Access private method for testing
        ffmpeg_path = importer._find_ffmpeg()
        self.assertEqual(ffmpeg_path, "C:\\ffmpeg\\bin\\ffmpeg.exe")
    
    @patch('src.core.media_importer.subprocess.run')
    def test_find_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg not found"""
        mock_run.side_effect = FileNotFoundError()
        
        importer = MediaImporter()
        ffmpeg_path = importer._find_ffmpeg()
        self.assertIsNone(ffmpeg_path)
    
    @patch('src.core.validation.FileValidator.validate_video_file')
    @patch.object(MediaImporter, '_extract_video_metadata')
    def test_import_video_success(self, mock_extract, mock_validate):
        """Test successful video import"""
        # Setup mocks
        video_file = VideoFile(path=self.test_video_path)
        mock_validate.return_value = video_file
        mock_extract.return_value = {
            'duration': 120.5,
            'width': 1920,
            'height': 1080,
            'frame_rate': 30.0
        }
        
        # Test import
        result = self.importer.import_video(self.test_video_path)
        
        # Verify results
        self.assertIsInstance(result, VideoFile)
        self.assertEqual(result.duration, 120.5)
        self.assertEqual(result.resolution['width'], 1920)
        self.assertEqual(result.resolution['height'], 1080)
        self.assertEqual(result.frame_rate, 30.0)
        
        mock_validate.assert_called_once_with(self.test_video_path)
        mock_extract.assert_called_once_with(self.test_video_path)
    
    @patch('src.core.validation.FileValidator.validate_video_file')
    def test_import_video_validation_error(self, mock_validate):
        """Test video import with validation error"""
        mock_validate.side_effect = ValidationError("Invalid video format")
        
        with self.assertRaises(MediaImportError) as context:
            self.importer.import_video(self.test_video_path)
        
        self.assertIn("Invalid video format", str(context.exception))
    
    @patch('src.core.validation.FileValidator.validate_audio_file')
    @patch.object(MediaImporter, '_extract_audio_metadata')
    def test_import_audio_success(self, mock_extract, mock_validate):
        """Test successful audio import"""
        # Setup mocks
        audio_file = AudioFile(path=self.test_audio_path)
        mock_validate.return_value = audio_file
        mock_extract.return_value = {
            'duration': 180.0,
            'sample_rate': 44100,
            'channels': 2,
            'bitrate': 320000
        }
        
        # Test import
        result = self.importer.import_audio(self.test_audio_path)
        
        # Verify results
        self.assertIsInstance(result, AudioFile)
        self.assertEqual(result.duration, 180.0)
        self.assertEqual(result.sample_rate, 44100)
        self.assertEqual(result.channels, 2)
        self.assertEqual(result.bitrate, 320000)
    
    @patch('src.core.validation.FileValidator.validate_image_file')
    @patch.object(MediaImporter, '_extract_image_metadata')
    def test_import_image_success(self, mock_extract, mock_validate):
        """Test successful image import"""
        # Setup mocks
        image_file = ImageFile(path=self.test_image_path)
        mock_validate.return_value = image_file
        mock_extract.return_value = {
            'width': 1920,
            'height': 1080
        }
        
        # Test import
        result = self.importer.import_image(self.test_image_path)
        
        # Verify results
        self.assertIsInstance(result, ImageFile)
        self.assertEqual(result.resolution['width'], 1920)
        self.assertEqual(result.resolution['height'], 1080)
    
    @patch('src.core.validation.FileValidator.validate_subtitle_file')
    def test_import_subtitles_success(self, mock_validate):
        """Test successful subtitle import"""
        # Setup mock
        subtitle_file = SubtitleFile(path=self.test_subtitle_path)
        mock_validate.return_value = subtitle_file
        
        # Test import
        result = self.importer.import_subtitles(self.test_subtitle_path)
        
        # Verify results
        self.assertIsInstance(result, SubtitleFile)
        self.assertEqual(result.path, self.test_subtitle_path)
    
    @patch('src.core.validation.FileValidator.validate_media_file')
    def test_validate_file_success(self, mock_validate):
        """Test successful file validation"""
        mock_validate.return_value = VideoFile(path=self.test_video_path)
        
        result = self.importer.validate_file(self.test_video_path, MediaType.VIDEO)
        self.assertTrue(result)
    
    @patch('src.core.validation.FileValidator.validate_media_file')
    def test_validate_file_failure(self, mock_validate):
        """Test file validation failure"""
        mock_validate.side_effect = ValidationError("Invalid format")
        
        result = self.importer.validate_file(self.test_video_path, MediaType.VIDEO)
        self.assertFalse(result)
    
    def test_create_file_filter(self):
        """Test file filter creation for dialogs"""
        extensions = ['.mp4', '.mov', '.avi']
        filter_str = self.importer._create_file_filter("Video Files", extensions)
        
        expected = "Video Files (*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI);;All Files (*)"
        self.assertEqual(filter_str, expected)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_extract_video_metadata_success(self, mock_run):
        """Test successful video metadata extraction"""
        # Mock FFmpeg output
        ffmpeg_output = {
            "streams": [{
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "codec_name": "h264"
            }],
            "format": {
                "duration": "120.5",
                "bit_rate": "5000000"
            }
        }
        
        mock_run.return_value.stdout = json.dumps(ffmpeg_output)
        mock_run.return_value.returncode = 0
        
        # Set FFmpeg path for testing
        self.importer._ffmpeg_path = "ffmpeg"
        
        metadata = self.importer._extract_video_metadata(self.test_video_path)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['duration'], 120.5)
        self.assertEqual(metadata['width'], 1920)
        self.assertEqual(metadata['height'], 1080)
        self.assertEqual(metadata['frame_rate'], 30.0)
        self.assertEqual(metadata['codec'], 'h264')
    
    @patch('src.core.media_importer.subprocess.run')
    def test_extract_audio_metadata_success(self, mock_run):
        """Test successful audio metadata extraction"""
        # Mock FFmpeg output
        ffmpeg_output = {
            "streams": [{
                "codec_type": "audio",
                "sample_rate": "44100",
                "channels": 2,
                "bit_rate": "320000",
                "codec_name": "mp3"
            }],
            "format": {
                "duration": "180.0"
            }
        }
        
        mock_run.return_value.stdout = json.dumps(ffmpeg_output)
        mock_run.return_value.returncode = 0
        
        # Set FFmpeg path for testing
        self.importer._ffmpeg_path = "ffmpeg"
        
        metadata = self.importer._extract_audio_metadata(self.test_audio_path)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['duration'], 180.0)
        self.assertEqual(metadata['sample_rate'], 44100)
        self.assertEqual(metadata['channels'], 2)
        self.assertEqual(metadata['bitrate'], 320000)
        self.assertEqual(metadata['codec'], 'mp3')
    
    @patch('src.core.media_importer.subprocess.run')
    def test_extract_image_metadata_success(self, mock_run):
        """Test successful image metadata extraction"""
        # Mock FFmpeg output
        ffmpeg_output = {
            "streams": [{
                "width": 1920,
                "height": 1080,
                "codec_name": "mjpeg",
                "pix_fmt": "yuvj420p"
            }]
        }
        
        mock_run.return_value.stdout = json.dumps(ffmpeg_output)
        mock_run.return_value.returncode = 0
        
        # Set FFmpeg path for testing
        self.importer._ffmpeg_path = "ffmpeg"
        
        metadata = self.importer._extract_image_metadata(self.test_image_path)
        
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['width'], 1920)
        self.assertEqual(metadata['height'], 1080)
        self.assertEqual(metadata['codec'], 'mjpeg')
    
    def test_extract_metadata_no_ffmpeg(self):
        """Test metadata extraction when FFmpeg is not available"""
        self.importer._ffmpeg_path = None
        
        video_metadata = self.importer._extract_video_metadata(self.test_video_path)
        audio_metadata = self.importer._extract_audio_metadata(self.test_audio_path)
        image_metadata = self.importer._extract_image_metadata(self.test_image_path)
        
        self.assertIsNone(video_metadata)
        self.assertIsNone(audio_metadata)
        self.assertIsNone(image_metadata)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_extract_metadata_ffmpeg_error(self, mock_run):
        """Test metadata extraction when FFmpeg fails"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'ffprobe')
        
        # Set FFmpeg path for testing
        self.importer._ffmpeg_path = "ffmpeg"
        
        metadata = self.importer._extract_video_metadata(self.test_video_path)
        self.assertIsNone(metadata)
    
    def test_parse_frame_rate(self):
        """Test frame rate parsing"""
        # Test fraction format
        self.assertEqual(self.importer._parse_frame_rate("30/1"), 30.0)
        self.assertEqual(self.importer._parse_frame_rate("24000/1001"), 23.976023976023978)
        
        # Test decimal format
        self.assertEqual(self.importer._parse_frame_rate("29.97"), 29.97)
        
        # Test invalid format
        self.assertEqual(self.importer._parse_frame_rate("invalid"), 0.0)
        self.assertEqual(self.importer._parse_frame_rate("30/0"), 0.0)
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        formats = self.importer.get_supported_formats()
        
        self.assertIn('video', formats)
        self.assertIn('audio', formats)
        self.assertIn('image', formats)
        self.assertIn('subtitle', formats)
        
        self.assertIn('.mp4', formats['video'])
        self.assertIn('.mp3', formats['audio'])
        self.assertIn('.jpg', formats['image'])
        self.assertIn('.ass', formats['subtitle'])
    
    def test_signals_emitted(self):
        """Test that signals are emitted correctly"""
        # Create signal spies
        import_started_spy = Mock()
        import_completed_spy = Mock()
        import_failed_spy = Mock()
        
        self.importer.import_started.connect(import_started_spy)
        self.importer.import_completed.connect(import_completed_spy)
        self.importer.import_failed.connect(import_failed_spy)
        
        # Test successful import
        with patch('src.core.validation.FileValidator.validate_video_file') as mock_validate:
            video_file = VideoFile(path=self.test_video_path)
            mock_validate.return_value = video_file
            
            with patch.object(self.importer, '_extract_video_metadata', return_value=None):
                result = self.importer.import_video(self.test_video_path)
                
                import_started_spy.assert_called_once_with(self.test_video_path)
                import_completed_spy.assert_called_once_with(video_file)
                import_failed_spy.assert_not_called()
        
        # Reset spies
        import_started_spy.reset_mock()
        import_completed_spy.reset_mock()
        import_failed_spy.reset_mock()
        
        # Test failed import
        with patch('src.core.validation.FileValidator.validate_video_file') as mock_validate:
            mock_validate.side_effect = ValidationError("Test error")
            
            with self.assertRaises(MediaImportError):
                self.importer.import_video(self.test_video_path)
            
            import_started_spy.assert_called_once_with(self.test_video_path)
            import_completed_spy.assert_not_called()
            import_failed_spy.assert_called_once_with(self.test_video_path, "Test error")


if __name__ == '__main__':
    unittest.main()