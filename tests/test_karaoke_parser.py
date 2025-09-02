"""
Test karaoke timing parsing from ASS files.
"""

import pytest
from src.core.subtitle_parser import AssParser


def test_karaoke_timing_parsing():
    """Test parsing karaoke timing from ASS text."""
    parser = AssParser()
    
    # Test karaoke timing with \\k tags
    text = "{\\k25}Hello{\\k30}world"
    line_start = 1.0
    line_end = 2.0
    
    clean_text, word_timings = parser._parse_karaoke_timing(text, line_start, line_end, 1)
    
    assert clean_text == "Hello world"
    assert len(word_timings) == 2
    
    # Check first word timing
    assert word_timings[0].word == "Hello"
    assert word_timings[0].start_time == 1.0
    assert word_timings[0].end_time == 1.25  # 1.0 + 0.25 seconds
    
    # Check second word timing
    assert word_timings[1].word == "world"
    assert word_timings[1].start_time == 1.25
    assert word_timings[1].end_time == 1.55  # 1.25 + 0.30 seconds


def test_automatic_word_timing():
    """Test automatic word timing when no karaoke tags present."""
    parser = AssParser()
    
    text = "Hello world test"
    line_start = 1.0
    line_end = 4.0
    
    clean_text, word_timings = parser._parse_karaoke_timing(text, line_start, line_end, 1)
    
    assert clean_text == "Hello world test"
    assert len(word_timings) == 3
    
    # Each word should get 1 second (3 seconds / 3 words)
    expected_duration = 1.0
    
    assert word_timings[0].word == "Hello"
    assert word_timings[0].start_time == 1.0
    assert word_timings[0].end_time == 2.0
    
    assert word_timings[1].word == "world"
    assert word_timings[1].start_time == 2.0
    assert word_timings[1].end_time == 3.0
    
    assert word_timings[2].word == "test"
    assert word_timings[2].start_time == 3.0
    assert word_timings[2].end_time == 4.0


def test_empty_text_handling():
    """Test handling of empty text."""
    parser = AssParser()
    
    text = ""
    line_start = 1.0
    line_end = 2.0
    
    clean_text, word_timings = parser._parse_karaoke_timing(text, line_start, line_end, 1)
    
    assert clean_text == ""
    assert len(word_timings) == 0


if __name__ == "__main__":
    pytest.main([__file__])