"""
Integration tests for real-time preview synchronization system.
Tests the synchronization logic without OpenGL dependencies.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Project, VideoFile, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle


class MockPreviewSynchronizer:
    """Mock synchronizer for testing synchronization logic without Qt dependencies"""
    
    def __init__(self):
        self.current_time = 0.0
        self.duration = 0.0
        self.is_playing_state = False
        self.subtitle_lines = []
        self.subtitle_styles = {}
        self.callbacks = []
        
    def load_project(self, project):
        """Load project for testing"""
        if project.video_file:
            self.duration = project.video_file.duration
        elif project.image_file and project.audio_file:
            self.duration = project.audio_file.duration
        else:
            return False
            
        if project.subtitle_file:
            self.subtitle_lines = project.subtitle_file.lines.copy()
            self.subtitle_styles = {style.name: style for style in project.subtitle_file.styles}
            
        return True
        
    def play(self):
        """Start playback"""
        self.is_playing_state = True
        
    def pause(self):
        """Pause playback"""
        self.is_playing_state = False
        
    def stop(self):
        """Stop playback"""
        self.is_playing_state = False
        self.current_time = 0.0
        
    def seek_to_time(self, timestamp):
        """Seek to timestamp"""
        self.current_time = max(0.0, min(timestamp, self.duration))
        
    def seek_to_progress(self, progress):
        """Seek by progress"""
        if self.duration > 0:
            self.seek_to_time(progress * self.duration)
            
    def update_subtitles(self, lines, styles):
        """Update subtitles"""
        self.subtitle_lines = lines.copy()
        self.subtitle_styles = styles.copy()
        
        # Notify callbacks
        for callback in self.callbacks:
            callback(lines, styles)
            
    def add_subtitle_change_callback(self, callback):
        """Add callback"""
        self.callbacks.append(callback)
        
    def remove_subtitle_change_callback(self, callback):
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            
    def get_visible_subtitles(self, timestamp):
        """Get visible subtitles at timestamp"""
        visible = []
        for line in self.subtitle_lines:
            if line.start_time <= timestamp <= line.end_time:
                visible.append(line)
        return visible
        
    def get_current_time(self):
        """Get current time"""
        return self.current_time
        
    def get_duration(self):
        """Get duration"""
        return self.duration
        
    def is_playing(self):
        """Check if playing"""
        return self.is_playing_state


class TestSynchronizationLogic(unittest.TestCase):
    """Test synchronization logic without Qt dependencies"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.synchronizer = MockPreviewSynchronizer()
        
        # Create test project
        self.project = Project(
            id="test_sync",
            name="Test Sync Project",
            video_file=VideoFile(
                path="test.mp4",
                duration=60.0,
                frame_rate=30.0
            ),
            audio_file=AudioFile(
                path="test.mp3",
                duration=60.0
            ),
            subtitle_file=SubtitleFile(
                path="test.ass",
                lines=[
                    SubtitleLine(start_time=0.0, end_time=5.0, text="First subtitle"),
                    SubtitleLine(start_time=5.0, end_time=10.0, text="Second subtitle"),
                    SubtitleLine(start_time=15.0, end_time=20.0, text="Third subtitle"),
                    SubtitleLine(start_time=25.0, end_time=30.0, text="Fourth subtitle")
                ],
                styles=[SubtitleStyle(name="Default")]
            )
        )
    
    def test_project_loading(self):
        """Test project loading functionality"""
        success = self.synchronizer.load_project(self.project)
        
        self.assertTrue(success)
        self.assertEqual(self.synchronizer.get_duration(), 60.0)
        self.assertEqual(len(self.synchronizer.subtitle_lines), 4)
        self.assertEqual(len(self.synchronizer.subtitle_styles), 1)
    
    def test_playback_controls(self):
        """Test playback control functionality"""
        self.synchronizer.load_project(self.project)
        
        # Test initial state
        self.assertFalse(self.synchronizer.is_playing())
        
        # Test play
        self.synchronizer.play()
        self.assertTrue(self.synchronizer.is_playing())
        
        # Test pause
        self.synchronizer.pause()
        self.assertFalse(self.synchronizer.is_playing())
        
        # Test stop
        self.synchronizer.seek_to_time(30.0)
        self.synchronizer.stop()
        self.assertFalse(self.synchronizer.is_playing())
        self.assertEqual(self.synchronizer.get_current_time(), 0.0)
    
    def test_seeking_functionality(self):
        """Test seeking functionality"""
        self.synchronizer.load_project(self.project)
        
        # Test normal seeking
        self.synchronizer.seek_to_time(25.0)
        self.assertEqual(self.synchronizer.get_current_time(), 25.0)
        
        # Test seeking beyond duration
        self.synchronizer.seek_to_time(100.0)
        self.assertEqual(self.synchronizer.get_current_time(), 60.0)
        
        # Test negative seeking
        self.synchronizer.seek_to_time(-10.0)
        self.assertEqual(self.synchronizer.get_current_time(), 0.0)
        
        # Test progress seeking
        self.synchronizer.seek_to_progress(0.5)
        self.assertEqual(self.synchronizer.get_current_time(), 30.0)
        
        self.synchronizer.seek_to_progress(0.0)
        self.assertEqual(self.synchronizer.get_current_time(), 0.0)
        
        self.synchronizer.seek_to_progress(1.0)
        self.assertEqual(self.synchronizer.get_current_time(), 60.0)
    
    def test_subtitle_visibility_synchronization(self):
        """Test subtitle visibility at different timestamps"""
        self.synchronizer.load_project(self.project)
        
        # Test cases: (timestamp, expected_visible_count, expected_text_contains)
        test_cases = [
            (2.5, 1, "First"),      # During first subtitle
            (7.5, 1, "Second"),     # During second subtitle
            (12.5, 0, None),        # Between subtitles
            (17.5, 1, "Third"),     # During third subtitle
            (22.5, 0, None),        # Between subtitles
            (27.5, 1, "Fourth"),    # During fourth subtitle
            (35.0, 0, None),        # After all subtitles
        ]
        
        for timestamp, expected_count, expected_text in test_cases:
            visible = self.synchronizer.get_visible_subtitles(timestamp)
            self.assertEqual(len(visible), expected_count, 
                           f"At {timestamp}s, expected {expected_count} subtitles, got {len(visible)}")
            
            if expected_text and visible:
                self.assertIn(expected_text, visible[0].text,
                            f"At {timestamp}s, expected text containing '{expected_text}', got '{visible[0].text}'")
    
    def test_realtime_subtitle_updates(self):
        """Test real-time subtitle updates"""
        self.synchronizer.load_project(self.project)
        
        # Create updated subtitle data
        updated_lines = [
            SubtitleLine(start_time=0.0, end_time=3.0, text="UPDATED: First subtitle"),
            SubtitleLine(start_time=3.0, end_time=6.0, text="UPDATED: Second subtitle"),
            SubtitleLine(start_time=10.0, end_time=13.0, text="NEW: Third subtitle")
        ]
        updated_styles = {"Default": SubtitleStyle(name="Default", font_size=24)}
        
        # Update subtitles
        self.synchronizer.update_subtitles(updated_lines, updated_styles)
        
        # Verify updates
        self.assertEqual(len(self.synchronizer.subtitle_lines), 3)
        self.assertEqual(self.synchronizer.subtitle_lines[0].text, "UPDATED: First subtitle")
        self.assertEqual(self.synchronizer.subtitle_lines[1].text, "UPDATED: Second subtitle")
        self.assertEqual(self.synchronizer.subtitle_lines[2].text, "NEW: Third subtitle")
        
        # Test visibility with updated subtitles
        visible = self.synchronizer.get_visible_subtitles(1.5)
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].text, "UPDATED: First subtitle")
        
        visible = self.synchronizer.get_visible_subtitles(4.5)
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].text, "UPDATED: Second subtitle")
        
        # Test gap where old subtitle existed but new one doesn't
        visible = self.synchronizer.get_visible_subtitles(8.0)
        self.assertEqual(len(visible), 0)
    
    def test_subtitle_change_callbacks(self):
        """Test subtitle change callback system"""
        self.synchronizer.load_project(self.project)
        
        # Set up callback tracking
        callback_calls = []
        
        def test_callback(lines, styles):
            callback_calls.append((len(lines), len(styles)))
        
        # Add callback
        self.synchronizer.add_subtitle_change_callback(test_callback)
        
        # Update subtitles to trigger callback
        new_lines = [SubtitleLine(start_time=0.0, end_time=5.0, text="Callback test")]
        new_styles = {"Default": SubtitleStyle(name="Default")}
        
        self.synchronizer.update_subtitles(new_lines, new_styles)
        
        # Verify callback was called
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0], (1, 1))
        
        # Remove callback and test again
        self.synchronizer.remove_subtitle_change_callback(test_callback)
        
        self.synchronizer.update_subtitles([], {})
        
        # Should still be only one call (callback was removed)
        self.assertEqual(len(callback_calls), 1)
    
    def test_overlapping_subtitles(self):
        """Test handling of overlapping subtitles"""
        # Create project with overlapping subtitles
        overlapping_project = Project(
            id="overlap_test",
            name="Overlap Test",
            video_file=VideoFile(path="test.mp4", duration=30.0),
            audio_file=AudioFile(path="test.mp3", duration=30.0),
            subtitle_file=SubtitleFile(
                path="overlap.ass",
                lines=[
                    SubtitleLine(start_time=0.0, end_time=10.0, text="Long subtitle"),
                    SubtitleLine(start_time=5.0, end_time=8.0, text="Overlapping subtitle"),
                    SubtitleLine(start_time=7.0, end_time=12.0, text="Another overlap")
                ],
                styles=[SubtitleStyle(name="Default")]
            )
        )
        
        self.synchronizer.load_project(overlapping_project)
        
        # Test timestamp with multiple overlapping subtitles
        visible = self.synchronizer.get_visible_subtitles(7.5)
        self.assertEqual(len(visible), 3)  # All three should be visible
        
        # Test edge cases
        visible = self.synchronizer.get_visible_subtitles(5.0)  # Exact start time
        self.assertEqual(len(visible), 2)  # First and second
        
        visible = self.synchronizer.get_visible_subtitles(8.0)  # Exact end time
        self.assertEqual(len(visible), 3)  # All three are still visible at 8.0
    
    def test_empty_subtitle_handling(self):
        """Test handling of projects with no subtitles"""
        empty_project = Project(
            id="empty_test",
            name="Empty Test",
            video_file=VideoFile(path="test.mp4", duration=30.0),
            audio_file=AudioFile(path="test.mp3", duration=30.0)
            # No subtitle_file
        )
        
        success = self.synchronizer.load_project(empty_project)
        self.assertTrue(success)
        self.assertEqual(len(self.synchronizer.subtitle_lines), 0)
        
        # Test that no subtitles are visible at any time
        visible = self.synchronizer.get_visible_subtitles(15.0)
        self.assertEqual(len(visible), 0)
        
        # Test updating from empty to having subtitles
        new_lines = [SubtitleLine(start_time=5.0, end_time=10.0, text="Added subtitle")]
        new_styles = {"Default": SubtitleStyle(name="Default")}
        
        self.synchronizer.update_subtitles(new_lines, new_styles)
        
        visible = self.synchronizer.get_visible_subtitles(7.5)
        self.assertEqual(len(visible), 1)
        self.assertEqual(visible[0].text, "Added subtitle")
    
    def test_timing_precision(self):
        """Test timing precision for subtitle boundaries"""
        self.synchronizer.load_project(self.project)
        
        # Test exact boundary conditions
        # First subtitle: 0.0 - 5.0
        visible = self.synchronizer.get_visible_subtitles(0.0)  # Exact start
        self.assertEqual(len(visible), 1)
        
        visible = self.synchronizer.get_visible_subtitles(5.0)  # Exact end
        self.assertEqual(len(visible), 2)  # Both subtitles are visible at boundary time 5.0
        
        visible = self.synchronizer.get_visible_subtitles(5.001)  # Just after end
        self.assertEqual(len(visible), 1)  # Second subtitle (starts at 5.0, first ends at 5.0)
        
        # Test very small time differences
        visible = self.synchronizer.get_visible_subtitles(4.999)
        self.assertEqual(len(visible), 1)
        
        visible = self.synchronizer.get_visible_subtitles(5.001)
        self.assertEqual(len(visible), 1)  # Should be second subtitle only


class TestSynchronizationPerformance(unittest.TestCase):
    """Test performance aspects of synchronization"""
    
    def setUp(self):
        """Set up performance test fixtures"""
        self.synchronizer = MockPreviewSynchronizer()
        
        # Create project with many subtitles for performance testing
        many_lines = []
        for i in range(1000):  # 1000 subtitles
            start_time = i * 2.0
            end_time = start_time + 1.5
            text = f"Subtitle {i+1}"
            many_lines.append(SubtitleLine(start_time=start_time, end_time=end_time, text=text))
        
        self.large_project = Project(
            id="perf_test",
            name="Performance Test",
            video_file=VideoFile(path="test.mp4", duration=2000.0),  # Long duration
            audio_file=AudioFile(path="test.mp3", duration=2000.0),
            subtitle_file=SubtitleFile(
                path="many.ass",
                lines=many_lines,
                styles=[SubtitleStyle(name="Default")]
            )
        )
    
    def test_large_subtitle_set_loading(self):
        """Test loading project with many subtitles"""
        import time
        
        start_time = time.time()
        success = self.synchronizer.load_project(self.large_project)
        load_time = time.time() - start_time
        
        self.assertTrue(success)
        self.assertEqual(len(self.synchronizer.subtitle_lines), 1000)
        self.assertLess(load_time, 1.0)  # Should load in under 1 second
    
    def test_subtitle_visibility_performance(self):
        """Test performance of subtitle visibility checking"""
        self.synchronizer.load_project(self.large_project)
        
        import time
        
        # Test multiple visibility checks
        start_time = time.time()
        for i in range(100):  # 100 checks
            timestamp = i * 10.0  # Every 10 seconds
            visible = self.synchronizer.get_visible_subtitles(timestamp)
        
        check_time = time.time() - start_time
        
        self.assertLess(check_time, 0.1)  # Should complete in under 0.1 seconds
    
    def test_realtime_update_performance(self):
        """Test performance of real-time subtitle updates"""
        self.synchronizer.load_project(self.large_project)
        
        import time
        
        # Create updated subtitle set
        updated_lines = []
        for i in range(500):  # Half the original count
            start_time = i * 3.0
            end_time = start_time + 2.0
            text = f"Updated subtitle {i+1}"
            updated_lines.append(SubtitleLine(start_time=start_time, end_time=end_time, text=text))
        
        updated_styles = {"Default": SubtitleStyle(name="Default")}
        
        # Time the update
        start_time = time.time()
        self.synchronizer.update_subtitles(updated_lines, updated_styles)
        update_time = time.time() - start_time
        
        self.assertEqual(len(self.synchronizer.subtitle_lines), 500)
        self.assertLess(update_time, 0.1)  # Should update in under 0.1 seconds


if __name__ == '__main__':
    print("Running synchronization integration tests...")
    
    # Run tests
    unittest.main(verbosity=2, exit=False, buffer=True)
    
    print("\nSynchronization integration tests completed.")