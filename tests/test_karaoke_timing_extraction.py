"""
Unit tests for karaoke timing extraction from ASS files.

Tests the parsing and extraction of karaoke timing tags (\k, \K, \kf)
from ASS subtitle files and their conversion to internal data structures.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.core.libass_integration import LibassIntegration, LibassError
from src.core.subtitle_parser import AssParser
from src.core.models import SubtitleFile, SubtitleLine, WordTiming, KaraokeTimingInfo


class TestKaraokeTagParsing:
    """Test parsing of karaoke timing tags from ASS text."""
    
    def test_parse_basic_k_tags(self):
        """Test parsing basic \\k tags."""
        ass_content = """[Script Info]
Title: Karaoke Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\k25}Hello{\\k30}world{\\k20}test
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Check that karaoke timing was parsed
            assert len(line.word_timings) == 3
            assert line.word_timings[0].word == "Hello"
            assert line.word_timings[1].word == "world"
            assert line.word_timings[2].word == "test"
            
            # Check timing durations (converted from centiseconds)
            assert abs(line.word_timings[0].end_time - line.word_timings[0].start_time - 0.25) < 0.01
            assert abs(line.word_timings[1].end_time - line.word_timings[1].start_time - 0.30) < 0.01
            assert abs(line.word_timings[2].end_time - line.word_timings[2].start_time - 0.20) < 0.01
            
            # Check karaoke data extraction
            assert len(karaoke_data) == 1
            karaoke_info = karaoke_data[0]
            assert karaoke_info.syllable_count == 3
            assert len(karaoke_info.syllable_timings) == 3
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_K_tags(self):
        """Test parsing \\K tags (uppercase)."""
        ass_content = """[Script Info]
Title: Karaoke Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\K50}Sing{\\K50}along
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should parse \\K tags as well
            assert len(line.word_timings) == 2
            assert line.word_timings[0].word == "Sing"
            assert line.word_timings[1].word == "along"
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_kf_tags(self):
        """Test parsing \\kf tags."""
        ass_content = """[Script Info]
Title: Karaoke Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\kf40}Fade{\\kf60}effect
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should parse \\kf tags
            assert len(line.word_timings) == 2
            assert line.word_timings[0].word == "Fade"
            assert line.word_timings[1].word == "effect"
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_mixed_karaoke_tags(self):
        """Test parsing mixed karaoke tag types."""
        ass_content = """[Script Info]
Title: Karaoke Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\k25}Mix{\\K30}ed{\\kf20}tags
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should parse all tag types
            assert len(line.word_timings) == 3
            assert line.word_timings[0].word == "Mix"
            assert line.word_timings[1].word == "ed"
            assert line.word_timings[2].word == "tags"
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_no_karaoke_tags(self):
        """Test parsing text without karaoke tags."""
        ass_content = """[Script Info]
Title: No Karaoke Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Regular subtitle text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should create automatic word timing
            assert len(line.word_timings) == 3  # "Regular", "subtitle", "text"
            assert line.word_timings[0].word == "Regular"
            assert line.word_timings[1].word == "subtitle"
            assert line.word_timings[2].word == "text"
            
            # Timing should be evenly distributed
            total_duration = line.end_time - line.start_time
            expected_word_duration = total_duration / 3
            
            for word_timing in line.word_timings:
                actual_duration = word_timing.end_time - word_timing.start_time
                assert abs(actual_duration - expected_word_duration) < 0.01
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_empty_text(self):
        """Test parsing empty or whitespace-only text."""
        ass_content = """[Script Info]
Title: Empty Text Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,   
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Empty text should result in no word timings
            assert len(line.word_timings) == 0
            
        finally:
            os.unlink(temp_file)


class TestKaraokeTimingValidation:
    """Test validation of karaoke timing data."""
    
    def test_timing_exceeds_line_duration(self):
        """Test handling when karaoke timing exceeds line duration."""
        ass_content = """[Script Info]
Title: Timing Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\\k100}Too{\\k100}long
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Timing should be scaled to fit within line duration
            assert len(line.word_timings) == 2
            
            # Last word should end at or before line end time
            last_word_end = line.word_timings[-1].end_time
            assert last_word_end <= line.end_time + 0.01  # Small tolerance for floating point
            
        finally:
            os.unlink(temp_file)
    
    def test_zero_duration_karaoke_tags(self):
        """Test handling of zero-duration karaoke tags."""
        ass_content = """[Script Info]
Title: Zero Duration Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\k0}Zero{\\k50}Normal
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should handle zero-duration tags
            assert len(line.word_timings) == 2
            assert line.word_timings[0].word == "Zero"
            assert line.word_timings[1].word == "Normal"
            
            # Zero duration should result in minimal timing
            zero_duration = line.word_timings[0].end_time - line.word_timings[0].start_time
            assert zero_duration >= 0.0
            
        finally:
            os.unlink(temp_file)
    
    def test_large_karaoke_values(self):
        """Test handling of very large karaoke timing values."""
        ass_content = """[Script Info]
Title: Large Values Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\k9999}Huge{\\k1}tiny
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should handle large values by scaling
            assert len(line.word_timings) == 2
            
            # Total timing should not exceed line duration
            total_word_time = sum(wt.end_time - wt.start_time for wt in line.word_timings)
            line_duration = line.end_time - line.start_time
            assert total_word_time <= line_duration + 0.01
            
        finally:
            os.unlink(temp_file)


class TestComplexKaraokeScenarios:
    """Test complex karaoke timing scenarios."""
    
    def test_multiple_lines_with_karaoke(self):
        """Test multiple subtitle lines with different karaoke patterns."""
        ass_content = """[Script Info]
Title: Multiple Lines Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\k25}First{\\k25}line
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,Regular text without karaoke
Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,{\\k30}Third{\\k20}line{\\k25}here
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 3
            
            # First line: has karaoke timing
            line1 = subtitle_file.lines[0]
            assert len(line1.word_timings) == 2
            assert line1.word_timings[0].word == "First"
            assert line1.word_timings[1].word == "line"
            
            # Second line: no karaoke timing, should have automatic word timing
            line2 = subtitle_file.lines[1]
            assert len(line2.word_timings) == 4  # "Regular", "text", "without", "karaoke"
            
            # Third line: has karaoke timing
            line3 = subtitle_file.lines[2]
            assert len(line3.word_timings) == 3
            assert line3.word_timings[0].word == "Third"
            assert line3.word_timings[1].word == "line"
            assert line3.word_timings[2].word == "here"
            
            # Should extract karaoke data for lines with timing
            assert len(karaoke_data) == 2  # Only lines 1 and 3 have karaoke timing
            
        finally:
            os.unlink(temp_file)
    
    def test_karaoke_with_other_ass_tags(self):
        """Test karaoke timing mixed with other ASS formatting tags."""
        ass_content = """[Script Info]
Title: Mixed Tags Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\k25\\b1}Bold{\\k30\\i1}italic{\\k20\\b0\\i0}normal
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should extract karaoke timing despite other formatting tags
            assert len(line.word_timings) == 3
            assert line.word_timings[0].word == "Bold"
            assert line.word_timings[1].word == "italic"
            assert line.word_timings[2].word == "normal"
            
            # Clean text should not contain formatting tags
            assert "\\b1" not in line.text
            assert "\\i1" not in line.text
            assert line.text == "Bold italic normal"
            
        finally:
            os.unlink(temp_file)
    
    def test_karaoke_with_special_characters(self):
        """Test karaoke timing with special characters and Unicode."""
        ass_content = """[Script Info]
Title: Special Characters Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,{\\k30}こんにちは{\\k40}世界{\\k25}!
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert len(subtitle_file.lines) == 1
            line = subtitle_file.lines[0]
            
            # Should handle Unicode characters
            assert len(line.word_timings) == 3
            assert line.word_timings[0].word == "こんにちは"
            assert line.word_timings[1].word == "世界"
            assert line.word_timings[2].word == "!"
            
        finally:
            os.unlink(temp_file)


class TestKaraokeDataStructures:
    """Test karaoke data structure creation and validation."""
    
    def test_karaoke_timing_info_creation(self):
        """Test creation of KaraokeTimingInfo objects."""
        karaoke_info = KaraokeTimingInfo(
            start_time=0.0,
            end_time=2.0,
            text="Test karaoke",
            syllable_count=2,
            syllable_timings=[1.0, 1.0],
            style_overrides="\\b1"
        )
        
        assert karaoke_info.start_time == 0.0
        assert karaoke_info.end_time == 2.0
        assert karaoke_info.text == "Test karaoke"
        assert karaoke_info.syllable_count == 2
        assert karaoke_info.syllable_timings == [1.0, 1.0]
        assert karaoke_info.style_overrides == "\\b1"
    
    def test_karaoke_timing_info_validation(self):
        """Test validation of KaraokeTimingInfo objects."""
        # Test invalid start time
        with pytest.raises(ValueError):
            KaraokeTimingInfo(
                start_time=-1.0,
                end_time=2.0,
                text="Test"
            )
        
        # Test invalid end time
        with pytest.raises(ValueError):
            KaraokeTimingInfo(
                start_time=2.0,
                end_time=1.0,
                text="Test"
            )
        
        # Test invalid syllable count
        with pytest.raises(ValueError):
            KaraokeTimingInfo(
                start_time=0.0,
                end_time=2.0,
                text="Test",
                syllable_count=-1
            )
    
    def test_subtitle_file_karaoke_detection(self):
        """Test detection of karaoke timing in SubtitleFile."""
        # Create subtitle file with karaoke data
        karaoke_info = KaraokeTimingInfo(
            start_time=0.0,
            end_time=2.0,
            text="Test karaoke"
        )
        
        subtitle_file = SubtitleFile(
            path="test.ass",
            karaoke_data=[karaoke_info]
        )
        
        assert subtitle_file.has_karaoke_timing() is True
        
        # Test with word timings
        word_timing = WordTiming("test", 0.0, 1.0)
        subtitle_line = SubtitleLine(
            start_time=0.0,
            end_time=1.0,
            text="test",
            word_timings=[word_timing]
        )
        
        subtitle_file2 = SubtitleFile(
            path="test2.ass",
            lines=[subtitle_line]
        )
        
        # Should detect karaoke timing from word timings
        assert subtitle_file2.has_karaoke_timing() is False  # No karaoke_data, but has word timings
        
        # Test without karaoke timing
        subtitle_file3 = SubtitleFile(path="test3.ass")
        assert subtitle_file3.has_karaoke_timing() is False


if __name__ == "__main__":
    pytest.main([__file__])