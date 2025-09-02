"""
Tests for ASS subtitle parser functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.subtitle_parser import AssParser, parse_ass_file, ParseError
from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle


class TestAssParser:
    """Test cases for ASS subtitle parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = AssParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_ass_file(self, content: str, filename: str = "test.ass") -> str:
        """Create a temporary ASS file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_parse_valid_ass_file(self):
        """Test parsing a valid ASS file."""
        content = """[Script Info]
Title: Test Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello World
Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,This is a test
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        # Check basic properties
        assert subtitle_file.path == file_path
        assert subtitle_file.format == "ass"
        assert len(subtitle_file.lines) == 2
        assert len(subtitle_file.styles) == 1
        
        # Check first subtitle line
        line1 = subtitle_file.lines[0]
        assert line1.start_time == 1.0
        assert line1.end_time == 3.0
        assert line1.text == "Hello World"
        assert line1.style == "Default"
        
        # Check second subtitle line
        line2 = subtitle_file.lines[1]
        assert line2.start_time == 4.0
        assert line2.end_time == 6.0
        assert line2.text == "This is a test"
        
        # Check style
        style = subtitle_file.styles[0]
        assert style.name == "Default"
        assert style.font_name == "Arial"
        assert style.font_size == 20
        assert not self.parser.has_errors()
    
    def test_parse_file_not_found(self):
        """Test parsing a non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("nonexistent.ass")
    
    def test_parse_invalid_extension(self):
        """Test parsing a file with wrong extension."""
        file_path = self.create_temp_ass_file("content", "test.txt")
        with pytest.raises(ValueError, match="Invalid file extension"):
            self.parser.parse_file(file_path)
    
    def test_parse_empty_file(self):
        """Test parsing an empty file."""
        file_path = self.create_temp_ass_file("")
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.lines) == 0
        assert len(subtitle_file.styles) == 1  # Default style added
        assert self.parser.has_warnings()
    
    def test_parse_file_with_bom(self):
        """Test parsing a file with UTF-8 BOM."""
        content = """\ufeff[Script Info]
Title: Test with BOM

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Test with BOM
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.lines) == 1
        assert subtitle_file.lines[0].text == "Test with BOM"
    
    def test_parse_time_formats(self):
        """Test parsing various time formats."""
        # Valid time formats
        assert self.parser._parse_time("0:00:01.00", 1) == 1.0
        assert self.parser._parse_time("0:01:30.50", 1) == 90.5
        assert self.parser._parse_time("1:23:45.99", 1) == 5025.99
        
        # Invalid time formats
        assert self.parser._parse_time("", 1) is None
        assert self.parser._parse_time("invalid", 1) is None
        assert self.parser._parse_time("0:60:00.00", 1) == 3600.0  # Should still parse
        
        assert self.parser.has_errors()
    
    def test_parse_style_with_missing_fields(self):
        """Test parsing style with missing fields."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert self.parser.has_errors()
    
    def test_parse_dialogue_with_commas_in_text(self):
        """Test parsing dialogue with commas in the text field."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hello, world, this is a test
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.lines) == 1
        assert subtitle_file.lines[0].text == "Hello, world, this is a test"
    
    def test_parse_multiple_styles(self):
        """Test parsing multiple styles."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10
Style: Title,Times New Roman,24,&H00FFFF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Title,,0,0,0,,Title Text
Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,Regular Text
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.styles) == 2
        assert subtitle_file.styles[0].name == "Default"
        assert subtitle_file.styles[1].name == "Title"
        assert subtitle_file.styles[1].font_name == "Times New Roman"
        assert subtitle_file.styles[1].font_size == 24
        assert subtitle_file.styles[1].bold == True
        
        assert len(subtitle_file.lines) == 2
        assert subtitle_file.lines[0].style == "Title"
        assert subtitle_file.lines[1].style == "Default"
    
    def test_parse_comments_and_empty_lines(self):
        """Test that comments and empty lines are ignored."""
        content = """[Script Info]
; This is a comment
Title: Test

; Another comment

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
; Comment in events
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Test line

; Final comment
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.lines) == 1
        assert subtitle_file.lines[0].text == "Test line"
    
    def test_validation_overlapping_subtitles(self):
        """Test validation of overlapping subtitles."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,First line
Dialogue: 0,0:00:02.00,0:00:04.00,Default,,0,0,0,,Overlapping line
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert self.parser.has_warnings()
        warnings = self.parser.get_warnings()
        assert any("Overlapping subtitles" in w.message for w in warnings)
    
    def test_validation_short_duration(self):
        """Test validation of very short subtitle duration."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:01.05,Default,,0,0,0,,Very short
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert self.parser.has_warnings()
        warnings = self.parser.get_warnings()
        assert any("Very short subtitle duration" in w.message for w in warnings)
    
    def test_validation_empty_text(self):
        """Test validation of empty subtitle text."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert self.parser.has_warnings()
        warnings = self.parser.get_warnings()
        assert any("Empty subtitle text" in w.message for w in warnings)
    
    def test_subtitle_lines_sorted_by_time(self):
        """Test that subtitle lines are sorted by start time."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:05.00,0:00:07.00,Default,,0,0,0,,Third line
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,First line
Dialogue: 0,0:00:03.00,0:00:05.00,Default,,0,0,0,,Second line
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert len(subtitle_file.lines) == 3
        assert subtitle_file.lines[0].text == "First line"
        assert subtitle_file.lines[1].text == "Second line"
        assert subtitle_file.lines[2].text == "Third line"
    
    def test_parse_ass_file_convenience_function(self):
        """Test the convenience function parse_ass_file."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Test line
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file, errors, warnings = parse_ass_file(file_path)
        
        assert len(subtitle_file.lines) == 1
        assert subtitle_file.lines[0].text == "Test line"
        assert len(errors) == 0
        assert len(warnings) == 0
    
    def test_error_and_warning_tracking(self):
        """Test that errors and warnings are properly tracked."""
        content = """[V4+ Styles]
Format: Name, Fontname
Style: Default,Arial,20,ExtraField

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,invalid_time,0:00:03.00,Default,,0,0,0,,Test
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.parser.parse_file(file_path)
        
        assert self.parser.has_errors()
        assert len(self.parser.get_errors()) > 0
        
        errors = self.parser.get_errors()
        assert any("field count mismatch" in error.message.lower() for error in errors)
        assert any("invalid time format" in error.message.lower() for error in errors)


class TestParseError:
    """Test cases for ParseError class."""
    
    def test_parse_error_creation(self):
        """Test creating ParseError objects."""
        error = ParseError(10, "Test error message", "error")
        
        assert error.line_number == 10
        assert error.message == "Test error message"
        assert error.severity == "error"
    
    def test_parse_error_default_severity(self):
        """Test ParseError with default severity."""
        error = ParseError(5, "Test message")
        
        assert error.severity == "error"


if __name__ == "__main__":
    pytest.main([__file__])