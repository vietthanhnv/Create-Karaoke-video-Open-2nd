"""
Integration tests for the complete media import system.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock

from PyQt6.QtWidgets import QApplication

from src.core.media_importer import MediaImporter
from src.ui.import_widget import ImportWidget
from src.core.models import VideoFile, AudioFile, ImageFile, SubtitleFile


class TestMediaImportIntegration(unittest.TestCase):
    """Integration tests for media import system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for widget testing"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files with proper content
        self.test_video_path = os.path.join(self.temp_dir, "test_video.mp4")
        self.test_audio_path = os.path.join(self.temp_dir, "test_audio.mp3")
        self.test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        self.test_subtitle_path = os.path.join(self.temp_dir, "test_subtitle.ass")
        
        # Create dummy files
        for path in [self.test_video_path, self.test_audio_path, 
                     self.test_image_path]:
            with open(path, 'wb') as f:
                f.write(b"dummy binary content")
        
        # Create a valid ASS subtitle file
        ass_content = """[Script Info]
Title: Test Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,Test subtitle line
"""
        with open(self.test_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_complete_import_workflow(self, mock_run):
        """Test complete import workflow with all file types"""
        # Mock FFmpeg responses
        def mock_ffmpeg_response(cmd, **kwargs):
            if 'test_video.mp4' in ' '.join(cmd):
                return Mock(
                    stdout='{"streams":[{"codec_type":"video","width":1920,"height":1080,"r_frame_rate":"30/1","codec_name":"h264"}],"format":{"duration":"120.5","bit_rate":"5000000"}}',
                    returncode=0
                )
            elif 'test_audio.mp3' in ' '.join(cmd):
                return Mock(
                    stdout='{"streams":[{"codec_type":"audio","sample_rate":"44100","channels":2,"bit_rate":"320000","codec_name":"mp3"}],"format":{"duration":"180.0"}}',
                    returncode=0
                )
            elif 'test_image.jpg' in ' '.join(cmd):
                return Mock(
                    stdout='{"streams":[{"width":1920,"height":1080,"codec_name":"mjpeg","pix_fmt":"yuvj420p"}]}',
                    returncode=0
                )
            return Mock(stdout='{}', returncode=0)
        
        mock_run.side_effect = mock_ffmpeg_response
        
        # Create import widget
        widget = ImportWidget()
        
        # Mock FFmpeg path
        widget.media_importer._ffmpeg_path = "ffmpeg"
        
        # Test importing all file types
        video_file = widget.media_importer.import_video(self.test_video_path)
        audio_file = widget.media_importer.import_audio(self.test_audio_path)
        image_file = widget.media_importer.import_image(self.test_image_path)
        subtitle_file = widget.media_importer.import_subtitles(self.test_subtitle_path)
        
        # Verify all files were imported successfully
        self.assertIsInstance(video_file, VideoFile)
        self.assertEqual(video_file.duration, 120.5)
        self.assertEqual(video_file.resolution['width'], 1920)
        self.assertEqual(video_file.resolution['height'], 1080)
        self.assertEqual(video_file.frame_rate, 30.0)
        
        self.assertIsInstance(audio_file, AudioFile)
        self.assertEqual(audio_file.duration, 180.0)
        self.assertEqual(audio_file.sample_rate, 44100)
        self.assertEqual(audio_file.channels, 2)
        self.assertEqual(audio_file.bitrate, 320000)
        
        self.assertIsInstance(image_file, ImageFile)
        self.assertEqual(image_file.resolution['width'], 1920)
        self.assertEqual(image_file.resolution['height'], 1080)
        
        self.assertIsInstance(subtitle_file, SubtitleFile)
        self.assertEqual(subtitle_file.format, 'ass')
        
        # Test widget state
        widget._imported_files['video'] = video_file
        widget._imported_files['audio'] = audio_file
        widget._imported_files['image'] = image_file
        widget._imported_files['subtitle'] = subtitle_file
        
        self.assertTrue(widget.has_required_files())
        
        imported_files = widget.get_imported_files()
        self.assertEqual(len(imported_files), 4)
        self.assertIn('video', imported_files)
        self.assertIn('audio', imported_files)
        self.assertIn('image', imported_files)
        self.assertIn('subtitle', imported_files)
        
        widget.close()
    
    def test_import_widget_signals(self):
        """Test that import widget signals work correctly"""
        widget = ImportWidget()
        
        # Set up signal spies
        video_spy = Mock()
        audio_spy = Mock()
        image_spy = Mock()
        subtitle_spy = Mock()
        error_spy = Mock()
        
        widget.video_imported.connect(video_spy)
        widget.audio_imported.connect(audio_spy)
        widget.image_imported.connect(image_spy)
        widget.subtitle_imported.connect(subtitle_spy)
        widget.import_error.connect(error_spy)
        
        # Test successful imports
        with patch.object(widget.media_importer, 'import_video') as mock_import:
            video_file = VideoFile(path=self.test_video_path)
            mock_import.return_value = video_file
            
            widget._select_video_file()
            
            video_spy.assert_called_once_with(video_file)
            self.assertEqual(widget._imported_files['video'], video_file)
        
        # Test error handling
        with patch.object(widget.media_importer, 'import_audio') as mock_import:
            from src.core.media_importer import MediaImportError
            mock_import.side_effect = MediaImportError("Test error")
            
            with patch.object(widget, '_show_error') as mock_show_error:
                widget._select_audio_file()
                mock_show_error.assert_called_once_with("Audio Import Error", "Test error")
        
        widget.close()
    
    def test_drag_drop_functionality(self):
        """Test drag and drop functionality"""
        widget = ImportWidget()
        
        # Test file type detection
        self.assertTrue(widget._is_supported_file(self.test_video_path))
        self.assertTrue(widget._is_supported_file(self.test_audio_path))
        self.assertTrue(widget._is_supported_file(self.test_image_path))
        self.assertTrue(widget._is_supported_file(self.test_subtitle_path))
        self.assertFalse(widget._is_supported_file("unsupported.xyz"))
        
        # Test dropped file import
        with patch.object(widget.media_importer, 'import_video') as mock_import:
            video_file = VideoFile(path=self.test_video_path)
            mock_import.return_value = video_file
            
            video_spy = Mock()
            widget.video_imported.connect(video_spy)
            
            widget._import_dropped_file(self.test_video_path)
            
            video_spy.assert_called_once_with(video_file)
            self.assertEqual(widget._imported_files['video'], video_file)
        
        widget.close()
    
    def test_metadata_display(self):
        """Test metadata display in widget"""
        widget = ImportWidget()
        
        # Test video metadata display
        video_file = VideoFile(
            path=self.test_video_path,
            duration=125.5,
            resolution={'width': 1920, 'height': 1080},
            frame_rate=29.97,
            file_size=1048576
        )
        
        widget._on_import_completed(video_file)
        
        text = widget.info_display.toPlainText()
        self.assertIn("✓ Video: test_video.mp4", text)
        self.assertIn("Duration: 02:05", text)
        self.assertIn("Resolution: 1920x1080", text)
        self.assertIn("Frame Rate: 29.97 fps", text)
        self.assertIn("Size: 1.0 MB", text)
        
        # Test audio metadata display
        audio_file = AudioFile(
            path=self.test_audio_path,
            duration=240.0,
            sample_rate=48000,
            channels=2,
            file_size=2097152
        )
        
        widget._on_import_completed(audio_file)
        
        text = widget.info_display.toPlainText()
        self.assertIn("✓ Audio: test_audio.mp3", text)
        self.assertIn("Duration: 04:00", text)
        self.assertIn("Sample Rate: 48000 Hz", text)
        self.assertIn("Channels: 2", text)
        self.assertIn("Size: 2.0 MB", text)
        
        widget.close()
    
    def test_clear_and_reset(self):
        """Test clearing imported files"""
        widget = ImportWidget()
        
        # Add some files
        widget._imported_files['video'] = VideoFile(path=self.test_video_path)
        widget._imported_files['audio'] = AudioFile(path=self.test_audio_path)
        widget.info_display.append("Test content")
        
        # Verify files are present
        self.assertEqual(len(widget._imported_files), 2)
        self.assertIn("Test content", widget.info_display.toPlainText())
        
        # Clear imports
        widget.clear_imports()
        
        # Verify everything is cleared
        self.assertEqual(len(widget._imported_files), 0)
        self.assertEqual(widget.info_display.toPlainText(), "No files imported yet...")
        
        widget.close()


if __name__ == '__main__':
    unittest.main()