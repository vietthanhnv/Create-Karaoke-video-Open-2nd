"""
Unit tests for the Integrated Editor Widget
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.ui.integrated_editor_widget import IntegratedEditorWidget
from src.core.models import Project, SubtitleFile, SubtitleLine, SubtitleStyle


class TestIntegratedEditorWidget:
    """Test cases for IntegratedEditorWidget"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def widget(self, app):
        """Create IntegratedEditorWidget instance"""
        return IntegratedEditorWidget()
    
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing"""
        # Create sample subtitle file
        subtitle_content = """[Script Info]
Title: Test Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Hello World
Dialogue: 0,0:00:03.00,0:00:06.00,Default,,0,0,0,,This is a test
"""
        
        subtitle_file = tmp_path / "test.ass"
        subtitle_file.write_text(subtitle_content, encoding='utf-8')
        
        # Create project
        project = Project(
            id="test_project_1",
            name="Test Project",
            video_file=None,
            audio_file=None,
            subtitle_file=SubtitleFile(path=str(subtitle_file))
        )
        
        return project
    
    def test_widget_initialization(self, widget):
        """Test widget initializes correctly"""
        assert widget is not None
        assert hasattr(widget, 'text_editor')
        assert hasattr(widget, 'timeline_widget')
        assert hasattr(widget, 'opengl_widget')
        assert hasattr(widget, 'effects_manager')
        assert hasattr(widget, 'synchronizer')
        
    def test_ui_components_exist(self, widget):
        """Test that all UI components are created"""
        # Check main components
        assert widget.editing_tabs is not None
        assert widget.text_editor is not None
        assert widget.timeline_widget is not None
        assert widget.opengl_widget is not None
        
        # Check tabs
        assert widget.editing_tabs.count() == 3
        assert widget.editing_tabs.tabText(0) == "Text Editor"
        assert widget.editing_tabs.tabText(1) == "Timeline"
        assert widget.editing_tabs.tabText(2) == "Effects"
        
        # Check playback controls
        assert widget.play_button is not None
        assert widget.stop_button is not None
        assert widget.timeline_slider is not None
        
        # Check effects components
        assert widget.effects_list is not None
        assert widget.applied_effects_list is not None
        assert widget.presets_combo is not None
        
    def test_load_project(self, widget, sample_project):
        """Test loading a project"""
        # Mock the synchronizer to avoid OpenGL issues in tests
        widget.synchronizer = Mock()
        widget.synchronizer.load_project.return_value = True
        widget.synchronizer.get_duration.return_value = 10.0
        widget.synchronizer.seek_to_time = Mock()
        
        # Load project
        success = widget.load_project(sample_project)
        
        assert success is True
        assert widget.current_project == sample_project
        
        # Check that synchronizer methods were called
        widget.synchronizer.load_project.assert_called_once_with(sample_project)
        widget.synchronizer.seek_to_time.assert_called_once_with(0.0)
        
    def test_load_subtitle_file(self, widget, sample_project):
        """Test loading subtitle file content"""
        widget.load_subtitle_file(sample_project.subtitle_file)
        
        # Check that content was loaded
        content = widget.text_editor.toPlainText()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Hello World" in content
        assert "This is a test" in content
        
    def test_text_editor_changes_trigger_updates(self, widget):
        """Test that text editor changes trigger appropriate updates"""
        # Mock the update methods to avoid complex parsing in tests
        widget._update_timeline_and_list = Mock()
        widget._schedule_preview_update = Mock()
        widget.validation_timer = Mock()
        
        # Change text
        widget.text_editor.setPlainText("New content")
        
        # Check that update methods were called
        widget._update_timeline_and_list.assert_called()
        widget._schedule_preview_update.assert_called()
        
    def test_playback_controls(self, widget):
        """Test playback control functionality"""
        # Mock synchronizer
        widget.synchronizer = Mock()
        widget.synchronizer.play = Mock()
        widget.synchronizer.pause = Mock()
        widget.synchronizer.stop = Mock()
        widget.synchronizer.seek_to_time = Mock()
        widget.synchronizer.get_duration.return_value = 100.0
        
        # Test play/pause toggle
        widget.is_playing = False
        widget._toggle_playback()
        widget.synchronizer.play.assert_called_once()
        
        widget.is_playing = True
        widget._toggle_playback()
        widget.synchronizer.pause.assert_called_once()
        
        # Test stop
        widget._stop_playback()
        widget.synchronizer.stop.assert_called_once()
        widget.synchronizer.seek_to_time.assert_called_with(0.0)
        
        # Test timeline seek
        widget._on_timeline_seek(50)  # 50% position
        widget.synchronizer.seek_to_time.assert_called_with(50.0)  # 50% of 100s duration
        
    def test_effects_management(self, widget):
        """Test effects management functionality"""
        # Mock effects manager
        widget.effects_manager = Mock()
        widget.effects_manager.get_available_presets.return_value = ["preset1", "preset2"]
        widget.effects_manager.get_preset_info.return_value = Mock(name="Test Preset")
        widget.effects_manager.create_effect.return_value = Mock(id="effect1", parameters={})
        widget.effects_manager.add_effect_layer.return_value = Mock()
        widget.effects_manager.effect_layers = []  # Mock empty list for iteration
        
        # Test adding effect
        # First select an effect
        widget.effects_list.setCurrentRow(0)
        widget._add_effect()
        
        # Check that effect was created and added
        widget.effects_manager.create_effect.assert_called()
        widget.effects_manager.add_effect_layer.assert_called()
        
    def test_timeline_integration(self, widget, sample_project):
        """Test timeline integration with subtitle editing"""
        # Load subtitle content first
        widget.load_subtitle_file(sample_project.subtitle_file)
        
        # Mock timeline widget
        widget.timeline_widget = Mock()
        widget.timeline_widget.set_subtitle_lines = Mock()
        
        # Trigger timeline update
        widget._update_timeline_and_list()
        
        # Check that timeline was updated
        widget.timeline_widget.set_subtitle_lines.assert_called()
        
    def test_individual_subtitle_editing(self, widget):
        """Test individual subtitle line editing"""
        # Create mock parsed lines
        widget.parsed_lines = [
            SubtitleLine(start_time=0.0, end_time=3.0, text="Test line", style="Default")
        ]
        widget.selected_subtitle_index = 0
        
        # Mock update method
        widget._update_text_from_parsed_lines = Mock()
        
        # Test timing changes
        widget.start_time_editor.setValue(1.0)
        widget._on_individual_timing_changed()
        
        assert widget.parsed_lines[0].start_time == 1.0
        widget._update_text_from_parsed_lines.assert_called()
        
        # Test text changes
        widget.line_text_editor.setText("Updated text")
        widget._on_individual_text_changed()
        
        assert widget.parsed_lines[0].text == "Updated text"
        
    def test_validation_functionality(self, widget):
        """Test subtitle validation"""
        # Test valid content
        valid_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        widget.text_editor.setPlainText(valid_content)
        widget._validate_content()
        
        # Check validation display
        validation_text = widget.validation_display.toPlainText()
        assert "valid" in validation_text.lower() or "✓" in validation_text
        
    def test_format_time_utility(self, widget):
        """Test time formatting utility"""
        assert widget._format_time(0) == "00:00"
        assert widget._format_time(65) == "01:05"
        assert widget._format_time(3661) == "61:01"
        
    def test_format_ass_time_utility(self, widget):
        """Test ASS time formatting utility"""
        assert widget._format_ass_time(0) == "0:00:00.00"
        assert widget._format_ass_time(65.5) == "0:01:05.50"
        assert widget._format_ass_time(3661.25) == "1:01:01.25"
        
    def test_add_subtitle_line(self, widget):
        """Test adding new subtitle lines"""
        widget.current_time = 10.0
        widget.parsed_lines = []
        widget._update_text_from_parsed_lines = Mock()
        widget.timeline_widget = Mock()
        
        widget._add_subtitle_line()
        
        assert len(widget.parsed_lines) == 1
        assert widget.parsed_lines[0].start_time == 10.0
        assert widget.parsed_lines[0].end_time == 13.0
        assert widget.parsed_lines[0].text == "New subtitle line"
        
    def test_auto_format_functionality(self, widget):
        """Test auto-formatting of subtitle text"""
        # Test incomplete content
        incomplete_content = "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Test line"
        widget.text_editor.setPlainText(incomplete_content)
        
        widget._auto_format_text()
        
        formatted_content = widget.text_editor.toPlainText()
        assert "[Script Info]" in formatted_content
        # The auto-format logic inserts styles section before [Events]
        # Let's check that it at least has the Events section
        assert "[Events]" in formatted_content
        # Check that the original dialogue line is preserved
        assert "Test line" in formatted_content
        
    def test_save_subtitle_file(self, widget, tmp_path):
        """Test saving subtitle file"""
        test_content = "Test subtitle content"
        widget.text_editor.setPlainText(test_content)
        
        save_path = tmp_path / "output.ass"
        widget.save_subtitle_file(str(save_path))
        
        # Check file was created and contains correct content
        assert save_path.exists()
        assert save_path.read_text(encoding='utf-8') == test_content
        
        # Check status was updated
        assert "Saved" in widget.status_label.text()
        
    def test_synchronizer_event_handling(self, widget):
        """Test handling of synchronizer events"""
        # Test frame update
        test_image = QImage(100, 100, QImage.Format.Format_RGB32)
        widget._on_frame_updated(test_image, 1.0)
        
        # Test time position change
        widget._on_time_position_changed(5.0, 10.0)
        assert widget.current_time == 5.0
        assert widget.timeline_slider.value() == 50  # 50% of duration
        
        # Test playback state change
        widget._on_playback_state_changed(True)
        assert widget.is_playing is True
        assert widget.play_button.text() == "Pause"
        
        widget._on_playback_state_changed(False)
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
        
    def test_effects_parameter_updates(self, widget):
        """Test effects parameter updates"""
        # Mock effects manager
        widget.effects_manager = Mock()
        widget.effects_manager.update_effect_parameters = Mock()
        widget._schedule_preview_update = Mock()
        
        # Test parameter update
        widget._update_effect_parameter("effect1", "intensity", 0.8)
        
        widget.effects_manager.update_effect_parameters.assert_called_once_with(
            "effect1", {"intensity": 0.8}
        )
        widget._schedule_preview_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])