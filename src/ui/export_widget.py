"""
Export Widget for Video Export Configuration and Processing
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QGroupBox, QComboBox, QSpinBox, QPushButton,
    QProgressBar, QTextEdit, QFileDialog, QLineEdit,
    QCheckBox, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Optional

try:
    from src.core.export_manager import ExportManager, ExportConfiguration
    from src.core.models import Project
    from src.core.validation import ValidationLevel
except ImportError:
    from export_manager import ExportManager, ExportConfiguration
    from models import Project
    from validation import ValidationLevel


class ExportWidget(QWidget):
    """Widget for configuring and executing video export"""
    
    # Export signals
    export_started = pyqtSignal(dict)
    export_cancelled = pyqtSignal()
    export_completed = pyqtSignal(str)  # output_path
    export_failed = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        
        # Initialize export manager
        self.export_manager = ExportManager()
        self.current_project: Optional[Project] = None
        
        self._setup_ui()
        self._connect_export_manager()
        self._export_in_progress = False
        
    def _setup_ui(self):
        """Set up the export widget UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Export Karaoke Video")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Export settings
        self._create_export_settings(layout)
        
        # Output settings
        self._create_output_settings(layout)
        
        # Export controls
        self._create_export_controls(layout)
        
        # Progress section
        self._create_progress_section(layout)
        
    def _connect_export_manager(self):
        """Connect export manager signals to UI updates."""
        self.export_manager.export_started.connect(self._on_export_started)
        self.export_manager.export_progress.connect(self._on_export_progress)
        self.export_manager.export_completed.connect(self._on_export_completed)
        self.export_manager.export_failed.connect(self._on_export_failed)
        self.export_manager.export_cancelled.connect(self._on_export_cancelled)
        self.export_manager.validation_completed.connect(self._on_validation_completed)
        
    def _create_export_settings(self, parent_layout):
        """Create export quality and format settings"""
        settings_group = QGroupBox("Export Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Quality preset
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Quality Preset:"))
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low (720p)", "Medium (1080p)", "High (1080p HQ)", "Custom"])
        self.quality_combo.setCurrentText("Medium (1080p)")
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        
        settings_layout.addLayout(quality_layout)
        
        # Resolution settings
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Resolution:"))
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(480, 3840)
        self.width_spinbox.setValue(1920)
        self.width_spinbox.setSuffix(" px")
        resolution_layout.addWidget(self.width_spinbox)
        
        resolution_layout.addWidget(QLabel("×"))
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(360, 2160)
        self.height_spinbox.setValue(1080)
        self.height_spinbox.setSuffix(" px")
        resolution_layout.addWidget(self.height_spinbox)
        resolution_layout.addStretch()
        
        settings_layout.addLayout(resolution_layout)
        
        # Bitrate settings
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("Video Bitrate:"))
        
        self.bitrate_spinbox = QSpinBox()
        self.bitrate_spinbox.setRange(1, 50)
        self.bitrate_spinbox.setValue(8)
        self.bitrate_spinbox.setSuffix(" Mbps")
        bitrate_layout.addWidget(self.bitrate_spinbox)
        bitrate_layout.addStretch()
        
        settings_layout.addLayout(bitrate_layout)
        
        # Format settings
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Format:"))
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (H.264)", "MP4 (H.265)"])
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()
        
        settings_layout.addLayout(format_layout)
        
        parent_layout.addWidget(settings_group)
        
    def _create_output_settings(self, parent_layout):
        """Create output file and directory settings"""
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout(output_group)
        
        # Output directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Directory:"))
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText("./output/")
        self.output_dir_edit.setReadOnly(True)
        dir_layout.addWidget(self.output_dir_edit)
        
        browse_dir_button = QPushButton("Browse...")
        browse_dir_button.clicked.connect(self._browse_output_directory)
        dir_layout.addWidget(browse_dir_button)
        
        output_layout.addLayout(dir_layout)
        
        # Output filename
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("Filename:"))
        
        self.filename_edit = QLineEdit()
        self.filename_edit.setText("karaoke_video.mp4")
        filename_layout.addWidget(self.filename_edit)
        
        output_layout.addLayout(filename_layout)
        
        # Options
        self.cleanup_checkbox = QCheckBox("Clean up temporary files after export")
        self.cleanup_checkbox.setChecked(True)
        output_layout.addWidget(self.cleanup_checkbox)
        
        parent_layout.addWidget(output_group)
        
    def _create_export_controls(self, parent_layout):
        """Create export control buttons"""
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        self.export_button = QPushButton("Start Export")
        self.export_button.clicked.connect(self._start_export)
        self.export_button.setMinimumWidth(120)
        controls_layout.addWidget(self.export_button)
        
        self.cancel_button = QPushButton("Cancel Export")
        self.cancel_button.clicked.connect(self._cancel_export)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setMinimumWidth(120)
        controls_layout.addWidget(self.cancel_button)
        
        controls_layout.addStretch()
        parent_layout.addLayout(controls_layout)
        
    def _create_progress_section(self, parent_layout):
        """Create export progress display"""
        progress_group = QGroupBox("Export Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # Status display
        self.status_display = QTextEdit()
        self.status_display.setMaximumHeight(150)
        self.status_display.setReadOnly(True)
        self.status_display.setPlainText("Ready to export. Configure settings and click 'Start Export'.")
        progress_layout.addWidget(self.status_display)
        
        parent_layout.addWidget(progress_group)
        
    def _on_quality_changed(self, quality_text):
        """Handle quality preset changes"""
        # Get current configuration
        config = self._get_export_configuration()
        
        # Apply quality preset
        config = self.export_manager.apply_quality_preset(quality_text, config)
        
        # Update UI controls
        self.width_spinbox.setValue(config.width)
        self.height_spinbox.setValue(config.height)
        self.bitrate_spinbox.setValue(config.bitrate // 1000)  # Convert kbps to Mbps for display
        
    def _browse_output_directory(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Output Directory",
            self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)
            
    def _start_export(self):
        """Start the export process"""
        if self._export_in_progress:
            return
        
        # Check if project is loaded
        if not self.current_project:
            QMessageBox.warning(self, "Export Error", "No project loaded. Please import media files first.")
            return
        
        # Get export configuration
        config = self._get_export_configuration()
        
        # Start export using export manager
        success = self.export_manager.start_export(config)
        
        if not success:
            QMessageBox.critical(self, "Export Error", "Failed to start export process.")
            return
        
        # Update UI state will be handled by export manager signals
        
    def _cancel_export(self):
        """Cancel the export process"""
        if self._export_in_progress:
            self.export_manager.cancel_export()
            # UI state will be updated by export manager signals
        

        
    def _get_export_configuration(self) -> ExportConfiguration:
        """Get current export configuration from UI controls."""
        return ExportConfiguration(
            width=self.width_spinbox.value(),
            height=self.height_spinbox.value(),
            bitrate=self.bitrate_spinbox.value() * 1000,  # Convert Mbps to kbps
            output_dir=self.output_dir_edit.text(),
            filename=self.filename_edit.text(),
            format=self.format_combo.currentText(),
            cleanup_temp=self.cleanup_checkbox.isChecked(),
            quality_preset=self.quality_combo.currentText()
        )
    
    def load_project(self, project: Project):
        """Load a project for export."""
        self.current_project = project
        self.export_manager.set_project(project)
        
        # Update UI to show project is loaded
        if project:
            self.status_display.append(f"Project loaded: {project.name}")
            
            # Update filename suggestion based on project
            if project.name and project.name != "Untitled":
                suggested_name = f"{project.name}_karaoke.mp4"
                self.filename_edit.setText(suggested_name)
        else:
            self.status_display.append("No project loaded")
    
    def _on_export_started(self):
        """Handle export start from export manager."""
        self._export_in_progress = True
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.status_display.append("Export started...")
        self.export_started.emit(self._get_export_configuration().__dict__)
    
    def _on_export_progress(self, progress_info: dict):
        """Handle export progress updates."""
        progress_percent = progress_info.get('progress_percent', 0)
        status = progress_info.get('status', 'Processing...')
        fps = progress_info.get('fps', 0)
        elapsed = progress_info.get('elapsed_time', 0)
        remaining = progress_info.get('estimated_remaining', 0)
        
        # Update progress bar (convert float to int)
        self.progress_bar.setValue(int(progress_percent))
        
        # Update status display
        if int(progress_percent) % 10 == 0 or progress_percent >= 95:  # Update every 10% or near completion
            self.status_display.append(f"Progress: {progress_percent}% - {status}")
            
            if fps > 0:
                self.status_display.append(f"Rendering at {fps:.1f} fps - Elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")
    
    def _on_export_completed(self, output_path: str):
        """Handle export completion."""
        self._export_in_progress = False
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(100)
        
        self.status_display.append("Export completed successfully!")
        self.status_display.append(f"Video saved to: {output_path}")
        
        # Show completion message
        QMessageBox.information(
            self, 
            "Export Complete", 
            f"Karaoke video exported successfully!\n\nSaved to: {output_path}"
        )
        
        self.export_completed.emit(output_path)
    
    def _on_export_failed(self, error_message: str):
        """Handle export failure."""
        self._export_in_progress = False
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.status_display.append(f"Export failed: {error_message}")
        
        # Show error message
        QMessageBox.critical(
            self,
            "Export Failed",
            f"Export failed with error:\n\n{error_message}"
        )
        
        self.export_failed.emit(error_message)
    
    def _on_export_cancelled(self):
        """Handle export cancellation."""
        self._export_in_progress = False
        self.export_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.status_display.append("Export cancelled by user.")
        self.export_cancelled.emit()
    
    def _on_validation_completed(self, validation_results):
        """Handle validation results from export manager."""
        # Display validation messages
        for result in validation_results:
            if result.level == ValidationLevel.ERROR:
                self.status_display.append(f"ERROR: {result.message}")
                if result.suggestion:
                    self.status_display.append(f"  Suggestion: {result.suggestion}")
            elif result.level == ValidationLevel.WARNING:
                self.status_display.append(f"WARNING: {result.message}")
                if result.suggestion:
                    self.status_display.append(f"  Suggestion: {result.suggestion}")
            elif result.level == ValidationLevel.INFO:
                self.status_display.append(f"INFO: {result.message}")
    
    def _export_completed(self):
        """Legacy method - replaced by _on_export_completed"""
        pass
    
    def update_default_settings(self, export_settings):
        """Update the widget with new default export settings"""
        # Update resolution
        self.width_spinbox.setValue(export_settings.resolution["width"])
        self.height_spinbox.setValue(export_settings.resolution["height"])
        
        # Update bitrate (convert from kbps to Mbps for display)
        self.bitrate_spinbox.setValue(export_settings.bitrate // 1000)
        
        # Update output directory
        self.output_dir_edit.setText(export_settings.output_directory)
        
        # Update quality preset based on settings
        if export_settings.quality == "low":
            self.quality_combo.setCurrentText("Low (720p)")
        elif export_settings.quality == "medium":
            self.quality_combo.setCurrentText("Medium (1080p)")
        elif export_settings.quality == "high":
            self.quality_combo.setCurrentText("High (1080p HQ)")
        else:
            self.quality_combo.setCurrentText("Custom")
    
    def set_file_manager(self, file_manager):
        """Set the file manager for the export widget"""
        # Pass file manager to export manager if needed
        if hasattr(self.export_manager, 'set_file_manager'):
            self.export_manager.set_file_manager(file_manager)