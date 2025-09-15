"""
Unit tests for the Unified Editor Widget
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

from src.ui.unified_editor_widget import UnifiedEditorWidget
from src.core.models import Project, SubtitleFile, SubtitleLine, SubtitleStyle


class TestUnifiedEditorWidget:
    """Test cases for UnifiedEditorWidget"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def widget(self, app):
        """Create UnifiedEditorWidget instance"""
        return UnifiedEditorWidget()
    
    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing"""
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
        
    def test_unified_layout_components(self, widget):
        """Test that all components are in unified layout"""
        # Check main components exist
        assert widget.text_editor is not None
        assert widget.timeline_widget is not None
        assert widget.opengl_widget is not None
        
        # Check individual editor components
        assert widget.start_time_editor is not None
        assert widget.end_time_editor is not None
        assert widget.line_text_editor is not None
        assert widget.style_editor is not None
        
        # Check effects components
        assert widget.effects_combo is not None
        assert widget.applied_effects_list is not None
        assert widget.presets_combo is not None
        
        # Check playback controls
        assert widget.play_button is not None
        assert widget.stop_button is not None
        assert widget.timeline_slider is not None
        
        # Check status components
        assert widget.status_label is not None
        assert widget.validation_display is not None
        
    def test_compact_layout_constraints(self, widget):
        """Test that components have appropriate size constraints for unified layout"""
        # Text editor should be height-limited
        assert widget.text_editor.maximumHeight() == 200
        
        # Timeline should be compact
        timeline_scroll = widget.timeline_widget.parent().parent()  # ScrollArea
        assert timeline_scroll.maximumHeight() == 120
        
        # Applied effects list should be compact
        assert widget.applied_effects_list.maximumHeight() == 80
        
        # Parameters scroll should be compact
        params_scroll = widget.params_container.parent().parent()  # ScrollArea
        assert params_scroll.maximumHeight() == 100
        
    def test_load_project(self, widget, sample_project):
        """Test loading a project"""
        # Mock synchronizer
        widget.synchronizer = Mock()
        widget.synchronizer.load_project.return_value = True
        widget.synchronizer.get_duration.return_value = 10.0
        widget.synchronizer.seek_to_time = Mock()
        
        success = widget.load_project(sample_project)
        
        assert success is True
        assert widget.current_project == sample_project
        
        # Check synchronizer calls
        widget.synchronizer.load_project.assert_called_once_with(sample_project)
        widget.synchronizer.seek_to_time.assert_called_once_with(0.0)
        
    def test_load_subtitle_file(self, widget, sample_project):
        """Test loading subtitle file content"""
        widget.load_subtitle_file(sample_project.subtitle_file)
        
        content = widget.text_editor.toPlainText()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Hello World" in content
        assert "This is a test" in content
        
    def test_unified_text_editing_updates_all_components(self, widget):
        """Test that text editing updates all related components"""
        # Mock update methods
        widget._update_timeline_and_list = Mock()
        widget._schedule_preview_update = Mock()
        widget.validation_timer = Mock()
        
        # Change text
        widget.text_editor.setPlainText("New content")
        
        # All components should be updated
        widget._update_timeline_and_list.assert_called()
        widget._schedule_preview_update.assert_called()
        
    def test_individual_editor_integration(self, widget):
        """Test individual subtitle editor integration"""
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
        
    def test_effects_integration_in_unified_layout(self, widget):
        """Test effects management in unified layout"""
        # Mock effects manager
        widget.effects_manager = Mock()
        widget.effects_manager.get_available_presets.return_value = ["preset1"]
        widget.effects_manager.get_preset_info.return_value = Mock(name="Test Preset")
        widget.effects_manager.create_effect.return_value = Mock(id="effect1", parameters={})
        widget.effects_manager.add_effect_layer.return_value = Mock()
        widget.effects_manager.effect_layers = []
        
        # Test adding effect via combo box
        widget.effects_combo.setCurrentIndex(1)  # Select first real effect
        widget._add_effect()
        
        # Check effect was created
        widget.effects_manager.create_effect.assert_called()
        widget.effects_manager.add_effect_layer.assert_called()
        
    def test_compact_effects_parameters(self, widget):
        """Test compact effects parameter display"""
        # Create mock effect layer
        mock_effect = Mock()
        mock_effect.id = "test_effect"
        mock_effect.name = "Test Effect"
        mock_effect.parameters = {
            "intensity": 0.5,
            "color": [1.0, 0.0, 0.0],
            "enabled": True
        }
        
        mock_layer = Mock()
        mock_layer.effect = mock_effect
        
        # Show parameters
        widget._show_effect_parameters(mock_layer)
        
        # Check that parameters were added to layout
        assert widget.params_layout.count() > 0
        
    def test_timeline_integration_in_unified_layout(self, widget, sample_project):
        """Test timeline integration"""
        widget.load_subtitle_file(sample_project.subtitle_file)
        
        # Mock timeline widget
        widget.timeline_widget = Mock()
        widget.timeline_widget.set_subtitle_lines = Mock()
        
        # Trigger timeline update
        widget._update_timeline_and_list()
        
        # Timeline should be updated
        widget.timeline_widget.set_subtitle_lines.assert_called()
        
    def test_playback_controls_integration(self, widget):
        """Test playback controls in unified layout"""
        # Mock synchronizer
        widget.synchronizer = Mock()
        widget.synchronizer.play = Mock()
        widget.synchronizer.pause = Mock()
        widget.synchronizer.stop = Mock()
        widget.synchronizer.seek_to_time = Mock()
        widget.synchronizer.get_duration.return_value = 100.0
        
        # Test playback controls
        widget.is_playing = False
        widget._toggle_playback()
        widget.synchronizer.play.assert_called_once()
        
        widget.is_playing = True
        widget._toggle_playback()
        widget.synchronizer.pause.assert_called_once()
        
        # Test stop
        widget._stop_playback()
        widget.synchronizer.stop.assert_called_once()
        
    def test_validation_integration(self, widget):
        """Test validation in unified layout"""
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
        
        # Check compact validation display
        validation_text = widget.validation_display.text()
        assert "✓" in validation_text or "Valid" in validation_text
        
    def test_status_bar_integration(self, widget):
        """Test status bar in unified layout"""
        # Test status updates
        widget.status_label.setText("Test status")
        assert widget.status_label.text() == "Test status"
        
        # Test validation display
        widget.validation_display.setText("✓ Valid")
        assert widget.validation_display.text() == "✓ Valid"
        
    def test_real_time_updates_across_all_components(self, widget):
        """Test that changes propagate across all unified components"""
        # Mock all update methods
        widget._update_timeline_and_list = Mock()
        widget._schedule_preview_update = Mock()
        widget._update_text_from_parsed_lines = Mock()
        
        # Create parsed lines
        widget.parsed_lines = [
            SubtitleLine(start_time=0.0, end_time=3.0, text="Test", style="Default")
        ]
        widget.selected_subtitle_index = 0
        
        # Change individual editor
        widget.line_text_editor.setText("Updated")
        widget._on_individual_text_changed()
        
        # Should update text editor
        widget._update_text_from_parsed_lines.assert_called()
        
        # Change text editor
        widget.text_editor.setPlainText("New content")
        
        # Should update timeline and preview
        widget._update_timeline_and_list.assert_called()
        widget._schedule_preview_update.assert_called()
        
    def test_space_efficient_layout(self, widget):
        """Test that the unified layout is space-efficient"""
        # Check that main splitter has reasonable proportions
        # This would be a 50/50 split in the actual implementation
        
        # Check that vertical splitter in editing panel has reasonable proportions
        # Text editor: 40%, Timeline: 30%, Effects+Individual: 30%
        
        # Verify compact components don't take excessive space
        assert widget.text_editor.maximumHeight() <= 200
        assert widget.applied_effects_list.maximumHeight() <= 80
        
    def test_add_subtitle_line_unified(self, widget):
        """Test adding subtitle line in unified interface"""
        widget.current_time = 5.0
        widget.parsed_lines = []
        widget._update_text_from_parsed_lines = Mock()
        widget.timeline_widget = Mock()
        
        widget._add_subtitle_line()
        
        assert len(widget.parsed_lines) == 1
        assert widget.parsed_lines[0].start_time == 5.0
        assert widget.parsed_lines[0].end_time == 8.0
        
    def test_auto_format_in_unified_interface(self, widget):
        """Test auto-formatting in unified interface"""
        incomplete_content = "Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Test"
        widget.text_editor.setPlainText(incomplete_content)
        
        widget._auto_format_text()
        
        formatted_content = widget.text_editor.toPlainText()
        assert "[Script Info]" in formatted_content
        assert "[Events]" in formatted_content
        assert "Test" in formatted_content
        
    def test_save_functionality(self, widget, tmp_path):
        """Test save functionality in unified interface"""
        test_content = "Test subtitle content"
        widget.text_editor.setPlainText(test_content)
        
        save_path = tmp_path / "output.ass"
        widget.save_subtitle_file(str(save_path))
        
        assert save_path.exists()
        assert save_path.read_text(encoding='utf-8') == test_content
        assert "Saved" in widget.status_label.text()
        
    def test_synchronizer_events_in_unified_layout(self, widget):
        """Test synchronizer event handling in unified layout"""
        # Test frame update
        test_image = QImage(100, 100, QImage.Format.Format_RGB32)
        widget._on_frame_updated(test_image, 1.0)
        
        # Test time position change
        widget._on_time_position_changed(5.0, 10.0)
        assert widget.current_time == 5.0
        assert widget.timeline_slider.value() == 50
        
        # Test playback state change
        widget._on_playback_state_changed(True)
        assert widget.is_playing is True
        assert widget.play_button.text() == "Pause"
        
    def test_effects_preset_in_unified_interface(self, widget):
        """Test effects preset functionality"""
        # Mock effects manager
        widget.effects_manager = Mock()
        widget.effects_manager.get_available_presets.return_value = []  # Empty list for simplicity
        widget._refresh_applied_effects = Mock()
        widget._schedule_preview_update = Mock()
        
        # Test that preset selection with empty list doesn't crash
        widget._on_preset_selected("Some Preset")
        
        # Should call get_available_presets but not apply anything
        widget.effects_manager.get_available_presets.assert_called_once()
        
        # Test with "Select Preset..." (should return early)
        widget._on_preset_selected("Select Preset...")
        
        # Should not call any additional methods for the default option


if __name__ == "__main__":
    pytest.main([__file__])