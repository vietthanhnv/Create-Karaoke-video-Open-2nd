"""
Unit tests for Export Manager
"""

import unittest
import tempfile
import os
import shutil
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules to test
try:
    from src.core.export_manager import ExportManager, ExportConfiguration
    from src.core.models import Project, AudioFile, VideoFile, SubtitleFile
    from src.core.validation import ValidationResult, ValidationLevel
except ImportError:
    from export_manager import ExportManager, ExportConfiguration
    from models import Project, AudioFile, VideoFile, SubtitleFile
    from validation import ValidationResult, ValidationLevel


class TestExportConfiguration(unittest.TestCase):
    """Test ExportConfiguration dataclass."""
    
    def test_default_configuration(self):
        """Test default export configuration."""
        config = ExportConfiguration()
        
        self.assertEqual(config.width, 1920)
        self.assertEqual(config.height, 1080)
        self.assertEqual(config.fps, 30.0)
        self.assertEqual(config.bitrate, 8000)
        self.assertEqual(config.output_dir, "./output/")
        self.assertEqual(config.filename, "karaoke_video.mp4")
        self.assertTrue(config.cleanup_temp)
    
    def test_custom_configuration(self):
        """Test custom export configuration."""
        config = ExportConfiguration(
            width=1280,
            height=720,
            fps=25.0,
            bitrate=5000,
            output_dir="./custom_output/",
            filename="custom_video.mp4",
            cleanup_temp=False
        )
        
        self.assertEqual(config.width, 1280)
        self.assertEqual(config.height, 720)
        self.assertEqual(config.fps, 25.0)
        self.assertEqual(config.bitrate, 5000)
        self.assertEqual(config.output_dir, "./custom_output/")
        self.assertEqual(config.filename, "custom_video.mp4")
        self.assertFalse(config.cleanup_temp)
    
    def test_to_export_settings(self):
        """Test conversion to export settings."""
        config = ExportConfiguration(
            width=1280,
            height=720,
            bitrate=5000,
            output_dir="./test_output/",
            filename="test.mp4",
            format="MP4 (H.264)"
        )
        
        settings = config.to_export_settings()
        
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.bitrate, 5000)
        self.assertEqual(settings.codec, "libx264")
        self.assertTrue(settings.output_path.endswith("test.mp4"))
    
    def test_codec_mapping(self):
        """Test format to codec mapping."""
        # Test H.264
        config = ExportConfiguration(format="MP4 (H.264)")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx264")
        
        # Test H.265
        config = ExportConfiguration(format="MP4 (H.265)")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx265")
        
        # Test unknown format (should default to H.264)
        config = ExportConfiguration(format="Unknown Format")
        settings = config.to_export_settings()
        self.assertEqual(settings.codec, "libx264")


class TestExportManager(unittest.TestCase):
    """Test Export Manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test project
        self.test_project = Project(
            id="test_project",
            name="Test Project",
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
                lines=[],
                styles=[]
            )
        )
        
        # Create test configuration
        self.test_config = ExportConfiguration(
            output_dir=self.temp_dir,
            filename="test_export.mp4"
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test manager initialization."""
        self.assertIsNotNone(self.manager)
        self.assertFalse(self.manager.is_exporting)
        self.assertIsNone(self.manager.current_project)
        self.assertIsNone(self.manager.export_config)
    
    def test_set_project(self):
        """Test setting project."""
        self.manager.set_project(self.test_project)
        
        self.assertEqual(self.manager.current_project, self.test_project)
    
    def test_validate_export_requirements_no_project(self):
        """Test validation without project."""
        results = self.manager.validate_export_requirements(self.test_config)
        
        # Should have error for no project
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertTrue(any("No project loaded" in r.message for r in error_results))
    
    def test_validate_export_requirements_complete_project(self):
        """Test validation with complete project."""
        self.manager.set_project(self.test_project)
        
        results = self.manager.validate_export_requirements(self.test_config)
        
        # Should not have critical errors for complete project
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        project_errors = [r for r in error_results if "project" in r.message.lower()]
        self.assertEqual(len(project_errors), 0)
    
    def test_validate_export_requirements_missing_audio(self):
        """Test validation with missing audio."""
        incomplete_project = Project(
            id="incomplete",
            name="Incomplete",
            video_file=self.test_project.video_file,
            subtitle_file=self.test_project.subtitle_file
        )
        
        self.manager.set_project(incomplete_project)
        results = self.manager.validate_export_requirements(self.test_config)
        
        # Should have error for missing audio
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertTrue(any("No audio file" in r.message for r in error_results))
    
    def test_validate_export_requirements_missing_background(self):
        """Test validation with missing video/image background."""
        incomplete_project = Project(
            id="incomplete",
            name="Incomplete",
            audio_file=self.test_project.audio_file,
            subtitle_file=self.test_project.subtitle_file
        )
        
        self.manager.set_project(incomplete_project)
        results = self.manager.validate_export_requirements(self.test_config)
        
        # Should have error for missing background
        error_results = [r for r in results if r.level == ValidationLevel.ERROR]
        self.assertTrue(any("No video or image background" in r.message for r in error_results))
    
    def test_estimate_output_size(self):
        """Test output size estimation."""
        self.manager.set_project(self.test_project)
        
        estimated_size = self.manager._estimate_output_size(self.test_config)
        
        # Should return reasonable size estimate
        self.assertGreater(estimated_size, 0)
        
        # For 30 second video at 8Mbps + 128kbps audio
        expected_size = (8000 + 128) * 1000 * 30 / 8  # bits to bytes
        self.assertAlmostEqual(estimated_size, expected_size, delta=expected_size * 0.1)
    
    def test_estimate_output_size_no_project(self):
        """Test size estimation without project."""
        estimated_size = self.manager._estimate_output_size(self.test_config)
        self.assertEqual(estimated_size, 0)
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available_success(self, mock_run):
        """Test FFmpeg availability check - success."""
        mock_run.return_value.returncode = 0
        
        available = self.manager._check_ffmpeg_available()
        self.assertTrue(available)
        
        mock_run.assert_called_once_with(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
    
    @patch('subprocess.run')
    def test_check_ffmpeg_available_failure(self, mock_run):
        """Test FFmpeg availability check - failure."""
        mock_run.side_effect = FileNotFoundError()
        
        available = self.manager._check_ffmpeg_available()
        self.assertFalse(available)
    
    def test_get_quality_presets(self):
        """Test quality presets."""
        presets = self.manager.get_quality_presets()
        
        self.assertIsInstance(presets, dict)
        self.assertIn("Low (720p)", presets)
        self.assertIn("Medium (1080p)", presets)
        self.assertIn("High (1080p HQ)", presets)
        self.assertIn("4K (2160p)", presets)
        
        # Check preset structure
        low_preset = presets["Low (720p)"]
        self.assertEqual(low_preset["width"], 1280)
        self.assertEqual(low_preset["height"], 720)
        self.assertIn("description", low_preset)
    
    def test_apply_quality_preset(self):
        """Test applying quality preset."""
        config = ExportConfiguration()
        
        # Apply high quality preset
        updated_config = self.manager.apply_quality_preset("High (1080p HQ)", config)
        
        self.assertEqual(updated_config.width, 1920)
        self.assertEqual(updated_config.height, 1080)
        self.assertEqual(updated_config.bitrate, 15000)
        self.assertEqual(updated_config.quality_preset, "High (1080p HQ)")
    
    def test_apply_quality_preset_unknown(self):
        """Test applying unknown quality preset."""
        config = ExportConfiguration(width=1280, height=720)
        original_width = config.width
        
        # Apply unknown preset (should not change anything)
        updated_config = self.manager.apply_quality_preset("Unknown Preset", config)
        
        self.assertEqual(updated_config.width, original_width)
    
    @patch('tempfile.mkdtemp')
    def test_setup_export(self, mock_mkdtemp):
        """Test export setup."""
        mock_mkdtemp.return_value = "/tmp/test_export"
        
        self.manager.current_project = self.test_project
        self.manager.export_config = self.test_config
        
        # Mock OpenGL renderer
        self.manager.opengl_renderer = Mock()
        self.manager.opengl_renderer.setup_export = Mock(return_value=True)
        
        success = self.manager._setup_export()
        
        self.assertTrue(success)
        self.assertEqual(self.manager.temp_dir, "/tmp/test_export")
        self.manager.opengl_renderer.setup_export.assert_called_once()
    
    def test_setup_export_no_project(self):
        """Test export setup without project."""
        success = self.manager._setup_export()
        self.assertFalse(success)
    
    def test_get_export_status(self):
        """Test export status."""
        status = self.manager.get_export_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('is_exporting', status)
        self.assertIn('has_project', status)
        self.assertIn('renderer_available', status)
        self.assertIn('temp_dir', status)
        
        self.assertFalse(status['is_exporting'])
        self.assertFalse(status['has_project'])
    
    def test_get_export_status_with_project(self):
        """Test export status with project loaded."""
        self.manager.set_project(self.test_project)
        
        status = self.manager.get_export_status()
        self.assertTrue(status['has_project'])
    
    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_cleanup_export(self, mock_exists, mock_rmtree):
        """Test export cleanup."""
        mock_exists.return_value = True
        self.manager.temp_dir = "/tmp/test_cleanup"
        
        self.manager._cleanup_export()
        
        mock_rmtree.assert_called_once_with("/tmp/test_cleanup")
        self.assertIsNone(self.manager.temp_dir)
    
    def test_cleanup_export_no_temp_dir(self):
        """Test cleanup without temp directory."""
        # Should not raise exception
        self.manager._cleanup_export()
        self.assertIsNone(self.manager.temp_dir)
    
    def test_start_export_no_project(self):
        """Test starting export without project."""
        success = self.manager.start_export(self.test_config)
        self.assertFalse(success)
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_start_export_validation_failure(self, mock_ffmpeg_check):
        """Test export start with validation failure."""
        mock_ffmpeg_check.return_value = False  # FFmpeg not available
        
        # Set project but FFmpeg unavailable
        self.manager.set_project(self.test_project)
        
        success = self.manager.start_export(self.test_config)
        self.assertFalse(success)
    
    def test_cancel_export_not_exporting(self):
        """Test cancelling when not exporting."""
        # Should not raise exception
        self.manager.cancel_export()
        self.assertFalse(self.manager.is_exporting)
    
    def test_cancel_export_with_renderer(self):
        """Test cancelling with OpenGL renderer."""
        self.manager.is_exporting = True
        self.manager.opengl_renderer = Mock()
        self.manager.opengl_renderer.cancel_export = Mock()
        
        self.manager.cancel_export()
        
        self.manager.opengl_renderer.cancel_export.assert_called_once()
        self.assertFalse(self.manager.is_exporting)


class TestExportManagerSignals(unittest.TestCase):
    """Test Export Manager signal handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
        
        # Mock signal connections
        self.manager.export_started = Mock()
        self.manager.export_progress = Mock()
        self.manager.export_completed = Mock()
        self.manager.export_failed = Mock()
        self.manager.export_cancelled = Mock()
        self.manager.detailed_progress = Mock()
        self.manager.status_changed = Mock()
        
        # Mock emit methods
        self.manager.export_started.emit = Mock()
        self.manager.export_progress.emit = Mock()
        self.manager.export_completed.emit = Mock()
        self.manager.export_failed.emit = Mock()
        self.manager.export_cancelled.emit = Mock()
        self.manager.detailed_progress.emit = Mock()
        self.manager.status_changed.emit = Mock()
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_on_export_completed(self, mock_getsize, mock_exists):
        """Test export completion handling."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1 MB
        
        output_path = "/test/output.mp4"
        
        self.manager._on_export_completed(output_path)
        
        self.assertFalse(self.manager.is_exporting)
        self.manager.export_completed.emit.assert_called_once_with(output_path)
        self.manager.detailed_progress.emit.assert_called()
    
    def test_on_export_failed(self):
        """Test export failure handling."""
        error_message = "Test error"
        
        self.manager._on_export_failed(error_message)
        
        self.assertFalse(self.manager.is_exporting)
        # The error message gets enhanced with context, so check if it contains the original message
        self.manager.export_failed.emit.assert_called_once()
        emitted_error = self.manager.export_failed.emit.call_args[0][0]
        self.assertIn(error_message, emitted_error)
    
    def test_on_progress_updated(self):
        """Test progress update handling."""
        from src.core.opengl_export_renderer import ExportProgress
        
        # Set up progress info with start time
        self.manager.progress_info.start_time = time.time() - 1.0  # 1 second ago
        
        progress = ExportProgress(
            current_frame=50,
            total_frames=100,
            elapsed_time=10.0,
            fps=5.0,
            status="Rendering..."
        )
        
        self.manager._on_progress_updated(progress)
        
        # Verify progress signal was emitted
        self.manager.export_progress.emit.assert_called_once()
        self.manager.detailed_progress.emit.assert_called()
        
        # Check emitted data
        emitted_data = self.manager.export_progress.emit.call_args[0][0]
        self.assertEqual(emitted_data['current_frame'], 50)
        self.assertEqual(emitted_data['total_frames'], 100)
        # Progress percent should be calculated correctly
        self.assertGreaterEqual(emitted_data['progress_percent'], 0)


class TestExportProgressTracking(unittest.TestCase):
    """Test enhanced progress tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
        
        # Mock signals
        self.manager.detailed_progress = Mock()
        self.manager.detailed_progress.emit = Mock()
        self.manager.status_changed = Mock()
        self.manager.status_changed.emit = Mock()
    
    def test_progress_info_initialization(self):
        """Test progress info initialization."""
        from src.core.export_manager import ExportProgressInfo, ExportStatus
        
        progress = ExportProgressInfo()
        
        self.assertEqual(progress.status, ExportStatus.IDLE)
        self.assertEqual(progress.current_frame, 0)
        self.assertEqual(progress.total_frames, 0)
        self.assertEqual(progress.progress_percent, 0.0)
        self.assertIsInstance(progress.start_time, float)
    
    def test_progress_timing_calculation(self):
        """Test progress timing calculations."""
        from src.core.export_manager import ExportProgressInfo
        
        progress = ExportProgressInfo()
        progress.start_time = time.time() - 10.0  # 10 seconds ago
        progress.current_frame = 50
        progress.total_frames = 100
        
        progress.update_timing()
        
        self.assertGreater(progress.elapsed_time, 9.0)
        self.assertLess(progress.elapsed_time, 11.0)
        self.assertEqual(progress.progress_percent, 50.0)
        self.assertGreater(progress.frames_per_second, 0)
        self.assertGreater(progress.estimated_remaining, 0)
    
    def test_status_update(self):
        """Test status update functionality."""
        from src.core.export_manager import ExportStatus
        
        self.manager._update_status(
            ExportStatus.RENDERING, 
            "Test operation", 
            "Test details"
        )
        
        self.assertEqual(self.manager.export_status, ExportStatus.RENDERING)
        self.assertEqual(self.manager.progress_info.current_operation, "Test operation")
        self.assertEqual(self.manager.progress_info.detailed_status, "Test details")
        
        self.manager.status_changed.emit.assert_called_with("rendering")
        self.manager.detailed_progress.emit.assert_called()
    
    def test_calculate_total_frames(self):
        """Test total frames calculation."""
        # Set up project with audio file
        audio_file = AudioFile(
            path="test.mp3",
            duration=30.0,
            format="mp3",
            sample_rate=44100,
            channels=2
        )
        
        project = Project(
            id="test",
            name="Test",
            audio_file=audio_file
        )
        
        config = ExportConfiguration(fps=25.0)
        
        self.manager.current_project = project
        self.manager.export_config = config
        
        self.manager._calculate_total_frames()
        
        expected_frames = int(30.0 * 25.0)  # 750 frames
        self.assertEqual(self.manager.progress_info.total_frames, expected_frames)


class TestExportErrorHandling(unittest.TestCase):
    """Test enhanced error handling functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
        
        # Mock signals
        self.manager.export_failed = Mock()
        self.manager.export_failed.emit = Mock()
        self.manager.detailed_progress = Mock()
        self.manager.detailed_progress.emit = Mock()
    
    def test_get_error_suggestions_ffmpeg(self):
        """Test error suggestions for FFmpeg errors."""
        suggestions = self.manager._get_error_suggestions("ffmpeg not found")
        
        self.assertIn("Install FFmpeg", suggestions[0])
        self.assertIn("system PATH", suggestions[1])
    
    def test_get_error_suggestions_disk_space(self):
        """Test error suggestions for disk space errors."""
        suggestions = self.manager._get_error_suggestions("No space left on disk")
        
        disk_suggestions = [s for s in suggestions if "disk space" in s.lower()]
        self.assertGreater(len(disk_suggestions), 0)
    
    def test_get_error_suggestions_permission(self):
        """Test error suggestions for permission errors."""
        suggestions = self.manager._get_error_suggestions("Permission denied")
        
        permission_suggestions = [s for s in suggestions if "permission" in s.lower()]
        self.assertGreater(len(permission_suggestions), 0)
    
    def test_handle_export_error(self):
        """Test export error handling."""
        error_message = "Test error"
        context = "Test context"
        
        self.manager._handle_export_error(error_message, context)
        
        # Check error was added to history
        self.assertIn(f"{context}: {error_message}", self.manager.error_history)
        
        # Check progress info was updated
        self.assertEqual(self.manager.progress_info.last_error, f"{context}: {error_message}")
        self.assertGreater(len(self.manager.progress_info.error_suggestions), 0)
        
        # Check signals were emitted
        self.manager.export_failed.emit.assert_called_once()
        self.manager.detailed_progress.emit.assert_called_once()
    
    def test_retry_functionality(self):
        """Test export retry functionality."""
        config = ExportConfiguration()
        self.manager.export_config = config
        self.manager.retry_count = 0
        
        # Test can retry
        self.assertTrue(self.manager.can_retry())
        
        # Test retry count increment
        with patch.object(self.manager, 'start_export', return_value=True) as mock_start:
            success = self.manager.retry_export()
            self.assertTrue(success)
            self.assertEqual(self.manager.retry_count, 1)
    
    def test_retry_max_attempts(self):
        """Test retry with maximum attempts exceeded."""
        self.manager.retry_count = self.manager.max_retries
        
        success = self.manager.retry_export()
        self.assertFalse(success)
    
    def test_error_history_management(self):
        """Test error history management."""
        # Add some errors
        self.manager._handle_export_error("Error 1", "Context 1")
        self.manager._handle_export_error("Error 2", "Context 2")
        
        # Check history
        history = self.manager.get_error_history()
        self.assertEqual(len(history), 2)
        self.assertIn("Context 1: Error 1", history)
        self.assertIn("Context 2: Error 2", history)
        
        # Clear history
        self.manager.clear_error_history()
        self.assertEqual(len(self.manager.get_error_history()), 0)
        self.assertEqual(self.manager.retry_count, 0)


class TestExportCancellation(unittest.TestCase):
    """Test export cancellation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
        
        # Mock signals
        self.manager.export_cancelled = Mock()
        self.manager.export_cancelled.emit = Mock()
        self.manager.detailed_progress = Mock()
        self.manager.detailed_progress.emit = Mock()
    
    def test_cancel_export_not_running(self):
        """Test cancelling when export is not running."""
        self.manager.is_exporting = False
        
        self.manager.cancel_export()
        
        # Should not emit cancellation signal
        self.manager.export_cancelled.emit.assert_not_called()
    
    def test_cancel_export_running(self):
        """Test cancelling running export."""
        self.manager.is_exporting = True
        
        # Mock OpenGL renderer
        self.manager.opengl_renderer = Mock()
        self.manager.opengl_renderer.cancel_export = Mock()
        
        self.manager.cancel_export()
        
        # Check state
        self.assertFalse(self.manager.is_exporting)
        self.assertTrue(self.manager.cancel_requested)
        
        # Check renderer was cancelled
        self.manager.opengl_renderer.cancel_export.assert_called_once()
        
        # Check signals were emitted
        self.manager.export_cancelled.emit.assert_called_once()
    
    def test_force_cancel_export(self):
        """Test force cancellation."""
        self.manager.is_exporting = True
        
        self.manager.force_cancel_export()
        
        self.assertFalse(self.manager.is_exporting)
        self.assertTrue(self.manager.cancel_requested)
        self.manager.export_cancelled.emit.assert_called_once()


class TestExportUtilities(unittest.TestCase):
    """Test export utility methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ExportManager()
    
    def test_get_detailed_progress(self):
        """Test getting detailed progress information."""
        progress = self.manager.get_detailed_progress()
        
        self.assertIsInstance(progress, dict)
        self.assertIn('status', progress)
        self.assertIn('current_frame', progress)
        self.assertIn('total_frames', progress)
        self.assertIn('progress_percent', progress)
    
    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        metrics = self.manager.get_performance_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('frames_per_second', metrics)
        self.assertIn('elapsed_time', metrics)
        self.assertIn('current_fps', metrics)
    
    def test_enhanced_export_status(self):
        """Test enhanced export status information."""
        status = self.manager.get_export_status()
        
        # Check new fields
        self.assertIn('export_status', status)
        self.assertIn('cancel_requested', status)
        self.assertIn('retry_count', status)
        self.assertIn('max_retries', status)
        self.assertIn('error_count', status)
        self.assertIn('progress_percent', status)
        self.assertIn('estimated_remaining', status)


class TestIntegration(unittest.TestCase):
    """Integration tests for export manager."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ExportManager()
        
        # Create test project
        self.project = Project(
            id="integration_test",
            name="Integration Test",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=5.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            )
        )
        
        self.config = ExportConfiguration(
            output_dir=self.temp_dir,
            filename="integration_test.mp4",
            width=640,
            height=480
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_validation_workflow(self):
        """Test complete validation workflow."""
        # Set project
        self.manager.set_project(self.project)
        
        # Validate requirements
        results = self.manager.validate_export_requirements(self.config)
        
        # Should have some results
        self.assertGreater(len(results), 0)
        
        # Check for expected validation items
        messages = [r.message for r in results]
        
        # Should check for missing background (video/image)
        background_errors = [msg for msg in messages if "background" in msg.lower()]
        self.assertGreater(len(background_errors), 0)
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_export_workflow_with_mocks(self, mock_ffmpeg_check):
        """Test export workflow with mocked dependencies."""
        mock_ffmpeg_check.return_value = True
        
        # Create a complete project with video file to pass validation
        complete_project = Project(
            id="complete_test",
            name="Complete Test",
            audio_file=self.project.audio_file,
            video_file=VideoFile(
                path="test_video.mp4",
                duration=5.0,
                resolution={"width": 640, "height": 480},
                format="mp4",
                frame_rate=25.0
            )
        )
        
        # Set up project and manager
        self.manager.set_project(complete_project)
        
        # Mock OpenGL renderer
        self.manager.opengl_renderer = Mock()
        self.manager.opengl_renderer.setup_export = Mock(return_value=True)
        self.manager.opengl_renderer.start_export_async = Mock(return_value=True)
        
        # Start export
        success = self.manager.start_export(self.config)
        
        # Should succeed with mocked dependencies
        self.assertTrue(success)
        self.assertTrue(self.manager.is_exporting)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)