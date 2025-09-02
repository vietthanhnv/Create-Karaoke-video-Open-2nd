#!/usr/bin/env python3
"""
Karaoke Video Creator - Main Application Entry Point
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Add current directory and src directory to Python path
current_dir = Path(__file__).parent.parent  # Go up to project root
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import MainWindow


def main():
    """Main application entry point"""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName("Karaoke Video Creator")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Karaoke Creator")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()