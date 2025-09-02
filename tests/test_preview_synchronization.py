"""
Unit tests for real-time preview synchronization system.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.preview_synchronizer import PreviewSynchronizer, MediaDecoder, SyncState
from core.models import Project, VideoFile, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle


class TestSyncState(unittest.TestCase):
    """Test SyncState dataclass"""
    
    def test_sync_state_initialization(self):
        """Test SyncState default initialization"""
        state = SyncState()
        
        self.assertEqual(state.current_time, 0.0)
        self.assertFalse(state.is_playing)
        self.assertEqual(state.duration, 0.0)
        self.assertEqual(state.frame_rate, 30.0)
        self.assertEqual(state.last_update_time, 0.0)
    
    def test_sync_state_custom_values(self):
        """Test SyncState with custom values"""
        state = SyncState(
            current_time=10.5,
            is_playing=True,
            duration=120.0,
            frame_rate=60.0,
            last_update_time=1234567890.0
        )
        
        self.assertEqual(state.current_time, 10.5)
        self.assertTrue(state.is_playing)
        self.assertEqual(state.duration, 120.0)
        self.assertEqual(state.frame_rate, 60.0)
        self.assertEqual(state.last_update_time, 1234567890.0)


class TestMediaDecoder(unittest.TestCase):
    """Test MediaDecoder functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.decoder = MediaDecoder()
        
        # Create test project with video
        self.video_project = Project(
            id="test_video",
            name="Test Video Project",
            video_file=VideoFile(
                path="test_video.mp4",
                duration=60.0,
                frame_rate=30.0,
                resolution={"width": 1920, "height": 1080}
            ),
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=60.0
            )
        )
        
        # Create test project with image
        self.image_project = Project(
            id="test_image",
            name="Test Image Project",
            image_file=Mock(),
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=45.0
            )
        )
    
    def test_load_video_project(self):
        """Test loading project with video file"""
        success = self.decoder.load_project(self.video_project)
        
        self.assertTrue(success)
        self.assertTrue(self.decoder.is_initialized)
        self.assertEqual(self.decoder.duration, 60.0)
        self.assertEqual(self.decoder.frame_rate, 30.0)
    
    def test_load_image_project(self):
        """Test loading project with image file"""
        success = self.decoder.load_project(self.image_project)
        
        self.assertTrue(success)
        self.assertTrue(self.decoder.is_initialized)
        self.assertEqual(self.decoder.duration, 45.0)
        self.assertEqual(self.decoder.frame_rate, 30.0)
    
    def test_load_invalid_project(self):
        """Test loading project without required files"""
        invalid_project = Project(id="invalid", name="Invalid")
        
        success = self.decoder.load_project(invalid_project)
        
        self.assertFalse(success)
        self.assertFalse(self.decoder.is_initialized)
    
    def test_seek_to_time_video(self):
        """Test seeking to specific time with video"""
        self.decoder.load_project(self.video_project)
        
        frame = self.decoder.seek_to_time(30.0)
        
        self.assertIsInstance(frame, QImage)
        self.assertFalse(frame.isNull())
    
    def test_seek_to_time_image(self):
        """Test seeking to specific time with image"""
        # Mock image file path
        self.image_project.image_file.path = "nonexistent.jpg"
        self.decoder.load_project(self.image_project)
        
        frame = self.decoder.seek_to_time(15.0)
        
        self.assertIsInstance(frame, QImage)
        # Should return fallback frame even if image doesn't exist
        self.assertFalse(frame.isNull())
    
    def test_get_duration(self):
        """Test getting media duration"""
        self.decoder.load_project(self.video_project)
        
        duration = self.decoder.get_duration()
        
        self.assertEqual(duration, 60.0)
    
    def test_get_frame_rate(self):
        """Test getting frame rate"""
        self.decoder.load_project(self.video_project)
        
        frame_rate = self.decoder.get_frame_rate()
        
        self.assertEqual(frame_rate, 30.0)


class TestPreviewSynchronizer(unittest.TestCase):
    """Test PreviewSynchronizer functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.synchronizer = PreviewSynchronizer()
        
        # Create test project
        self.project = Project(
            id="test_sync",
            name="Test Sync Project",
            video_file=VideoFile(
                path="test.mp4",
                duration=120.0,
                frame_rate=30.0
            ),
            audio_file=AudioFile(
                path="test.mp3",
                duration=120.0
            ),
            subtitle_file=SubtitleFile(
                path="test.ass",
                lines=[
                    SubtitleLine(start_time=0.0, end_time=5.0, text="First subtitle"),
                    SubtitleLine(start_time=5.0, end_time=10.0, text="Second subtitle"),
                    SubtitleLine(start_time=15.0, end_time=20.0, text="Third subtitle")
                ],
                styles=[SubtitleStyle(name="Default")]
            )
        )
    
    def test_initialization(self):
        """Test synchronizer initialization"""
        self.assertIsNotNone(self.synchronizer.media_decoder)
        self.assertIsNotNone(self.synchronizer.subtitle_renderer)
        self.assertIsNotNone(self.synchronizer.sync_state)
        self.assertIsNotNone(self.synchronizer.sync_timer)
        self.assertEqual(len(self.synchronizer.subtitle_lines), 0)
        self.assertEqual(len(self.synchronizer.subtitle_styles), 0)
    
    def test_load_project(self):
        """Test loading project into synchronizer"""
        success = self.synchronizer.load_project(self.project)
        
        self.assertTrue(success)
        self.assertEqual(self.synchronizer.current_project, self.project)
        self.assertEqual(len(self.synchronizer.subtitle_lines), 3)
        self.assertEqual(len(self.synchronizer.subtitle_styles), 1)
        self.assertEqual(self.synchronizer.sync_state.duration, 120.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 0.0)
        self.assertFalse(self.synchronizer.sync_state.is_playing)
    
    def test_play_pause_functionality(self):
        """Test play and pause functionality"""
        self.synchronizer.load_project(self.project)
        
        # Test play
        self.synchronizer.play()
        self.assertTrue(self.synchronizer.sync_state.is_playing)
        self.assertTrue(self.synchronizer.sync_timer.isActive())
        
        # Test pause
        self.synchronizer.pause()
        self.assertFalse(self.synchronizer.sync_state.is_playing)
        self.assertFalse(self.synchronizer.sync_timer.isActive())
    
    def test_stop_functionality(self):
        """Test stop functionality"""
        self.synchronizer.load_project(self.project)
        self.synchronizer.play()
        self.synchronizer.seek_to_time(30.0)
        
        # Test stop
        self.synchronizer.stop()
        
        self.assertFalse(self.synchronizer.sync_state.is_playing)
        self.assertEqual(self.synchronizer.sync_state.current_time, 0.0)
    
    def test_seek_to_time(self):
        """Test seeking to specific timestamp"""
        self.synchronizer.load_project(self.project)
        
        # Test normal seek
        self.synchronizer.seek_to_time(45.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 45.0)
        
        # Test seek beyond duration (should clamp)
        self.synchronizer.seek_to_time(150.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 120.0)
        
        # Test negative seek (should clamp to 0)
        self.synchronizer.seek_to_time(-10.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 0.0)
    
    def test_seek_to_progress(self):
        """Test seeking by progress percentage"""
        self.synchronizer.load_project(self.project)
        
        # Test 50% progress
        self.synchronizer.seek_to_progress(0.5)
        self.assertEqual(self.synchronizer.sync_state.current_time, 60.0)
        
        # Test 0% progress
        self.synchronizer.seek_to_progress(0.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 0.0)
        
        # Test 100% progress
        self.synchronizer.seek_to_progress(1.0)
        self.assertEqual(self.synchronizer.sync_state.current_time, 120.0)
    
    def test_update_subtitles_realtime(self):
        """Test real-time subtitle updates"""
        self.synchronizer.load_project(self.project)
        
        # Create new subtitle data
        new_lines = [
            SubtitleLine(start_time=0.0, end_time=3.0, text="Updated first subtitle"),
            SubtitleLine(start_time=3.0, end_time=6.0, text="Updated second subtitle")
        ]
        new_styles = {"Default": SubtitleStyle(name="Default")}
        
        # Update subtitles
        self.synchronizer.update_subtitles(new_lines, new_styles)
        
        self.assertEqual(len(self.synchronizer.subtitle_lines), 2)
        self.assertEqual(self.synchronizer.subtitle_lines[0].text, "Updated first subtitle")
        self.assertEqual(self.synchronizer.subtitle_lines[1].text, "Updated second subtitle")
    
    def test_get_visible_subtitles(self):
        """Test getting visible subtitles at specific timestamp"""
        self.synchronizer.load_project(self.project)
        
        # Test timestamp with visible subtitle
        visible = self.synchronizer._get_visible_subtitles(2.5)
        self.assertEqual(len(visible), 1)
        
        # Test timestamp with no visible subtitles
        visible = self.synchronizer._get_visible_subtitles(12.0)
        self.assertEqual(len(visible), 0)
        
        # Test timestamp with multiple visible subtitles (if overlapping)
        visible = self.synchronizer._get_visible_subtitles(7.5)
        self.assertEqual(len(visible), 1)
    
    def test_subtitle_change_callbacks(self):
        """Test subtitle change callback system"""
        callback_called = False
        callback_args = None
        
        def test_callback(lines, styles):
            nonlocal callback_called, callback_args
            callback_called = True
            callback_args = (lines, styles)
        
        # Add callback
        self.synchronizer.add_subtitle_change_callback(test_callback)
        
        # Update subtitles to trigger callback
        new_lines = [SubtitleLine(start_time=0.0, end_time=5.0, text="Test")]
        new_styles = {"Default": SubtitleStyle(name="Default")}
        self.synchronizer.update_subtitles(new_lines, new_styles)
        
        self.assertTrue(callback_called)
        self.assertEqual(len(callback_args[0]), 1)
        self.assertEqual(callback_args[0][0].text, "Test")
        
        # Remove callback
        self.synchronizer.remove_subtitle_change_callback(test_callback)
        
        # Reset and update again
        callback_called = False
        self.synchronizer.update_subtitles([], {})
        
        # Callback should not be called after removal
        self.assertFalse(callback_called)
    
    def test_performance_stats(self):
        """Test performance statistics"""
        self.synchronizer.load_project(self.project)
        
        stats = self.synchronizer.get_performance_stats()
        
        self.assertIn('frame_count', stats)
        self.assertIn('current_time', stats)
        self.assertIn('is_playing', stats)
        self.assertIn('duration', stats)
        self.assertIn('frame_rate', stats)
        self.assertIn('subtitle_cache_size', stats)
        
        self.assertIsInstance(stats['frame_count'], int)
        self.assertIsInstance(stats['current_time'], float)
        self.assertIsInstance(stats['is_playing'], bool)
        self.assertIsInstance(stats['duration'], float)
        self.assertIsInstance(stats['frame_rate'], float)
    
    def test_cleanup(self):
        """Test resource cleanup"""
        self.synchronizer.load_project(self.project)
        
        # Add a callback to test cleanup
        def dummy_callback(lines, styles):
            pass
        self.synchronizer.add_subtitle_change_callback(dummy_callback)
        
        # Cleanup
        self.synchronizer.cleanup()
        
        # Verify cleanup
        self.assertFalse(self.synchronizer.sync_state.is_playing)
        self.assertEqual(len(self.synchronizer.subtitle_change_callbacks), 0)
    
    @patch('time.time')
    def test_sync_update_timing(self, mock_time):
        """Test synchronization timing updates"""
        self.synchronizer.load_project(self.project)
        
        # Mock time progression
        mock_time.side_effect = [0.0, 0.033, 0.066, 0.1]  # 33ms intervals
        
        # Start playback
        self.synchronizer.play()
        
        # Simulate timer updates
        initial_time = self.synchronizer.sync_state.current_time
        self.synchronizer._update_sync()
        
        # Time should have advanced
        self.assertGreater(self.synchronizer.sync_state.current_time, initial_time)
    
    def test_signal_connections(self):
        """Test that signals are properly connected"""
        # Check that synchronizer has the expected signals
        self.assertTrue(hasattr(self.synchronizer, 'frame_updated'))
        self.assertTrue(hasattr(self.synchronizer, 'time_position_changed'))
        self.assertTrue(hasattr(self.synchronizer, 'playback_state_changed'))
        self.assertTrue(hasattr(self.synchronizer, 'subtitle_updated'))
        
        # Check that media decoder has expected signals
        self.assertTrue(hasattr(self.synchronizer.media_decoder, 'frame_ready'))
        self.assertTrue(hasattr(self.synchronizer.media_decoder, 'audio_position_changed'))


class TestSynchronizationIntegration(unittest.TestCase):
    """Integration tests for synchronization system"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.synchronizer = PreviewSynchronizer()
        
        # Create comprehensive test project
        self.project = Project(
            id="integration_test",
            name="Integration Test Project",
            video_file=VideoFile(
                path="integration_test.mp4",
                duration=30.0,
                frame_rate=25.0,
                resolution={"width": 1280, "height": 720}
            ),
            audio_file=AudioFile(
                path="integration_test.mp3",
                duration=30.0,
                sample_rate=44100,
                channels=2
            ),
            subtitle_file=SubtitleFile(
                path="integration_test.ass",
                lines=[
                    SubtitleLine(start_time=1.0, end_time=4.0, text="Integration test line 1"),
                    SubtitleLine(start_time=5.0, end_time=8.0, text="Integration test line 2"),
                    SubtitleLine(start_time=10.0, end_time=13.0, text="Integration test line 3"),
                    SubtitleLine(start_time=15.0, end_time=18.0, text="Integration test line 4")
                ],
                styles=[
                    SubtitleStyle(name="Default", font_size=24),
                    SubtitleStyle(name="Large", font_size=32)
                ]
            )
        )
    
    def test_full_playback_cycle(self):
        """Test complete playback cycle with synchronization"""
        # Load project
        success = self.synchronizer.load_project(self.project)
        self.assertTrue(success)
        
        # Test initial state
        self.assertEqual(self.synchronizer.get_current_time(), 0.0)
        self.assertEqual(self.synchronizer.get_duration(), 30.0)
        self.assertFalse(self.synchronizer.is_playing())
        
        # Start playback
        self.synchronizer.play()
        self.assertTrue(self.synchronizer.is_playing())
        
        # Seek to middle
        self.synchronizer.seek_to_time(15.0)
        self.assertEqual(self.synchronizer.get_current_time(), 15.0)
        
        # Pause
        self.synchronizer.pause()
        self.assertFalse(self.synchronizer.is_playing())
        
        # Stop (should reset to beginning)
        self.synchronizer.stop()
        self.assertEqual(self.synchronizer.get_current_time(), 0.0)
        self.assertFalse(self.synchronizer.is_playing())
    
    def test_subtitle_synchronization_accuracy(self):
        """Test subtitle visibility synchronization accuracy"""
        self.synchronizer.load_project(self.project)
        
        # Test various timestamps for subtitle visibility
        test_cases = [
            (0.5, 0),   # Before first subtitle
            (2.5, 1),   # During first subtitle
            (4.5, 0),   # Between first and second
            (6.5, 1),   # During second subtitle
            (11.5, 1),  # During third subtitle
            (20.0, 0),  # After all subtitles
        ]
        
        for timestamp, expected_count in test_cases:
            visible = self.synchronizer._get_visible_subtitles(timestamp)
            self.assertEqual(len(visible), expected_count, 
                           f"At timestamp {timestamp}, expected {expected_count} subtitles, got {len(visible)}")
    
    def test_realtime_subtitle_updates_during_playback(self):
        """Test real-time subtitle updates while playing"""
        self.synchronizer.load_project(self.project)
        
        # Start playback
        self.synchronizer.play()
        
        # Seek to a position with visible subtitle
        self.synchronizer.seek_to_time(2.0)
        
        # Update subtitles in real-time
        updated_lines = [
            SubtitleLine(start_time=1.0, end_time=4.0, text="UPDATED: Integration test line 1"),
            SubtitleLine(start_time=5.0, end_time=8.0, text="UPDATED: Integration test line 2")
        ]
        updated_styles = {"Default": SubtitleStyle(name="Default", font_size=28)}
        
        self.synchronizer.update_subtitles(updated_lines, updated_styles)
        
        # Verify updates took effect
        self.assertEqual(len(self.synchronizer.subtitle_lines), 2)
        self.assertTrue(self.synchronizer.subtitle_lines[0].text.startswith("UPDATED:"))
        
        # Verify subtitle is still visible at current time
        visible = self.synchronizer._get_visible_subtitles(2.0)
        self.assertEqual(len(visible), 1)


if __name__ == '__main__':
    # Create QApplication for tests that need Qt
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Run tests silently
    unittest.main(verbosity=0, exit=False, buffer=True)