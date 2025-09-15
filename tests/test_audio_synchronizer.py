"""
Unit tests for audio-subtitle synchronization functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.audio.synchronizer import (
    AudioSubtitleSynchronizer, SyncPoint, SyncAnalysis
)
from src.core.models import AudioFile, SubtitleFile


class TestAudioSubtitleSynchronizer:
    """Test cases for AudioSubtitleSynchronizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.synchronizer = AudioSubtitleSynchronizer()
        
    def test_init(self):
        """Test synchronizer initialization."""
        sync = AudioSubtitleSynchronizer()
        assert sync.timing_tolerance == 0.1
        assert sync.min_sync_points == 3
    
    def test_analyze_synchronization_no_lines(self):
        """Test synchronization analysis with no subtitle lines."""
        audio_file = AudioFile(path="test.mp3", duration=180.0)
        subtitle_file = Mock()
        subtitle_file.lines = []
        
        analysis = self.synchronizer.analyze_synchronization(audio_file, subtitle_file)
        
        assert isinstance(analysis, SyncAnalysis)
        assert len(analysis.sync_points) == 0
        assert analysis.average_offset == 0.0
        assert analysis.offset_variance == 0.0
        assert analysis.sync_quality == 0.0
        assert "No synchronization points found" in analysis.recommendations
    
    def test_analyze_synchronization_with_lines(self):
        """Test synchronization analysis with subtitle lines."""
        audio_file = AudioFile(path="test.mp3", duration=180.0)
        
        # Mock subtitle file with lines
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0, text="Hello world this is a test"),
            Mock(start_time=10.0, end_time=12.0, text="Short"),
            Mock(start_time=20.0, end_time=25.0, text="Another longer line for testing"),
            Mock(start_time=30.0, end_time=35.0, text="Final line")
        ]
        
        analysis = self.synchronizer.analyze_synchronization(audio_file, subtitle_file)
        
        assert len(analysis.sync_points) > 0
        assert analysis.average_offset == 0.0  # Perfect sync assumed initially
        assert analysis.offset_variance == 0.0
        assert analysis.sync_quality == 1.0
        assert len(analysis.recommendations) > 0
    
    def test_find_sync_points(self):
        """Test finding synchronization points."""
        audio_file = AudioFile(path="test.mp3", duration=180.0)
        
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, text="Very long line with lots of text for confidence"),
            Mock(start_time=10.0, text="Short"),
            Mock(start_time=20.0, text="Medium length line"),
        ]
        
        sync_points = self.synchronizer._find_sync_points(audio_file, subtitle_file)
        
        assert len(sync_points) == 3
        assert all(isinstance(point, SyncPoint) for point in sync_points)
        
        # Check that longer lines have higher confidence
        confidences = [point.confidence for point in sync_points]
        assert max(confidences) > min(confidences)
    
    def test_find_sync_points_no_lines(self):
        """Test finding sync points with no subtitle lines."""
        audio_file = AudioFile(path="test.mp3", duration=180.0)
        subtitle_file = Mock()
        subtitle_file.lines = []
        
        sync_points = self.synchronizer._find_sync_points(audio_file, subtitle_file)
        
        assert len(sync_points) == 0
    
    def test_generate_recommendations_good_sync(self):
        """Test recommendation generation for good synchronization."""
        sync_points = [
            SyncPoint(0.0, 0.0, 1.0),
            SyncPoint(10.0, 10.0, 0.8),
            SyncPoint(20.0, 20.0, 0.9)
        ]
        
        audio_file = AudioFile(path="test.mp3", duration=25.0)
        subtitle_file = Mock()
        subtitle_file.lines = [Mock(end_time=25.0)]
        
        recommendations = self.synchronizer._generate_recommendations(
            sync_points, 0.0, 0.0, audio_file, subtitle_file
        )
        
        assert "Synchronization appears good" in recommendations
    
    def test_generate_recommendations_offset_needed(self):
        """Test recommendation generation when offset is needed."""
        sync_points = [
            SyncPoint(1.0, 0.0, 1.0),
            SyncPoint(11.0, 10.0, 0.8),
            SyncPoint(21.0, 20.0, 0.9)
        ]
        
        audio_file = AudioFile(path="test.mp3", duration=30.0)
        subtitle_file = Mock()
        subtitle_file.lines = [Mock(end_time=25.0)]
        
        recommendations = self.synchronizer._generate_recommendations(
            sync_points, 1.0, 0.0, audio_file, subtitle_file
        )
        
        assert any("Apply timing offset" in rec for rec in recommendations)
    
    def test_generate_recommendations_high_variance(self):
        """Test recommendation generation for high variance."""
        sync_points = [
            SyncPoint(0.0, 0.0, 1.0),
            SyncPoint(10.0, 10.0, 0.8),
            SyncPoint(20.0, 20.0, 0.9)
        ]
        
        audio_file = AudioFile(path="test.mp3", duration=30.0)
        subtitle_file = Mock()
        subtitle_file.lines = [Mock(end_time=25.0)]
        
        recommendations = self.synchronizer._generate_recommendations(
            sync_points, 0.0, 0.5, audio_file, subtitle_file  # High variance
        )
        
        assert any("High timing variance" in rec for rec in recommendations)
    
    def test_generate_recommendations_duration_mismatch(self):
        """Test recommendation generation for duration mismatch."""
        sync_points = [
            SyncPoint(0.0, 0.0, 1.0),
            SyncPoint(10.0, 10.0, 0.8),
            SyncPoint(20.0, 20.0, 0.9)
        ]
        
        audio_file = AudioFile(path="test.mp3", duration=30.0)
        subtitle_file = Mock()
        subtitle_file.lines = [Mock(end_time=25.0)]  # 5 second difference, > 2.0 threshold
        
        recommendations = self.synchronizer._generate_recommendations(
            sync_points, 0.0, 0.0, audio_file, subtitle_file
        )
        
        assert any("Duration mismatch" in rec for rec in recommendations)
    
    def test_get_subtitle_duration(self):
        """Test getting subtitle duration."""
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(end_time=10.0),
            Mock(end_time=25.0),
            Mock(end_time=15.0)
        ]
        
        duration = self.synchronizer._get_subtitle_duration(subtitle_file)
        assert duration == 25.0
    
    def test_get_subtitle_duration_no_lines(self):
        """Test getting subtitle duration with no lines."""
        subtitle_file = Mock()
        subtitle_file.lines = []
        
        duration = self.synchronizer._get_subtitle_duration(subtitle_file)
        assert duration == 0.0
    
    def test_apply_timing_correction(self):
        """Test applying timing correction."""
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0),
            Mock(start_time=10.0, end_time=15.0),
            Mock(start_time=20.0, end_time=25.0)
        ]
        
        result = self.synchronizer.apply_timing_correction(subtitle_file, 2.0)
        
        assert result == True
        assert subtitle_file.lines[0].start_time == 2.0
        assert subtitle_file.lines[0].end_time == 7.0
        assert subtitle_file.lines[1].start_time == 12.0
        assert subtitle_file.lines[1].end_time == 17.0
        assert subtitle_file.lines[2].start_time == 22.0
        assert subtitle_file.lines[2].end_time == 27.0
    
    def test_apply_timing_correction_negative_offset(self):
        """Test applying negative timing correction with clamping."""
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=1.0, end_time=5.0),
            Mock(start_time=10.0, end_time=15.0)
        ]
        
        result = self.synchronizer.apply_timing_correction(subtitle_file, -2.0)
        
        assert result == True
        assert subtitle_file.lines[0].start_time == 0.0  # Clamped to 0
        assert subtitle_file.lines[0].end_time == 3.0
        assert subtitle_file.lines[1].start_time == 8.0
        assert subtitle_file.lines[1].end_time == 13.0
    
    def test_apply_timing_correction_no_lines(self):
        """Test applying timing correction with no lines."""
        subtitle_file = Mock()
        subtitle_file.lines = []
        
        result = self.synchronizer.apply_timing_correction(subtitle_file, 2.0)
        
        assert result == False
    
    def test_validate_timing_precision(self):
        """Test timing precision validation."""
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=0.0, end_time=5.0),    # Good duration
            Mock(start_time=6.0, end_time=6.2),    # Short duration (warning)
            Mock(start_time=7.0, end_time=18.0),   # Long duration (warning)
            Mock(start_time=15.0, end_time=20.0),  # Overlap with previous (error)
        ]
        
        results = self.synchronizer.validate_timing_precision(subtitle_file)
        
        assert results['total_lines'] == 4
        assert len(results['timing_errors']) > 0
        assert len(results['warnings']) > 0
        assert results['average_duration'] > 0
        
        # Check for specific issues
        timing_errors = ' '.join(results['timing_errors'])
        warnings = ' '.join(results['warnings'])
        
        assert "Overlapping timing" in timing_errors
        assert "Very short duration" in warnings
        assert "Very long duration" in warnings
    
    def test_validate_timing_precision_invalid_duration(self):
        """Test timing precision validation with invalid duration."""
        subtitle_file = Mock()
        subtitle_file.lines = [
            Mock(start_time=5.0, end_time=3.0),  # Invalid: end before start
        ]
        
        results = self.synchronizer.validate_timing_precision(subtitle_file)
        
        assert len(results['timing_errors']) > 0
        assert "Invalid duration" in results['timing_errors'][0]
    
    def test_validate_timing_precision_no_lines(self):
        """Test timing precision validation with no lines."""
        subtitle_file = Mock()
        subtitle_file.lines = []
        
        results = self.synchronizer.validate_timing_precision(subtitle_file)
        
        assert results['total_lines'] == 0
        assert len(results['timing_errors']) == 0
        assert len(results['warnings']) == 0
        assert results['average_duration'] == 0.0


class TestSyncPoint:
    """Test cases for SyncPoint dataclass."""
    
    def test_sync_point_creation(self):
        """Test SyncPoint creation."""
        point = SyncPoint(
            audio_time=10.5,
            subtitle_time=10.0,
            confidence=0.8
        )
        
        assert point.audio_time == 10.5
        assert point.subtitle_time == 10.0
        assert point.confidence == 0.8


class TestSyncAnalysis:
    """Test cases for SyncAnalysis dataclass."""
    
    def test_sync_analysis_creation(self):
        """Test SyncAnalysis creation."""
        sync_points = [
            SyncPoint(0.0, 0.0, 1.0),
            SyncPoint(10.0, 10.5, 0.8)
        ]
        
        analysis = SyncAnalysis(
            sync_points=sync_points,
            average_offset=0.25,
            offset_variance=0.1,
            sync_quality=0.9,
            recommendations=["Good synchronization"]
        )
        
        assert len(analysis.sync_points) == 2
        assert analysis.average_offset == 0.25
        assert analysis.offset_variance == 0.1
        assert analysis.sync_quality == 0.9
        assert analysis.recommendations == ["Good synchronization"]