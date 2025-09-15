"""
Integrated Editor Widget - Combines Preview, Subtitle Editing, and Effects
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QSplitter, QFrame, QPushButton, QScrollArea,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QApplication,
    QSlider, QCheckBox, QTabWidget, QComboBox, QColorDialog,
    QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint, QSize
from PyQt6.QtGui import (
    QFont, QTextCharFormat, QColor, QPainter, QPen, QBrush,
    QSyntaxHighlighter, QTextDocument, QMouseEvent, QPaintEvent,
    QImage, QPixmap
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
import re
from typing import List, Optional, Tuple, Dict

try:
    from ..core.models import SubtitleFile, SubtitleLine, SubtitleStyle, Project
    from ..core.subtitle_parser import AssParser, ParseError
    from ..core.preview_synchronizer import PreviewSynchronizer
    from ..core.effects_manager import EffectsManager, EffectType, EffectLayer
    from ..core.opengl_subtitle_renderer import RenderedSubtitle
    from .preview_widget import OpenGLVideoWidget
    from .editor_widget import AssHighlighter, TimelineWidget
except ImportError:
    from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle, Project
    from src.core.subtitle_parser import AssParser, ParseError
    from src.core.preview_synchronizer import PreviewSynchronizer
    from src.core.effects_manager import EffectsManager, EffectType, EffectLayer
    from src.core.opengl_subtitle_renderer import RenderedSubtitle
    from src.ui.preview_widget import OpenGLVideoWidget
    from src.ui.editor_widget import AssHighlighter, TimelineWidget


class IntegratedEditorWidget(QWidget):
    """Integrated widget combining preview, subtitle editing, and effects"""
    
    # Signals for external communication
    subtitle_changed = pyqtSignal(str)
    timing_changed = pyqtSignal(int, float, float)
    subtitle_selected = pyqtSignal(int)
    validation_updated = pyqtSignal(list)
    effect_applied = pyqtSignal(str, dict)
    effect_removed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.parser = AssParser()
        self.synchronizer = PreviewSynchronizer()
        self.effects_manager = EffectsManager()
        
        # State management
        self.current_project: Optional[Project] = None
        self.current_subtitle_file: Optional[SubtitleFile] = None
        self.selected_subtitle_index = -1
        self.is_playing = False
        self.current_time = 0.0
        
        # Timers for debouncing updates
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_content)
        
        self.preview_update_timer = QTimer()
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.timeout.connect(self._update_realtime_preview)
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the integrated editor UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Karaoke Video Editor")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Main content area with splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel: Preview and playback controls
        self._create_preview_panel(main_splitter)
        
        # Right panel: Editing interface
        self._create_editing_panel(main_splitter)
        
        # Set initial splitter proportions (60% preview, 40% editing)
        main_splitter.setSizes([600, 400])
        
    def _create_preview_panel(self, parent_splitter):
        """Create the preview panel with video display and controls"""
        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        
        # Preview area
        preview_group = QGroupBox("Real-time Preview")
        preview_group_layout = QVBoxLayout(preview_group)
        
        # OpenGL video widget
        self.opengl_widget = OpenGLVideoWidget()
        self.opengl_widget.setMinimumSize(640, 360)
        preview_group_layout.addWidget(self.opengl_widget)
        
        # Placeholder for when no video is loaded
        self.placeholder_label = QLabel("Load a project to see preview")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(
            "color: #666; font-size: 16px; font-style: italic;"
        )
        preview_group_layout.addWidget(self.placeholder_label)
        
        preview_layout.addWidget(preview_group)
        
        # Playback controls
        self._create_playback_controls(preview_layout)
        
        # Current subtitle display
        self._create_current_subtitle_display(preview_layout)
        
        parent_splitter.addWidget(preview_frame)
        
    def _create_playback_controls(self, parent_layout):
        """Create playback control interface"""
        controls_group = QGroupBox("Playback Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Timeline slider
        timeline_layout = QHBoxLayout()
        
        self.time_label_start = QLabel("00:00")
        timeline_layout.addWidget(self.time_label_start)
        
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(100)
        self.timeline_slider.setValue(0)
        self.timeline_slider.valueChanged.connect(self._on_timeline_seek)
        timeline_layout.addWidget(self.timeline_slider)
        
        self.time_label_end = QLabel("00:00")
        timeline_layout.addWidget(self.time_label_end)
        
        controls_layout.addLayout(timeline_layout)
        
        # Playback buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_playback)
        buttons_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._stop_playback)
        buttons_layout.addWidget(self.stop_button)
        
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)
        
        parent_layout.addWidget(controls_group)
        
    def _create_current_subtitle_display(self, parent_layout):
        """Create display for currently active subtitles"""
        current_group = QGroupBox("Current Subtitles")
        current_layout = QVBoxLayout(current_group)
        
        self.current_subtitle_label = QLabel("No active subtitles")
        self.current_subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_subtitle_label.setStyleSheet(
            "background-color: #2a2a2a; "
            "color: #ffff64; "
            "padding: 15px; "
            "border: 2px solid #444; "
            "border-radius: 5px; "
            "font-size: 14px; "
            "font-weight: bold; "
            "min-height: 60px;"
        )
        current_layout.addWidget(self.current_subtitle_label)
        
        parent_layout.addWidget(current_group)
        
    def _create_editing_panel(self, parent_splitter):
        """Create the editing panel with tabs for different editing modes"""
        editing_frame = QFrame()
        editing_layout = QVBoxLayout(editing_frame)
        
        # Tabbed interface for different editing modes
        self.editing_tabs = QTabWidget()
        
        # Tab 1: Subtitle Text Editor
        self._create_text_editor_tab()
        
        # Tab 2: Timeline Editor
        self._create_timeline_editor_tab()
        
        # Tab 3: Effects Editor
        self._create_effects_editor_tab()
        
        editing_layout.addWidget(self.editing_tabs)
        
        # Validation and status area
        self._create_validation_area(editing_layout)
        
        parent_splitter.addWidget(editing_frame)
        
    def _create_text_editor_tab(self):
        """Create the text editor tab"""
        text_tab = QWidget()
        text_layout = QVBoxLayout(text_tab)
        
        # Text editor with syntax highlighting
        editor_label = QLabel("Subtitle Text (.ass format)")
        editor_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        text_layout.addWidget(editor_label)
        
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Consolas", 10))
        
        # Set up syntax highlighter
        self.highlighter = AssHighlighter(self.text_editor.document())
        
        # Default content
        default_content = (
            "[Script Info]\n"
            "Title: Karaoke Subtitles\n"
            "ScriptType: v4.00+\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            "Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,Sample subtitle text here\n"
        )
        
        self.text_editor.setPlainText(default_content)
        self.text_editor.textChanged.connect(self._on_text_changed)
        text_layout.addWidget(self.text_editor)
        
        # Quick edit controls
        quick_edit_layout = QHBoxLayout()
        
        add_line_button = QPushButton("Add Line")
        add_line_button.clicked.connect(self._add_subtitle_line)
        quick_edit_layout.addWidget(add_line_button)
        
        format_button = QPushButton("Auto Format")
        format_button.clicked.connect(self._auto_format_text)
        quick_edit_layout.addWidget(format_button)
        
        quick_edit_layout.addStretch()
        text_layout.addLayout(quick_edit_layout)
        
        self.editing_tabs.addTab(text_tab, "Text Editor")
        
    def _create_timeline_editor_tab(self):
        """Create the timeline editor tab"""
        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        
        # Timeline widget
        timeline_label = QLabel("Subtitle Timeline")
        timeline_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        timeline_layout.addWidget(timeline_label)
        
        # Timeline with scroll area
        timeline_scroll = QScrollArea()
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        timeline_scroll.setMinimumHeight(200)
        
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.subtitle_selected.connect(self._on_timeline_subtitle_selected)
        self.timeline_widget.timing_changed.connect(self._on_timeline_timing_changed)
        
        timeline_scroll.setWidget(self.timeline_widget)
        timeline_scroll.setWidgetResizable(True)
        timeline_layout.addWidget(timeline_scroll)
        
        # Individual subtitle editor
        self._create_individual_subtitle_editor(timeline_layout)
        
        self.editing_tabs.addTab(timeline_tab, "Timeline")
        
    def _create_individual_subtitle_editor(self, parent_layout):
        """Create editor for individual subtitle properties"""
        editor_group = QGroupBox("Edit Selected Subtitle")
        editor_layout = QFormLayout(editor_group)
        
        # Start time
        self.start_time_editor = QDoubleSpinBox()
        self.start_time_editor.setRange(0.0, 9999.0)
        self.start_time_editor.setDecimals(2)
        self.start_time_editor.setSuffix(" s")
        self.start_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("Start Time:", self.start_time_editor)
        
        # End time
        self.end_time_editor = QDoubleSpinBox()
        self.end_time_editor.setRange(0.0, 9999.0)
        self.end_time_editor.setDecimals(2)
        self.end_time_editor.setSuffix(" s")
        self.end_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("End Time:", self.end_time_editor)
        
        # Text
        self.line_text_editor = QLineEdit()
        self.line_text_editor.textChanged.connect(self._on_individual_text_changed)
        editor_layout.addRow("Text:", self.line_text_editor)
        
        # Style
        self.style_editor = QLineEdit()
        self.style_editor.setText("Default")
        self.style_editor.textChanged.connect(self._on_individual_style_changed)
        editor_layout.addRow("Style:", self.style_editor)
        
        parent_layout.addWidget(editor_group)
        
    def _create_effects_editor_tab(self):
        """Create the effects editor tab"""
        effects_tab = QWidget()
        effects_layout = QHBoxLayout(effects_tab)
        
        # Left side: Effects library
        effects_library = self._create_effects_library()
        effects_layout.addWidget(effects_library)
        
        # Right side: Effect parameters
        effects_params = self._create_effects_parameters()
        effects_layout.addWidget(effects_params)
        
        self.editing_tabs.addTab(effects_tab, "Effects")
        
    def _create_effects_library(self):
        """Create effects library section"""
        library_group = QGroupBox("Effects Library")
        library_layout = QVBoxLayout(library_group)
        
        # Presets
        presets_label = QLabel("Presets:")
        library_layout.addWidget(presets_label)
        
        self.presets_combo = QComboBox()
        self.presets_combo.addItem("Select Preset...")
        for preset_name in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_name)
            self.presets_combo.addItem(preset_info.name, preset_name)
        self.presets_combo.currentTextChanged.connect(self._on_preset_selected)
        library_layout.addWidget(self.presets_combo)
        
        # Available effects
        effects_label = QLabel("Available Effects:")
        library_layout.addWidget(effects_label)
        
        self.effects_list = QListWidget()
        effect_items = [
            ("Glow Effect", EffectType.GLOW.value),
            ("Outline Effect", EffectType.OUTLINE.value),
            ("Shadow Effect", EffectType.SHADOW.value),
            ("Fade In/Out", EffectType.FADE.value),
            ("Bounce Animation", EffectType.BOUNCE.value),
            ("Color Transition", EffectType.COLOR_TRANSITION.value),
            ("Wave Animation", EffectType.WAVE.value)
        ]
        
        for display_name, effect_type in effect_items:
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, effect_type)
            self.effects_list.addItem(item)
        
        self.effects_list.currentItemChanged.connect(self._on_available_effect_selected)
        library_layout.addWidget(self.effects_list)
        
        # Add effect button
        self.add_effect_button = QPushButton("Add Effect")
        self.add_effect_button.clicked.connect(self._add_effect)
        self.add_effect_button.setEnabled(False)
        library_layout.addWidget(self.add_effect_button)
        
        # Applied effects
        applied_label = QLabel("Applied Effects:")
        library_layout.addWidget(applied_label)
        
        self.applied_effects_list = QListWidget()
        self.applied_effects_list.currentItemChanged.connect(self._on_applied_effect_selected)
        library_layout.addWidget(self.applied_effects_list)
        
        # Effect control buttons
        buttons_layout = QGridLayout()
        
        self.remove_effect_button = QPushButton("Remove")
        self.remove_effect_button.clicked.connect(self._remove_effect)
        self.remove_effect_button.setEnabled(False)
        buttons_layout.addWidget(self.remove_effect_button, 0, 0)
        
        self.toggle_effect_button = QPushButton("Toggle")
        self.toggle_effect_button.clicked.connect(self._toggle_effect)
        self.toggle_effect_button.setEnabled(False)
        buttons_layout.addWidget(self.toggle_effect_button, 0, 1)
        
        library_layout.addLayout(buttons_layout)
        
        return library_group
        
    def _create_effects_parameters(self):
        """Create effects parameters section"""
        params_group = QGroupBox("Effect Parameters")
        params_layout = QVBoxLayout(params_group)
        
        # Parameters scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.params_container = QWidget()
        self.params_layout = QGridLayout(self.params_container)
        
        # Default message
        default_label = QLabel("Select an effect to adjust parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.params_layout.addWidget(default_label, 0, 0)
        
        scroll_area.setWidget(self.params_container)
        params_layout.addWidget(scroll_area)
        
        return params_group
        
    def _create_validation_area(self, parent_layout):
        """Create validation and status area"""
        validation_group = QGroupBox("Status & Validation")
        validation_layout = QVBoxLayout(validation_group)
        
        # Status display
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        validation_layout.addWidget(self.status_label)
        
        # Validation display
        self.validation_display = QTextEdit()
        self.validation_display.setMaximumHeight(80)
        self.validation_display.setReadOnly(True)
        self.validation_display.setPlainText("Validation results will appear here...")
        validation_layout.addWidget(self.validation_display)
        
        parent_layout.addWidget(validation_group)
        
    def _connect_signals(self):
        """Connect internal signals for real-time updates"""
        # Connect synchronizer signals
        self.synchronizer.frame_updated.connect(self._on_frame_updated)
        self.synchronizer.time_position_changed.connect(self._on_time_position_changed)
        self.synchronizer.playback_state_changed.connect(self._on_playback_state_changed)
        self.synchronizer.subtitle_updated.connect(self._on_subtitle_updated)
        
        # Connect text changes to real-time updates
        self.text_editor.textChanged.connect(self._schedule_preview_update)
        
    def load_project(self, project: Project):
        """Load a project into the integrated editor"""
        self.current_project = project
        
        # Load into synchronizer for preview
        success = self.synchronizer.load_project(project)
        
        if success:
            # Load subtitle file into text editor
            if project.subtitle_file:
                self.load_subtitle_file(project.subtitle_file)
            
            # Update UI state
            self.placeholder_label.hide()
            duration = self.synchronizer.get_duration()
            self.time_label_end.setText(self._format_time(duration))
            
            # Seek to beginning to show first frame
            self.synchronizer.seek_to_time(0.0)
            
            self.status_label.setText("Project loaded successfully")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Failed to load project")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
        return success
        
    def load_subtitle_file(self, subtitle_file: SubtitleFile):
        """Load subtitle file into the editor"""
        self.current_subtitle_file = subtitle_file
        
        try:
            with open(subtitle_file.path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            self.text_editor.setPlainText(content)
            self._update_timeline_and_list()
            self._validate_content()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load subtitle file: {str(e)}")
            
    def _on_text_changed(self):
        """Handle text editor changes"""
        # Schedule validation
        self.validation_timer.start(500)
        
        # Update timeline and list
        self._update_timeline_and_list()
        
        # Schedule preview update
        self._schedule_preview_update()
        
    def _update_timeline_and_list(self):
        """Update timeline widget from current text content"""
        try:
            content = self.text_editor.toPlainText()
            
            # Parse content
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                parsed_file = self.parser.parse_file(temp_path)
                self.timeline_widget.set_subtitle_lines(parsed_file.lines)
                
                # Store parsed lines for other operations
                self.parsed_lines = parsed_file.lines
                
            except Exception as e:
                print(f"Parse error: {e}")
            finally:
                import os
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Timeline update error: {e}")
            
    def _schedule_preview_update(self):
        """Schedule a preview update with debouncing"""
        self.preview_update_timer.start(200)
        
    def _update_realtime_preview(self):
        """Update the real-time preview with current subtitle content"""
        if not self.synchronizer or not hasattr(self, 'parsed_lines'):
            return
            
        try:
            # Update synchronizer with new subtitle content
            if hasattr(self, 'parsed_lines'):
                # Create a simple style dict
                styles = {"Default": SubtitleStyle(
                    name="Default",
                    font_name="Arial",
                    font_size=20,
                    primary_color=[1.0, 1.0, 1.0, 1.0],
                    secondary_color=[0.0, 0.0, 1.0, 1.0],
                    outline_color=[0.0, 0.0, 0.0, 1.0],
                    back_color=[0.5, 0.0, 0.0, 0.5]
                )}
                
                self.synchronizer.update_subtitles(self.parsed_lines, styles)
                
        except Exception as e:
            print(f"Preview update error: {e}")
            
    def _validate_content(self):
        """Validate the current subtitle content"""
        try:
            content = self.text_editor.toPlainText()
            
            # Basic validation
            errors = []
            
            # Check for required sections
            if "[Script Info]" not in content:
                errors.append("Missing [Script Info] section")
            if "[V4+ Styles]" not in content:
                errors.append("Missing [V4+ Styles] section")
            if "[Events]" not in content:
                errors.append("Missing [Events] section")
                
            # Try parsing
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                parsed_file = self.parser.parse_file(temp_path)
                if not errors:
                    self.validation_display.setPlainText("✓ Subtitle format is valid")
                    self.validation_display.setStyleSheet("color: green;")
                else:
                    self.validation_display.setPlainText("⚠ " + "; ".join(errors))
                    self.validation_display.setStyleSheet("color: orange;")
            except Exception as e:
                errors.append(f"Parse error: {str(e)}")
                self.validation_display.setPlainText("✗ " + "; ".join(errors))
                self.validation_display.setStyleSheet("color: red;")
            finally:
                import os
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            self.validation_display.setPlainText(f"Validation error: {str(e)}")
            self.validation_display.setStyleSheet("color: red;")
            
    # Playback control methods
    def _toggle_playback(self):
        """Toggle play/pause"""
        if self.is_playing:
            self.synchronizer.pause()
        else:
            self.synchronizer.play()
            
    def _stop_playback(self):
        """Stop playback"""
        self.synchronizer.stop()
        self.synchronizer.seek_to_time(0.0)
        
    def _on_timeline_seek(self, value):
        """Handle timeline slider changes"""
        if self.synchronizer:
            duration = self.synchronizer.get_duration()
            position = (value / 100.0) * duration
            self.synchronizer.seek_to_time(position)
            
    # Synchronizer event handlers
    def _on_frame_updated(self, frame: QImage, timestamp: float):
        """Handle frame updates from synchronizer"""
        if frame and not frame.isNull():
            self.opengl_widget.load_frame(frame)
            self.placeholder_label.hide()
            
    def _on_time_position_changed(self, current_time: float, duration: float):
        """Handle time position changes"""
        self.current_time = current_time
        
        # Update timeline slider
        if duration > 0:
            progress = int((current_time / duration) * 100)
            self.timeline_slider.setValue(progress)
            
        # Update time labels
        self.time_label_start.setText(self._format_time(current_time))
        self.time_label_end.setText(self._format_time(duration))
        
    def _on_playback_state_changed(self, is_playing: bool):
        """Handle playback state changes"""
        self.is_playing = is_playing
        self.play_button.setText("Pause" if is_playing else "Play")
        
    def _on_subtitle_updated(self, visible_subtitles: List[RenderedSubtitle]):
        """Handle subtitle updates from synchronizer"""
        if visible_subtitles:
            # Show current subtitles
            subtitle_texts = [sub.text for sub in visible_subtitles]
            display_text = "<br>".join(subtitle_texts)
            self.current_subtitle_label.setText(display_text)
        else:
            self.current_subtitle_label.setText("No active subtitles")
            
    # Timeline editor methods
    def _on_timeline_subtitle_selected(self, index: int):
        """Handle subtitle selection from timeline"""
        self.selected_subtitle_index = index
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            line = self.parsed_lines[index]
            
            # Update individual editors
            self.start_time_editor.setValue(line.start_time)
            self.end_time_editor.setValue(line.end_time)
            self.line_text_editor.setText(line.text)
            self.style_editor.setText(line.style)
            
        self.subtitle_selected.emit(index)
        
    def _on_timeline_timing_changed(self, index: int, start_time: float, end_time: float):
        """Handle timing changes from timeline"""
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            # Update the parsed line
            self.parsed_lines[index].start_time = start_time
            self.parsed_lines[index].end_time = end_time
            
            # Update text editor content
            self._update_text_from_parsed_lines()
            
            # Update individual editors if this line is selected
            if index == self.selected_subtitle_index:
                self.start_time_editor.setValue(start_time)
                self.end_time_editor.setValue(end_time)
                
        self.timing_changed.emit(index, start_time, end_time)
        
    def _on_individual_timing_changed(self):
        """Handle timing changes from individual editors"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                line = self.parsed_lines[index]
                line.start_time = self.start_time_editor.value()
                line.end_time = self.end_time_editor.value()
                
                # Update text editor and timeline
                self._update_text_from_parsed_lines()
                self.timeline_widget.set_subtitle_lines(self.parsed_lines)
                
    def _on_individual_text_changed(self):
        """Handle text changes from individual editor"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                self.parsed_lines[index].text = self.line_text_editor.text()
                self._update_text_from_parsed_lines()
                
    def _on_individual_style_changed(self):
        """Handle style changes from individual editor"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                self.parsed_lines[index].style = self.style_editor.text()
                self._update_text_from_parsed_lines()
                
    def _update_text_from_parsed_lines(self):
        """Update text editor content from parsed lines"""
        if not hasattr(self, 'parsed_lines'):
            return
            
        # Reconstruct ASS content
        content_lines = [
            "[Script Info]",
            "Title: Karaoke Subtitles",
            "ScriptType: v4.00+",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]
        
        # Add dialogue lines
        for line in self.parsed_lines:
            start_str = self._format_ass_time(line.start_time)
            end_str = self._format_ass_time(line.end_time)
            dialogue = f"Dialogue: 0,{start_str},{end_str},{line.style},,0,0,0,,{line.text}"
            content_lines.append(dialogue)
            
        # Update text editor (temporarily disconnect signal to avoid recursion)
        self.text_editor.textChanged.disconnect()
        self.text_editor.setPlainText("\n".join(content_lines))
        self.text_editor.textChanged.connect(self._on_text_changed)
        
        # Schedule preview update
        self._schedule_preview_update()
        
    # Effects methods
    def _on_available_effect_selected(self, current, previous):
        """Handle effect selection from library"""
        self.add_effect_button.setEnabled(current is not None)
        
    def _on_applied_effect_selected(self, current, previous):
        """Handle applied effect selection"""
        if current is None:
            self._clear_effect_parameters()
            return
            
        effect_id = current.data(Qt.ItemDataRole.UserRole)
        layer = self.effects_manager.get_effect_layer(effect_id)
        if layer:
            self._show_effect_parameters(layer)
            
    def _on_preset_selected(self, preset_display_name):
        """Handle preset selection"""
        if preset_display_name == "Select Preset...":
            return
            
        # Apply preset and refresh UI
        for preset_key in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_key)
            if preset_info.name == preset_display_name:
                self.effects_manager.apply_preset(preset_key)
                self._refresh_applied_effects()
                self._schedule_preview_update()
                break
                
    def _add_effect(self):
        """Add selected effect"""
        current_item = self.effects_list.currentItem()
        if not current_item:
            return
            
        effect_type = current_item.data(Qt.ItemDataRole.UserRole)
        effect_enum = EffectType(effect_type)
        
        effect = self.effects_manager.create_effect(effect_enum, {})
        layer = self.effects_manager.add_effect_layer(effect)
        
        self._refresh_applied_effects()
        self._schedule_preview_update()
        
    def _remove_effect(self):
        """Remove selected effect"""
        current_item = self.applied_effects_list.currentItem()
        if not current_item:
            return
            
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        self.effects_manager.remove_effect_layer(effect_id)
        self._refresh_applied_effects()
        self._clear_effect_parameters()
        self._schedule_preview_update()
        
    def _toggle_effect(self):
        """Toggle selected effect"""
        current_item = self.applied_effects_list.currentItem()
        if not current_item:
            return
            
        effect_id = current_item.data(Qt.ItemDataRole.UserRole)
        layer = self.effects_manager.get_effect_layer(effect_id)
        if layer:
            new_state = not layer.enabled
            self.effects_manager.toggle_effect_layer(effect_id, new_state)
            self._refresh_applied_effects()
            self._schedule_preview_update()
            
    def _refresh_applied_effects(self):
        """Refresh applied effects list"""
        self.applied_effects_list.clear()
        
        for layer in self.effects_manager.effect_layers:
            item_text = layer.effect.name
            if not layer.enabled:
                item_text += " (Disabled)"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, layer.effect.id)
            
            if not layer.enabled:
                item.setForeground(QColor(128, 128, 128))
                
            self.applied_effects_list.addItem(item)
            
    def _show_effect_parameters(self, layer: EffectLayer):
        """Show parameters for selected effect"""
        self._clear_effect_parameters()
        
        # Add basic parameters based on effect type
        # This is a simplified version - you can expand based on your effects system
        effect = layer.effect
        
        row = 0
        for param_name, param_value in effect.parameters.items():
            # Create label
            label = QLabel(f"{param_name.replace('_', ' ').title()}:")
            self.params_layout.addWidget(label, row, 0)
            
            # Create appropriate widget based on value type
            if isinstance(param_value, bool):
                widget = QCheckBox()
                widget.setChecked(param_value)
                widget.toggled.connect(lambda v, p=param_name: self._update_effect_parameter(layer.effect.id, p, v))
            elif isinstance(param_value, (int, float)):
                widget = QDoubleSpinBox()
                widget.setRange(-1000.0, 1000.0)
                widget.setValue(float(param_value))
                widget.valueChanged.connect(lambda v, p=param_name: self._update_effect_parameter(layer.effect.id, p, v))
            elif isinstance(param_value, list) and len(param_value) == 3:
                # Color parameter
                widget = QPushButton("Choose Color")
                color = QColor(int(param_value[0]*255), int(param_value[1]*255), int(param_value[2]*255))
                widget.setStyleSheet(f"background-color: {color.name()};")
                widget.clicked.connect(lambda _, p=param_name: self._choose_effect_color(layer.effect.id, p))
            else:
                widget = QLineEdit(str(param_value))
                widget.textChanged.connect(lambda v, p=param_name: self._update_effect_parameter(layer.effect.id, p, v))
                
            self.params_layout.addWidget(widget, row, 1)
            row += 1
            
    def _clear_effect_parameters(self):
        """Clear effect parameters display"""
        for i in reversed(range(self.params_layout.count())):
            child = self.params_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                
    def _update_effect_parameter(self, effect_id: str, param_name: str, value):
        """Update effect parameter"""
        self.effects_manager.update_effect_parameters(effect_id, {param_name: value})
        self._schedule_preview_update()
        
    def _choose_effect_color(self, effect_id: str, param_name: str):
        """Choose color for effect parameter"""
        color = QColorDialog.getColor(QColor(255, 255, 255), self)
        if color.isValid():
            rgb_values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
            self._update_effect_parameter(effect_id, param_name, rgb_values)
            
            # Update button color
            sender = self.sender()
            sender.setStyleSheet(f"background-color: {color.name()};")
            
    # Utility methods
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS format"""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def _format_ass_time(self, seconds: float) -> str:
        """Format time in ASS format (H:MM:SS.CC)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
        
    def _add_subtitle_line(self):
        """Add a new subtitle line"""
        # Add at current playback time or end of timeline
        start_time = self.current_time if self.current_time > 0 else 0.0
        end_time = start_time + 3.0  # Default 3 second duration
        
        new_line = SubtitleLine(
            start_time=start_time,
            end_time=end_time,
            text="New subtitle line",
            style="Default"
        )
        
        if not hasattr(self, 'parsed_lines'):
            self.parsed_lines = []
            
        self.parsed_lines.append(new_line)
        self._update_text_from_parsed_lines()
        self.timeline_widget.set_subtitle_lines(self.parsed_lines)
        
    def _auto_format_text(self):
        """Auto-format the subtitle text"""
        # Basic formatting - ensure proper structure
        content = self.text_editor.toPlainText()
        
        # Add missing sections if needed
        if "[Script Info]" not in content:
            content = "[Script Info]\nTitle: Karaoke Subtitles\nScriptType: v4.00+\n\n" + content
            
        if "[V4+ Styles]" not in content:
            styles_section = (
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n"
            )
            if "[Events]" in content:
                content = content.replace("[Events]", styles_section + "[Events]")
            else:
                content += "\n\n" + styles_section
            
        if "[Events]" not in content:
            content += "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            
        self.text_editor.setPlainText(content)
        
    def get_subtitle_content(self) -> str:
        """Get current subtitle content"""
        return self.text_editor.toPlainText()
        
    def save_subtitle_file(self, file_path: str):
        """Save current subtitle content to file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.get_subtitle_content())
            self.status_label.setText(f"Saved to {file_path}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        except Exception as e:
            self.status_label.setText(f"Save failed: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")