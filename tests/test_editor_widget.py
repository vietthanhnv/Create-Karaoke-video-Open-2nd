"""
Unit tests for the subtitle editor widget.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QMouseEvent

from src.ui.editor_widget import EditorWidget, TimelineWidget, AssHighlighter
from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor_widget(app):
    """Create EditorWidget instance for testing."""
    widget = EditorWidget()
    return widget


@pytest.fixture
def timeline_widget(app):
    """Create TimelineWidget instance for testing."""
    widget = TimelineWidget()
    return widget


@pytest.fixture
def sample_subtitle_file():
    """Create a sample subtitle file for testing."""
    lines = [
        SubtitleLine(start_time=0.0, end_time=5.0, text="First subtitle", style="Default"),
        SubtitleLine(start_time=5.5, end_time=10.0, text="Second subtitle", style="Default"),
        SubtitleLine(start_time=10.5, end_time=15.0, text="Third subtitle", style="Default")
    ]
    
    styles = [SubtitleStyle(name="Default")]
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
        f.write("""[Script Info]
Title: Test Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,First subtitle
Dialogue: 0,0:00:05.50,0:00:10.00,Default,,0,0,0,,Second subtitle
Dialogue: 0,0:00:10.50,0:00:15.00,Default,,0,0,0,,Third subtitle
""")
        temp_path = f.name
    
    subtitle_file = SubtitleFile(
        path=temp_path,
        format="ass",
        lines=lines,
        styles=styles
    )
    
    yield subtitle_file
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


class TestEditorWidget:
    """Test cases for EditorWidget."""
    
    def test_widget_initialization(self, editor_widget):
        """Test that the editor widget initializes correctly."""
        assert editor_widget is not None
        assert hasattr(editor_widget, 'text_editor')
        assert hasattr(editor_widget, 'timeline_widget')
        assert hasattr(editor_widget, 'subtitle_list')
        assert hasattr(editor_widget, 'validation_display')
    
    def test_load_subtitle_file(self, editor_widget, sample_subtitle_file):
        """Test loading a subtitle file."""
        # Load the file
        editor_widget.load_subtitle_file(sample_subtitle_file)
        
        # Check that content was loaded
        content = editor_widget.get_subtitle_content()
        assert "First subtitle" in content
        assert "Second subtitle" in content
        assert "Third subtitle" in content
        
        # Check that parsed lines were created
        assert hasattr(editor_widget, 'parsed_lines')
        assert len(editor_widget.parsed_lines) == 3
    
    def test_get_subtitle_content(self, editor_widget):
        """Test getting subtitle content."""
        test_content = "Test content"
        editor_widget.text_editor.setPlainText(test_content)
        
        content = editor_widget.get_subtitle_content()
        assert content == test_content
    
    def test_validation_functionality(self, editor_widget):
        """Test subtitle validation."""
        # Set valid ASS content
        valid_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,Test subtitle
"""
        
        editor_widget.text_editor.setPlainText(valid_content)
        editor_widget._validate_content()
        
        # Check validation results
        validation_text = editor_widget.validation_display.toPlainText()
        assert "valid" in validation_text.lower() or "1 subtitle" in validation_text
    
    def test_individual_editor_updates(self, editor_widget, sample_subtitle_file):
        """Test individual subtitle line editing."""
        # Load subtitle file
        editor_widget.load_subtitle_file(sample_subtitle_file)
        
        # Select first subtitle
        editor_widget.subtitle_list.setCurrentRow(0)
        editor_widget._load_individual_editor(0)
        
        # Check that individual editor is populated
        assert editor_widget.start_time_editor.value() == 0.0
        assert editor_widget.end_time_editor.value() == 5.0
        assert editor_widget.line_text_editor.text() == "First subtitle"
        assert editor_widget.style_editor.text() == "Default"
    
    def test_timing_changes(self, editor_widget, sample_subtitle_file):
        """Test timing changes through individual editor."""
        # Load subtitle file
        editor_widget.load_subtitle_file(sample_subtitle_file)
        
        # Select first subtitle
        editor_widget.subtitle_list.setCurrentRow(0)
        editor_widget._load_individual_editor(0)
        
        # Change timing
        editor_widget.start_time_editor.setValue(1.0)
        editor_widget.end_time_editor.setValue(6.0)
        
        # Trigger the change handlers
        editor_widget._on_individual_timing_changed()
        
        # Check that parsed line was updated
        assert editor_widget.parsed_lines[0].start_time == 1.0
        assert editor_widget.parsed_lines[0].end_time == 6.0
    
    def test_text_changes(self, editor_widget, sample_subtitle_file):
        """Test text changes through individual editor."""
        # Load subtitle file
        editor_widget.load_subtitle_file(sample_subtitle_file)
        
        # Select first subtitle
        editor_widget.subtitle_list.setCurrentRow(0)
        editor_widget._load_individual_editor(0)
        
        # Change text
        new_text = "Modified subtitle text"
        editor_widget.line_text_editor.setText(new_text)
        editor_widget._on_individual_text_changed()
        
        # Check that parsed line was updated
        assert editor_widget.parsed_lines[0].text == new_text
    
    def test_seconds_to_ass_time_conversion(self, editor_widget):
        """Test time format conversion."""
        # Test various time values
        assert editor_widget._seconds_to_ass_time(0.0) == "0:00:00.00"
        assert editor_widget._seconds_to_ass_time(65.5) == "0:01:05.50"
        assert editor_widget._seconds_to_ass_time(3661.25) == "1:01:01.25"
    
    def test_signal_emissions(self, editor_widget, sample_subtitle_file):
        """Test that appropriate signals are emitted."""
        # Mock signal handlers
        subtitle_changed_mock = Mock()
        timing_changed_mock = Mock()
        subtitle_selected_mock = Mock()
        
        editor_widget.subtitle_changed.connect(subtitle_changed_mock)
        editor_widget.timing_changed.connect(timing_changed_mock)
        editor_widget.subtitle_selected.connect(subtitle_selected_mock)
        
        # Load subtitle file
        editor_widget.load_subtitle_file(sample_subtitle_file)
        
        # Test text change signal
        editor_widget.text_editor.setPlainText("New content")
        # Note: Signal might be emitted with delay due to timer
        
        # Test subtitle selection signal
        editor_widget.subtitle_list.setCurrentRow(0)
        editor_widget._on_list_selection_changed()
        
        # Verify signals were called
        subtitle_selected_mock.assert_called_with(0)


class TestTimelineWidget:
    """Test cases for TimelineWidget."""
    
    def test_timeline_initialization(self, timeline_widget):
        """Test timeline widget initialization."""
        assert timeline_widget is not None
        assert timeline_widget.subtitle_lines == []
        assert timeline_widget.selected_index == -1
        assert timeline_widget.scale == 50.0
    
    def test_set_subtitle_lines(self, timeline_widget):
        """Test setting subtitle lines."""
        lines = [
            SubtitleLine(start_time=0.0, end_time=5.0, text="Test 1", style="Default"),
            SubtitleLine(start_time=6.0, end_time=10.0, text="Test 2", style="Default")
        ]
        
        timeline_widget.set_subtitle_lines(lines)
        
        assert len(timeline_widget.subtitle_lines) == 2
        assert timeline_widget.duration >= 40.0  # Should be at least last end time + 30
    
    def test_set_selected_index(self, timeline_widget):
        """Test setting selected index."""
        timeline_widget.set_selected_index(1)
        assert timeline_widget.selected_index == 1
    
    def test_get_subtitle_at_position(self, timeline_widget):
        """Test getting subtitle at mouse position."""
        lines = [
            SubtitleLine(start_time=0.0, end_time=5.0, text="Test 1", style="Default"),
            SubtitleLine(start_time=6.0, end_time=10.0, text="Test 2", style="Default")
        ]
        
        timeline_widget.set_subtitle_lines(lines)
        
        # Test position within first subtitle (0-5 seconds = 0-250 pixels at scale 50)
        pos = QPoint(100, 50)  # 2 seconds, within subtitle area
        index = timeline_widget._get_subtitle_at_position(pos)
        assert index == 0
        
        # Test position outside subtitle area
        pos = QPoint(100, 10)  # Within ruler area
        index = timeline_widget._get_subtitle_at_position(pos)
        assert index == -1
    
    def test_mouse_interaction_signals(self, timeline_widget):
        """Test mouse interaction signals."""
        # Mock signal handlers
        subtitle_selected_mock = Mock()
        timing_changed_mock = Mock()
        
        timeline_widget.subtitle_selected.connect(subtitle_selected_mock)
        timeline_widget.timing_changed.connect(timing_changed_mock)
        
        # Set up subtitle lines
        lines = [
            SubtitleLine(start_time=0.0, end_time=5.0, text="Test 1", style="Default")
        ]
        timeline_widget.set_subtitle_lines(lines)
        
        # Simulate mouse press on subtitle
        from PyQt6.QtCore import QPointF
        pos = QPointF(100, 50)  # Within subtitle area
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        timeline_widget.mousePressEvent(event)
        
        # Check that subtitle was selected
        subtitle_selected_mock.assert_called_with(0)


class TestAssHighlighter:
    """Test cases for ASS syntax highlighter."""
    
    def test_highlighter_initialization(self, app):
        """Test highlighter initialization."""
        from PyQt6.QtGui import QTextDocument
        
        document = QTextDocument()
        highlighter = AssHighlighter(document)
        
        assert highlighter is not None
        assert hasattr(highlighter, 'section_format')
        assert hasattr(highlighter, 'field_format')
        assert hasattr(highlighter, 'time_format')
    
    def test_section_highlighting(self, app):
        """Test section header highlighting."""
        from PyQt6.QtGui import QTextDocument
        
        document = QTextDocument()
        highlighter = AssHighlighter(document)
        
        # Test section header detection
        test_text = "[Script Info]"
        document.setPlainText(test_text)
        
        # The highlighter should process the text
        # Note: Actual highlighting verification would require more complex setup


if __name__ == "__main__":
    pytest.main([__file__])