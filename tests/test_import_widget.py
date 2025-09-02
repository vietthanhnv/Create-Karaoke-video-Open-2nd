"""
Unit tests for the ImportWidget class and UI functionality.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QUrl, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from src.ui.import_widget import ImportWidget
from src.core.models import VideoFile, AudioFile, ImageFile, SubtitleFile
from src.core.media_importer import MediaImportError


class TestImportWidget(unittest.TestCase):
    """Test cases for ImportWidget class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for widget testing"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures"""
        self.widget = ImportWidget()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test file paths
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
        self.widget.close()
    
    def test_init(self):
        """Test ImportWidget initialization"""
        widget = ImportWidget()
        self.assertIsNotNone(widget.media_importer)
        self.assertEqual(widget._imported_files, {})
        self.assertTrue(widget.acceptDrops())
    
    def test_drag_drop_setup(self):
        """Test drag and drop is properly enabled"""
        self.assertTrue(self.widget.acceptDrops())
    
    @patch.object(ImportWidget, '_show_error')
    def test_select_video_file_success(self, mock_show_error):
        """Test successful video file selection"""
        video_file = VideoFile(path=self.test_video_path, duration=120.0)
        
        with patch.object(self.widget.media_importer, 'import_video', return_value=video_file):
            # Connect signal spy
            signal_spy = Mock()
            self.widget.video_imported.connect(signal_spy)
            
            self.widget._select_video_file()
            
            # Verify file was imported and signal emitted
            self.assertEqual(self.widget._imported_files['video'], video_file)
            signal_spy.assert_called_once_with(video_file)
            mock_show_error.assert_not_called()
    
    @patch.object(ImportWidget, '_show_error')
    def test_select_video_file_error(self, mock_show_error):
        """Test video file selection with error"""
        with patch.object(self.widget.media_importer, 'import_video', 
                         side_effect=MediaImportError("Test error")):
            self.widget._select_video_file()
            
            mock_show_error.assert_called_once_with("Video Import Error", "Test error")
            self.assertNotIn('video', self.widget._imported_files)
    
    @patch.object(ImportWidget, '_show_error')
    def test_select_audio_file_success(self, mock_show_error):
        """Test successful audio file selection"""
        audio_file = AudioFile(path=self.test_audio_path, duration=180.0)
        
        with patch.object(self.widget.media_importer, 'import_audio', return_value=audio_file):
            # Connect signal spy
            signal_spy = Mock()
            self.widget.audio_imported.connect(signal_spy)
            
            self.widget._select_audio_file()
            
            # Verify file was imported and signal emitted
            self.assertEqual(self.widget._imported_files['audio'], audio_file)
            signal_spy.assert_called_once_with(audio_file)
            mock_show_error.assert_not_called()
    
    @patch.object(ImportWidget, '_show_error')
    def test_select_image_file_success(self, mock_show_error):
        """Test successful image file selection"""
        image_file = ImageFile(path=self.test_image_path)
        
        with patch.object(self.widget.media_importer, 'import_image', return_value=image_file):
            # Connect signal spy
            signal_spy = Mock()
            self.widget.image_imported.connect(signal_spy)
            
            self.widget._select_image_file()
            
            # Verify file was imported and signal emitted
            self.assertEqual(self.widget._imported_files['image'], image_file)
            signal_spy.assert_called_once_with(image_file)
            mock_show_error.assert_not_called()
    
    @patch.object(ImportWidget, '_show_error')
    def test_select_subtitle_file_success(self, mock_show_error):
        """Test successful subtitle file selection"""
        subtitle_file = SubtitleFile(path=self.test_subtitle_path)
        
        with patch.object(self.widget.media_importer, 'import_subtitles', return_value=subtitle_file):
            # Connect signal spy
            signal_spy = Mock()
            self.widget.subtitle_imported.connect(signal_spy)
            
            self.widget._select_subtitle_file()
            
            # Verify file was imported and signal emitted
            self.assertEqual(self.widget._imported_files['subtitle'], subtitle_file)
            signal_spy.assert_called_once_with(subtitle_file)
            mock_show_error.assert_not_called()
    
    def test_is_supported_file(self):
        """Test supported file detection"""
        with patch.object(self.widget.media_importer, 'validate_file') as mock_validate:
            # Test supported file
            mock_validate.return_value = True
            result = self.widget._is_supported_file(self.test_video_path)
            self.assertTrue(result)
            
            # Test unsupported file
            mock_validate.return_value = False
            result = self.widget._is_supported_file("unsupported.xyz")
            self.assertFalse(result)
    
    def test_drag_enter_event_supported_file(self):
        """Test drag enter event with supported file"""
        # Create mock drag event
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(self.test_video_path)]
        mime_data.setUrls(urls)
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        with patch.object(self.widget, '_is_supported_file', return_value=True):
            self.widget.dragEnterEvent(event)
            event.acceptProposedAction.assert_called_once()
    
    def test_drag_enter_event_unsupported_file(self):
        """Test drag enter event with unsupported file"""
        # Create mock drag event
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile("unsupported.xyz")]
        mime_data.setUrls(urls)
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        with patch.object(self.widget, '_is_supported_file', return_value=False):
            self.widget.dragEnterEvent(event)
            event.ignore.assert_called_once()
    
    def test_drop_event(self):
        """Test file drop event"""
        # Create mock drop event
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(self.test_video_path)]
        mime_data.setUrls(urls)
        
        event = Mock()
        event.mimeData.return_value = mime_data
        
        with patch.object(self.widget, '_import_dropped_file') as mock_import:
            self.widget.dropEvent(event)
            # Use Path to normalize the path for comparison
            expected_path = str(Path(self.test_video_path))
            actual_path = str(Path(mock_import.call_args[0][0]))
            self.assertEqual(actual_path, expected_path)
            event.acceptProposedAction.assert_called_once()
    
    @patch.object(ImportWidget, '_show_error')
    def test_import_dropped_file_video(self, mock_show_error):
        """Test importing dropped video file"""
        video_file = VideoFile(path=self.test_video_path)
        
        with patch.object(self.widget.media_importer, 'validate_file', return_value=True) as mock_validate:
            with patch.object(self.widget.media_importer, 'import_video', return_value=video_file):
                signal_spy = Mock()
                self.widget.video_imported.connect(signal_spy)
                
                self.widget._import_dropped_file(self.test_video_path)
                
                self.assertEqual(self.widget._imported_files['video'], video_file)
                signal_spy.assert_called_once_with(video_file)
                mock_show_error.assert_not_called()
    
    @patch.object(ImportWidget, '_show_error')
    def test_import_dropped_file_unsupported(self, mock_show_error):
        """Test importing unsupported dropped file"""
        with patch.object(self.widget.media_importer, 'validate_file', return_value=False):
            self.widget._import_dropped_file("unsupported.xyz")
            
            mock_show_error.assert_called_once()
            error_args = mock_show_error.call_args[0]
            self.assertEqual(error_args[0], "Unsupported File")
            self.assertIn("File format not supported", error_args[1])
    
    def test_on_import_started(self):
        """Test import started signal handler"""
        self.widget._on_import_started(self.test_video_path)
        
        # Check that info display was updated
        text = self.widget.info_display.toPlainText()
        self.assertIn("Importing test_video.mp4", text)
    
    def test_on_import_completed_video(self):
        """Test import completed signal handler for video"""
        video_file = VideoFile(
            path=self.test_video_path,
            duration=120.5,
            resolution={'width': 1920, 'height': 1080},
            frame_rate=30.0,
            file_size=1024000
        )
        
        self.widget._on_import_completed(video_file)
        
        text = self.widget.info_display.toPlainText()
        self.assertIn("✓ Video: test_video.mp4", text)
        self.assertIn("Duration: 02:00", text)
        self.assertIn("Resolution: 1920x1080", text)
        self.assertIn("Frame Rate: 30.00 fps", text)
        self.assertIn("Size: 1000.0 KB", text)
    
    def test_on_import_completed_audio(self):
        """Test import completed signal handler for audio"""
        audio_file = AudioFile(
            path=self.test_audio_path,
            duration=180.0,
            sample_rate=44100,
            channels=2,
            file_size=5120000
        )
        
        self.widget._on_import_completed(audio_file)
        
        text = self.widget.info_display.toPlainText()
        self.assertIn("✓ Audio: test_audio.mp3", text)
        self.assertIn("Duration: 03:00", text)
        self.assertIn("Sample Rate: 44100 Hz", text)
        self.assertIn("Channels: 2", text)
        self.assertIn("Size: 4.9 MB", text)  # 5120000 bytes = 4.88 MB, rounded to 4.9
    
    def test_on_import_failed(self):
        """Test import failed signal handler"""
        error_spy = Mock()
        self.widget.import_error.connect(error_spy)
        
        self.widget._on_import_failed(self.test_video_path, "Test error message")
        
        text = self.widget.info_display.toPlainText()
        self.assertIn("✗ Failed to import test_video.mp4: Test error message", text)
        error_spy.assert_called_once_with(self.test_video_path, "Test error message")
    
    def test_format_duration(self):
        """Test duration formatting"""
        self.assertEqual(self.widget._format_duration(65), "01:05")
        self.assertEqual(self.widget._format_duration(120), "02:00")
        self.assertEqual(self.widget._format_duration(3661), "61:01")
    
    def test_format_file_size(self):
        """Test file size formatting"""
        self.assertEqual(self.widget._format_file_size(512), "512.0 B")
        self.assertEqual(self.widget._format_file_size(1024), "1.0 KB")
        self.assertEqual(self.widget._format_file_size(1048576), "1.0 MB")
        self.assertEqual(self.widget._format_file_size(1073741824), "1.0 GB")
    
    def test_get_imported_files(self):
        """Test getting imported files"""
        video_file = VideoFile(path=self.test_video_path)
        self.widget._imported_files['video'] = video_file
        
        files = self.widget.get_imported_files()
        self.assertEqual(files['video'], video_file)
        
        # Verify it returns a copy
        files['test'] = 'value'
        self.assertNotIn('test', self.widget._imported_files)
    
    def test_clear_imports(self):
        """Test clearing imported files"""
        # Add some files
        self.widget._imported_files['video'] = VideoFile(path=self.test_video_path)
        self.widget.info_display.append("Test content")
        
        self.widget.clear_imports()
        
        self.assertEqual(self.widget._imported_files, {})
        self.assertEqual(self.widget.info_display.toPlainText(), "No files imported yet...")
    
    def test_has_required_files(self):
        """Test checking for required files"""
        # No files
        self.assertFalse(self.widget.has_required_files())
        
        # Only video
        self.widget._imported_files['video'] = VideoFile(path=self.test_video_path)
        self.assertFalse(self.widget.has_required_files())
        
        # Video and audio
        self.widget._imported_files['audio'] = AudioFile(path=self.test_audio_path)
        self.assertFalse(self.widget.has_required_files())
        
        # All required files
        self.widget._imported_files['subtitle'] = SubtitleFile(path=self.test_subtitle_path)
        self.assertTrue(self.widget.has_required_files())
        
        # Test with image instead of video
        del self.widget._imported_files['video']
        self.widget._imported_files['image'] = ImageFile(path=self.test_image_path)
        self.assertTrue(self.widget.has_required_files())
    
    def test_signal_connections(self):
        """Test that MediaImporter signals are properly connected"""
        # Test signal connections by checking if the info display gets updated
        # when signals are emitted (which proves the handlers are connected)
        
        # Test import_started signal
        initial_text = self.widget.info_display.toPlainText()
        self.widget.media_importer.import_started.emit("test_file.mp4")
        updated_text = self.widget.info_display.toPlainText()
        self.assertNotEqual(initial_text, updated_text)
        self.assertIn("Importing test_file.mp4", updated_text)
        
        # Test import_failed signal
        error_spy = Mock()
        self.widget.import_error.connect(error_spy)
        self.widget.media_importer.import_failed.emit("test_file.mp4", "Test error")
        error_spy.assert_called_once_with("test_file.mp4", "Test error")


if __name__ == '__main__':
    unittest.main()