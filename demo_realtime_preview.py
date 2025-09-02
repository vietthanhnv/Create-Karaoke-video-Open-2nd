#!/usr/bin/env python3
"""
Demo script for real-time preview functionality.

This script demonstrates the enhanced real-time preview in both
the subtitle editor and text effects sections.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from ui.editor_widget import EditorWidget
from ui.effects_widget import EffectsWidget
from ui.preview_widget import PreviewWidget
from core.models import Project, SubtitleFile, SubtitleLine, SubtitleStyle, WordTiming, ImageFile, AudioFile


def create_demo_project_with_effects():
    """Create a demo project with karaoke timing and effects."""
    
    # Create word timings for karaoke effect
    word_timings_1 = [
        WordTiming("Real", 1.0, 1.3),
        WordTiming("time", 1.3, 1.6),
        WordTiming("preview", 1.6, 2.2),
        WordTiming("demo", 2.2, 2.8)
    ]
    
    word_timings_2 = [
        WordTiming("Watch", 3.0, 3.3),
        WordTiming("effects", 3.3, 3.8),
        WordTiming("update", 3.8, 4.3),
        WordTiming("live", 4.3, 4.8)
    ]
    
    # Create subtitle lines with karaoke timing
    subtitle_lines = [
        SubtitleLine(
            start_time=1.0,
            end_time=2.8,
            text="Real time preview demo",
            style="Default",
            word_timings=word_timings_1
        ),
        SubtitleLine(
            start_time=3.0,
            end_time=4.8,
            text="Watch effects update live",
            style="Default",
            word_timings=word_timings_2
        ),
        SubtitleLine(
            start_time=5.0,
            end_time=7.0,
            text="Edit and see changes instantly",
            style="Default"
        )
    ]
    
    # Create subtitle style
    subtitle_style = SubtitleStyle(
        name="Default",
        font_name="Arial",
        font_size=24,
        primary_color="#FFFFFF",
        bold=True
    )
    
    # Create subtitle file
    subtitle_file = SubtitleFile(
        path="demo_realtime.ass",
        format="ass",
        lines=subtitle_lines,
        styles=[subtitle_style]
    )
    
    # Create demo media files
    image_file = ImageFile(
        path="demo_background.jpg",
        resolution={"width": 1920, "height": 1080},
        format="jpg"
    )
    
    audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=8.0,
        format="mp3"
    )
    
    # Create project
    project = Project(
        id="realtime_demo",
        name="Real-time Preview Demo",
        image_file=image_file,
        audio_file=audio_file,
        subtitle_file=subtitle_file
    )
    
    return project


class RealtimePreviewDemo(QMainWindow):
    """Demo window showing real-time preview functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time Preview Demo")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget with horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Create editor widget (left side)
        self.editor_widget = EditorWidget()
        layout.addWidget(self.editor_widget)
        
        # Create effects widget (right side)
        self.effects_widget = EffectsWidget()
        layout.addWidget(self.effects_widget)
        
        # Create preview widget (bottom)
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        
        self.preview_widget = PreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        
        # Add preview to main layout
        layout.addWidget(preview_container)
        
        # Set layout proportions
        layout.setStretch(0, 2)  # Editor widget
        layout.setStretch(1, 2)  # Effects widget  
        layout.setStretch(2, 3)  # Preview widget
        
        # Load demo project
        self.demo_project = create_demo_project_with_effects()
        self._setup_demo()
        
        # Connect real-time updates
        self._connect_realtime_signals()
        
    def _setup_demo(self):
        """Set up the demo with sample content."""
        try:
            # Load project into widgets
            self.editor_widget.load_project(self.demo_project)
            self.preview_widget.load_project(self.demo_project)
            
            print("Demo project loaded successfully!")
            
        except Exception as e:
            print(f"Error setting up demo: {e}")
    
    def _connect_realtime_signals(self):
        """Connect signals for real-time preview updates."""
        # Connect editor to preview
        self.editor_widget.subtitles_updated_realtime.connect(
            self.preview_widget.update_subtitles_realtime
        )
        
        # Connect effects to preview
        self.effects_widget.effect_applied.connect(self._on_effect_applied)
        self.effects_widget.effect_removed.connect(self._on_effect_removed)
        self.effects_widget.effect_parameters_changed.connect(self._on_effect_parameters_changed)
        self.effects_widget.effect_toggled.connect(self._on_effect_toggled)
        self.effects_widget.preset_applied.connect(self._on_preset_applied)
        
        print("Real-time signals connected!")
    
    def _on_effect_applied(self, effect_id: str, parameters: dict):
        """Handle effect application."""
        self.preview_widget.add_effect(effect_id, parameters)
        print(f"Effect applied: {effect_id}")
    
    def _on_effect_removed(self, effect_id: str):
        """Handle effect removal."""
        self.preview_widget.remove_effect(effect_id)
        print(f"Effect removed: {effect_id}")
    
    def _on_effect_parameters_changed(self, effect_id: str, parameters: dict):
        """Handle effect parameter changes."""
        self.preview_widget.update_effect_parameters(effect_id, parameters)
        # Don't print for parameter changes to avoid spam
    
    def _on_effect_toggled(self, effect_id: str, enabled: bool):
        """Handle effect toggle."""
        self.preview_widget.toggle_effect(effect_id, enabled)
        status = "enabled" if enabled else "disabled"
        print(f"Effect {status}: {effect_id}")
    
    def _on_preset_applied(self, preset_name: str):
        """Handle preset application."""
        self.preview_widget.apply_effect_preset(preset_name)
        print(f"Preset applied: {preset_name}")


def main():
    """Run the real-time preview demo."""
    app = QApplication(sys.argv)
    
    # Create and show demo window
    demo_window = RealtimePreviewDemo()
    demo_window.show()
    
    print("Real-time Preview Demo Started!")
    print("\nFeatures to test:")
    print("1. Edit subtitle text in the editor - see live preview updates")
    print("2. Adjust timing with the timeline - see karaoke animation")
    print("3. Add text effects - see them applied in real-time")
    print("4. Adjust effect parameters - see immediate changes")
    print("5. Toggle effects on/off - see instant updates")
    print("6. Try different effect presets")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()