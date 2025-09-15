#!/usr/bin/env python3
"""
Demo of the Unified Editor Widget

This demo shows the ultimate unified interface that combines ALL editing tools
in a single window:
- Real-time video preview
- Subtitle text editing
- Visual timeline editing
- Individual subtitle editing
- Effects management
- All in one space-efficient layout

No more tabs - everything is visible and accessible at once!
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMenuBar, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.ui.unified_editor_widget import UnifiedEditorWidget
from src.core.models import Project, SubtitleFile, VideoFile, AudioFile


class UnifiedEditorDemo(QMainWindow):
    """Demo application for the unified editor"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karaoke Video Creator - Unified Editor (All-in-One)")
        self.setGeometry(50, 50, 1600, 1000)  # Larger window for unified interface
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create unified editor
        self.editor = UnifiedEditorWidget()
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
        
        # Load demo content
        demo_action = QAction('Load Demo Content', self)
        demo_action.triggered.connect(self._load_demo_content)
        file_menu.addAction(demo_action)
        
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
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        # Show layout info
        layout_info_action = QAction('Layout Information', self)
        layout_info_action.triggered.connect(self._show_layout_info)
        view_menu.addAction(layout_info_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About Unified Editor', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
        workflow_action = QAction('Workflow Guide', self)
        workflow_action.triggered.connect(self._show_workflow_guide)
        help_menu.addAction(workflow_action)
        
    def _connect_signals(self):
        """Connect editor signals"""
        self.editor.subtitle_changed.connect(self._on_subtitle_changed)
        self.editor.timing_changed.connect(self._on_timing_changed)
        self.editor.effect_applied.connect(self._on_effect_applied)
        
    def _show_welcome_message(self):
        """Show welcome message with unified editor features"""
        welcome_text = """
        <h2>🎵 Welcome to the Unified Karaoke Editor! 🎵</h2>
        
        <p><b>Everything in One Place - No More Tab Switching!</b></p>
        
        <p>This unified interface combines ALL editing tools in a single, efficient layout:</p>
        
        <table border="1" cellpadding="5" style="border-collapse: collapse;">
        <tr><th>Left Panel (Preview)</th><th>Right Panel (Editing)</th></tr>
        <tr>
        <td>
        • <b>Real-time Video Preview</b><br>
        • <b>Playback Controls</b><br>
        • <b>Current Subtitle Display</b><br>
        • <b>Karaoke Highlighting</b>
        </td>
        <td>
        • <b>Text Editor</b> (compact, syntax highlighted)<br>
        • <b>Visual Timeline</b> (drag-and-drop timing)<br>
        • <b>Individual Subtitle Editor</b><br>
        • <b>Effects Management</b> (presets & parameters)<br>
        • <b>Validation & Status</b>
        </td>
        </tr>
        </table>
        
        <p><b>🚀 Key Benefits:</b></p>
        <ul>
        <li><b>Instant Feedback:</b> See changes immediately as you edit</li>
        <li><b>No Context Switching:</b> All tools visible simultaneously</li>
        <li><b>Space Efficient:</b> Compact layout maximizes screen usage</li>
        <li><b>Streamlined Workflow:</b> Edit text → Adjust timing → Apply effects → See results</li>
        </ul>
        
        <p><b>🎯 Quick Start:</b></p>
        <ol>
        <li>Click "File → Load Demo Content" to see the unified editor in action</li>
        <li>Edit text in the Text Editor (top right) - see instant preview</li>
        <li>Drag subtitle blocks in the Timeline (middle right) for timing</li>
        <li>Select a subtitle and edit details in Individual Editor (bottom left)</li>
        <li>Add effects and adjust parameters (bottom right) with live preview</li>
        </ol>
        
        <p><i>Try editing now - everything updates in real-time!</i></p>
        """
        
        QMessageBox.information(self, "Unified Editor", welcome_text)
        
    def _new_project(self):
        """Create a new project"""
        project = Project(
            id="unified_demo_project",
            name="Unified Editor Demo Project"
        )
        
        # Create minimal sample content
        sample_content = """[Script Info]
Title: Unified Editor Demo
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,,0,0,0,,Edit this text and see instant preview!
Dialogue: 0,0:00:03.00,0:00:06.00,Default,,0,0,0,,Try the timeline for visual timing
"""
        
        # Save to temp file
        temp_path = Path("temp") / "unified_demo.ass"
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_text(sample_content, encoding='utf-8')
        
        project.subtitle_file = SubtitleFile(path=str(temp_path))
        
        # Load project
        success = self.editor.load_project(project)
        if success:
            QMessageBox.information(self, "Success", "New project created! Try editing the text to see real-time updates.")
        else:
            QMessageBox.warning(self, "Error", "Failed to create new project")
            
    def _load_demo_content(self):
        """Load comprehensive demo content"""
        project = Project(
            id="comprehensive_demo",
            name="Comprehensive Unified Editor Demo"
        )
        
        # Create rich demo content
        demo_content = """[Script Info]
Title: Comprehensive Karaoke Demo
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1
Style: Chorus,Arial,28,&H0000FFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:04.00,Default,,0,0,0,,Welcome to the unified karaoke editor
Dialogue: 0,0:00:04.00,0:00:08.00,Default,,0,0,0,,All editing tools in one interface
Dialogue: 0,0:00:08.00,0:00:12.00,Chorus,,0,0,0,,No more switching between tabs!
Dialogue: 0,0:00:12.00,0:00:16.00,Default,,0,0,0,,Edit text and see instant preview
Dialogue: 0,0:00:16.00,0:00:20.00,Default,,0,0,0,,Drag timeline blocks for timing
Dialogue: 0,0:00:20.00,0:00:24.00,Chorus,,0,0,0,,Add effects with live feedback
Dialogue: 0,0:00:24.00,0:00:28.00,Default,,0,0,0,,Everything updates in real-time
Dialogue: 0,0:00:28.00,0:00:32.00,Default,,0,0,0,,This is the future of karaoke editing!
"""
        
        # Save demo content
        temp_path = Path("temp") / "comprehensive_demo.ass"
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_text(demo_content, encoding='utf-8')
        
        project.subtitle_file = SubtitleFile(path=str(temp_path))
        
        # Load project
        success = self.editor.load_project(project)
        if success:
            QMessageBox.information(
                self, 
                "Demo Loaded!", 
                "Comprehensive demo content loaded!\n\n"
                "Try these features:\n"
                "• Edit text in the Text Editor (top right)\n"
                "• Drag subtitle blocks in Timeline (middle right)\n"
                "• Select subtitles to edit individually (bottom left)\n"
                "• Add effects and adjust parameters (bottom right)\n"
                "• Use playback controls to see karaoke highlighting\n\n"
                "Everything updates in real-time!"
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to load demo content")
            
    def _load_video(self):
        """Load a video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Video File", 
            "", 
            "Video Files (*.mp4 *.mov *.avi);;All Files (*)"
        )
        
        if file_path:
            QMessageBox.information(
                self, 
                "Video Loading", 
                f"Video selected: {Path(file_path).name}\n\n"
                "In the unified editor, video would:\n"
                "• Display in the preview panel (left)\n"
                "• Enable synchronized playback\n"
                "• Show video frames with subtitle overlay\n"
                "• Allow scrubbing through timeline\n\n"
                "The unified layout keeps video preview always visible\n"
                "while you edit subtitles and effects!"
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
                "Audio Loading", 
                f"Audio selected: {Path(file_path).name}\n\n"
                "In the unified editor, audio would:\n"
                "• Enable synchronized playback with subtitles\n"
                "• Show waveform in timeline (future feature)\n"
                "• Allow precise timing adjustments\n"
                "• Provide audio feedback during editing\n\n"
                "The unified layout lets you hear audio while\n"
                "editing text and effects simultaneously!"
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
                QMessageBox.information(
                    self, 
                    "Subtitles Loaded", 
                    f"Loaded: {Path(file_path).name}\n\n"
                    "Notice how the unified editor immediately shows:\n"
                    "• Text content in the editor (top right)\n"
                    "• Visual timeline blocks (middle right)\n"
                    "• Validation status (bottom)\n"
                    "• Ready for real-time editing!"
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to load subtitles: {str(e)}")
                
    def _save_subtitles(self):
        """Save current subtitles"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Subtitle File", 
            "unified_karaoke.ass", 
            "Subtitle Files (*.ass);;All Files (*)"
        )
        
        if file_path:
            try:
                self.editor.save_subtitle_file(file_path)
                QMessageBox.information(
                    self, 
                    "Saved Successfully", 
                    f"Subtitles saved: {Path(file_path).name}\n\n"
                    "The unified editor makes saving efficient:\n"
                    "• All changes are already validated\n"
                    "• Real-time preview ensures accuracy\n"
                    "• No need to switch views to verify content"
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save subtitles: {str(e)}")
                
    def _show_layout_info(self):
        """Show layout information"""
        layout_info = """
        <h2>🎛️ Unified Editor Layout</h2>
        
        <p><b>Space-Efficient Design:</b></p>
        
        <table border="1" cellpadding="8" style="border-collapse: collapse;">
        <tr><th colspan="2" style="background-color: #f0f0f0;">Main Layout (50/50 Split)</th></tr>
        <tr>
        <td><b>Left Panel: Preview (50%)</b><br>
        • OpenGL Video Display<br>
        • Playback Controls<br>
        • Current Subtitle Display<br>
        • Always visible during editing
        </td>
        <td><b>Right Panel: Editing Tools (50%)</b><br>
        • Text Editor (40% height)<br>
        • Timeline Editor (30% height)<br>
        • Individual + Effects (30% height)
        </td>
        </tr>
        </table>
        
        <p><b>🎯 Compact Components:</b></p>
        <ul>
        <li><b>Text Editor:</b> Limited to 200px height with scrolling</li>
        <li><b>Timeline:</b> Compact 120px height with horizontal scroll</li>
        <li><b>Effects List:</b> 80px height for applied effects</li>
        <li><b>Parameters:</b> 100px scrollable area for effect controls</li>
        <li><b>Status Bar:</b> Single line validation and status</li>
        </ul>
        
        <p><b>🔄 Real-time Updates:</b></p>
        <ul>
        <li>Text changes → Timeline + Preview update (200ms debounce)</li>
        <li>Timeline changes → Text + Individual editor update</li>
        <li>Individual changes → Text + Timeline update</li>
        <li>Effect changes → Preview update immediately</li>
        </ul>
        
        <p><i>Every pixel is optimized for maximum productivity!</i></p>
        """
        
        QMessageBox.information(self, "Layout Information", layout_info)
        
    def _show_workflow_guide(self):
        """Show workflow guide"""
        workflow_guide = """
        <h2>🚀 Unified Editor Workflow Guide</h2>
        
        <p><b>Efficient Karaoke Creation Workflow:</b></p>
        
        <p><b>1. 📝 Text Editing (Top Right)</b></p>
        <ul>
        <li>Edit subtitle content with syntax highlighting</li>
        <li>Use "Add Line" button for new subtitles</li>
        <li>Auto-format fixes common issues</li>
        <li>Validation shows errors immediately</li>
        </ul>
        
        <p><b>2. ⏱️ Timing Adjustment (Middle Right)</b></p>
        <ul>
        <li>Drag subtitle blocks to adjust timing</li>
        <li>Resize blocks by dragging edges</li>
        <li>Visual representation syncs with preview</li>
        <li>Precise timing with individual editor</li>
        </ul>
        
        <p><b>3. 🎯 Individual Editing (Bottom Left)</b></p>
        <ul>
        <li>Select subtitle from timeline</li>
        <li>Edit start/end times precisely</li>
        <li>Modify text and style properties</li>
        <li>Changes update text editor and timeline</li>
        </ul>
        
        <p><b>4. ✨ Effects Management (Bottom Right)</b></p>
        <ul>
        <li>Choose from preset combinations</li>
        <li>Add individual effects (glow, outline, etc.)</li>
        <li>Adjust parameters with live preview</li>
        <li>Layer multiple effects for rich appearance</li>
        </ul>
        
        <p><b>5. 👁️ Real-time Preview (Left Panel)</b></p>
        <ul>
        <li>See all changes immediately</li>
        <li>Use playback controls to test timing</li>
        <li>Current subtitle display shows active text</li>
        <li>Karaoke highlighting for word timing</li>
        </ul>
        
        <p><b>🎵 Pro Tips:</b></p>
        <ul>
        <li><b>Start with text:</b> Write all lyrics first</li>
        <li><b>Rough timing:</b> Use timeline for approximate timing</li>
        <li><b>Fine-tune:</b> Use individual editor for precision</li>
        <li><b>Add effects:</b> Apply effects after timing is set</li>
        <li><b>Preview often:</b> Use playback to verify results</li>
        </ul>
        
        <p><i>The unified layout eliminates context switching for maximum flow!</i></p>
        """
        
        QMessageBox.information(self, "Workflow Guide", workflow_guide)
        
    def _show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>🎵 Unified Karaoke Editor 🎵</h2>
        
        <p><b>The Ultimate All-in-One Karaoke Creation Interface</b></p>
        
        <p>This unified editor represents the pinnacle of karaoke video creation efficiency by combining ALL editing tools in a single, optimized interface.</p>
        
        <p><b>🌟 Revolutionary Features:</b></p>
        <ul>
        <li><b>Zero Tab Switching:</b> Everything visible simultaneously</li>
        <li><b>Real-time Feedback:</b> Instant preview of all changes</li>
        <li><b>Space Optimization:</b> Maximum tools in minimum space</li>
        <li><b>Workflow Integration:</b> Seamless tool interaction</li>
        <li><b>Professional Results:</b> Studio-quality karaoke videos</li>
        </ul>
        
        <p><b>🎯 Design Philosophy:</b></p>
        <ul>
        <li><b>Efficiency First:</b> Minimize clicks and context switches</li>
        <li><b>Visual Feedback:</b> See results immediately</li>
        <li><b>Compact Layout:</b> Fit more tools in less space</li>
        <li><b>Intuitive Flow:</b> Natural editing progression</li>
        </ul>
        
        <p><b>🚀 Technical Excellence:</b></p>
        <ul>
        <li><b>OpenGL Rendering:</b> Hardware-accelerated preview</li>
        <li><b>Debounced Updates:</b> Smooth performance during editing</li>
        <li><b>Signal Architecture:</b> Proper component communication</li>
        <li><b>Memory Efficient:</b> Optimized for large projects</li>
        </ul>
        
        <p><b>🎪 Perfect For:</b></p>
        <ul>
        <li>Professional karaoke video production</li>
        <li>Content creators and YouTubers</li>
        <li>Music educators and trainers</li>
        <li>Event organizers and DJs</li>
        <li>Anyone who wants efficient subtitle editing</li>
        </ul>
        
        <p><i>Experience the future of karaoke video creation!</i></p>
        
        <p style="text-align: center; margin-top: 20px;">
        <b>Version 1.0 - Unified Editor Demo</b><br>
        Built with PyQt6, OpenGL, and lots of ❤️
        </p>
        """
        
        QMessageBox.about(self, "About Unified Editor", about_text)
        
    # Signal handlers
    def _on_subtitle_changed(self, content):
        """Handle subtitle content changes"""
        print(f"Unified Editor: Subtitle content changed ({len(content)} characters)")
        
    def _on_timing_changed(self, index, start_time, end_time):
        """Handle timing changes"""
        print(f"Unified Editor: Subtitle {index} timing: {start_time:.2f}s - {end_time:.2f}s")
        
    def _on_effect_applied(self, effect_id, parameters):
        """Handle effect application"""
        print(f"Unified Editor: Effect {effect_id} applied with {len(parameters)} parameters")


def main():
    """Run the unified editor demo"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Unified Karaoke Editor")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Demo")
    
    # Create and show demo window
    demo = UnifiedEditorDemo()
    demo.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()