#!/usr/bin/env python3
"""
Demo script for karaoke timing system.

This script demonstrates the word-by-word karaoke animation functionality
and aspect ratio correction in the preview system.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QImage, QColor

from core.models import Project, SubtitleFile, SubtitleLine, SubtitleStyle, WordTiming, ImageFile, AudioFile
from core.preview_synchronizer import PreviewSynchronizer
from ui.preview_widget import PreviewWidget


def create_demo_project():
    """Create a demo project with karaoke timing."""
    
    # Create word timings for karaoke effect
    word_timings_1 = [
        WordTiming("Hello", 1.0, 1.5),
        WordTiming("beautiful", 1.5, 2.2),
        WordTiming("world", 2.2, 2.8)
    ]
    
    word_timings_2 = [
        WordTiming("This", 3.0, 3.3),
        WordTiming("is", 3.3, 3.5),
        WordTiming("karaoke", 3.5, 4.2),
        WordTiming("magic", 4.2, 4.8)
    ]
    
    word_timings_3 = [
        WordTiming("Watch", 5.0, 5.4),
        WordTiming("the", 5.4, 5.6),
        WordTiming("words", 5.6, 6.0),
        WordTiming("light", 6.0, 6.4),
        WordTiming("up", 6.4, 6.8)
    ]
    
    # Create subtitle lines with karaoke timing
    subtitle_lines = [
        SubtitleLine(
            start_time=1.0,
            end_time=2.8,
            text="Hello beautiful world",
            style="Default",
            word_timings=word_timings_1
        ),
        SubtitleLine(
            start_time=3.0,
            end_time=4.8,
            text="This is karaoke magic",
            style="Default",
            word_timings=word_timings_2
        ),
        SubtitleLine(
            start_time=5.0,
            end_time=6.8,
            text="Watch the words light up",
            style="Default",
            word_timings=word_timings_3
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
        path="demo_karaoke.ass",
        format="ass",
        lines=subtitle_lines,
        styles=[subtitle_style]
    )
    
    # Create a demo image file (placeholder)
    image_file = ImageFile(
        path="demo_background.jpg",
        resolution={"width": 1920, "height": 1080},
        format="jpg"
    )
    
    # Create a demo audio file (placeholder)
    audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=8.0,
        format="mp3"
    )
    
    # Create project
    project = Project(
        id="karaoke_demo",
        name="Karaoke Demo Project",
        image_file=image_file,
        audio_file=audio_file,
        subtitle_file=subtitle_file
    )
    
    return project


class KaraokeDemoWindow(QMainWindow):
    """Demo window showing karaoke functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karaoke System Demo")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add title
        title = QLabel("Karaoke Word-by-Word Animation Demo")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Add instructions
        instructions = QLabel(
            "This demo shows word-by-word karaoke timing and aspect ratio correction.\n"
            "Click Play to see the karaoke animation in action!"
        )
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Create preview widget
        self.preview_widget = PreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # Load demo project
        self.demo_project = create_demo_project()
        
        # Initialize preview
        self._setup_preview()
        
    def _setup_preview(self):
        """Set up the preview with demo project."""
        try:
            # Load project into preview
            success = self.preview_widget.load_project(self.demo_project)
            
            if success:
                print("Demo project loaded successfully!")
                
                # Create a demo background image
                self._create_demo_background()
                
                # Connect to preview updates
                self.preview_widget.subtitle_updated.connect(self._on_subtitle_updated)
                self.preview_widget.time_changed.connect(self._on_time_changed)
                
            else:
                print("Failed to load demo project")
                
        except Exception as e:
            print(f"Error setting up preview: {e}")
            
    def _create_demo_background(self):
        """Create a demo background image."""
        # Create a gradient background image
        width, height = 1920, 1080
        image = QImage(width, height, QImage.Format.Format_RGB888)
        
        # Fill with gradient (blue to purple)
        for y in range(height):
            progress = y / height
            red = int(50 + progress * 100)
            green = int(50 + progress * 50)
            blue = int(150 + progress * 105)
            color = QColor(red, green, blue).rgb()
            
            for x in range(width):
                image.setPixel(x, y, color)
        
        # Load the background into preview
        self.preview_widget.load_video_frame(image)
        
    def _on_subtitle_updated(self, visible_subtitles):
        """Handle subtitle updates."""
        print(f"Visible subtitles: {len(visible_subtitles)}")
        
    def _on_time_changed(self, current_time, duration):
        """Handle time changes."""
        # Update window title with current time
        self.setWindowTitle(f"Karaoke Demo - {current_time:.1f}s / {duration:.1f}s")


def main():
    """Run the karaoke demo."""
    app = QApplication(sys.argv)
    
    # Create and show demo window
    demo_window = KaraokeDemoWindow()
    demo_window.show()
    
    print("Karaoke demo started!")
    print("Features demonstrated:")
    print("- Word-by-word karaoke timing")
    print("- Aspect ratio correction")
    print("- Real-time subtitle rendering")
    print("- Color animation for sung/unsung words")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()