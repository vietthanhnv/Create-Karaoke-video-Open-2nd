"""
Integration tests for subtitle parsing with media importer.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.media_importer import MediaImporter, MediaImportError
from src.core.models import SubtitleFile, SubtitleLine


class TestSubtitleIntegration:
    """Test integration between subtitle parser and media importer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.importer = MediaImporter()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_ass_file(self, content: str, filename: str = "test.ass") -> str:
        """Create a temporary ASS file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_import_valid_ass_file(self):
        """Test importing a valid ASS file through media importer."""
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
        subtitle_file = self.importer.import_subtitles(file_path)
        
        # Verify the import was successful
        assert subtitle_file is not None
        assert isinstance(subtitle_file, SubtitleFile)
        assert subtitle_file.path == file_path
        assert subtitle_file.format == "ass"
        assert len(subtitle_file.lines) == 2
        assert len(subtitle_file.styles) == 1
        
        # Check subtitle content
        assert subtitle_file.lines[0].text == "Hello World"
        assert subtitle_file.lines[0].start_time == 1.0
        assert subtitle_file.lines[0].end_time == 3.0
        
        assert subtitle_file.lines[1].text == "This is a test"
        assert subtitle_file.lines[1].start_time == 4.0
        assert subtitle_file.lines[1].end_time == 6.0
    
    def test_import_ass_file_with_parsing_errors(self):
        """Test importing an ASS file with parsing errors."""
        content = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,invalid_time,0:00:03.00,Default,,0,0,0,,Test
"""
        
        file_path = self.create_temp_ass_file(content)
        
        with pytest.raises(MediaImportError) as exc_info:
            self.importer.import_subtitles(file_path)
        
        assert "Subtitle parsing errors" in str(exc_info.value)
    
    def test_import_nonexistent_file(self):
        """Test importing a non-existent subtitle file."""
        with pytest.raises(MediaImportError):
            self.importer.import_subtitles("nonexistent.ass")
    
    def test_import_invalid_extension(self):
        """Test importing a file with invalid extension."""
        file_path = self.create_temp_ass_file("content", "test.txt")
        
        with pytest.raises(MediaImportError):
            self.importer.import_subtitles(file_path)
    
    def test_import_empty_ass_file(self):
        """Test importing an empty ASS file."""
        file_path = self.create_temp_ass_file("")
        subtitle_file = self.importer.import_subtitles(file_path)
        
        # Should succeed but with default style and no lines
        assert subtitle_file is not None
        assert len(subtitle_file.lines) == 0
        assert len(subtitle_file.styles) == 1  # Default style added
    
    def test_import_ass_file_with_complex_content(self):
        """Test importing an ASS file with complex content."""
        content = """[Script Info]
Title: Complex Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10
Style: Title,Times New Roman,24,&H00FFFF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.50,0:00:02.50,Title,,0,0,0,,Song Title
Dialogue: 0,0:00:03.00,0:00:05.00,Default,,0,0,0,,First verse line
Dialogue: 0,0:00:05.50,0:00:07.50,Default,,0,0,0,,Second verse line
Dialogue: 0,0:00:08.00,0:00:10.00,Default,,0,0,0,,Text with, commas, in it
"""
        
        file_path = self.create_temp_ass_file(content)
        subtitle_file = self.importer.import_subtitles(file_path)
        
        # Verify complex content parsing
        assert subtitle_file is not None
        assert len(subtitle_file.lines) == 4
        assert len(subtitle_file.styles) == 2
        
        # Check styles
        style_names = [style.name for style in subtitle_file.styles]
        assert "Default" in style_names
        assert "Title" in style_names
        
        # Check lines are sorted by time
        assert subtitle_file.lines[0].start_time == 0.5
        assert subtitle_file.lines[1].start_time == 3.0
        assert subtitle_file.lines[2].start_time == 5.5
        assert subtitle_file.lines[3].start_time == 8.0
        
        # Check text with commas
        assert subtitle_file.lines[3].text == "Text with, commas, in it"
        
        # Check different styles
        assert subtitle_file.lines[0].style == "Title"
        assert subtitle_file.lines[1].style == "Default"


if __name__ == "__main__":
    pytest.main([__file__])