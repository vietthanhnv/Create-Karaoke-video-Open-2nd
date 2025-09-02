"""
Integration test for export progress tracking and error handling
"""

import unittest
import tempfile
import os
import time
from unittest.mock import Mock, patch

try:
    from src.core.export_manager import ExportManager, ExportConfiguration, ExportStatus
    from src.core.models import Project, AudioFile, VideoFile
    from src.core.validation import ValidationResult, ValidationLevel
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
    from export_manager import ExportManager, ExportConfiguration, ExportStatus
    from models import Project, AudioFile, VideoFile
    from validation import ValidationResult, ValidationLevel


class TestExportProgressIntegration(unittest.TestCase):
    """Integration test for enhanced export progress tracking and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ExportManager()
        
        # Create test project
        self.project = Project(
            id="progress_test",
            name="Progress Test",
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
            filename="progress_test.mp4",
            width=640,
            height=480,
            fps=25.0
        )
        
        # Track emitted signals
        self.progress_updates = []
        self.status_updates = []
        self.detailed_updates = []
        
        # Connect to signals
        if hasattr(self.manager, 'export_progress'):
            self.manager.export_progress.connect(self._on_progress_update)
        if hasattr(self.manager, 'status_changed'):
            self.manager.status_changed.connect(self._on_status_update)
        if hasattr(self.manager, 'detailed_progress'):
            self.manager.detailed_progress.connect(self._on_detailed_update)
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def _on_progress_update(self, progress_info):
        """Handle progress updates."""
        self.progress_updates.append(progress_info.copy())
    
    def _on_status_update(self, status):
        """Handle status updates."""
        self.status_updates.append(status)
    
    def _on_detailed_update(self, detailed_info):
        """Handle detailed progress updates."""
        self.detailed_updates.append(detailed_info.copy())
    
    @patch('src.core.export_manager.ExportManager._check_ffmpeg_available')
    def test_complete_export_progress_flow(self, mock_ffmpeg_check):
        """Test complete export progress flow with mock export."""
        mock_ffmpeg_check.return_value = True
        
        # Disable OpenGL renderer to avoid context issues
        self.manager.opengl_renderer = None
        
        # Set up project
        self.manager.set_project(self.project)
        
        # Start export (will use mock export since no OpenGL renderer)
        success = self.manager.start_export(self.config)
        self.assertTrue(success)
        
        # Wait for mock export to complete
        timeout = 10  # seconds
        start_time = time.time()
        
        while self.manager.is_exporting and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        # Verify export completed
        self.assertFalse(self.manager.is_exporting)
        
        # Check that we received progress updates
        self.assertGreater(len(self.progress_updates), 0)
        
        # Check that we received status updates
        self.assertGreater(len(self.status_updates), 0)
        
        # Verify status progression
        expected_statuses = ['validating', 'preparing', 'rendering']
        for status in expected_statuses:
            self.assertIn(status, self.status_updates)
        
        # Check final progress
        if self.progress_updates:
            final_progress = self.progress_updates[-1]
            self.assertEqual(final_progress['progress_percent'], 100.0)
        
        print(f"Received {len(self.progress_updates)} progress updates")
        print(f"Status progression: {self.status_updates}")
    
    def test_export_error_handling_and_suggestions(self):
        """Test export error handling with suggestions."""
        # Test FFmpeg not available error
        with patch('src.core.export_manager.ExportManager._check_ffmpeg_available', return_value=False):
            self.manager.set_project(self.project)
            
            success = self.manager.start_export(self.config)
            self.assertFalse(success)
            
            # Check error history
            errors = self.manager.get_error_history()
            self.assertGreater(len(errors), 0)
            
            # Check that error contains FFmpeg reference
            ffmpeg_error = any("ffmpeg" in error.lower() for error in errors)
            self.assertTrue(ffmpeg_error)
            
            # Check suggestions
            if self.detailed_updates:
                last_update = self.detailed_updates[-1]
                if 'error_suggestions' in last_update:
                    suggestions = last_update['error_suggestions']
                    self.assertGreater(len(suggestions), 0)
                    # Should suggest FFmpeg installation
                    ffmpeg_suggestion = any("ffmpeg" in suggestion.lower() for suggestion in suggestions)
                    self.assertTrue(ffmpeg_suggestion)
    
    def test_export_cancellation(self):
        """Test export cancellation functionality."""
        with patch('src.core.export_manager.ExportManager._check_ffmpeg_available', return_value=True):
            # Disable OpenGL renderer to avoid context issues
            self.manager.opengl_renderer = None
            
            self.manager.set_project(self.project)
            
            # Start export
            success = self.manager.start_export(self.config)
            self.assertTrue(success)
            self.assertTrue(self.manager.is_exporting)
            
            # Cancel export
            self.manager.cancel_export()
            
            # Verify cancellation
            self.assertFalse(self.manager.is_exporting)
            self.assertTrue(self.manager.cancel_requested)
            
            # Check status
            status = self.manager.get_export_status()
            self.assertEqual(status['export_status'], 'cancelled')
    
    def test_retry_functionality(self):
        """Test export retry functionality."""
        # Set up configuration
        self.manager.export_config = self.config
        self.manager.retry_count = 0
        
        # Test can retry
        self.assertTrue(self.manager.can_retry())
        
        # Test retry count increment without mocking start_export
        # (since retry_export calls start_export internally)
        original_retry_count = self.manager.retry_count
        
        # Mock the validation to fail so retry doesn't actually start export
        with patch.object(self.manager, 'validate_export_requirements') as mock_validate:
            mock_validate.return_value = [ValidationResult(
                level=ValidationLevel.ERROR,
                message="Test validation error",
                suggestion="Test suggestion"
            )]
            
            success = self.manager.retry_export()
            self.assertFalse(success)  # Should fail due to validation error
            self.assertEqual(self.manager.retry_count, original_retry_count + 1)
        
        # Test max retries
        self.manager.retry_count = self.manager.max_retries
        self.assertFalse(self.manager.can_retry())
        
        success = self.manager.retry_export()
        self.assertFalse(success)
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics tracking during export."""
        with patch('src.core.export_manager.ExportManager._check_ffmpeg_available', return_value=True):
            # Disable OpenGL renderer to avoid context issues
            self.manager.opengl_renderer = None
            
            self.manager.set_project(self.project)
            
            # Start export
            success = self.manager.start_export(self.config)
            self.assertTrue(success)
            
            # Let it run briefly
            time.sleep(0.5)
            
            # Get performance metrics
            metrics = self.manager.get_performance_metrics()
            
            # Verify metrics structure
            expected_keys = [
                'frames_per_second', 'elapsed_time', 'estimated_total',
                'current_fps', 'progress_percent', 'total_frames', 'current_frame'
            ]
            
            for key in expected_keys:
                self.assertIn(key, metrics)
            
            # Cancel to clean up
            self.manager.cancel_export()
    
    def test_detailed_progress_information(self):
        """Test detailed progress information."""
        progress = self.manager.get_detailed_progress()
        
        # Verify detailed progress structure
        expected_keys = [
            'status', 'current_frame', 'total_frames', 'progress_percent',
            'elapsed_time', 'estimated_remaining', 'current_operation',
            'detailed_status', 'error_suggestions'
        ]
        
        for key in expected_keys:
            self.assertIn(key, progress)
        
        # Initial status should be idle
        self.assertEqual(progress['status'], 'idle')
        self.assertEqual(progress['progress_percent'], 0.0)


if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2, buffer=True)