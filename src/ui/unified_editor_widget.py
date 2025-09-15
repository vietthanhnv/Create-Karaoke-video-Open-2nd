"""
Unified Editor Widget - All editing tools in one interface

Combines preview, text editing, timeline, and effects in a single window
for maximum efficiency and real-time feedback.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QSplitter, QFrame, QPushButton, QScrollArea,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QApplication,
    QSlider, QCheckBox, QComboBox, QColorDialog, QGridLayout
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
    from .detachable_preview_widget import DetachablePreviewWidget
    from .editor_widget import AssHighlighter, TimelineWidget
except ImportError:
    from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle, Project
    from src.core.subtitle_parser import AssParser, ParseError
    from src.core.preview_synchronizer import PreviewSynchronizer
    from src.core.effects_manager import EffectsManager, EffectType, EffectLayer
    from src.core.opengl_subtitle_renderer import RenderedSubtitle
    from src.ui.detachable_preview_widget import DetachablePreviewWidget
    from src.ui.editor_widget import AssHighlighter, TimelineWidget


class UnifiedEditorWidget(QWidget):
    """Unified editor combining all editing tools in one interface"""
    
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
        self.current_effect_id = None
        self.parameter_widgets = {}
        
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
        """Set up the unified editor UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Unified Karaoke Video Editor")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Main content area with horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left panel: Preview (50%)
        self._create_preview_panel(main_splitter)
        
        # Right panel: All editing tools (50%)
        self._create_unified_editing_panel(main_splitter)
        
        # Set initial splitter proportions (50/50)
        main_splitter.setSizes([500, 500])
        
        # Status bar at bottom
        self._create_status_bar(layout)
        
    def _create_preview_panel(self, parent_splitter):
        """Create the preview panel with detachable preview widget"""
        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        
        # Use detachable preview widget
        self.detachable_preview = DetachablePreviewWidget()
        self.detachable_preview.setMinimumSize(480, 270)  # 16:9 aspect ratio
        preview_layout.addWidget(self.detachable_preview)
        
        # Current subtitle display
        self._create_current_subtitle_display(preview_layout)
        
        parent_splitter.addWidget(preview_frame)
        
    # Playback controls are now handled by the detachable preview widget
        
    def _create_current_subtitle_display(self, parent_layout):
        """Create current subtitle display"""
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
        
    def _create_unified_editing_panel(self, parent_splitter):
        """Create unified editing panel with all tools"""
        editing_frame = QFrame()
        editing_layout = QVBoxLayout(editing_frame)
        
        # Create vertical splitter for different editing sections
        editing_splitter = QSplitter(Qt.Orientation.Vertical)
        editing_layout.addWidget(editing_splitter)
        
        # Top section: Text Editor (40%)
        self._create_text_editor_section(editing_splitter)
        
        # Middle section: Timeline Editor (30%)
        self._create_timeline_section(editing_splitter)
        
        # Bottom section: Effects and Individual Editor (30%)
        self._create_effects_and_individual_section(editing_splitter)
        
        # Set splitter proportions
        editing_splitter.setSizes([400, 300, 300])
        
        parent_splitter.addWidget(editing_frame)
        
    def _create_text_editor_section(self, parent_splitter):
        """Create text editor section"""
        text_frame = QFrame()
        text_layout = QVBoxLayout(text_frame)
        
        # Header
        header_layout = QHBoxLayout()
        
        text_label = QLabel("Subtitle Text Editor")
        text_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(text_label)
        
        header_layout.addStretch()
        
        # Quick action buttons
        add_line_button = QPushButton("Add Line")
        add_line_button.clicked.connect(self._add_subtitle_line)
        header_layout.addWidget(add_line_button)
        
        format_button = QPushButton("Format")
        format_button.clicked.connect(self._auto_format_text)
        header_layout.addWidget(format_button)
        
        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self._validate_content)
        header_layout.addWidget(validate_button)
        
        text_layout.addLayout(header_layout)
        
        # Text editor
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Consolas", 10))
        self.text_editor.setMaximumHeight(200)  # Limit height to save space
        
        # Syntax highlighter
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
        
        parent_splitter.addWidget(text_frame)
        
    def _create_timeline_section(self, parent_splitter):
        """Create timeline editor section"""
        timeline_frame = QFrame()
        timeline_layout = QVBoxLayout(timeline_frame)
        
        # Header
        timeline_label = QLabel("Visual Timeline Editor")
        timeline_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        timeline_layout.addWidget(timeline_label)
        
        # Timeline widget with scroll area
        timeline_scroll = QScrollArea()
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        timeline_scroll.setMaximumHeight(120)  # Compact timeline
        
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.subtitle_selected.connect(self._on_timeline_subtitle_selected)
        self.timeline_widget.timing_changed.connect(self._on_timeline_timing_changed)
        
        timeline_scroll.setWidget(self.timeline_widget)
        timeline_scroll.setWidgetResizable(True)
        timeline_layout.addWidget(timeline_scroll)
        
        parent_splitter.addWidget(timeline_frame)
        
    def _create_effects_and_individual_section(self, parent_splitter):
        """Create effects and individual editing section"""
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        
        # Left side: Individual subtitle editor
        self._create_individual_editor(bottom_layout)
        
        # Right side: Effects management
        self._create_effects_section(bottom_layout)
        
        parent_splitter.addWidget(bottom_frame)
        
    def _create_individual_editor(self, parent_layout):
        """Create individual subtitle editor"""
        editor_group = QGroupBox("Selected Subtitle")
        editor_layout = QFormLayout(editor_group)
        
        # Start time
        self.start_time_editor = QDoubleSpinBox()
        self.start_time_editor.setRange(0.0, 9999.0)
        self.start_time_editor.setDecimals(2)
        self.start_time_editor.setSuffix(" s")
        self.start_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("Start:", self.start_time_editor)
        
        # End time
        self.end_time_editor = QDoubleSpinBox()
        self.end_time_editor.setRange(0.0, 9999.0)
        self.end_time_editor.setDecimals(2)
        self.end_time_editor.setSuffix(" s")
        self.end_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("End:", self.end_time_editor)
        
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
        
    def _create_effects_section(self, parent_layout):
        """Create effects management section"""
        effects_group = QGroupBox("Text Effects")
        effects_layout = QVBoxLayout(effects_group)
        
        # Effects controls in horizontal layout
        effects_controls = QHBoxLayout()
        
        # Left: Available effects and presets
        effects_left = QVBoxLayout()
        
        # Presets
        presets_label = QLabel("Presets:")
        effects_left.addWidget(presets_label)
        
        self.presets_combo = QComboBox()
        self.presets_combo.addItem("Select Preset...")
        for preset_name in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_name)
            self.presets_combo.addItem(preset_info.name, preset_name)
        self.presets_combo.currentTextChanged.connect(self._on_preset_selected)
        effects_left.addWidget(self.presets_combo)
        
        # Available effects (compact list)
        effects_label = QLabel("Add Effect:")
        effects_left.addWidget(effects_label)
        
        self.effects_combo = QComboBox()
        self.effects_combo.addItem("Select Effect...")
        effect_items = [
            ("Glow", EffectType.GLOW.value),
            ("Outline", EffectType.OUTLINE.value),
            ("Shadow", EffectType.SHADOW.value),
            ("Fade", EffectType.FADE.value),
            ("Bounce", EffectType.BOUNCE.value),
            ("Color Transition", EffectType.COLOR_TRANSITION.value),
            ("Wave", EffectType.WAVE.value)
        ]
        
        for display_name, effect_type in effect_items:
            self.effects_combo.addItem(display_name, effect_type)
        
        effects_left.addWidget(self.effects_combo)
        
        self.add_effect_button = QPushButton("Add")
        self.add_effect_button.clicked.connect(self._add_effect)
        effects_left.addWidget(self.add_effect_button)
        
        effects_controls.addLayout(effects_left)
        
        # Right: Applied effects and parameters
        effects_right = QVBoxLayout()
        
        # Applied effects (compact list)
        applied_label = QLabel("Applied Effects:")
        effects_right.addWidget(applied_label)
        
        self.applied_effects_list = QListWidget()
        self.applied_effects_list.setMaximumHeight(80)
        self.applied_effects_list.currentItemChanged.connect(self._on_applied_effect_selected)
        effects_right.addWidget(self.applied_effects_list)
        
        # Effect control buttons
        buttons_layout = QHBoxLayout()
        
        self.remove_effect_button = QPushButton("Remove")
        self.remove_effect_button.clicked.connect(self._remove_effect)
        self.remove_effect_button.setEnabled(False)
        buttons_layout.addWidget(self.remove_effect_button)
        
        self.toggle_effect_button = QPushButton("Toggle")
        self.toggle_effect_button.clicked.connect(self._toggle_effect)
        self.toggle_effect_button.setEnabled(False)
        buttons_layout.addWidget(self.toggle_effect_button)
        
        effects_right.addLayout(buttons_layout)
        
        effects_controls.addLayout(effects_right)
        
        effects_layout.addLayout(effects_controls)
        
        # Effect parameters (compact)
        params_label = QLabel("Parameters:")
        effects_layout.addWidget(params_label)
        
        # Parameters scroll area (compact)
        params_scroll = QScrollArea()
        params_scroll.setMaximumHeight(100)
        params_scroll.setWidgetResizable(True)
        
        self.params_container = QWidget()
        self.params_layout = QGridLayout(self.params_container)
        
        # Default message
        default_label = QLabel("Select effect to adjust parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.params_layout.addWidget(default_label, 0, 0)
        
        params_scroll.setWidget(self.params_container)
        effects_layout.addWidget(params_scroll)
        
        parent_layout.addWidget(effects_group)
        
    def _create_status_bar(self, parent_layout):
        """Create status and validation bar"""
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # Validation display (compact)
        validation_label = QLabel("Validation:")
        status_layout.addWidget(validation_label)
        
        self.validation_display = QLabel("OK")
        self.validation_display.setStyleSheet("color: green;")
        status_layout.addWidget(self.validation_display)
        
        parent_layout.addWidget(status_frame)
        
    def _connect_signals(self):
        """Connect internal signals"""
        # Connect to detachable preview signals
        self.detachable_preview.subtitle_updated.connect(self._on_subtitle_updated)
        self.detachable_preview.time_changed.connect(self._on_time_changed)
        
        # Text changes trigger updates
        self.text_editor.textChanged.connect(self._schedule_preview_update)
        
        # Connect effects signals to preview
        self.effects_manager.effect_applied.connect(self._on_effect_applied_to_preview)
        self.effects_manager.effect_removed.connect(self._on_effect_removed_from_preview)
        self.effects_manager.effect_parameters_changed.connect(self._on_effect_parameters_changed_in_preview)
        
    # Project and file loading methods
    def load_project(self, project: Project):
        """Load a project into the unified editor"""
        self.current_project = project
        
        # Load into detachable preview
        success = self.detachable_preview.load_project(project)
        
        if success:
            # Load subtitle file
            if project.subtitle_file:
                self.load_subtitle_file(project.subtitle_file)
            
            self.status_label.setText("Project loaded successfully")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Failed to load project")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            
        return success
        
    def load_subtitle_file(self, subtitle_file: SubtitleFile):
        """Load subtitle file"""
        self.current_subtitle_file = subtitle_file
        
        try:
            with open(subtitle_file.path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            self.text_editor.setPlainText(content)
            self._update_timeline_and_list()
            self._validate_content()
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load subtitle file: {str(e)}")
            
    # Text editor methods
    def _on_text_changed(self):
        """Handle text editor changes"""
        self.validation_timer.start(500)
        self._update_timeline_and_list()
        self._schedule_preview_update()
        
    def _update_timeline_and_list(self):
        """Update timeline from text content"""
        try:
            content = self.text_editor.toPlainText()
            
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                parsed_file = self.parser.parse_file(temp_path)
                self.timeline_widget.set_subtitle_lines(parsed_file.lines)
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
        """Schedule preview update"""
        self.preview_update_timer.start(200)
        
    def _update_realtime_preview(self):
        """Update real-time preview"""
        if not hasattr(self, 'parsed_lines'):
            return
            
        try:
            if hasattr(self, 'parsed_lines'):
                styles = {"Default": SubtitleStyle(
                    name="Default",
                    font_name="Arial",
                    font_size=20,
                    primary_color=[1.0, 1.0, 1.0, 1.0],
                    secondary_color=[0.0, 0.0, 1.0, 1.0],
                    outline_color=[0.0, 0.0, 0.0, 1.0],
                    back_color=[0.5, 0.0, 0.0, 0.5]
                )}
                
                self.detachable_preview.update_subtitles_realtime(self.parsed_lines, styles)
        except Exception as e:
            print(f"Preview update error: {e}")
            
    def _validate_content(self):
        """Validate subtitle content"""
        try:
            content = self.text_editor.toPlainText()
            errors = []
            
            # Basic validation
            if "[Script Info]" not in content:
                errors.append("Missing [Script Info]")
            if "[V4+ Styles]" not in content:
                errors.append("Missing [V4+ Styles]")
            if "[Events]" not in content:
                errors.append("Missing [Events]")
                
            # Try parsing
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                parsed_file = self.parser.parse_file(temp_path)
                if not errors:
                    self.validation_display.setText("✓ Valid")
                    self.validation_display.setStyleSheet("color: green;")
                else:
                    self.validation_display.setText("⚠ Issues")
                    self.validation_display.setStyleSheet("color: orange;")
            except Exception as e:
                self.validation_display.setText("✗ Invalid")
                self.validation_display.setStyleSheet("color: red;")
            finally:
                import os
                try:
                    os.unlink(temp_path)
                except:
                    pass
        except Exception as e:
            self.validation_display.setText("✗ Error")
            self.validation_display.setStyleSheet("color: red;")
            
    # Playback control methods are now handled by the detachable preview widget
            
    # Event handlers for detachable preview
    def _on_time_changed(self, current_time: float, duration: float):
        """Handle time position changes from preview"""
        self.current_time = current_time
        
    def _on_subtitle_updated(self, visible_subtitles: List[RenderedSubtitle]):
        """Handle subtitle updates from preview"""
        if visible_subtitles:
            subtitle_texts = [sub.text for sub in visible_subtitles]
            display_text = "<br>".join(subtitle_texts)
            self.current_subtitle_label.setText(display_text)
        else:
            self.current_subtitle_label.setText("No active subtitles")
            
    def _on_effect_applied_to_preview(self, effect_id: str, parameters: dict):
        """Handle effect applied - update preview"""
        self.detachable_preview.add_effect(effect_id, parameters)
        
    def _on_effect_removed_from_preview(self, effect_id: str):
        """Handle effect removed - update preview"""
        self.detachable_preview.remove_effect(effect_id)
        
    def _on_effect_parameters_changed_in_preview(self, effect_id: str, parameters: dict):
        """Handle effect parameters changed - update preview"""
        self.detachable_preview.update_effect_parameters(effect_id, parameters)
            
    # Timeline editor methods
    def _on_timeline_subtitle_selected(self, index: int):
        """Handle subtitle selection from timeline"""
        self.selected_subtitle_index = index
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            line = self.parsed_lines[index]
            
            self.start_time_editor.setValue(line.start_time)
            self.end_time_editor.setValue(line.end_time)
            self.line_text_editor.setText(line.text)
            self.style_editor.setText(line.style)
            
        self.subtitle_selected.emit(index)
        
    def _on_timeline_timing_changed(self, index: int, start_time: float, end_time: float):
        """Handle timing changes from timeline"""
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            self.parsed_lines[index].start_time = start_time
            self.parsed_lines[index].end_time = end_time
            
            self._update_text_from_parsed_lines()
            
            if index == self.selected_subtitle_index:
                self.start_time_editor.setValue(start_time)
                self.end_time_editor.setValue(end_time)
                
        self.timing_changed.emit(index, start_time, end_time)
        
    # Individual editor methods
    def _on_individual_timing_changed(self):
        """Handle individual timing changes"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                line = self.parsed_lines[index]
                line.start_time = self.start_time_editor.value()
                line.end_time = self.end_time_editor.value()
                
                self._update_text_from_parsed_lines()
                self.timeline_widget.set_subtitle_lines(self.parsed_lines)
                
    def _on_individual_text_changed(self):
        """Handle individual text changes"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                self.parsed_lines[index].text = self.line_text_editor.text()
                self._update_text_from_parsed_lines()
                
    def _on_individual_style_changed(self):
        """Handle individual style changes"""
        if self.selected_subtitle_index >= 0 and hasattr(self, 'parsed_lines'):
            index = self.selected_subtitle_index
            if 0 <= index < len(self.parsed_lines):
                self.parsed_lines[index].style = self.style_editor.text()
                self._update_text_from_parsed_lines()
                
    def _update_text_from_parsed_lines(self):
        """Update text editor from parsed lines"""
        if not hasattr(self, 'parsed_lines'):
            return
            
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
        
        for line in self.parsed_lines:
            start_str = self._format_ass_time(line.start_time)
            end_str = self._format_ass_time(line.end_time)
            dialogue = f"Dialogue: 0,{start_str},{end_str},{line.style},,0,0,0,,{line.text}"
            content_lines.append(dialogue)
            
        self.text_editor.textChanged.disconnect()
        self.text_editor.setPlainText("\n".join(content_lines))
        self.text_editor.textChanged.connect(self._on_text_changed)
        
        self._schedule_preview_update()
        
    # Effects methods
    def _on_preset_selected(self, preset_display_name):
        """Handle preset selection"""
        if preset_display_name == "Select Preset...":
            return
            
        for preset_key in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_key)
            if preset_info.name == preset_display_name:
                self.effects_manager.apply_preset(preset_key)
                self._refresh_applied_effects()
                self._schedule_preview_update()
                break
                
    def _add_effect(self):
        """Add selected effect"""
        current_data = self.effects_combo.currentData()
        if not current_data:
            return
            
        effect_enum = EffectType(current_data)
        effect = self.effects_manager.create_effect(effect_enum, {})
        layer = self.effects_manager.add_effect_layer(effect)
        
        self._refresh_applied_effects()
        self._schedule_preview_update()
        
        # Update preview directly
        self.detachable_preview.add_effect(effect.id, effect.parameters)
        self.effect_applied.emit(effect.id, effect.parameters)
        
    def _on_applied_effect_selected(self, current, previous):
        """Handle applied effect selection"""
        if current is None:
            self.current_effect_id = None
            self._clear_effect_parameters()
            self.remove_effect_button.setEnabled(False)
            self.toggle_effect_button.setEnabled(False)
            return
            
        effect_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_effect_id = effect_id
        
        layer = self.effects_manager.get_effect_layer(effect_id)
        if layer:
            self._show_effect_parameters(layer)
            
        self.remove_effect_button.setEnabled(True)
        self.toggle_effect_button.setEnabled(True)
        
    def _remove_effect(self):
        """Remove selected effect"""
        if not self.current_effect_id:
            return
            
        # Update preview first
        self.detachable_preview.remove_effect(self.current_effect_id)
        self.effect_removed.emit(self.current_effect_id)
        
        self.effects_manager.remove_effect_layer(self.current_effect_id)
        self._refresh_applied_effects()
        self._clear_effect_parameters()
        self._schedule_preview_update()
        
    def _toggle_effect(self):
        """Toggle selected effect"""
        if not self.current_effect_id:
            return
            
        layer = self.effects_manager.get_effect_layer(self.current_effect_id)
        if layer:
            new_state = not layer.enabled
            self.effects_manager.toggle_effect_layer(self.current_effect_id, new_state)
            self._refresh_applied_effects()
            self._schedule_preview_update()
            
            # Update preview directly
            self.detachable_preview.toggle_effect(self.current_effect_id, new_state)
            
    def _refresh_applied_effects(self):
        """Refresh applied effects list"""
        self.applied_effects_list.clear()
        
        for layer in self.effects_manager.effect_layers:
            item_text = layer.effect.name
            if not layer.enabled:
                item_text += " (Off)"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, layer.effect.id)
            
            if not layer.enabled:
                item.setForeground(QColor(128, 128, 128))
                
            self.applied_effects_list.addItem(item)
            
    def _show_effect_parameters(self, layer: EffectLayer):
        """Show effect parameters"""
        self._clear_effect_parameters()
        
        effect = layer.effect
        row = 0
        
        for param_name, param_value in effect.parameters.items():
            # Create compact parameter controls
            label = QLabel(f"{param_name.replace('_', ' ').title()}:")
            self.params_layout.addWidget(label, row, 0)
            
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
                widget = QPushButton("Color")
                color = QColor(int(param_value[0]*255), int(param_value[1]*255), int(param_value[2]*255))
                widget.setStyleSheet(f"background-color: {color.name()};")
                widget.clicked.connect(lambda _, p=param_name: self._choose_effect_color(layer.effect.id, p))
            else:
                widget = QLineEdit(str(param_value))
                widget.textChanged.connect(lambda v, p=param_name: self._update_effect_parameter(layer.effect.id, p, v))
                
            self.params_layout.addWidget(widget, row, 1)
            row += 1
            
    def _clear_effect_parameters(self):
        """Clear effect parameters"""
        for i in reversed(range(self.params_layout.count())):
            child = self.params_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                
    def _update_effect_parameter(self, effect_id: str, param_name: str, value):
        """Update effect parameter"""
        self.effects_manager.update_effect_parameters(effect_id, {param_name: value})
        self._schedule_preview_update()
        
        # Update preview directly
        self.detachable_preview.update_effect_parameters(effect_id, {param_name: value})
        
    def _choose_effect_color(self, effect_id: str, param_name: str):
        """Choose color for effect"""
        color = QColorDialog.getColor(QColor(255, 255, 255), self)
        if color.isValid():
            rgb_values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
            self._update_effect_parameter(effect_id, param_name, rgb_values)
            
            sender = self.sender()
            sender.setStyleSheet(f"background-color: {color.name()};")
            
    # Utility methods
    def _format_time(self, seconds: float) -> str:
        """Format time in MM:SS"""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def _format_ass_time(self, seconds: float) -> str:
        """Format time in ASS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
        
    def _add_subtitle_line(self):
        """Add new subtitle line"""
        start_time = self.current_time if self.current_time > 0 else 0.0
        end_time = start_time + 3.0
        
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
        """Auto-format subtitle text"""
        content = self.text_editor.toPlainText()
        
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
        """Save subtitle file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.get_subtitle_content())
            self.status_label.setText(f"Saved to {file_path}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        except Exception as e:
            self.status_label.setText(f"Save failed: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")