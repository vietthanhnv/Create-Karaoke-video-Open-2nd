"""
Subtitle Editor Widget with Timeline and Text Editing
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QSplitter, QFrame, QPushButton, QScrollArea,
    QListWidget, QListWidgetItem, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QApplication,
    QSlider, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect, QPoint, QSize
from PyQt6.QtGui import (
    QFont, QTextCharFormat, QColor, QPainter, QPen, QBrush,
    QSyntaxHighlighter, QTextDocument, QMouseEvent, QPaintEvent
)
import re
from typing import List, Optional, Tuple
from src.core.models import SubtitleFile, SubtitleLine, SubtitleStyle
from src.core.subtitle_parser import AssParser, ParseError


class AssHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for ASS subtitle format"""
    
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self._setup_highlighting_rules()
    
    def _setup_highlighting_rules(self):
        """Set up syntax highlighting rules for ASS format"""
        # Section headers
        self.section_format = QTextCharFormat()
        self.section_format.setForeground(QColor(0, 0, 255))
        self.section_format.setFontWeight(QFont.Weight.Bold)
        
        # Field names
        self.field_format = QTextCharFormat()
        self.field_format.setForeground(QColor(128, 0, 128))
        
        # Time stamps
        self.time_format = QTextCharFormat()
        self.time_format.setForeground(QColor(0, 128, 0))
        
        # Comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(128, 128, 128))
        self.comment_format.setFontItalic(True)
        
        # Errors
        self.error_format = QTextCharFormat()
        self.error_format.setBackground(QColor(255, 200, 200))
    
    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text"""
        # Section headers [Script Info], [V4+ Styles], [Events]
        if text.strip().startswith('[') and text.strip().endswith(']'):
            self.setFormat(0, len(text), self.section_format)
            return
        
        # Comments (lines starting with ; or !)
        if text.strip().startswith(';') or text.strip().startswith('!'):
            self.setFormat(0, len(text), self.comment_format)
            return
        
        # Format lines
        if text.startswith('Format:'):
            self.setFormat(0, 7, self.field_format)
        
        # Style lines
        elif text.startswith('Style:'):
            self.setFormat(0, 6, self.field_format)
        
        # Dialogue lines
        elif text.startswith('Dialogue:'):
            self.setFormat(0, 9, self.field_format)
            
            # Highlight time stamps in dialogue lines
            time_pattern = re.compile(r'\d{1,2}:\d{2}:\d{2}\.\d{2}')
            for match in time_pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), self.time_format)


class TimelineWidget(QWidget):
    """Custom widget for displaying and editing subtitle timeline"""
    
    # Signals
    subtitle_selected = pyqtSignal(int)  # subtitle index
    timing_changed = pyqtSignal(int, float, float)  # index, start, end
    
    def __init__(self):
        super().__init__()
        self.subtitle_lines: List[SubtitleLine] = []
        self.selected_index = -1
        self.dragging_index = -1
        self.drag_mode = None  # 'start', 'end', 'move'
        self.drag_start_pos = None
        self.scale = 50.0  # pixels per second
        self.duration = 300.0  # total timeline duration in seconds
        
        self.setMinimumHeight(150)
        self.setMouseTracking(True)
        
    def set_subtitle_lines(self, lines: List[SubtitleLine]):
        """Set the subtitle lines to display"""
        self.subtitle_lines = lines
        if lines:
            # Calculate total duration based on last subtitle
            self.duration = max(300.0, max(line.end_time for line in lines) + 30.0)
        self.update()
    
    def set_selected_index(self, index: int):
        """Set the selected subtitle index"""
        self.selected_index = index
        self.update()
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # Draw time ruler
        self._draw_time_ruler(painter)
        
        # Draw subtitle blocks
        self._draw_subtitle_blocks(painter)
        
    def _draw_time_ruler(self, painter: QPainter):
        """Draw the time ruler at the top"""
        ruler_height = 30
        painter.fillRect(0, 0, self.width(), ruler_height, QColor(220, 220, 220))
        
        # Draw time marks
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # Major marks every 10 seconds
        for i in range(0, int(self.duration) + 1, 10):
            x = int(i * self.scale)
            if x < self.width():
                painter.drawLine(x, 0, x, ruler_height)
                painter.drawText(x + 2, ruler_height - 5, f"{i}s")
        
        # Minor marks every 1 second
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        for i in range(0, int(self.duration) + 1, 1):
            x = int(i * self.scale)
            if x < self.width():
                painter.drawLine(x, ruler_height - 10, x, ruler_height)
    
    def _draw_subtitle_blocks(self, painter: QPainter):
        """Draw subtitle timing blocks"""
        ruler_height = 30
        block_height = 25
        y_offset = ruler_height + 10
        
        for i, line in enumerate(self.subtitle_lines):
            x_start = int(line.start_time * self.scale)
            x_end = int(line.end_time * self.scale)
            width = x_end - x_start
            
            # Skip if block is outside visible area
            if x_end < 0 or x_start > self.width():
                continue
            
            # Choose color based on selection
            if i == self.selected_index:
                color = QColor(100, 150, 255)
                border_color = QColor(50, 100, 200)
            else:
                color = QColor(180, 200, 255)
                border_color = QColor(120, 140, 200)
            
            # Draw block
            rect = QRect(x_start, y_offset, width, block_height)
            painter.fillRect(rect, color)
            painter.setPen(QPen(border_color, 2))
            painter.drawRect(rect)
            
            # Draw text (truncated if necessary)
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            font = QFont("Arial", 9)
            painter.setFont(font)
            
            text = line.text[:50] + "..." if len(line.text) > 50 else line.text
            text_rect = QRect(x_start + 2, y_offset + 2, width - 4, block_height - 4)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            
            # Draw resize handles for selected block
            if i == self.selected_index:
                handle_size = 6
                # Start handle
                start_handle = QRect(x_start - handle_size//2, y_offset + block_height//2 - handle_size//2, 
                                   handle_size, handle_size)
                painter.fillRect(start_handle, QColor(255, 255, 255))
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.drawRect(start_handle)
                
                # End handle
                end_handle = QRect(x_end - handle_size//2, y_offset + block_height//2 - handle_size//2,
                                 handle_size, handle_size)
                painter.fillRect(end_handle, QColor(255, 255, 255))
                painter.drawRect(end_handle)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            clicked_index = self._get_subtitle_at_position(pos)
            
            if clicked_index >= 0:
                self.selected_index = clicked_index
                self.subtitle_selected.emit(clicked_index)
                
                # Check if clicking on resize handles
                line = self.subtitle_lines[clicked_index]
                x_start = int(line.start_time * self.scale)
                x_end = int(line.end_time * self.scale)
                
                handle_size = 6
                start_handle_x = x_start - handle_size//2
                end_handle_x = x_end - handle_size//2
                
                if abs(pos.x() - (start_handle_x + handle_size//2)) <= handle_size:
                    self.drag_mode = 'start'
                    self.dragging_index = clicked_index
                elif abs(pos.x() - (end_handle_x + handle_size//2)) <= handle_size:
                    self.drag_mode = 'end'
                    self.dragging_index = clicked_index
                else:
                    self.drag_mode = 'move'
                    self.dragging_index = clicked_index
                
                self.drag_start_pos = pos
                self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events"""
        if self.dragging_index >= 0 and self.drag_start_pos:
            pos = event.position().toPoint()
            delta_x = pos.x() - self.drag_start_pos.x()
            delta_time = delta_x / self.scale
            
            line = self.subtitle_lines[self.dragging_index]
            
            if self.drag_mode == 'start':
                new_start = max(0, line.start_time + delta_time)
                if new_start < line.end_time - 0.1:  # Minimum 0.1s duration
                    line.start_time = new_start
                    self.timing_changed.emit(self.dragging_index, line.start_time, line.end_time)
            
            elif self.drag_mode == 'end':
                new_end = max(line.start_time + 0.1, line.end_time + delta_time)
                line.end_time = new_end
                self.timing_changed.emit(self.dragging_index, line.start_time, line.end_time)
            
            elif self.drag_mode == 'move':
                duration = line.end_time - line.start_time
                new_start = max(0, line.start_time + delta_time)
                line.start_time = new_start
                line.end_time = new_start + duration
                self.timing_changed.emit(self.dragging_index, line.start_time, line.end_time)
            
            self.drag_start_pos = pos
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events"""
        self.dragging_index = -1
        self.drag_mode = None
        self.drag_start_pos = None
    
    def _get_subtitle_at_position(self, pos: QPoint) -> int:
        """Get the subtitle index at the given position"""
        ruler_height = 30
        block_height = 25
        y_offset = ruler_height + 10
        
        # Check if click is in the subtitle area
        if pos.y() < y_offset or pos.y() > y_offset + block_height:
            return -1
        
        # Find which subtitle block was clicked
        for i, line in enumerate(self.subtitle_lines):
            x_start = int(line.start_time * self.scale)
            x_end = int(line.end_time * self.scale)
            
            if x_start <= pos.x() <= x_end:
                return i
        
        return -1


class EditorWidget(QWidget):
    """Widget for editing subtitle content and timing"""
    
    # Editing signals
    subtitle_changed = pyqtSignal(str)
    timing_changed = pyqtSignal(int, float, float)
    subtitle_selected = pyqtSignal(int)
    validation_updated = pyqtSignal(list)  # List of ParseError objects
    
    # Real-time update signals
    subtitles_updated_realtime = pyqtSignal(list, dict)  # subtitle_lines, styles
    
    def __init__(self):
        super().__init__()
        self.current_subtitle_file: Optional[SubtitleFile] = None
        self.parser = AssParser()
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_content)
        
        self._setup_ui()
        self._connect_preview_updates()
        
    def _setup_ui(self):
        """Set up the editor widget UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Edit Subtitles")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Create main splitter for editor and timeline
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(main_splitter)
        
        # Left side: Text editor and validation
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Text editor section
        self._create_text_editor(left_layout)
        
        # Validation section
        self._create_validation_section(left_layout)
        
        main_splitter.addWidget(left_widget)
        
        # Right side: Timeline and subtitle list
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Timeline section
        self._create_timeline_editor(right_layout)
        
        # Subtitle list section
        self._create_subtitle_list(right_layout)
        
        # Real-time preview section
        self._create_realtime_preview(right_layout)
        
        main_splitter.addWidget(right_widget)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 600])
        
    def _create_text_editor(self, parent_layout):
        """Create subtitle text editor"""
        # Editor label
        editor_label = QLabel("Subtitle Text (.ass format)")
        editor_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        parent_layout.addWidget(editor_label)
        
        # Text editor with syntax highlighting
        self.text_editor = QTextEdit()
        self.text_editor.setFont(QFont("Consolas", 10))
        
        # Set up syntax highlighter
        self.highlighter = AssHighlighter(self.text_editor.document())
        
        # Default ASS content
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
        parent_layout.addWidget(self.text_editor)
        
    def _create_timeline_editor(self, parent_layout):
        """Create timeline editor for subtitle timing"""
        # Timeline label
        timeline_label = QLabel("Subtitle Timeline")
        timeline_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        parent_layout.addWidget(timeline_label)
        
        # Timeline widget with scroll area
        timeline_scroll = QScrollArea()
        timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        timeline_scroll.setMinimumHeight(200)
        
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.subtitle_selected.connect(self._on_timeline_subtitle_selected)
        self.timeline_widget.timing_changed.connect(self._on_timeline_timing_changed)
        
        timeline_scroll.setWidget(self.timeline_widget)
        timeline_scroll.setWidgetResizable(True)
        parent_layout.addWidget(timeline_scroll)
        
    def _create_subtitle_list(self, parent_layout):
        """Create subtitle list for individual line editing"""
        # Subtitle list label
        list_label = QLabel("Subtitle Lines")
        list_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        parent_layout.addWidget(list_label)
        
        # Subtitle list widget
        self.subtitle_list = QListWidget()
        self.subtitle_list.itemSelectionChanged.connect(self._on_list_selection_changed)
        self.subtitle_list.setMaximumHeight(200)
        parent_layout.addWidget(self.subtitle_list)
        
        # Individual subtitle editor
        self._create_individual_editor(parent_layout)
    
    def _create_individual_editor(self, parent_layout):
        """Create editor for individual subtitle lines"""
        editor_group = QGroupBox("Edit Selected Subtitle")
        editor_layout = QFormLayout(editor_group)
        
        # Start time editor
        self.start_time_editor = QDoubleSpinBox()
        self.start_time_editor.setRange(0.0, 9999.0)
        self.start_time_editor.setDecimals(2)
        self.start_time_editor.setSuffix(" s")
        self.start_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("Start Time:", self.start_time_editor)
        
        # End time editor
        self.end_time_editor = QDoubleSpinBox()
        self.end_time_editor.setRange(0.0, 9999.0)
        self.end_time_editor.setDecimals(2)
        self.end_time_editor.setSuffix(" s")
        self.end_time_editor.valueChanged.connect(self._on_individual_timing_changed)
        editor_layout.addRow("End Time:", self.end_time_editor)
        
        # Text editor
        self.line_text_editor = QLineEdit()
        self.line_text_editor.textChanged.connect(self._on_individual_text_changed)
        editor_layout.addRow("Text:", self.line_text_editor)
        
        # Style selector
        self.style_editor = QLineEdit()
        self.style_editor.setText("Default")
        self.style_editor.textChanged.connect(self._on_individual_style_changed)
        editor_layout.addRow("Style:", self.style_editor)
        
        parent_layout.addWidget(editor_group)
    
    def _create_realtime_preview(self, parent_layout):
        """Create real-time subtitle preview section"""
        preview_group = QGroupBox("Real-time Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview controls
        controls_layout = QHBoxLayout()
        
        # Preview time slider
        self.preview_time_label = QLabel("Preview Time:")
        controls_layout.addWidget(self.preview_time_label)
        
        self.preview_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_time_slider.setMinimum(0)
        self.preview_time_slider.setMaximum(100)
        self.preview_time_slider.setValue(50)
        self.preview_time_slider.valueChanged.connect(self._update_preview_time)
        controls_layout.addWidget(self.preview_time_slider)
        
        self.preview_time_value = QLabel("0.0s")
        controls_layout.addWidget(self.preview_time_value)
        
        preview_layout.addLayout(controls_layout)
        
        # Preview display area
        self.preview_display = QLabel("Subtitle preview will appear here")
        self.preview_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_display.setStyleSheet(
            "background-color: #1a1a1a; "
            "color: white; "
            "padding: 20px; "
            "border: 2px solid #444; "
            "border-radius: 5px; "
            "font-size: 16px; "
            "font-weight: bold; "
            "min-height: 80px;"
        )
        preview_layout.addWidget(self.preview_display)
        
        # Auto-update checkbox
        self.auto_update_preview = QCheckBox("Auto-update preview")
        self.auto_update_preview.setChecked(True)
        self.auto_update_preview.toggled.connect(self._toggle_auto_preview)
        preview_layout.addWidget(self.auto_update_preview)
        
        parent_layout.addWidget(preview_group)
        
        # Initialize preview timer
        self.preview_update_timer = QTimer()
        self.preview_update_timer.setSingleShot(True)
        self.preview_update_timer.timeout.connect(self._update_subtitle_preview)
    
    def _update_preview_time(self, value):
        """Update preview time from slider"""
        # Convert slider value (0-100) to time based on current subtitle duration
        if hasattr(self, 'parsed_lines') and self.parsed_lines:
            max_time = max(line.end_time for line in self.parsed_lines)
            preview_time = (value / 100.0) * max_time
        else:
            preview_time = value / 10.0  # Default scale
        
        self.preview_time_value.setText(f"{preview_time:.1f}s")
        
        # Update preview if auto-update is enabled
        if self.auto_update_preview.isChecked():
            self._schedule_preview_update()
    
    def _toggle_auto_preview(self, enabled):
        """Toggle auto-preview updates"""
        if enabled:
            self._schedule_preview_update()
    
    def _schedule_preview_update(self):
        """Schedule a preview update with debouncing"""
        if self.auto_update_preview.isChecked():
            self.preview_update_timer.start(200)  # 200ms delay
    
    def _update_subtitle_preview(self):
        """Update the real-time subtitle preview"""
        try:
            # Get current preview time
            slider_value = self.preview_time_slider.value()
            if hasattr(self, 'parsed_lines') and self.parsed_lines:
                max_time = max(line.end_time for line in self.parsed_lines)
                preview_time = (slider_value / 100.0) * max_time
            else:
                preview_time = slider_value / 10.0
            
            # Find active subtitles at preview time
            active_lines = []
            if hasattr(self, 'parsed_lines'):
                for line in self.parsed_lines:
                    if line.start_time <= preview_time <= line.end_time:
                        active_lines.append(line)
            
            # Generate preview text with karaoke highlighting
            if active_lines:
                preview_texts = []
                for line in active_lines:
                    # Get karaoke progress for this line
                    progress = line.get_progress_ratio(preview_time)
                    active_words = line.get_active_words(preview_time)
                    
                    # Create HTML with color coding
                    words = line.text.split()
                    html_words = []
                    
                    for word in words:
                        if word in active_words:
                            # Currently singing - yellow
                            html_words.append(f'<span style="color: #FFFF64;">{word}</span>')
                        elif line.word_timings:
                            # Check if word has been sung
                            word_sung = False
                            for word_timing in line.word_timings:
                                if word_timing.word == word and preview_time >= word_timing.end_time:
                                    word_sung = True
                                    break
                            
                            if word_sung:
                                # Already sung - bright yellow
                                html_words.append(f'<span style="color: #FFFF64;">{word}</span>')
                            else:
                                # Not yet sung - light gray
                                html_words.append(f'<span style="color: #C8C8C8;">{word}</span>')
                        else:
                            # No word timing - use progress-based coloring
                            if progress >= 1.0:
                                html_words.append(f'<span style="color: #FFFF64;">{word}</span>')
                            else:
                                html_words.append(f'<span style="color: #C8C8C8;">{word}</span>')
                    
                    preview_texts.append(' '.join(html_words))
                
                # Display the preview
                preview_html = '<br>'.join(preview_texts)
                self.preview_display.setText(preview_html)
            else:
                self.preview_display.setText("No subtitles at this time")
                
        except Exception as e:
            self.preview_display.setText(f"Preview error: {str(e)}")
    
    def _connect_preview_updates(self):
        """Connect events that should trigger preview updates"""
        # Connect text changes to preview updates
        self.text_editor.textChanged.connect(self._schedule_preview_update)
        
        # Connect individual editor changes
        self.start_time_editor.valueChanged.connect(self._schedule_preview_update)
        self.end_time_editor.valueChanged.connect(self._schedule_preview_update)
        self.line_text_editor.textChanged.connect(self._schedule_preview_update)
    
    def _create_validation_section(self, parent_layout):
        """Create validation feedback section"""
        # Validation label
        validation_label = QLabel("Validation Results")
        validation_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        parent_layout.addWidget(validation_label)
        
        # Validation display
        self.validation_display = QTextEdit()
        self.validation_display.setMaximumHeight(120)
        self.validation_display.setReadOnly(True)
        self.validation_display.setPlainText("Subtitle format validation will appear here...")
        parent_layout.addWidget(self.validation_display)
        
        # Validation controls
        validation_controls = QHBoxLayout()
        
        validate_button = QPushButton("Validate Now")
        validate_button.clicked.connect(self._validate_content)
        validation_controls.addWidget(validate_button)
        
        auto_validate_button = QPushButton("Auto-validate: ON")
        auto_validate_button.setCheckable(True)
        auto_validate_button.setChecked(True)
        auto_validate_button.toggled.connect(self._toggle_auto_validation)
        validation_controls.addWidget(auto_validate_button)
        
        validation_controls.addStretch()
        parent_layout.addLayout(validation_controls)
        
    def load_project(self, project):
        """Load a project into the editor - extracts subtitle file and loads it"""
        if hasattr(project, 'subtitle_file') and project.subtitle_file:
            self.load_subtitle_file(project.subtitle_file)
        else:
            QMessageBox.warning(self, "No Subtitles", "Project does not contain a subtitle file.")
    
    def load_subtitle_file(self, subtitle_file: SubtitleFile):
        """Load a subtitle file into the editor"""
        self.current_subtitle_file = subtitle_file
        
        # Load content into text editor
        try:
            with open(subtitle_file.path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            self.text_editor.setPlainText(content)
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load subtitle file: {str(e)}")
            return
        
        # Update timeline and list
        self._update_timeline_and_list()
        
        # Validate content
        self._validate_content()
    
    def get_subtitle_content(self) -> str:
        """Get the current subtitle content"""
        return self.text_editor.toPlainText()
    
    def _update_timeline_and_list(self):
        """Update timeline widget and subtitle list from current content"""
        try:
            # Parse current content
            content = self.text_editor.toPlainText()
            
            # Create temporary file for parsing
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                parsed_file = self.parser.parse_file(temp_path)
                
                # Update timeline
                self.timeline_widget.set_subtitle_lines(parsed_file.lines)
                
                # Update subtitle list
                self.subtitle_list.clear()
                for i, line in enumerate(parsed_file.lines):
                    item_text = f"{line.start_time:.2f}s - {line.end_time:.2f}s: {line.text[:50]}"
                    if len(line.text) > 50:
                        item_text += "..."
                    
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, i)
                    self.subtitle_list.addItem(item)
                
                # Store parsed lines for editing
                self.parsed_lines = parsed_file.lines.copy()
                
                # Emit real-time update signal for preview synchronization
                styles_dict = {style.name: style for style in parsed_file.styles}
                self.subtitles_updated_realtime.emit(parsed_file.lines, styles_dict)
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            # Clear timeline and list on parse error
            self.timeline_widget.set_subtitle_lines([])
            self.subtitle_list.clear()
            self.parsed_lines = []
            
            # Emit empty update for preview
            self.subtitles_updated_realtime.emit([], {})
    
    def _on_text_changed(self):
        """Handle text editor changes"""
        # Emit signal for external listeners
        self.subtitle_changed.emit(self.text_editor.toPlainText())
        
        # Update timeline and list (with delay to avoid too frequent updates)
        self.validation_timer.start(500)  # 500ms delay
    
    def _validate_content(self):
        """Validate subtitle format and display results"""
        try:
            content = self.text_editor.toPlainText()
            
            if not content.strip():
                self.validation_display.setPlainText("No content to validate.")
                return
            
            # Create temporary file for parsing
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            try:
                # Parse and get validation results
                parsed_file = self.parser.parse_file(temp_path)
                errors = self.parser.get_errors()
                warnings = self.parser.get_warnings()
                
                # Update timeline and list
                self._update_timeline_and_list()
                
                # Display validation results
                result_text = []
                
                if not errors and not warnings:
                    result_text.append("✓ Subtitle format is valid!")
                    result_text.append(f"Found {len(parsed_file.lines)} subtitle lines")
                    result_text.append(f"Found {len(parsed_file.styles)} styles")
                else:
                    if errors:
                        result_text.append(f"❌ {len(errors)} Error(s):")
                        for error in errors[:5]:  # Show first 5 errors
                            result_text.append(f"  Line {error.line_number}: {error.message}")
                        if len(errors) > 5:
                            result_text.append(f"  ... and {len(errors) - 5} more errors")
                    
                    if warnings:
                        result_text.append(f"⚠️ {len(warnings)} Warning(s):")
                        for warning in warnings[:3]:  # Show first 3 warnings
                            result_text.append(f"  Line {warning.line_number}: {warning.message}")
                        if len(warnings) > 3:
                            result_text.append(f"  ... and {len(warnings) - 3} more warnings")
                
                self.validation_display.setPlainText("\n".join(result_text))
                
                # Emit validation results
                all_issues = errors + warnings
                self.validation_updated.emit(all_issues)
                
            finally:
                os.unlink(temp_path)
                
        except Exception as e:
            self.validation_display.setPlainText(f"Validation error: {str(e)}")
    
    def _toggle_auto_validation(self, enabled: bool):
        """Toggle auto-validation on text changes"""
        sender = self.sender()
        if enabled:
            sender.setText("Auto-validate: ON")
            self.text_editor.textChanged.connect(self._on_text_changed)
        else:
            sender.setText("Auto-validate: OFF")
            try:
                self.text_editor.textChanged.disconnect(self._on_text_changed)
            except:
                pass
    
    def _on_timeline_subtitle_selected(self, index: int):
        """Handle subtitle selection from timeline"""
        if 0 <= index < self.subtitle_list.count():
            self.subtitle_list.setCurrentRow(index)
            self._load_individual_editor(index)
            self.subtitle_selected.emit(index)
    
    def _on_timeline_timing_changed(self, index: int, start_time: float, end_time: float):
        """Handle timing changes from timeline"""
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            # Update parsed lines
            self.parsed_lines[index].start_time = start_time
            self.parsed_lines[index].end_time = end_time
            
            # Update individual editor if this line is selected
            if self.subtitle_list.currentRow() == index:
                self.start_time_editor.blockSignals(True)
                self.end_time_editor.blockSignals(True)
                self.start_time_editor.setValue(start_time)
                self.end_time_editor.setValue(end_time)
                self.start_time_editor.blockSignals(False)
                self.end_time_editor.blockSignals(False)
            
            # Update text editor content
            self._update_text_editor_from_parsed_lines()
            
            # Emit timing change signal
            self.timing_changed.emit(index, start_time, end_time)
    
    def _on_list_selection_changed(self):
        """Handle subtitle list selection changes"""
        current_row = self.subtitle_list.currentRow()
        if current_row >= 0:
            self._load_individual_editor(current_row)
            self.timeline_widget.set_selected_index(current_row)
            self.subtitle_selected.emit(current_row)
    
    def _load_individual_editor(self, index: int):
        """Load subtitle line data into individual editor"""
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            line = self.parsed_lines[index]
            
            # Block signals to prevent recursive updates
            self.start_time_editor.blockSignals(True)
            self.end_time_editor.blockSignals(True)
            self.line_text_editor.blockSignals(True)
            self.style_editor.blockSignals(True)
            
            # Set values
            self.start_time_editor.setValue(line.start_time)
            self.end_time_editor.setValue(line.end_time)
            self.line_text_editor.setText(line.text)
            self.style_editor.setText(line.style)
            
            # Unblock signals
            self.start_time_editor.blockSignals(False)
            self.end_time_editor.blockSignals(False)
            self.line_text_editor.blockSignals(False)
            self.style_editor.blockSignals(False)
    
    def _on_individual_timing_changed(self):
        """Handle timing changes from individual editor"""
        current_row = self.subtitle_list.currentRow()
        if current_row >= 0 and hasattr(self, 'parsed_lines') and current_row < len(self.parsed_lines):
            line = self.parsed_lines[current_row]
            
            # Validate timing
            start_time = self.start_time_editor.value()
            end_time = self.end_time_editor.value()
            
            if end_time <= start_time:
                end_time = start_time + 0.1
                self.end_time_editor.blockSignals(True)
                self.end_time_editor.setValue(end_time)
                self.end_time_editor.blockSignals(False)
            
            # Update parsed line
            line.start_time = start_time
            line.end_time = end_time
            
            # Update timeline
            self.timeline_widget.set_subtitle_lines(self.parsed_lines)
            
            # Update text editor
            self._update_text_editor_from_parsed_lines()
            
            # Update list display
            self._update_list_item_text(current_row)
            
            # Emit signal
            self.timing_changed.emit(current_row, start_time, end_time)
    
    def _on_individual_text_changed(self):
        """Handle text changes from individual editor"""
        current_row = self.subtitle_list.currentRow()
        if current_row >= 0 and hasattr(self, 'parsed_lines') and current_row < len(self.parsed_lines):
            line = self.parsed_lines[current_row]
            line.text = self.line_text_editor.text()
            
            # Update timeline
            self.timeline_widget.set_subtitle_lines(self.parsed_lines)
            
            # Update text editor
            self._update_text_editor_from_parsed_lines()
            
            # Update list display
            self._update_list_item_text(current_row)
    
    def _on_individual_style_changed(self):
        """Handle style changes from individual editor"""
        current_row = self.subtitle_list.currentRow()
        if current_row >= 0 and hasattr(self, 'parsed_lines') and current_row < len(self.parsed_lines):
            line = self.parsed_lines[current_row]
            line.style = self.style_editor.text()
            
            # Update text editor
            self._update_text_editor_from_parsed_lines()
    
    def _update_list_item_text(self, index: int):
        """Update the display text for a list item"""
        if hasattr(self, 'parsed_lines') and 0 <= index < len(self.parsed_lines):
            line = self.parsed_lines[index]
            item_text = f"{line.start_time:.2f}s - {line.end_time:.2f}s: {line.text[:50]}"
            if len(line.text) > 50:
                item_text += "..."
            
            item = self.subtitle_list.item(index)
            if item:
                item.setText(item_text)
    
    def _update_text_editor_from_parsed_lines(self):
        """Update the text editor content from parsed lines"""
        if not hasattr(self, 'parsed_lines'):
            return
        
        # Generate ASS content from parsed lines
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
            start_str = self._seconds_to_ass_time(line.start_time)
            end_str = self._seconds_to_ass_time(line.end_time)
            dialogue = f"Dialogue: 0,{start_str},{end_str},{line.style},,0,0,0,,{line.text}"
            content_lines.append(dialogue)
        
        # Update text editor (block signals to prevent recursion)
        self.text_editor.blockSignals(True)
        self.text_editor.setPlainText("\n".join(content_lines))
        self.text_editor.blockSignals(False)
        
        # Emit real-time update after text editor update
        if hasattr(self, 'parsed_lines'):
            # Create default style if none exists
            from src.core.models import SubtitleStyle
            default_style = SubtitleStyle(name="Default")
            styles_dict = {"Default": default_style}
            self.subtitles_updated_realtime.emit(self.parsed_lines, styles_dict)
    
    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format (H:MM:SS.CC)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"