"""
Integration tests for the subtitle editor widget with the main application.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.ui.main_window import MainWindow
from src.ui.editor_widget import EditorWidget
from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing."""
    window = MainWindow()
    return window


@pytest.fixture
def sample_ass_content():
    """Sample ASS content for testing."""
    return """[Script Info]
Title: Test Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Hello world
Dialogue: 0,0:00:03.50,0:00:06.00,Default,,0,0,0,,This is a test
Dialogue: 0,0:00:06.50,0:00:09.00,Default,,0,0,0,,Karaoke subtitle
"""


class TestEditorIntegration:
    """Test integration of editor widget with main application."""
    
    def test_editor_widget_in_main_window(self, main_window):
        """Test that editor widget is properly integrated in main window."""
        # Check that editor widget exists
        assert hasattr(main_window, 'editor_widget')
        assert isinstance(main_window.editor_widget, EditorWidget)
        
        # Check that editor tab exists
        tab_widget = main_window.tab_widget
        editor_tab_index = -1
        for i in range(tab_widget.count()):
            if "Edit Subtitles" in tab_widget.tabText(i):
                editor_tab_index = i
                break
        
        assert editor_tab_index >= 0, "Editor tab not found"
        assert tab_widget.widget(editor_tab_index) == main_window.editor_widget
    
    def test_editor_widget_functionality(self, main_window, sample_ass_content):
        """Test basic editor widget functionality within main window."""
        editor = main_window.editor_widget
        
        # Set content in text editor
        editor.text_editor.setPlainText(sample_ass_content)
        
        # Trigger validation
        editor._validate_content()
        
        # Check that validation results are displayed
        validation_text = editor.validation_display.toPlainText()
        assert len(validation_text) > 0
        
        # Check that subtitle lines were parsed
        assert hasattr(editor, 'parsed_lines')
        assert len(editor.parsed_lines) == 3
    
    def test_editor_timeline_functionality(self, main_window, sample_ass_content):
        """Test timeline functionality within main window."""
        editor = main_window.editor_widget
        
        # Set content and validate
        editor.text_editor.setPlainText(sample_ass_content)
        editor._validate_content()
        
        # Check timeline widget
        timeline = editor.timeline_widget
        assert len(timeline.subtitle_lines) == 3
        
        # Test timeline selection
        timeline.set_selected_index(0)
        assert timeline.selected_index == 0
    
    def test_editor_subtitle_list_functionality(self, main_window, sample_ass_content):
        """Test subtitle list functionality within main window."""
        editor = main_window.editor_widget
        
        # Set content and validate
        editor.text_editor.setPlainText(sample_ass_content)
        editor._validate_content()
        
        # Check subtitle list
        subtitle_list = editor.subtitle_list
        assert subtitle_list.count() == 3
        
        # Test list selection
        subtitle_list.setCurrentRow(0)
        editor._on_list_selection_changed()
        
        # Check that individual editor is populated
        assert editor.start_time_editor.value() == 0.0
        assert editor.end_time_editor.value() == 3.0
        assert "Hello world" in editor.line_text_editor.text()
    
    def test_editor_individual_editing(self, main_window, sample_ass_content):
        """Test individual subtitle editing within main window."""
        editor = main_window.editor_widget
        
        # Set content and validate
        editor.text_editor.setPlainText(sample_ass_content)
        editor._validate_content()
        
        # Select first subtitle
        editor.subtitle_list.setCurrentRow(0)
        editor._load_individual_editor(0)
        
        # Modify text
        new_text = "Modified subtitle text"
        editor.line_text_editor.setText(new_text)
        editor._on_individual_text_changed()
        
        # Check that changes are reflected
        assert editor.parsed_lines[0].text == new_text
        
        # Check that text editor content is updated
        updated_content = editor.text_editor.toPlainText()
        assert new_text in updated_content
    
    def test_editor_timing_changes(self, main_window, sample_ass_content):
        """Test timing changes within main window."""
        editor = main_window.editor_widget
        
        # Set content and validate
        editor.text_editor.setPlainText(sample_ass_content)
        editor._validate_content()
        
        # Select first subtitle
        editor.subtitle_list.setCurrentRow(0)
        editor._load_individual_editor(0)
        
        # Change timing
        editor.start_time_editor.setValue(1.0)
        editor.end_time_editor.setValue(4.0)
        editor._on_individual_timing_changed()
        
        # Check that changes are reflected
        assert editor.parsed_lines[0].start_time == 1.0
        assert editor.parsed_lines[0].end_time == 4.0
        
        # Check that timeline is updated
        timeline_lines = editor.timeline_widget.subtitle_lines
        assert timeline_lines[0].start_time == 1.0
        assert timeline_lines[0].end_time == 4.0
    
    def test_editor_signal_connections(self, main_window):
        """Test that editor signals are properly connected."""
        editor = main_window.editor_widget
        
        # Check that signals exist
        assert hasattr(editor, 'subtitle_changed')
        assert hasattr(editor, 'timing_changed')
        assert hasattr(editor, 'subtitle_selected')
        assert hasattr(editor, 'validation_updated')
        
        # Test signal emission with mock handlers
        subtitle_changed_mock = Mock()
        timing_changed_mock = Mock()
        subtitle_selected_mock = Mock()
        
        editor.subtitle_changed.connect(subtitle_changed_mock)
        editor.timing_changed.connect(timing_changed_mock)
        editor.subtitle_selected.connect(subtitle_selected_mock)
        
        # Trigger signals
        editor.text_editor.setPlainText("Test content")
        # Note: subtitle_changed signal is emitted with delay due to timer
        
        # Test timing change signal
        editor.timing_changed.emit(0, 1.0, 2.0)
        timing_changed_mock.assert_called_with(0, 1.0, 2.0)
        
        # Test subtitle selection signal
        editor.subtitle_selected.emit(1)
        subtitle_selected_mock.assert_called_with(1)
    
    def test_editor_file_loading_integration(self, main_window, sample_ass_content):
        """Test loading subtitle files through the editor."""
        editor = main_window.editor_widget
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(sample_ass_content)
            temp_path = f.name
        
        try:
            # Create subtitle file object
            subtitle_file = SubtitleFile(path=temp_path, format="ass")
            
            # Load file through editor
            editor.load_subtitle_file(subtitle_file)
            
            # Check that content was loaded
            loaded_content = editor.get_subtitle_content()
            assert "Hello world" in loaded_content
            assert "This is a test" in loaded_content
            assert "Karaoke subtitle" in loaded_content
            
            # Check that parsing was successful
            assert hasattr(editor, 'parsed_lines')
            assert len(editor.parsed_lines) == 3
            
        finally:
            # Cleanup
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def test_editor_validation_integration(self, main_window):
        """Test validation integration within main window."""
        editor = main_window.editor_widget
        
        # Test with invalid content
        invalid_content = "This is not valid ASS content"
        editor.text_editor.setPlainText(invalid_content)
        editor._validate_content()
        
        # Check validation results
        validation_text = editor.validation_display.toPlainText()
        assert len(validation_text) > 0
        
        # Test with valid content
        valid_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,Test subtitle
"""
        
        editor.text_editor.setPlainText(valid_content)
        editor._validate_content()
        
        # Check validation results
        validation_text = editor.validation_display.toPlainText()
        assert "valid" in validation_text.lower() or "1 subtitle" in validation_text


if __name__ == "__main__":
    pytest.main([__file__])