#!/usr/bin/env python3
"""
Demo: Detachable Preview Widget

This demo shows the detachable preview functionality where the preview
can be detached to a separate window and reattached to tabs.
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, 
    QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.detachable_preview_widget import DetachablePreviewWidget
from src.core.models import Project, SubtitleFile


class DetachablePreviewDemo(QMainWindow):
    """Demo application for detachable preview"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Detachable Preview Demo")
        self.setMinimumSize(1000, 700)
        
        self._setup_ui()
        self._setup_demo_content()
        
    def _setup_ui(self):
        """Set up the demo UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Detachable Preview Demo")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "• Click 'Detach' in the preview tab to open it in a separate window\n"
            "• Click 'Attach' to bring it back to the main window\n"
            "• Try closing the detached window to see reattach dialog\n"
            "• The preview synchronizes with text effects in real-time"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(instructions)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_tabs()
        
        # Status
        self.status_label = QLabel("Ready - Try detaching the preview!")
        self.status_label.setStyleSheet("margin: 5px; color: green;")
        layout.addWidget(self.status_label)
        
    def _create_tabs(self):
        """Create demo tabs"""
        # Import tab (placeholder)
        import_tab = QWidget()
        import_layout = QVBoxLayout(import_tab)
        import_layout.addWidget(QLabel("Import Media Tab"))
        import_layout.addWidget(QLabel("(Placeholder - load your media files here)"))
        import_layout.addStretch()
        self.tab_widget.addTab(import_tab, "1. Import")
        
        # Detachable preview tab
        self.preview_widget = DetachablePreviewWidget()
        self.preview_widget.set_parent_tab_widget(self.tab_widget, 1, "2. Preview")
        self.tab_widget.addTab(self.preview_widget, "2. Preview")
        
        # Connect preview signals
        self.preview_widget.detach_requested.connect(self._on_preview_detached)
        self.preview_widget.attach_requested.connect(self._on_preview_attached)
        self.preview_widget.closed.connect(self._on_preview_closed)
        
        # Editor tab (placeholder)
        editor_tab = QWidget()
        editor_layout = QVBoxLayout(editor_tab)
        editor_layout.addWidget(QLabel("Subtitle Editor Tab"))
        editor_layout.addWidget(QLabel("(Placeholder - edit your subtitles here)"))
        
        # Add some demo controls that affect the preview
        controls_layout = QHBoxLayout()
        
        add_effect_btn = QPushButton("Add Glow Effect")
        add_effect_btn.clicked.connect(self._add_demo_effect)
        controls_layout.addWidget(add_effect_btn)
        
        remove_effect_btn = QPushButton("Remove Effects")
        remove_effect_btn.clicked.connect(self._remove_demo_effects)
        controls_layout.addWidget(remove_effect_btn)
        
        controls_layout.addStretch()
        editor_layout.addLayout(controls_layout)
        editor_layout.addStretch()
        
        self.tab_widget.addTab(editor_tab, "3. Editor")
        
        # Effects tab (placeholder)
        effects_tab = QWidget()
        effects_layout = QVBoxLayout(effects_tab)
        effects_layout.addWidget(QLabel("Text Effects Tab"))
        effects_layout.addWidget(QLabel("(Placeholder - configure text effects here)"))
        effects_layout.addWidget(QLabel("Effects changes are synchronized with the preview in real-time!"))
        effects_layout.addStretch()
        self.tab_widget.addTab(effects_tab, "4. Effects")
        
        # Export tab (placeholder)
        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)
        export_layout.addWidget(QLabel("Export Video Tab"))
        export_layout.addWidget(QLabel("(Placeholder - export your karaoke video here)"))
        export_layout.addStretch()
        self.tab_widget.addTab(export_tab, "5. Export")
        
    def _setup_demo_content(self):
        """Set up demo content in the preview"""
        # Create a mock project for demonstration
        try:
            # This would normally load a real project
            # For demo purposes, we'll just show the placeholder
            self.status_label.setText("Demo ready - Preview shows placeholder content")
        except Exception as e:
            self.status_label.setText(f"Demo setup: {str(e)}")
            
    def _add_demo_effect(self):
        """Add a demo effect to the preview"""
        try:
            # Demo effect parameters
            effect_params = {
                "radius": 5.0,
                "intensity": 0.8,
                "color": [1.0, 1.0, 0.0],  # Yellow glow
                "falloff": 2.0
            }
            
            self.preview_widget.add_effect("demo_glow", effect_params)
            self.status_label.setText("Added glow effect to preview")
            self.status_label.setStyleSheet("margin: 5px; color: blue;")
        except Exception as e:
            self.status_label.setText(f"Effect error: {str(e)}")
            self.status_label.setStyleSheet("margin: 5px; color: red;")
            
    def _remove_demo_effects(self):
        """Remove demo effects from preview"""
        try:
            self.preview_widget.remove_effect("demo_glow")
            self.status_label.setText("Removed effects from preview")
            self.status_label.setStyleSheet("margin: 5px; color: green;")
        except Exception as e:
            self.status_label.setText(f"Remove error: {str(e)}")
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


def main():
    """Run the detachable preview demo"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Detachable Preview Demo")
    app.setApplicationVersion("1.0.0")
    
    # Create and show demo window
    demo = DetachablePreviewDemo()
    demo.show()
    
    # Center on screen
    screen = app.primaryScreen()
    if screen:
        screen_geometry = screen.geometry()
        window_geometry = demo.geometry()
        
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        
        demo.move(x, y)
    
    print("Detachable Preview Demo")
    print("======================")
    print("• Click 'Detach' in the preview tab to open it in a separate window")
    print("• Click 'Attach' to bring it back to the main window")
    print("• Try the effect buttons to see real-time synchronization")
    print("• Close the detached window to see the reattach dialog")
    print()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())