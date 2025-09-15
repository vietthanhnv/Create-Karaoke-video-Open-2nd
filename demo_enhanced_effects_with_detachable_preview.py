#!/usr/bin/env python3
"""
Demo: Enhanced Effects Widget with Detachable Preview

This demo shows the enhanced effects system working with the detachable preview,
providing comprehensive font styling and visual effects with real-time preview.
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, 
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.detachable_preview_widget import DetachablePreviewWidget
from src.ui.enhanced_effects_widget import EnhancedEffectsWidget
from src.core.models import Project, SubtitleFile


class EnhancedEffectsDemo(QMainWindow):
    """Demo application for enhanced effects with detachable preview"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced Effects with Detachable Preview Demo")
        self.setMinimumSize(1400, 900)
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the demo UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Enhanced Effects with Detachable Preview Demo")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "• Use the Enhanced Effects widget to configure comprehensive font styling and visual effects\n"
            "• All changes are synchronized in real-time with the detachable preview\n"
            "• Try different presets from the Presets tab\n"
            "• Detach the preview to a separate window for multi-monitor workflows\n"
            "• Combine multiple effects for complex styling"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(instructions)
        
        # Main content area with splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left side: Enhanced Effects Widget
        self.enhanced_effects_widget = EnhancedEffectsWidget()
        main_splitter.addWidget(self.enhanced_effects_widget)
        
        # Right side: Detachable Preview
        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        
        preview_title = QLabel("Real-time Preview")
        preview_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_title)
        
        self.detachable_preview = DetachablePreviewWidget()
        self.detachable_preview.set_parent_tab_widget(None, -1, "Enhanced Preview")
        preview_layout.addWidget(self.detachable_preview)
        
        main_splitter.addWidget(preview_container)
        
        # Set splitter proportions (60% effects, 40% preview)
        main_splitter.setSizes([840, 560])
        
        # Status bar
        self.status_label = QLabel("Ready - Configure effects to see real-time preview")
        self.status_label.setStyleSheet("margin: 5px; color: green;")
        layout.addWidget(self.status_label)
        
        # Demo controls
        self._create_demo_controls(layout)
        
    def _create_demo_controls(self, parent_layout):
        """Create demo control buttons"""
        controls_frame = QWidget()
        controls_layout = QHBoxLayout(controls_frame)
        
        # Quick preset buttons
        controls_layout.addWidget(QLabel("Quick Presets:"))
        
        karaoke_btn = QPushButton("Classic Karaoke")
        karaoke_btn.clicked.connect(lambda: self._apply_quick_preset("karaoke_classic"))
        controls_layout.addWidget(karaoke_btn)
        
        neon_btn = QPushButton("Neon Style")
        neon_btn.clicked.connect(lambda: self._apply_quick_preset("karaoke_neon"))
        controls_layout.addWidget(neon_btn)
        
        movie_btn = QPushButton("Movie Subtitle")
        movie_btn.clicked.connect(lambda: self._apply_quick_preset("movie_classic"))
        controls_layout.addWidget(movie_btn)
        
        fire_btn = QPushButton("Fire Gaming")
        fire_btn.clicked.connect(lambda: self._apply_quick_preset("gaming_fire"))
        controls_layout.addWidget(fire_btn)
        
        gold_btn = QPushButton("Elegant Gold")
        gold_btn.clicked.connect(lambda: self._apply_quick_preset("elegant_gold"))
        controls_layout.addWidget(gold_btn)
        
        controls_layout.addStretch()
        
        # Reset button
        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self._reset_effects)
        controls_layout.addWidget(reset_btn)
        
        parent_layout.addWidget(controls_frame)
        
    def _connect_signals(self):
        """Connect signals between enhanced effects and preview"""
        # Connect enhanced effects signals to preview updates
        self.enhanced_effects_widget.font_properties_changed.connect(self._on_font_properties_changed)
        self.enhanced_effects_widget.effect_applied.connect(self._on_effect_applied)
        self.enhanced_effects_widget.effect_removed.connect(self._on_effect_removed)
        self.enhanced_effects_widget.effect_parameters_changed.connect(self._on_effect_parameters_changed)
        self.enhanced_effects_widget.effect_toggled.connect(self._on_effect_toggled)
        self.enhanced_effects_widget.preset_applied.connect(self._on_preset_applied)
        
        # Connect detachable preview signals
        self.detachable_preview.detach_requested.connect(self._on_preview_detached)
        self.detachable_preview.attach_requested.connect(self._on_preview_attached)
        self.detachable_preview.closed.connect(self._on_preview_closed)
        
    def _on_font_properties_changed(self, font_props):
        """Handle font properties changes"""
        self.status_label.setText(f"Font updated: {font_props.get('family', 'Unknown')} {font_props.get('size', 0)}pt")
        self.status_label.setStyleSheet("margin: 5px; color: blue;")
        
        # In a real implementation, this would update the preview with new font properties
        # For demo purposes, we'll just show the status
        
    def _on_effect_applied(self, effect_id, parameters):
        """Handle effect application"""
        self.status_label.setText(f"Effect applied: {effect_id}")
        self.status_label.setStyleSheet("margin: 5px; color: green;")
        
        # Apply effect to detachable preview
        try:
            self.detachable_preview.add_effect(effect_id, parameters)
        except Exception as e:
            self.status_label.setText(f"Effect application failed: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _on_effect_removed(self, effect_id):
        """Handle effect removal"""
        self.status_label.setText(f"Effect removed: {effect_id}")
        self.status_label.setStyleSheet("margin: 5px; color: orange;")
        
        # Remove effect from detachable preview
        try:
            self.detachable_preview.remove_effect(effect_id)
        except Exception as e:
            self.status_label.setText(f"Effect removal failed: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _on_effect_parameters_changed(self, effect_id, parameters):
        """Handle effect parameter changes"""
        # Update preview with new parameters (no status message to avoid spam)
        try:
            self.detachable_preview.update_effect_parameters(effect_id, parameters)
        except Exception as e:
            self.status_label.setText(f"Parameter update failed: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _on_effect_toggled(self, effect_id, enabled):
        """Handle effect toggle"""
        status = "enabled" if enabled else "disabled"
        self.status_label.setText(f"Effect {status}: {effect_id}")
        self.status_label.setStyleSheet("margin: 5px; color: purple;")
        
        # Toggle effect in preview
        try:
            self.detachable_preview.toggle_effect(effect_id, enabled)
        except Exception as e:
            self.status_label.setText(f"Effect toggle failed: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _on_preset_applied(self, preset_name):
        """Handle preset application"""
        self.status_label.setText(f"Preset applied: {preset_name}")
        self.status_label.setStyleSheet("margin: 5px; color: cyan;")
        
        # Apply preset to preview
        try:
            self.detachable_preview.apply_effect_preset(preset_name)
        except Exception as e:
            self.status_label.setText(f"Preset application failed: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _on_preview_detached(self):
        """Handle preview detached"""
        self.status_label.setText("Preview detached to separate window")
        self.status_label.setStyleSheet("margin: 5px; color: orange;")
        
    def _on_preview_attached(self):
        """Handle preview reattached"""
        self.status_label.setText("Preview reattached to main window")
        self.status_label.setStyleSheet("margin: 5px; color: green;")
        
    def _on_preview_closed(self):
        """Handle preview closed"""
        self.status_label.setText("Preview closed")
        self.status_label.setStyleSheet("margin: 5px; color: red;")
        
    def _apply_quick_preset(self, preset_name):
        """Apply a quick preset"""
        try:
            success = self.enhanced_effects_widget.apply_preset_by_name(preset_name)
            if success:
                self.status_label.setText(f"Quick preset applied: {preset_name}")
                self.status_label.setStyleSheet("margin: 5px; color: green;")
            else:
                self.status_label.setText(f"Preset not found: {preset_name}")
                self.status_label.setStyleSheet("margin: 5px; color: red;")
        except Exception as e:
            self.status_label.setText(f"Preset application error: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _reset_effects(self):
        """Reset all effects"""
        try:
            # Reset enhanced effects widget
            self.enhanced_effects_widget.load_project(None)
            
            self.status_label.setText("All effects reset")
            self.status_label.setStyleSheet("margin: 5px; color: green;")
        except Exception as e:
            self.status_label.setText(f"Reset error: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")


def main():
    """Run the enhanced effects with detachable preview demo"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Enhanced Effects with Detachable Preview Demo")
    app.setApplicationVersion("1.0.0")
    
    # Create and show demo window
    demo = EnhancedEffectsDemo()
    demo.show()
    
    # Center on screen
    screen = app.primaryScreen()
    if screen:
        screen_geometry = screen.geometry()
        window_geometry = demo.geometry()
        
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        
        demo.move(x, y)
    
    print("Enhanced Effects with Detachable Preview Demo")
    print("=" * 50)
    print("• Use the Enhanced Effects widget to configure comprehensive styling")
    print("• All changes are synchronized in real-time with the detachable preview")
    print("• Try different presets and effect combinations")
    print("• Detach the preview for multi-monitor workflows")
    print("• Use quick preset buttons for common styles")
    print()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())