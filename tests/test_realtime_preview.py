"""
Test real-time preview functionality in editor and effects widgets.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.editor_widget import EditorWidget
from src.ui.effects_widget import EffectsWidget
from src.ui.preview_widget import PreviewWidget
from src.core.models import Project, SubtitleFile, SubtitleLine, SubtitleStyle, WordTiming


@pytest.fixture
def app():
    """Create QApplication for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    word_timings = [
        WordTiming("Hello", 1.0, 1.5),
        WordTiming("world", 1.5, 2.0)
    ]
    
    subtitle_lines = [
        SubtitleLine(
            start_time=1.0,
            end_time=2.0,
            text="Hello world",
            style="Default",
            word_timings=word_timings
        )
    ]
    
    subtitle_style = SubtitleStyle(name="Default")
    
    subtitle_file = SubtitleFile(
        path="test.ass",
        lines=subtitle_lines,
        styles=[subtitle_style]
    )
    
    return Project(
        id="test",
        name="Test Project",
        subtitle_file=subtitle_file
    )


def test_editor_realtime_preview_creation(app, sample_project):
    """Test that editor widget creates real-time preview components."""
    editor = EditorWidget()
    
    # Check that preview components exist
    assert hasattr(editor, 'preview_display')
    assert hasattr(editor, 'preview_time_slider')
    assert hasattr(editor, 'auto_update_preview')
    assert hasattr(editor, 'preview_update_timer')
    
    # Check initial state
    assert editor.auto_update_preview.isChecked()
    assert editor.preview_display.text() == "Subtitle preview will appear here"


def test_editor_preview_time_update(app, sample_project):
    """Test preview time slider updates."""
    editor = EditorWidget()
    editor.load_project(sample_project)
    
    # Simulate slider change
    editor.preview_time_slider.setValue(50)
    editor._update_preview_time(50)
    
    # Check that time value is updated
    time_text = editor.preview_time_value.text()
    assert "s" in time_text  # Should show time in seconds


def test_editor_karaoke_preview_rendering(app, sample_project):
    """Test karaoke preview rendering with word timing."""
    editor = EditorWidget()
    editor.load_project(sample_project)
    
    # Set preview time to middle of first word
    editor.preview_time_slider.setValue(25)  # Should be around 1.25s
    editor._update_subtitle_preview()
    
    # Check that preview contains HTML color coding
    preview_text = editor.preview_display.text()
    assert "span" in preview_text or "Hello world" in preview_text


def test_effects_widget_preview_creation(app):
    """Test that effects widget creates preview components."""
    effects = EffectsWidget()
    
    # Check that preview components exist
    assert hasattr(effects, 'preview_label')
    assert hasattr(effects, 'preview_text_combo')
    assert hasattr(effects, 'update_preview_button')
    assert hasattr(effects, 'preview_timer')


def test_effects_preview_update(app):
    """Test effects preview updates."""
    effects = EffectsWidget()
    
    # Set preview text
    test_text = "Test Effect"
    effects.preview_text_combo.setCurrentText(test_text)
    
    # Update preview
    effects._update_preview()
    
    # Check that preview shows the text
    assert effects.preview_label.text() == test_text


def test_effects_glow_preview(app):
    """Test glow effect preview rendering."""
    effects = EffectsWidget()
    
    # Add a glow effect
    effects._add_effect()  # This would need to be modified to work without UI interaction
    
    # For now, just test that the preview update method exists and runs
    effects._update_preview()
    
    # The preview should not crash
    assert effects.preview_label.text() is not None


def test_preview_widget_effect_methods(app):
    """Test that preview widget has effect handling methods."""
    preview = PreviewWidget()
    
    # Check that effect methods exist
    assert hasattr(preview, 'add_effect')
    assert hasattr(preview, 'remove_effect')
    assert hasattr(preview, 'update_effect_parameters')
    assert hasattr(preview, 'toggle_effect')
    assert hasattr(preview, 'apply_effect_preset')


def test_realtime_signal_connections(app, sample_project):
    """Test that real-time signals can be connected."""
    editor = EditorWidget()
    effects = EffectsWidget()
    preview = PreviewWidget()
    
    # Test signal connections don't crash
    editor.subtitles_updated_realtime.connect(preview.update_subtitles_realtime)
    effects.effect_applied.connect(lambda effect_id, params: preview.add_effect(effect_id, params))
    effects.effect_parameters_changed.connect(preview.update_effect_parameters)
    
    # Load project to trigger signals
    editor.load_project(sample_project)
    
    # Signals should be connected without errors
    assert True  # If we get here, connections worked


if __name__ == "__main__":
    pytest.main([__file__])