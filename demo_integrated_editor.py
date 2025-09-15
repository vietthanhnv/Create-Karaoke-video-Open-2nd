#!/usr/bin/env python3
"""
Demo of the Integrated Editor Widget

This demo shows the new integrated editor that combines:
- Real-time video preview
- Subtitle text editing
- Timeline editing
- Effects management

All in one cohesive interface for efficient karaoke video creation.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMenuBar, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.integrated_editor_widget import IntegratedEditorWidget
from src.core.models import Project, SubtitleFile, VideoFile, AudioFile


class IntegratedEditorDemo(QMainWindow):
    """Demo application for the integrated editor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karaoke Video Creator - Integrated Editor Demo")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create integrated editor
        self.editor = IntegratedEditorWidget()
        layout.addWidget(self.editor)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Connect signals
        self._connect_signals()
        
        # Show welcome message
        self._show_welcome_message()
        
    def _create_menu_bar(self):
        """Create menu bar with file operations"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # New project
        new_action = QAction('New Project', self)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        # Open project
        open_action = QAction('Open Project...', self)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Load video
        load_video_action = QAction('Load Video...', self)
        load_video_action.triggered.connect(self._load_video)
        file_menu.addAction(load_video_action)
        
        # Load audio
        load_audio_action = QAction('Load Audio...', self)
        load_audio_action.triggered.connect(self._load_audio)
        file_menu.addAction(load_audio_action)
        
        # Load subtitles
        load_subtitles_action = QAction('Load Subtitles...', self)
        load_subtitles_action.triggered.connect(self._load_subtitles)
        file_menu.addAction(load_subtitles_action)
        
        file_menu.addSeparator()
        
        # Save subtitles
        save_subtitles_action = QAction('Save Subtitles...', self)
        save_subtitles_action.triggered.connect(self._save_subtitles)
        file_menu.addAction(save_subtitles_action)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _connect_signals(self):
        """Connect editor signals"""
        self.editor.subtitle_changed.connect(self._on_subtitle_changed)
        self.editor.timing_changed.connect(self._on_timing_changed)
        self.editor.effect_applied.connect(self._on_effect_applied)
        
    def _show_welcome_message(self):
        """Show welcome message with instructions"""
        welcome_text = """
        <h2>Welcome to the Integrated Karaoke Editor!</h2>
        
        <p>This integrated interface combines all editing tools in one place:</p>
        
        <ul>
        <li><b>Real-time Preview:</b> See your changes instantly as you edit</li>
        <li><b>Text Editor:</b> Edit subtitle content with syntax highlighting</li>
        <li><b>Timeline Editor:</b> Visually adjust subtitle timing</li>
        <li><b>Effects Editor:</b> Apply and customize text effects</li>
        </ul>
        
        <p><b>Getting Started:</b></p>
        <ol>
        <li>Use File → Load Video/Audio to add media files</li>
        <li>Use File → Load Subtitles to load existing subtitles, or start editing in the Text Editor tab</li>
        <li>Switch between tabs to edit different aspects of your karaoke video</li>
        <li>Use the preview controls to play and see your changes in real-time</li>
        </ol>
        
        <p>Try editing the sample subtitle content to see the real-time preview in action!</p>
        """
        
        QMessageBox.information(self, "Welcome", welcome_text)
        
    def _new_project(self):
        """Create a new project"""
        project = Project(
            id="demo_project",
            name="Demo Karaoke Project"
        )
        
        # Create a sample subtitle file
        sample_content = """[Script Info]
Title: Demo Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Welcome to the karaoke editor!
Dialogue: 0,0:00:03.00,0:00:06.00,Default,,0,0,0,,Edit this text to see real-time updates
Dialogue: 0,0:00:06.00,0:00:09.00,Default,,0,0,0,,Try the Timeline tab for visual editing
Dialogue: 0,0:00:09.00,0:00:12.00,Default,,0,0,0,,Use the Effects tab to add cool effects
"""
        
        # Save to temp file
        temp_path = Path("temp") / "demo_subtitles.ass"
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_text(sample_content, encoding='utf-8')
        
        project.subtitle_file = SubtitleFile(path=str(temp_path))
        
        # Load project into editor
        success = self.editor.load_project(project)
        if success:
            QMessageBox.information(self, "Success", "New project created with sample content!")
        else:
            QMessageBox.warning(self, "Error", "Failed to create new project")
            
    def _open_project(self):
        """Open an existing project (simplified for demo)"""
        QMessageBox.information(self, "Demo", "Project loading not implemented in demo. Use 'New Project' to start.")
        
    def _load_video(self):
        """Load a video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Video File", 
            "", 
            "Video Files (*.mp4 *.mov *.avi);;All Files (*)"
        )
        
        if file_path:
            # For demo, just show that it would be loaded
            QMessageBox.information(
                self, 
                "Demo", 
                f"Video file selected: {Path(file_path).name}\n\n"
                "In a full implementation, this would:\n"
                "• Load the video into the preview\n"
                "• Extract duration and frame rate\n"
                "• Enable video playback controls"
            )
            
    def _load_audio(self):
        """Load an audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Audio File", 
            "", 
            "Audio Files (*.mp3 *.wav *.aac);;All Files (*)"
        )
        
        if file_path:
            QMessageBox.information(
                self, 
                "Demo", 
                f"Audio file selected: {Path(file_path).name}\n\n"
                "In a full implementation, this would:\n"
                "• Load the audio for playback\n"
                "• Enable audio synchronization\n"
                "• Show audio waveform in timeline"
            )
            
    def _load_subtitles(self):
        """Load a subtitle file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Subtitle File", 
            "", 
            "Subtitle Files (*.ass);;All Files (*)"
        )
        
        if file_path:
            try:
                subtitle_file = SubtitleFile(path=file_path)
                self.editor.load_subtitle_file(subtitle_file)
                QMessageBox.information(self, "Success", f"Loaded subtitles from {Path(file_path).name}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load subtitles: {str(e)}")
                
    def _save_subtitles(self):
        """Save current subtitles"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Subtitle File", 
            "subtitles.ass", 
            "Subtitle Files (*.ass);;All Files (*)"
        )
        
        if file_path:
            try:
                self.editor.save_subtitle_file(file_path)
                QMessageBox.information(self, "Success", f"Subtitles saved to {Path(file_path).name}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save subtitles: {str(e)}")
                
    def _show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>Integrated Karaoke Editor Demo</h2>
        
        <p>This demo showcases the integrated editing interface that combines:</p>
        
        <ul>
        <li>Real-time video preview with OpenGL rendering</li>
        <li>Subtitle text editor with syntax highlighting</li>
        <li>Visual timeline editor for timing adjustments</li>
        <li>Effects management with real-time preview</li>
        </ul>
        
        <p>The integrated approach provides a much more efficient workflow compared to 
        separate tabs, allowing you to see the results of your edits immediately.</p>
        
        <p><b>Key Features:</b></p>
        <ul>
        <li>Real-time preview updates as you type</li>
        <li>Visual timeline editing with drag-and-drop</li>
        <li>Individual subtitle line editing</li>
        <li>Effect parameter adjustment with live preview</li>
        <li>Automatic validation and formatting</li>
        </ul>
        """
        
        QMessageBox.about(self, "About", about_text)
        
    # Signal handlers
    def _on_subtitle_changed(self, content):
        """Handle subtitle content changes"""
        print(f"Subtitle content changed: {len(content)} characters")
        
    def _on_timing_changed(self, index, start_time, end_time):
        """Handle timing changes"""
        print(f"Subtitle {index} timing changed: {start_time:.2f}s - {end_time:.2f}s")
        
    def _on_effect_applied(self, effect_id, parameters):
        """Handle effect application"""
        print(f"Effect applied: {effect_id} with parameters: {parameters}")


def main():
    """Run the integrated editor demo"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Karaoke Video Creator")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Demo")
    
    # Create and show demo window
    demo = IntegratedEditorDemo()
    demo.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()