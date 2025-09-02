"""
Integration tests for the unified OpenGL export system
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
try:
    from src.core.export_manager import ExportManager, ExportConfiguration
    from src.core.opengl_export_renderer import OpenGLExportRenderer, ExportSettings
    from src.core.models import Project, AudioFile, VideoFile, SubtitleFile, SubtitleLine, SubtitleStyle
    from src.ui.export_widget import ExportWidget
except ImportError:
    from export_manager import ExportManager, ExportConfiguration
    from opengl_export_renderer import OpenGLExportRenderer, ExportSettings
    from models import Project, AudioFile, VideoFile, SubtitleFile, SubtitleLine, SubtitleStyle
    from export_widget import ExportWidget


class TestExportSystemIntegration(unittest.TestCase):
    """Test integration between export components."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create complete test project
        self.test_project = Project(
            id="integration_test",
            name="Integration Test Project",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=30.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            ),
            video_file=VideoFile(
                path="test_video.mp4",
                duration=30.0,
                resolution={"width": 1920, "height": 1080},
                format="mp4",
                frame_rate=30.0
            ),
            subtitle_file=SubtitleFile(
                path="test_subtitles.ass",
                format="ass",
                lines=[
                    SubtitleLine(
                        start_time=0.0,
                        end_time=5.0,
                        text="Hello World",
                        style="Default"
                    ),
                    SubtitleLine(
                        start_time=5.0,
                        end_time=10.0,
                        text="Karaoke Test",
                        style="Default"
                    )
                ],
                styles=[
                    SubtitleStyle(
                        name="Default",
                        font_name="Arial",
                        font_size=24,
                        primary_color="#FFFFFF",
                        secondary_color="#000000",
                        outline_color="#000000",
                        back_color="#000000"
                    )
                ]
            )
        )
        
        # Create test export configuration
        self.test_config = ExportConfiguration(
            width=1280,
            height=720,
            fps=25.0,
            bitrate=5000,
            output_dir=self.temp_dir,
            filename="integration_test.mp4"
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_export_manager_initialization(self):
        """Test export manager initializes correctly."""
        manager = ExportManager()
        
        self.assertIsNotNone(manager)
        self.assertFalse(manager.is_exporting)
        self.assertIsNotNone(manager.opengl_renderer)
        
        # Test status
        status = manager.get_export_status()
        self.assertIn('is_exporting', status)
        self.assertIn('renderer_available', status)
    
    def test_export_configuration_conversion(self):
        """Test export configuration to settings conversion."""
        settings = self.test_config.to_export_settings()
        
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.fps, 25.0)
        self.assertEqual(settings.bitrate, 5000)
        self.assertEqual(settings.codec, "libx264")
        self.assertTrue(settings.output_path.endswith("integration_test.mp4"))
    
    def test_validation_workflow(self):
        """Test complete validation workflow."""
        manager = ExportManager()
        manager.set_project(self.test_project)
        
        # Validate requirements
        results = manager.validate_export_requirements(self.test_config)
        
        # Complete project should have minimal validation results (at least subtitle warning)
        # The test project has subtitles, so it might have no validation issues
        # Let's test with incomplete project instead
        incomplete_project = Project(
            id="incomplete",
            name="Incomplete Project",
            audio_file=self.test_project.audio_file
            # Missing video/image and subtitles
        )
        
        manager.set_project(incomplete_project)
        results = manager.validate_export_requirements(self.test_config)
        
        # Should have validation results for incomplete project
        self.assertGreater(len(results), 0)
        
        # Check that we have expected validation messages
        messages = [r.message for r in results]
        self.assertTrue(any("background" in msg.lower() for msg in messages))
    
    def test_quality_preset_application(self):
        """Test quality preset application."""
        manager = ExportManager()
        
        # Test different presets
        presets = manager.get_quality_presets()
        
        for preset_name, preset_data in presets.items():
            config = ExportConfiguration()
            updated_config = manager.apply_quality_preset(preset_name, config)
            
            self.assertEqual(updated_config.width, preset_data["width"])
            self.assertEqual(updated_config.height, preset_data["height"])
            self.assertEqual(updated_config.bitrate, preset_data["bitrate"])
            self.assertEqual(updated_config.quality_preset, preset_name)
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_export_setup_workflow(self, mock_ffmpeg_check):
        """Test export setup workflow."""
        mock_ffmpeg_check.return_value = True
        
        manager = ExportManager()
        manager.set_project(self.test_project)
        
        # Mock OpenGL renderer
        manager.opengl_renderer = Mock()
        manager.opengl_renderer.setup_export = Mock(return_value=True)
        manager.opengl_renderer.start_export_async = Mock(return_value=True)
        
        # Test setup
        success = manager._setup_export()
        self.assertTrue(success)
        
        # Verify renderer was called
        manager.opengl_renderer.setup_export.assert_called_once()
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_mock_export_process(self, mock_ffmpeg_check):
        """Test mock export process."""
        mock_ffmpeg_check.return_value = True
        
        manager = ExportManager()
        manager.set_project(self.test_project)
        
        # Mock OpenGL renderer to use mock export
        manager.opengl_renderer = None  # This will trigger mock export
        
        # Start export
        success = manager.start_export(self.test_config)
        self.assertTrue(success)
        self.assertTrue(manager.is_exporting)
    
    def test_opengl_renderer_project_duration(self):
        """Test OpenGL renderer project duration calculation."""
        renderer = OpenGLExportRenderer()
        renderer.current_project = self.test_project
        
        duration = renderer._get_project_duration()
        self.assertEqual(duration, 30.0)  # From audio file
    
    def test_opengl_renderer_subtitle_style_lookup(self):
        """Test subtitle style lookup in OpenGL renderer."""
        renderer = OpenGLExportRenderer()
        renderer.current_project = self.test_project
        
        # Test existing style
        subtitle = SubtitleLine(
            start_time=0.0,
            end_time=5.0,
            text="Test",
            style="Default"
        )
        
        style = renderer._get_subtitle_style(subtitle)
        self.assertIsNotNone(style)
        self.assertEqual(style.name, "Default")
        self.assertEqual(style.font_name, "Arial")
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_opengl_renderer_mock_setup(self):
        """Test OpenGL renderer setup with mock implementation."""
        renderer = OpenGLExportRenderer()
        
        # Setup should work with mock
        success = renderer.setup_export(self.test_project, self.test_config.to_export_settings())
        self.assertTrue(success)
        
        # Test frame rendering
        frame = renderer.render_frame_at_time(1.0)
        self.assertIsNotNone(frame)
    
    def test_export_widget_configuration_extraction(self):
        """Test export widget configuration extraction."""
        try:
            from PyQt6.QtWidgets import QApplication
            import sys
            
            # Create QApplication if it doesn't exist
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            
            widget = ExportWidget()
            
            # Test default configuration
            config = widget._get_export_configuration()
            
            self.assertIsInstance(config, ExportConfiguration)
            self.assertEqual(config.width, 1920)  # Default medium quality
            self.assertEqual(config.height, 1080)
            self.assertEqual(config.bitrate, 8)
            
        except ImportError:
            # Skip if PyQt6 not available
            self.skipTest("PyQt6 not available for widget testing")
    
    def test_end_to_end_validation_flow(self):
        """Test end-to-end validation and setup flow."""
        manager = ExportManager()
        
        # Test without project (should fail validation)
        results = manager.validate_export_requirements(self.test_config)
        error_results = [r for r in results if r.level.value == "error"]
        self.assertTrue(any("No project loaded" in r.message for r in error_results))
        
        # Set project and test again
        manager.set_project(self.test_project)
        results = manager.validate_export_requirements(self.test_config)
        
        # Should have fewer errors now
        error_results = [r for r in results if r.level.value == "error"]
        project_errors = [r for r in error_results if "project" in r.message.lower()]
        self.assertEqual(len(project_errors), 0)
    
    def test_export_settings_codec_mapping(self):
        """Test export settings codec mapping."""
        # Test H.264
        config = ExportConfiguration(format="MP4 (H.264)")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx264")
        
        # Test H.265
        config = ExportConfiguration(format="MP4 (H.265)")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx265")
        
        # Test unknown format
        config = ExportConfiguration(format="Unknown")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx264")  # Should default to H.264
    
    def test_size_estimation(self):
        """Test output size estimation."""
        manager = ExportManager()
        manager.set_project(self.test_project)
        
        estimated_size = manager._estimate_output_size(self.test_config)
        
        # Should be reasonable size for 30 second video
        self.assertGreater(estimated_size, 0)
        
        # Rough calculation: (5000 + 128) kbps * 30 seconds / 8 bits per byte
        expected_size = (5000 + 128) * 1000 * 30 / 8
        self.assertAlmostEqual(estimated_size, expected_size, delta=expected_size * 0.1)


class TestExportErrorHandling(unittest.TestCase):
    """Test error handling in export system."""
    
    def test_export_manager_missing_project(self):
        """Test export manager behavior with missing project."""
        manager = ExportManager()
        config = ExportConfiguration()
        
        # Should fail without project
        success = manager.start_export(config)
        self.assertFalse(success)
    
    def test_export_manager_invalid_output_directory(self):
        """Test export manager with invalid output directory."""
        manager = ExportManager()
        
        # Create project
        project = Project(
            id="test",
            name="Test",
            audio_file=AudioFile(
                path="test.mp3",
                duration=10.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            )
        )
        manager.set_project(project)
        
        # Invalid output directory
        config = ExportConfiguration(output_dir="/invalid/path/that/does/not/exist")
        
        results = manager.validate_export_requirements(config)
        error_results = [r for r in results if r.level.value == "error"]
        
        # Should have error about output directory
        self.assertTrue(any("output directory" in r.message.lower() for r in error_results))
    
    def test_opengl_renderer_cleanup(self):
        """Test OpenGL renderer cleanup."""
        renderer = OpenGLExportRenderer()
        
        # Set up some mock resources
        renderer.ffmpeg_process = Mock()
        renderer.framebuffer = Mock()
        renderer.subtitle_renderer = Mock()
        renderer.subtitle_renderer.cleanup = Mock()
        
        # Test cleanup
        renderer._cleanup_export()
        
        self.assertFalse(renderer.is_exporting)
        self.assertIsNone(renderer.ffmpeg_process)
        self.assertIsNone(renderer.framebuffer)
        renderer.subtitle_renderer.cleanup.assert_called_once()


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)