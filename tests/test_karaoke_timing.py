"""
Test karaoke timing functionality for word-by-word animation.
"""

import pytest
from src.core.models import SubtitleLine, WordTiming, SubtitleStyle
from src.core.subtitle_parser import AssParser


def test_word_timing_creation():
    """Test creating word timing objects."""
    word_timing = WordTiming(
        word="Hello",
        start_time=1.0,
        end_time=1.5
    )
    
    assert word_timing.word == "Hello"
    assert word_timing.start_time == 1.0
    assert word_timing.end_time == 1.5


def test_subtitle_line_with_word_timings():
    """Test subtitle line with word-by-word timing."""
    word_timings = [
        WordTiming("Hello", 1.0, 1.5),
        WordTiming("world", 1.5, 2.0)
    ]
    
    line = SubtitleLine(
        start_time=1.0,
        end_time=2.0,
        text="Hello world",
        word_timings=word_timings
    )
    
    # Test active words at different times
    assert line.get_active_words(0.5) == []  # Before line starts
    assert line.get_active_words(1.2) == ["Hello"]  # During first word
    assert line.get_active_words(1.7) == ["world"]  # During second word
    assert line.get_active_words(2.5) == []  # After line ends


def test_progress_ratio_calculation():
    """Test karaoke progress ratio calculation."""
    word_timings = [
        WordTiming("Hello", 1.0, 1.5),
        WordTiming("world", 1.5, 2.0)
    ]
    
    line = SubtitleLine(
        start_time=1.0,
        end_time=2.0,
        text="Hello world",
        word_timings=word_timings
    )
    
    # Test progress at different times
    assert line.get_progress_ratio(0.5) == 0.0  # Before start
    assert line.get_progress_ratio(1.25) == 0.25  # 50% through first word (25% total)
    assert line.get_progress_ratio(1.5) == 0.5   # End of first word
    assert line.get_progress_ratio(1.75) == 0.75  # 50% through second word (75% total)
    assert line.get_progress_ratio(2.0) == 1.0   # Complete
    assert line.get_progress_ratio(2.5) == 1.0   # After end


if __name__ == "__main__":
    pytest.main([__file__])