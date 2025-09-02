"""
Unit tests for OpenGL Export Renderer
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules to test
try:
    from src.core.opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, ExportProgress, ExportThread
    )
    from src.core.models import Project, VideoFile, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle
except ImportError:
    from opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, ExportProgress, ExportThread
    )
    from models import Project, VideoFile, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle


class TestExportSettings(unittest.TestCase):
    """Test ExportSettings dataclass."""
    
    def test_default_settings(self):
        """Test default export settings."""
        settings = ExportSettings(output_path="test.mp4")
        
        self.assertEqual(settings.output_path, "test.mp4")
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.bitrate, 8000)
        self.assertEqual(settings.codec, "libx264")
    
    def test_custom_settings(self):
        """Test custom export settings."""
        settings = ExportSettings(
            output_path="custom.mp4",
            width=1280,
            height=720,
            fps=25.0,
            bitrate=5000,
            codec="libx265"
        )
        
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.fps, 25.0)
        self.assertEqual(settings.bitrate, 5000)
        self.assertEqual(settings.codec, "libx265")


class TestExportProgress(unittest.TestCase):
    """Test ExportProgress dataclass."""
    
    def test_default_progress(self):
        """Test default progress values."""
        progress = ExportProgress()
        
        self.assertEqual(progress.current_frame, 0)
        self.assertEqual(progress.total_frames, 0)
        self.assertEqual(progress.elapsed_time, 0.0)
        self.assertEqual(progress.estimated_remaining, 0.0)
        self.assertEqual(progress.fps, 0.0)
        self.assertEqual(progress.status, "Initializing")
        self.assertIsNone(progress.error)
    
    def test_progress_calculation(self):
        """Test progress calculations."""
        progress = ExportProgress(
            current_frame=50,
            total_frames=100,
            elapsed_time=10.0
        )
        
        # Calculate FPS
        if progress.elapsed_time > 0:
            calculated_fps = progress.current_frame / progress.elapsed_time
            self.assertEqual(calculated_fps, 5.0)


class TestOpenGLExportRenderer(unittest.TestCase):
    """Test OpenGL Export Renderer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
        
        # Create test project
        self.test_project = Project(
            id="test_project",
            name="Test Project",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=60.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            ),
            subtitle_file=SubtitleFile(
                path="test_subtitles.ass",
                format="ass",
                lines=[
                    SubtitleLine(
                        start_time=0.0,
                        end_time=5.0,
                        text="Test subtitle",
                        style="Default"
                    )
                ],
                styles=[
                    SubtitleStyle(
                        name="Default",
                        font_name="Arial",
                        font_size=20,
                        primary_color="#FFFFFF"
                    )
                ]
            )
        )
        
        # Create test export settings
        self.test_settings = ExportSettings(
            output_path="test_output.mp4",
            width=1280,
            height=720,
            fps=25.0
        )
    
    def test_initialization(self):
        """Test renderer initialization."""
        self.assertIsNotNone(self.renderer)
        self.assertFalse(self.renderer.is_exporting)
        self.assertFalse(self.renderer.should_cancel)
        self.assertIsNone(self.renderer.current_project)
        self.assertIsNone(self.renderer.export_settings)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_mock_initialization(self):
        """Test renderer with mock PyQt6."""
        renderer = OpenGLExportRenderer()
        
        # Should work without PyQt6
        success = renderer.initialize_opengl_context()
        self.assertTrue(success)
        
        success = renderer.create_framebuffer(1920, 1080)
        self.assertTrue(success)
    
    def test_get_project_duration(self):
        """Test project duration calculation."""
        # Set up project
        self.renderer.current_project = self.test_project
        
        duration = self.renderer._get_project_duration()
        self.assertEqual(duration, 60.0)  # From audio file
    
    def test_get_project_duration_no_project(self):
        """Test duration with no project."""
        duration = self.renderer._get_project_duration()
        self.assertEqual(duration, 0.0)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_setup_export(self):
        """Test export setup."""
        success = self.renderer.setup_export(self.test_project, self.test_settings)
        
        # Should succeed with mock implementation
        self.assertTrue(success)
        self.assertEqual(self.renderer.current_project, self.test_project)
        self.assertEqual(self.renderer.export_settings, self.test_settings)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_setup_export_no_project(self):
        """Test export setup without project."""
        success = self.renderer.setup_export(None, self.test_settings)
        self.assertFalse(success)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_setup_export_no_settings(self):
        """Test export setup without settings."""
        success = self.renderer.setup_export(self.test_project, None)
        self.assertFalse(success)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_render_frame_mock(self):
        """Test frame rendering with mock implementation."""
        self.renderer.setup_export(self.test_project, self.test_settings)
        
        # Mock framebuffer
        self.renderer.framebuffer = Mock()
        self.renderer.subtitle_renderer = Mock()
        
        frame = self.renderer.render_frame_at_time(1.0)
        
        # Should return a mock image
        self.assertIsNotNone(frame)
    
    def test_cancel_export(self):
        """Test export cancellation."""
        # Set up mock FFmpeg process
        self.renderer.ffmpeg_process = Mock()
        
        self.renderer.cancel_export()
        
        self.assertTrue(self.renderer.should_cancel)
        self.renderer.ffmpeg_process.terminate.assert_called_once()
    
    @patch('subprocess.Popen')
    @patch('pathlib.Path.mkdir')
    def test_start_ffmpeg_process(self, mock_mkdir, mock_popen):
        """Test FFmpeg process startup."""
        self.renderer.current_project = self.test_project
        self.renderer.export_settings = self.test_settings
        
        # Mock subprocess
        mock_process = Mock()
        mock_popen.return_value = mock_process
        
        success = self.renderer.start_ffmpeg_process()
        
        self.assertTrue(success)
        self.assertEqual(self.renderer.ffmpeg_process, mock_process)
        mock_popen.assert_called_once()
    
    def test_cleanup_export(self):
        """Test export cleanup."""
        # Set up mock resources
        self.renderer.ffmpeg_process = Mock()
        self.renderer.framebuffer = Mock()
        self.renderer.subtitle_renderer = Mock()
        
        self.renderer._cleanup_export()
        
        self.assertFalse(self.renderer.is_exporting)
        self.assertIsNone(self.renderer.ffmpeg_process)
        self.assertIsNone(self.renderer.framebuffer)
    
    def test_get_subtitle_style(self):
        """Test subtitle style retrieval."""
        self.renderer.current_project = self.test_project
        
        # Test existing style
        subtitle = SubtitleLine(
            start_time=0.0,
            end_time=5.0,
            text="Test",
            style="Default"
        )
        
        style = self.renderer._get_subtitle_style(subtitle)
        self.assertIsNotNone(style)
        self.assertEqual(style.name, "Default")
    
    def test_get_subtitle_style_missing(self):
        """Test subtitle style retrieval for missing style."""
        self.renderer.current_project = self.test_project
        
        # Test non-existent style
        subtitle = SubtitleLine(
            start_time=0.0,
            end_time=5.0,
            text="Test",
            style="NonExistent"
        )
        
        style = self.renderer._get_subtitle_style(subtitle)
        self.assertIsNotNone(style)  # Should return default
    
    def test_get_subtitle_style_no_project(self):
        """Test subtitle style retrieval without project."""
        subtitle = SubtitleLine(
            start_time=0.0,
            end_time=5.0,
            text="Test",
            style="Default"
        )
        
        style = self.renderer._get_subtitle_style(subtitle)
        self.assertIsNone(style)


class TestExportThread(unittest.TestCase):
    """Test ExportThread."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = Mock(spec=OpenGLExportRenderer)
        self.thread = ExportThread(self.renderer)
    
    def test_thread_initialization(self):
        """Test thread initialization."""
        self.assertEqual(self.thread.renderer, self.renderer)
    
    def test_thread_run(self):
        """Test thread execution."""
        # Mock the export_frames method
        self.renderer.export_frames = Mock()
        
        # Run the thread
        self.thread.run()
        
        # Verify export_frames was called
        self.renderer.export_frames.assert_called_once()
    
    def test_thread_run_with_exception(self):
        """Test thread execution with exception."""
        # Mock export_frames to raise exception
        self.renderer.export_frames = Mock(side_effect=Exception("Test error"))
        self.renderer.export_failed = Mock()
        self.renderer.export_failed.emit = Mock()
        
        # Run the thread
        self.thread.run()
        
        # Verify error handling
        self.renderer.export_failed.emit.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for export system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_path = os.path.join(self.temp_dir, "test_output.mp4")
        
        # Create test project with actual files
        self.project = Project(
            id="integration_test",
            name="Integration Test",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=10.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            )
        )
        
        self.settings = ExportSettings(
            output_path=self.output_path,
            width=640,
            height=480,
            fps=10.0  # Low FPS for faster testing
        )
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_full_export_setup(self):
        """Test complete export setup process."""
        renderer = OpenGLExportRenderer()
        
        # Test setup
        success = renderer.setup_export(self.project, self.settings)
        self.assertTrue(success)
        
        # Verify state
        self.assertEqual(renderer.current_project, self.project)
        self.assertEqual(renderer.export_settings, self.settings)
        
        # Test cleanup
        renderer._cleanup_export()
        self.assertFalse(renderer.is_exporting)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_mock_export_process(self):
        """Test export process with mock implementation."""
        renderer = OpenGLExportRenderer()
        
        # Setup export
        success = renderer.setup_export(self.project, self.settings)
        self.assertTrue(success)
        
        # Test frame rendering
        frame = renderer.render_frame_at_time(1.0)
        self.assertIsNotNone(frame)
        
        # Test duration calculation
        duration = renderer._get_project_duration()
        self.assertEqual(duration, 10.0)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)