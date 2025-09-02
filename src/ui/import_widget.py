"""
Import Widget for Media File Selection and Validation
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGroupBox, QTextEdit, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent

from src.core.media_importer import MediaImporter, MediaImportError
from src.core.models import VideoFile, AudioFile, ImageFile, SubtitleFile, MediaType


class ImportWidget(QWidget):
    """Widget for importing and validating media files with drag-and-drop support"""
    
    # Signals for file import events
    video_imported = pyqtSignal(VideoFile)
    audio_imported = pyqtSignal(AudioFile)
    image_imported = pyqtSignal(ImageFile)
    subtitle_imported = pyqtSignal(SubtitleFile)
    import_error = pyqtSignal(str, str)  # file_path, error_message
    project_loaded = pyqtSignal(object)  # Project object when ready for processing
    
    def __init__(self):
        super().__init__()
        self.media_importer = MediaImporter(self)
        self._imported_files = {}
        self.file_manager = None
        self._setup_ui()
        self._setup_drag_drop()
        self._connect_signals()
    
    def set_file_manager(self, file_manager):
        """Set the file manager for file validation and storage checks"""
        self.file_manager = file_manager
        
    def _setup_ui(self):
        """Set up the import widget UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Import Media Files")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Import your media files to create a karaoke video. "
            "You need either a video file OR an image background, plus audio and subtitle files."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; margin: 10px;")
        layout.addWidget(instructions)
        
        # File import sections
        video_section = self._create_video_section()
        audio_section = self._create_audio_section()
        subtitle_section = self._create_subtitle_section()
        
        layout.addWidget(video_section)
        layout.addWidget(audio_section)
        layout.addWidget(subtitle_section)
        
        # File information display
        self._create_info_section(layout)
        
        layout.addStretch()
    
    def _setup_drag_drop(self):
        """Enable drag and drop functionality"""
        self.setAcceptDrops(True)
    
    def _connect_signals(self):
        """Connect MediaImporter signals to widget handlers"""
        self.media_importer.import_started.connect(self._on_import_started)
        self.media_importer.import_completed.connect(self._on_import_completed)
        self.media_importer.import_failed.connect(self._on_import_failed)
        self.media_importer.metadata_extracted.connect(self._on_metadata_extracted)
        
    def _create_video_section(self):
        """Create video/image import section"""
        group = QGroupBox("Video/Background")
        layout = QVBoxLayout(group)
        
        # Video file button
        video_btn = QPushButton("Select Video File (MP4, MOV, AVI)")
        video_btn.clicked.connect(self._select_video_file)
        layout.addWidget(video_btn)
        
        # OR label
        or_label = QLabel("OR")
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        or_label.setStyleSheet("font-weight: bold; margin: 5px;")
        layout.addWidget(or_label)
        
        # Image file button
        image_btn = QPushButton("Select Image Background (JPG, PNG, BMP)")
        image_btn.clicked.connect(self._select_image_file)
        layout.addWidget(image_btn)
        
        return group
        
    def _create_audio_section(self):
        """Create audio import section"""
        group = QGroupBox("Audio Track")
        layout = QVBoxLayout(group)
        
        audio_btn = QPushButton("Select Audio File (MP3, WAV, AAC)")
        audio_btn.clicked.connect(self._select_audio_file)
        layout.addWidget(audio_btn)
        
        return group
        
    def _create_subtitle_section(self):
        """Create subtitle import section"""
        group = QGroupBox("Subtitles")
        layout = QVBoxLayout(group)
        
        subtitle_btn = QPushButton("Select Subtitle File (.ass format)")
        subtitle_btn.clicked.connect(self._select_subtitle_file)
        layout.addWidget(subtitle_btn)
        
        return group
        
    def _create_info_section(self, parent_layout):
        """Create file information display section"""
        group = QGroupBox("Imported Files Information")
        layout = QVBoxLayout(group)
        
        self.info_display = QTextEdit()
        self.info_display.setMaximumHeight(150)
        self.info_display.setReadOnly(True)
        self.info_display.setPlainText("No files imported yet...")
        layout.addWidget(self.info_display)
        
        # Create Project button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.create_project_button = QPushButton("Create Project")
        self.create_project_button.setEnabled(False)  # Disabled until files are imported
        self.create_project_button.clicked.connect(self.validate_storage_and_create_project)
        self.create_project_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        button_layout.addWidget(self.create_project_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        parent_layout.addWidget(group)
        
    def _select_video_file(self):
        """Handle video file selection"""
        try:
            video_file = self.media_importer.import_video()
            if video_file:
                self._imported_files['video'] = video_file
                self.video_imported.emit(video_file)
        except MediaImportError as e:
            self._show_error("Video Import Error", str(e))
        
    def _select_image_file(self):
        """Handle image file selection"""
        try:
            image_file = self.media_importer.import_image()
            if image_file:
                self._imported_files['image'] = image_file
                self.image_imported.emit(image_file)
        except MediaImportError as e:
            self._show_error("Image Import Error", str(e))
        
    def _select_audio_file(self):
        """Handle audio file selection"""
        try:
            audio_file = self.media_importer.import_audio()
            if audio_file:
                self._imported_files['audio'] = audio_file
                self.audio_imported.emit(audio_file)
        except MediaImportError as e:
            self._show_error("Audio Import Error", str(e))
        
    def _select_subtitle_file(self):
        """Handle subtitle file selection"""
        try:
            subtitle_file = self.media_importer.import_subtitles()
            if subtitle_file:
                self._imported_files['subtitle'] = subtitle_file
                self.subtitle_imported.emit(subtitle_file)
        except MediaImportError as e:
            self._show_error("Subtitle Import Error", str(e))
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for file drops"""
        if event.mimeData().hasUrls():
            # Check if any of the dragged files are supported
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self._is_supported_file(file_path):
                        event.acceptProposedAction()
                        return
        event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop events"""
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                self._import_dropped_file(file_path)
        event.acceptProposedAction()
    
    def _is_supported_file(self, file_path: str) -> bool:
        """Check if a file is supported by any media type"""
        for media_type in [MediaType.VIDEO, MediaType.AUDIO, MediaType.IMAGE, MediaType.SUBTITLE]:
            if self.media_importer.validate_file(file_path, media_type):
                return True
        return False
    
    def _import_dropped_file(self, file_path: str):
        """Import a file that was dropped onto the widget"""
        try:
            # Validate file integrity first if file manager is available
            if self.file_manager:
                is_valid, error_msg = self.file_manager.validate_file_integrity(file_path)
                if not is_valid:
                    self._show_error("File Validation Error", error_msg)
                    return
            
            # Determine file type and import accordingly
            if self.media_importer.validate_file(file_path, MediaType.VIDEO):
                video_file = self.media_importer.import_video(file_path)
                if video_file:
                    self._imported_files['video'] = video_file
                    self.video_imported.emit(video_file)
            elif self.media_importer.validate_file(file_path, MediaType.AUDIO):
                audio_file = self.media_importer.import_audio(file_path)
                if audio_file:
                    self._imported_files['audio'] = audio_file
                    self.audio_imported.emit(audio_file)
            elif self.media_importer.validate_file(file_path, MediaType.IMAGE):
                image_file = self.media_importer.import_image(file_path)
                if image_file:
                    self._imported_files['image'] = image_file
                    self.image_imported.emit(image_file)
            elif self.media_importer.validate_file(file_path, MediaType.SUBTITLE):
                subtitle_file = self.media_importer.import_subtitles(file_path)
                if subtitle_file:
                    self._imported_files['subtitle'] = subtitle_file
                    self.subtitle_imported.emit(subtitle_file)
            else:
                self._show_error("Unsupported File", f"File format not supported: {Path(file_path).suffix}")
        except MediaImportError as e:
            self._show_error("Import Error", str(e))
    
    def _on_import_started(self, file_path: str):
        """Handle import started signal"""
        filename = Path(file_path).name
        self.info_display.append(f"Importing {filename}...")
    
    def _on_import_completed(self, media_file):
        """Handle import completed signal"""
        filename = Path(media_file.path).name
        file_type = type(media_file).__name__.replace('File', '').lower()
        
        # CRITICAL FIX: Store the imported file in the dictionary
        # This was missing and causing the Create Project button to stay disabled
        if file_type == 'video':
            self._imported_files['video'] = media_file
        elif file_type == 'audio':
            self._imported_files['audio'] = media_file
        elif file_type == 'image':
            self._imported_files['image'] = media_file
        elif file_type == 'subtitle':
            self._imported_files['subtitle'] = media_file
        
        # Format file information
        info_lines = [f"✓ {file_type.title()}: {filename}"]
        
        if hasattr(media_file, 'duration') and media_file.duration > 0:
            duration_str = self._format_duration(media_file.duration)
            info_lines.append(f"  Duration: {duration_str}")
        
        if hasattr(media_file, 'resolution') and media_file.resolution['width'] > 0:
            width = media_file.resolution['width']
            height = media_file.resolution['height']
            info_lines.append(f"  Resolution: {width}x{height}")
        
        if hasattr(media_file, 'sample_rate') and media_file.sample_rate > 0:
            info_lines.append(f"  Sample Rate: {media_file.sample_rate} Hz")
            info_lines.append(f"  Channels: {media_file.channels}")
        
        if hasattr(media_file, 'frame_rate') and media_file.frame_rate > 0:
            info_lines.append(f"  Frame Rate: {media_file.frame_rate:.2f} fps")
        
        if media_file.file_size > 0:
            size_str = self._format_file_size(media_file.file_size)
            info_lines.append(f"  Size: {size_str}")
        
        self.info_display.append('\n'.join(info_lines))
        
        # Enable Create Project button if all required files are imported
        if hasattr(self, 'create_project_button'):
            self.create_project_button.setEnabled(self.has_required_files())
    
    def _on_import_failed(self, file_path: str, error_message: str):
        """Handle import failed signal"""
        filename = Path(file_path).name
        self.info_display.append(f"✗ Failed to import {filename}: {error_message}")
        self.import_error.emit(file_path, error_message)
    
    def _on_metadata_extracted(self, file_path: str, metadata: dict):
        """Handle metadata extracted signal"""
        # Metadata is already incorporated into the file object
        pass
    
    def _show_error(self, title: str, message: str):
        """Show error message dialog"""
        QMessageBox.critical(self, title, message)
    
    def _format_duration(self, duration: float) -> str:
        """Format duration in seconds to MM:SS format"""
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def get_imported_files(self) -> dict:
        """Get dictionary of imported files"""
        return self._imported_files.copy()
    
    def clear_imports(self):
        """Clear all imported files"""
        self._imported_files.clear()
        self.info_display.clear()
        self.info_display.setPlainText("No files imported yet...")
        
        # Disable Create Project button
        if hasattr(self, 'create_project_button'):
            self.create_project_button.setEnabled(False)
    
    def has_required_files(self) -> bool:
        """Check if all required files are imported"""
        has_background = 'video' in self._imported_files or 'image' in self._imported_files
        has_audio = 'audio' in self._imported_files
        has_subtitles = 'subtitle' in self._imported_files
        return has_background and has_audio and has_subtitles
    
    def refresh_button_state(self):
        """Manually refresh the Create Project button state - useful for debugging"""
        if hasattr(self, 'create_project_button'):
            should_enable = self.has_required_files()
            self.create_project_button.setEnabled(should_enable)
            return should_enable
        return False
    
    def validate_storage_and_create_project(self):
        """Validate storage space and create project if sufficient"""
        if not self.has_required_files():
            self._show_error("Incomplete Project", 
                           "Please import all required files: background (video or image), audio, and subtitles.")
            return False
        
        # Validate storage space if file manager is available
        if self.file_manager:
            # Estimate processing size (rough calculation)
            estimated_size_mb = 0
            
            # Add file sizes
            for file_type, media_file in self._imported_files.items():
                if hasattr(media_file, 'path') and os.path.exists(media_file.path):
                    file_size = os.path.getsize(media_file.path)
                    estimated_size_mb += file_size / (1024 * 1024)
            
            # Add buffer for processing (2x the input size)
            estimated_size_mb *= 2
            
            # Validate storage
            sufficient, warning = self.file_manager.validate_storage_before_processing(estimated_size_mb)
            if not sufficient:
                self._show_error("Insufficient Storage", warning)
                return False
            elif warning:
                # Show warning but allow to continue
                reply = QMessageBox.question(
                    self,
                    "Storage Warning",
                    f"{warning}\n\nDo you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return False
        
        # Create project object (simplified for now)
        project = type('Project', (), {
            'name': 'Karaoke Project',
            'video_file': self._imported_files.get('video'),
            'image_file': self._imported_files.get('image'),
            'audio_file': self._imported_files.get('audio'),
            'subtitle_file': self._imported_files.get('subtitle'),
            'files': self._imported_files.copy()
        })()
        
        # Emit project loaded signal
        self.project_loaded.emit(project)
        return True