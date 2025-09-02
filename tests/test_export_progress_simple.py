"""
Simple test for export progress tracking and error handling functionality
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch

try:
    from src.core.export_manager import (
        ExportManager, ExportConfiguration, ExportStatus, 
        ExportProgressInfo
    )
    from src.core.models import Project, AudioFile, VideoFile
    from src.core.validation import ValidationResult, ValidationLevel
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
    from export_manager import (
        ExportManager, ExportConfiguration, ExportStatus, 
        ExportProgressInfo
    )
    from models import Project, AudioFile, VideoFile
    from validation import ValidationResult, ValidationLevel


class TestExportProgressSimple(unittest.TestCase):
    """Simple test for export progress tracking and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ExportManager()
        
        # Disable Qt timers to avoid threading issues in tests
        self.manager.progress_timer = None
        
        # Create test project
        self.project = Project(
            id="simple_test",
            name="Simple Test",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=10.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            ),
            video_file=VideoFile(
                path="test_video.mp4",
                duration=10.0,
                resolution={"width": 640, "height": 480},
                format="mp4",
                frame_rate=25.0
            )
        )
        
        self.config = ExportConfiguration(
            output_dir=self.temp_dir,
            filename="simple_test.mp4",
            width=640,
            height=480,
            fps=25.0
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_progress_info_functionality(self):
        """Test ExportProgressInfo functionality."""
        progress = ExportProgressInfo()
        
        # Test initial state
        self.assertEqual(progress.status, ExportStatus.IDLE)
        self.assertEqual(progress.current_frame, 0)
        self.assertEqual(progress.total_frames, 0)
        self.assertEqual(progress.progress_percent, 0.0)
        
        # Test progress calculation
        progress.current_frame = 50
        progress.total_frames = 100
        progress.update_timing()
        
        self.assertEqual(progress.progress_percent, 50.0)
        
        # Test dictionary conversion
        progress_dict = progress.to_dict()
        self.assertIsInstance(progress_dict, dict)
        self.assertEqual(progress_dict['current_frame'], 50)
        self.assertEqual(progress_dict['total_frames'], 100)
        self.assertEqual(progress_dict['progress_percent'], 50.0)
    
    def test_error_suggestions_functionality(self):
        """Test error suggestion generation."""
        # Test FFmpeg error suggestions
        ffmpeg_suggestions = self.manager._get_error_suggestions("ffmpeg not found")
        self.assertGreater(len(ffmpeg_suggestions), 0)
        self.assertTrue(any("ffmpeg" in s.lower() for s in ffmpeg_suggestions))
        
        # Test disk space error suggestions
        disk_suggestions = self.manager._get_error_suggestions("No space left on disk")
        self.assertGreater(len(disk_suggestions), 0)
        self.assertTrue(any("disk space" in s.lower() for s in disk_suggestions))
        
        # Test permission error suggestions
        perm_suggestions = self.manager._get_error_suggestions("Permission denied")
        self.assertGreater(len(perm_suggestions), 0)
        self.assertTrue(any("permission" in s.lower() for s in perm_suggestions))
        
        # Test generic error suggestions
        generic_suggestions = self.manager._get_error_suggestions("Unknown error")
        self.assertGreater(len(generic_suggestions), 0)
    
    def test_error_handling_workflow(self):
        """Test error handling workflow."""
        error_message = "Test export error"
        context = "Test Context"
        
        # Handle error
        self.manager._handle_export_error(error_message, context)
        
        # Check error was recorded
        error_history = self.manager.get_error_history()
        self.assertEqual(len(error_history), 1)
        self.assertIn(error_message, error_history[0])
        self.assertIn(context, error_history[0])
        
        # Check progress info was updated
        progress = self.manager.get_detailed_progress()
        self.assertEqual(progress['status'], 'failed')
        self.assertIsNotNone(progress['last_error'])
        self.assertGreater(len(progress['error_suggestions']), 0)
        
        # Test error history management
        self.manager.clear_error_history()
        self.assertEqual(len(self.manager.get_error_history()), 0)
        self.assertEqual(self.manager.retry_count, 0)
    
    def test_status_update_functionality(self):
        """Test status update functionality."""
        # Test status update
        self.manager._update_status(
            ExportStatus.RENDERING,
            "Test operation",
            "Test details"
        )
        
        # Check status was updated
        self.assertEqual(self.manager.export_status, ExportStatus.RENDERING)
        self.assertEqual(self.manager.progress_info.current_operation, "Test operation")
        self.assertEqual(self.manager.progress_info.detailed_status, "Test details")
        
        # Check export status
        status = self.manager.get_export_status()
        self.assertEqual(status['export_status'], 'rendering')
    
    def test_total_frames_calculation(self):
        """Test total frames calculation."""
        self.manager.current_project = self.project
        self.manager.export_config = self.config
        
        self.manager._calculate_total_frames()
        
        # Should calculate based on audio duration and fps
        expected_frames = int(10.0 * 25.0)  # 250 frames
        self.assertEqual(self.manager.progress_info.total_frames, expected_frames)
    
    def test_retry_functionality_basic(self):
        """Test basic retry functionality."""
        # Set up for retry
        self.manager.export_config = self.config
        self.manager.retry_count = 0
        
        # Test can retry
        self.assertTrue(self.manager.can_retry())
        
        # Test retry count limits
        self.manager.retry_count = self.manager.max_retries
        self.assertFalse(self.manager.can_retry())
        
        # Test retry with max attempts
        success = self.manager.retry_export()
        self.assertFalse(success)
        
        # Check error was recorded
        errors = self.manager.get_error_history()
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("maximum retry" in error.lower() for error in errors))
    
    def test_cancellation_functionality(self):
        """Test export cancellation functionality."""
        # Set up export state
        self.manager.is_exporting = True
        self.manager.cancel_requested = False
        
        # Test cancellation
        self.manager.cancel_export()
        
        # Check state
        self.assertFalse(self.manager.is_exporting)
        self.assertTrue(self.manager.cancel_requested)
        
        # Check status
        status = self.manager.get_export_status()
        self.assertEqual(status['export_status'], 'cancelled')
    
    def test_force_cancellation(self):
        """Test force cancellation functionality."""
        # Set up export state
        self.manager.is_exporting = True
        self.manager.cancel_requested = False
        
        # Test force cancellation
        self.manager.force_cancel_export()
        
        # Check state
        self.assertFalse(self.manager.is_exporting)
        self.assertTrue(self.manager.cancel_requested)
        self.assertEqual(self.manager.export_status, ExportStatus.CANCELLED)
    
    def test_performance_metrics_structure(self):
        """Test performance metrics structure."""
        metrics = self.manager.get_performance_metrics()
        
        # Check required keys
        expected_keys = [
            'frames_per_second', 'elapsed_time', 'estimated_total',
            'current_fps', 'progress_percent', 'total_frames', 'current_frame'
        ]
        
        for key in expected_keys:
            self.assertIn(key, metrics)
            self.assertIsInstance(metrics[key], (int, float))
    
    def test_detailed_progress_structure(self):
        """Test detailed progress information structure."""
        progress = self.manager.get_detailed_progress()
        
        # Check required keys
        expected_keys = [
            'status', 'current_frame', 'total_frames', 'progress_percent',
            'elapsed_time', 'estimated_remaining', 'current_operation',
            'detailed_status', 'error_suggestions'
        ]
        
        for key in expected_keys:
            self.assertIn(key, progress)
    
    def test_validation_with_mock_export(self):
        """Test validation allows mock export when OpenGL not available."""
        # Disable OpenGL renderer
        self.manager.opengl_renderer = None
        self.manager.set_project(self.project)
        
        # Validate requirements
        results = self.manager.validate_export_requirements(self.config)
        
        # Should have warning about OpenGL but no blocking errors
        opengl_warnings = [r for r in results if "opengl" in r.message.lower() and r.level == ValidationLevel.WARNING]
        self.assertGreater(len(opengl_warnings), 0)
        
        # Should not have blocking errors for OpenGL
        opengl_errors = [r for r in results if "opengl" in r.message.lower() and r.level == ValidationLevel.ERROR]
        self.assertEqual(len(opengl_errors), 0)
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_validation_error_handling(self, mock_ffmpeg_check):
        """Test validation error handling."""
        mock_ffmpeg_check.return_value = False  # FFmpeg not available
        
        self.manager.set_project(self.project)
        
        # Validate requirements
        results = self.manager.validate_export_requirements(self.config)
        
        # Should have FFmpeg error
        ffmpeg_errors = [r for r in results if "ffmpeg" in r.message.lower() and r.level == ValidationLevel.ERROR]
        self.assertGreater(len(ffmpeg_errors), 0)


if __name__ == '__main__':
    # Run simple tests
    unittest.main(verbosity=2, buffer=True)