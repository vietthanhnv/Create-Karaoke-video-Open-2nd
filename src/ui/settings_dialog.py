"""
Settings Dialog for Karaoke Video Creator Application

This module provides a user interface for configuring application settings,
including default export settings, directories, and user preferences.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QGroupBox, QFormLayout, QFileDialog,
    QDialogButtonBox, QMessageBox, QListWidget, QListWidgetItem,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional

from src.core.settings_manager import SettingsManager
from src.core.models import ExportSettings


class SettingsDialog(QDialog):
    """
    Settings dialog for configuring application preferences.
    
    Provides tabs for:
    - General preferences
    - Default export settings
    - Directory settings
    - Recent projects management
    """
    
    settings_applied = pyqtSignal()
    
    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        self._setup_ui()
        self._load_current_settings()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self._create_general_tab()
        self._create_export_tab()
        self._create_directories_tab()
        self._create_projects_tab()
        
        # Create button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        layout.addWidget(self.button_box)
    
    def _create_general_tab(self):
        """Create the general preferences tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Application preferences group
        app_group = QGroupBox("Application Preferences")
        app_layout = QFormLayout(app_group)
        
        self.auto_save_checkbox = QCheckBox("Auto-save projects")
        self.auto_save_checkbox.setToolTip("Automatically save project changes")
        app_layout.addRow("Auto-save:", self.auto_save_checkbox)
        
        self.cleanup_temp_checkbox = QCheckBox("Cleanup temporary files on exit")
        self.cleanup_temp_checkbox.setToolTip("Remove temporary files when closing the application")
        app_layout.addRow("Cleanup temp files:", self.cleanup_temp_checkbox)
        
        self.show_tooltips_checkbox = QCheckBox("Show tooltips")
        self.show_tooltips_checkbox.setToolTip("Display helpful tooltips in the interface")
        app_layout.addRow("Show tooltips:", self.show_tooltips_checkbox)
        
        layout.addWidget(app_group)
        
        # UI preferences group
        ui_group = QGroupBox("User Interface")
        ui_layout = QFormLayout(ui_group)
        
        # Note: Window geometry and state are handled automatically
        ui_info = QLabel("Window size and position are saved automatically.")
        ui_info.setStyleSheet("color: gray; font-style: italic;")
        ui_layout.addRow(ui_info)
        
        layout.addWidget(ui_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "General")
    
    def _create_export_tab(self):
        """Create the export settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Video settings group
        video_group = QGroupBox("Default Video Settings")
        video_layout = QFormLayout(video_group)
        
        # Resolution
        resolution_layout = QHBoxLayout()
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(480, 7680)  # 480p to 8K
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.setValue(1920)
        
        resolution_layout.addWidget(self.width_spinbox)
        resolution_layout.addWidget(QLabel("×"))
        
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(360, 4320)  # 360p to 8K
        self.height_spinbox.setSuffix(" px")
        self.height_spinbox.setValue(1080)
        
        resolution_layout.addWidget(self.height_spinbox)
        resolution_layout.addStretch()
        
        video_layout.addRow("Resolution:", resolution_layout)
        
        # Frame rate
        self.frame_rate_spinbox = QDoubleSpinBox()
        self.frame_rate_spinbox.setRange(15.0, 120.0)
        self.frame_rate_spinbox.setSuffix(" fps")
        self.frame_rate_spinbox.setDecimals(1)
        self.frame_rate_spinbox.setValue(30.0)
        video_layout.addRow("Frame Rate:", self.frame_rate_spinbox)
        
        # Video bitrate
        self.video_bitrate_spinbox = QSpinBox()
        self.video_bitrate_spinbox.setRange(500, 50000)
        self.video_bitrate_spinbox.setSuffix(" kbps")
        self.video_bitrate_spinbox.setValue(5000)
        video_layout.addRow("Video Bitrate:", self.video_bitrate_spinbox)
        
        # Quality preset
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["low", "medium", "high", "custom"])
        self.quality_combo.setCurrentText("high")
        video_layout.addRow("Quality Preset:", self.quality_combo)
        
        layout.addWidget(video_group)
        
        # Audio settings group
        audio_group = QGroupBox("Default Audio Settings")
        audio_layout = QFormLayout(audio_group)
        
        # Audio bitrate
        self.audio_bitrate_spinbox = QSpinBox()
        self.audio_bitrate_spinbox.setRange(64, 320)
        self.audio_bitrate_spinbox.setSuffix(" kbps")
        self.audio_bitrate_spinbox.setValue(192)
        audio_layout.addRow("Audio Bitrate:", self.audio_bitrate_spinbox)
        
        layout.addWidget(audio_group)
        
        # Preset buttons
        preset_layout = QHBoxLayout()
        
        self.preset_720p_btn = QPushButton("720p HD")
        self.preset_720p_btn.clicked.connect(lambda: self._apply_preset(1280, 720, 30.0, 3000))
        preset_layout.addWidget(self.preset_720p_btn)
        
        self.preset_1080p_btn = QPushButton("1080p Full HD")
        self.preset_1080p_btn.clicked.connect(lambda: self._apply_preset(1920, 1080, 30.0, 5000))
        preset_layout.addWidget(self.preset_1080p_btn)
        
        self.preset_4k_btn = QPushButton("4K UHD")
        self.preset_4k_btn.clicked.connect(lambda: self._apply_preset(3840, 2160, 30.0, 15000))
        preset_layout.addWidget(self.preset_4k_btn)
        
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "Export Defaults")
    
    def _create_directories_tab(self):
        """Create the directories settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Directories group
        dirs_group = QGroupBox("Default Directories")
        dirs_layout = QFormLayout(dirs_group)
        
        # Input directory
        input_layout = QHBoxLayout()
        self.input_dir_edit = QLineEdit()
        self.input_dir_edit.setReadOnly(True)
        input_layout.addWidget(self.input_dir_edit)
        
        self.input_dir_btn = QPushButton("Browse...")
        self.input_dir_btn.clicked.connect(lambda: self._browse_directory(self.input_dir_edit))
        input_layout.addWidget(self.input_dir_btn)
        
        dirs_layout.addRow("Input Directory:", input_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        output_layout.addWidget(self.output_dir_edit)
        
        self.output_dir_btn = QPushButton("Browse...")
        self.output_dir_btn.clicked.connect(lambda: self._browse_directory(self.output_dir_edit))
        output_layout.addWidget(self.output_dir_btn)
        
        dirs_layout.addRow("Output Directory:", output_layout)
        
        # Temp directory
        temp_layout = QHBoxLayout()
        self.temp_dir_edit = QLineEdit()
        self.temp_dir_edit.setReadOnly(True)
        temp_layout.addWidget(self.temp_dir_edit)
        
        self.temp_dir_btn = QPushButton("Browse...")
        self.temp_dir_btn.clicked.connect(lambda: self._browse_directory(self.temp_dir_edit))
        temp_layout.addWidget(self.temp_dir_btn)
        
        dirs_layout.addRow("Temp Directory:", temp_layout)
        
        layout.addWidget(dirs_group)
        
        # Directory info
        info_label = QLabel(
            "These directories will be used as defaults when importing media files "
            "and exporting videos. The temp directory is used for intermediate files "
            "during processing."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "Directories")
    
    def _create_projects_tab(self):
        """Create the recent projects management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Recent projects group
        projects_group = QGroupBox("Recent Projects")
        projects_layout = QVBoxLayout(projects_group)
        
        # Projects list
        self.projects_list = QListWidget()
        projects_layout.addWidget(self.projects_list)
        
        # Projects buttons
        projects_btn_layout = QHBoxLayout()
        
        self.remove_project_btn = QPushButton("Remove Selected")
        self.remove_project_btn.clicked.connect(self._remove_selected_project)
        self.remove_project_btn.setEnabled(False)
        projects_btn_layout.addWidget(self.remove_project_btn)
        
        self.clear_projects_btn = QPushButton("Clear All")
        self.clear_projects_btn.clicked.connect(self._clear_all_projects)
        projects_btn_layout.addWidget(self.clear_projects_btn)
        
        projects_btn_layout.addStretch()
        projects_layout.addLayout(projects_btn_layout)
        
        layout.addWidget(projects_group)
        
        # Settings export/import group
        settings_group = QGroupBox("Settings Management")
        settings_layout = QHBoxLayout(settings_group)
        
        self.export_settings_btn = QPushButton("Export Settings...")
        self.export_settings_btn.clicked.connect(self._export_settings)
        settings_layout.addWidget(self.export_settings_btn)
        
        self.import_settings_btn = QPushButton("Import Settings...")
        self.import_settings_btn.clicked.connect(self._import_settings)
        settings_layout.addWidget(self.import_settings_btn)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "Projects & Settings")
    
    def _connect_signals(self):
        """Connect dialog signals"""
        # Button box signals
        self.button_box.accepted.connect(self._apply_and_accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._apply_settings)
        self.button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self._restore_defaults)
        
        # Projects list selection
        self.projects_list.itemSelectionChanged.connect(self._on_project_selection_changed)
        
        # Quality combo change
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
    
    def _load_current_settings(self):
        """Load current settings into the dialog"""
        # General settings
        self.auto_save_checkbox.setChecked(self.settings_manager.get_auto_save_projects())
        self.cleanup_temp_checkbox.setChecked(self.settings_manager.get_cleanup_temp_on_exit())
        self.show_tooltips_checkbox.setChecked(self.settings_manager.get_show_tooltips())
        
        # Export settings
        export_settings = self.settings_manager.get_default_export_settings()
        self.width_spinbox.setValue(export_settings.resolution["width"])
        self.height_spinbox.setValue(export_settings.resolution["height"])
        self.frame_rate_spinbox.setValue(export_settings.frame_rate)
        self.video_bitrate_spinbox.setValue(export_settings.bitrate)
        self.audio_bitrate_spinbox.setValue(export_settings.audio_bitrate)
        self.quality_combo.setCurrentText(export_settings.quality)
        
        # Directory settings
        self.input_dir_edit.setText(self.settings_manager.get_input_directory())
        self.output_dir_edit.setText(self.settings_manager.get_output_directory())
        self.temp_dir_edit.setText(self.settings_manager.get_temp_directory())
        
        # Recent projects
        self._load_recent_projects()
    
    def _load_recent_projects(self):
        """Load recent projects into the list"""
        self.projects_list.clear()
        
        recent_projects = self.settings_manager.get_recent_projects()
        for project in recent_projects:
            item = QListWidgetItem()
            item.setText(f"{project.get('name', 'Unknown')} - {project.get('path', '')}")
            item.setData(Qt.ItemDataRole.UserRole, project)
            self.projects_list.addItem(item)
    
    def _apply_preset(self, width: int, height: int, fps: float, bitrate: int):
        """Apply a quality preset"""
        self.width_spinbox.setValue(width)
        self.height_spinbox.setValue(height)
        self.frame_rate_spinbox.setValue(fps)
        self.video_bitrate_spinbox.setValue(bitrate)
        self.quality_combo.setCurrentText("custom")
    
    def _browse_directory(self, line_edit: QLineEdit):
        """Browse for a directory"""
        current_path = line_edit.text()
        if not current_path:
            current_path = str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            current_path
        )
        
        if directory:
            line_edit.setText(directory)
    
    def _on_project_selection_changed(self):
        """Handle project selection change"""
        has_selection = bool(self.projects_list.selectedItems())
        self.remove_project_btn.setEnabled(has_selection)
    
    def _on_quality_changed(self, quality: str):
        """Handle quality preset change"""
        if quality == "low":
            self._apply_preset(1280, 720, 30.0, 2000)
        elif quality == "medium":
            self._apply_preset(1920, 1080, 30.0, 3500)
        elif quality == "high":
            self._apply_preset(1920, 1080, 30.0, 5000)
        # "custom" doesn't change values
    
    def _remove_selected_project(self):
        """Remove selected project from recent list"""
        current_item = self.projects_list.currentItem()
        if current_item:
            project_data = current_item.data(Qt.ItemDataRole.UserRole)
            if project_data and "path" in project_data:
                self.settings_manager.remove_recent_project(project_data["path"])
                self._load_recent_projects()
    
    def _clear_all_projects(self):
        """Clear all recent projects"""
        reply = QMessageBox.question(
            self,
            "Clear Recent Projects",
            "Are you sure you want to clear all recent projects?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.clear_recent_projects()
            self._load_recent_projects()
    
    def _export_settings(self):
        """Export settings to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            "karaoke_settings.json",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if self.settings_manager.export_settings(file_path):
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Settings exported successfully to:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to export settings. Please check the file path and permissions."
                )
    
    def _import_settings(self):
        """Import settings from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            reply = QMessageBox.question(
                self,
                "Import Settings",
                "Importing settings will overwrite current settings. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if self.settings_manager.import_settings(file_path):
                    QMessageBox.information(
                        self,
                        "Import Successful",
                        "Settings imported successfully. Please restart the application for all changes to take effect."
                    )
                    self._load_current_settings()  # Reload the dialog
                else:
                    QMessageBox.warning(
                        self,
                        "Import Failed",
                        "Failed to import settings. Please check the file format and content."
                    )
    
    def _apply_settings(self):
        """Apply current settings without closing dialog"""
        # General settings
        self.settings_manager.set_auto_save_projects(self.auto_save_checkbox.isChecked())
        self.settings_manager.set_cleanup_temp_on_exit(self.cleanup_temp_checkbox.isChecked())
        self.settings_manager.set_show_tooltips(self.show_tooltips_checkbox.isChecked())
        
        # Export settings
        export_settings = ExportSettings(
            resolution={
                "width": self.width_spinbox.value(),
                "height": self.height_spinbox.value()
            },
            bitrate=self.video_bitrate_spinbox.value(),
            format="mp4",
            quality=self.quality_combo.currentText(),
            frame_rate=self.frame_rate_spinbox.value(),
            audio_bitrate=self.audio_bitrate_spinbox.value(),
            output_directory=self.output_dir_edit.text()
        )
        self.settings_manager.set_default_export_settings(export_settings)
        
        # Directory settings
        self.settings_manager.set_input_directory(self.input_dir_edit.text())
        self.settings_manager.set_output_directory(self.output_dir_edit.text())
        self.settings_manager.set_temp_directory(self.temp_dir_edit.text())
        
        # Sync settings
        self.settings_manager.sync()
        
        # Emit signal
        self.settings_applied.emit()
    
    def _apply_and_accept(self):
        """Apply settings and close dialog"""
        self._apply_settings()
        self.accept()
    
    def _restore_defaults(self):
        """Restore default settings"""
        reply = QMessageBox.question(
            self,
            "Restore Defaults",
            "Are you sure you want to restore all settings to defaults? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            self._load_current_settings()
            QMessageBox.information(
                self,
                "Defaults Restored",
                "All settings have been restored to defaults."
            )