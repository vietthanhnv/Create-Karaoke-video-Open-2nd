"""
Main Window for Karaoke Video Creator Application
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QMenuBar, QStatusBar, QLabel,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QKeySequence, QAction

from src.ui.import_widget import ImportWidget
from src.ui.detachable_preview_widget import DetachablePreviewWidget
from src.ui.editor_widget import EditorWidget
from src.ui.effects_widget import EffectsWidget
from src.ui.export_widget import ExportWidget
from src.ui.settings_dialog import SettingsDialog
from src.core.file_manager import FileManager
from src.core.settings_manager import SettingsManager


class MainWindow(QMainWindow):
    """Main application window with tabbed workflow interface"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Karaoke Video Creator")
        self.setMinimumSize(1200, 800)
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Initialize file manager for directory structure and cleanup
        self.file_manager = FileManager()
        
        # Initialize UI components
        self._setup_ui()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._connect_signals()
        self._connect_file_manager_signals()
        self._connect_settings_signals()
        
        # Restore window state
        self._restore_window_state()
        
    def _setup_ui(self):
        """Set up the main UI layout with tabbed interface"""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout(central_widget)
        
        # Create tabbed interface for workflow steps
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create workflow tabs
        self.import_widget = ImportWidget()
        self.preview_widget = DetachablePreviewWidget()
        self.editor_widget = EditorWidget()
        self.effects_widget = EffectsWidget()
        self.export_widget = ExportWidget()
        
        # Pass file manager to widgets that need it
        if hasattr(self.import_widget, 'set_file_manager'):
            self.import_widget.set_file_manager(self.file_manager)
        if hasattr(self.export_widget, 'set_file_manager'):
            self.export_widget.set_file_manager(self.file_manager)
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.import_widget, "1. Import Media")
        self.tab_widget.addTab(self.preview_widget, "2. Preview")
        self.tab_widget.addTab(self.editor_widget, "3. Edit Subtitles")
        self.tab_widget.addTab(self.effects_widget, "4. Text Effects")
        self.tab_widget.addTab(self.export_widget, "5. Export Video")
        
        # Set up preview widget for detaching/merging
        self.preview_widget.set_parent_tab_widget(self.tab_widget, 1, "2. Preview")
        
    def _setup_menu_bar(self):
        """Set up the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _setup_status_bar(self):
        """Set up the status bar with progress indicators"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress indicator (will be added when needed)
        self.status_bar.showMessage("Application started successfully")
        
    def _connect_signals(self):
        """Connect signals between widgets"""
        # Tab change handling
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Connect editor to preview for real-time synchronization
        self.editor_widget.subtitles_updated_realtime.connect(
            self.preview_widget.update_subtitles_realtime
        )
        
        # Connect effects widget to preview for real-time effect updates
        self.effects_widget.effect_applied.connect(self._on_effect_applied)
        self.effects_widget.effect_removed.connect(self._on_effect_removed)
        self.effects_widget.effect_parameters_changed.connect(self._on_effect_parameters_changed)
        self.effects_widget.effect_toggled.connect(self._on_effect_toggled)
        self.effects_widget.preset_applied.connect(self._on_preset_applied)
        
        # Connect detachable preview signals
        self.preview_widget.detach_requested.connect(self._on_preview_detached)
        self.preview_widget.attach_requested.connect(self._on_preview_attached)
        self.preview_widget.closed.connect(self._on_preview_closed)
        
        # Connect preview playback controls
        self.preview_widget.play_requested.connect(self._on_preview_play)
        self.preview_widget.pause_requested.connect(self._on_preview_pause)
        self.preview_widget.seek_requested.connect(self._on_preview_seek)
        
        # Connect import widget to preview for project loading
        self.import_widget.project_loaded.connect(self._on_project_loaded)
        
        # Connect export widget signals
        self.export_widget.export_completed.connect(self._on_export_completed)
        self.export_widget.export_failed.connect(self._on_export_failed)
        
        # Connect editor and effects widgets for cross-widget updates
        self.editor_widget.subtitle_selected.connect(self._on_subtitle_selected)
        self.effects_widget.effect_parameters_changed.connect(self._update_preview_effects)
        
    def _on_tab_changed(self, index):
        """Handle tab change events"""
        tab_names = [
            "Import Media", "Preview", "Edit Subtitles", 
            "Text Effects", "Export Video"
        ]
        if 0 <= index < len(tab_names):
            self.status_label.setText(f"Current step: {tab_names[index]}")
            
            # Save current tab index to settings
            self.settings_manager.save_last_tab_index(index)
            
    def _new_project(self):
        """Create a new project"""
        # TODO: Implement new project functionality
        self.status_bar.showMessage("New project created", 2000)
        
    def _open_project(self):
        """Open an existing project"""
        # TODO: Implement open project functionality
        self.status_bar.showMessage("Open project functionality not yet implemented", 2000)
        
    def _save_project(self):
        """Save the current project"""
        # TODO: Implement save project functionality
        self.status_bar.showMessage("Save project functionality not yet implemented", 2000)
    
    def _on_project_loaded(self, project):
        """Handle project loading from import widget"""
        # Load project into preview widget
        if hasattr(self.preview_widget, 'load_project'):
            success = self.preview_widget.load_project(project)
            if success:
                self.status_bar.showMessage("Project loaded successfully", 2000)
                # Also load project into editor and effects widgets
                if hasattr(self.editor_widget, 'load_project'):
                    self.editor_widget.load_project(project)
                if hasattr(self.effects_widget, 'load_project'):
                    self.effects_widget.load_project(project)
                # CRITICAL FIX: Load project into export widget
                if hasattr(self.export_widget, 'load_project'):
                    self.export_widget.load_project(project)
            else:
                self.status_bar.showMessage("Failed to load project", 3000)
    
    def _on_effect_applied(self, effect_id: str, parameters: dict):
        """Handle effect application from effects widget"""
        # Update preview with new effect
        if hasattr(self.preview_widget, 'add_effect'):
            self.preview_widget.add_effect(effect_id, parameters)
        self.status_bar.showMessage(f"Effect applied: {effect_id}", 2000)
    
    def _on_effect_removed(self, effect_id: str):
        """Handle effect removal from effects widget"""
        # Remove effect from preview
        if hasattr(self.preview_widget, 'remove_effect'):
            self.preview_widget.remove_effect(effect_id)
        self.status_bar.showMessage(f"Effect removed: {effect_id}", 2000)
    
    def _on_effect_parameters_changed(self, effect_id: str, parameters: dict):
        """Handle effect parameter changes from effects widget"""
        # Update preview with new parameters
        if hasattr(self.preview_widget, 'update_effect_parameters'):
            self.preview_widget.update_effect_parameters(effect_id, parameters)
        # No status message for parameter changes to avoid spam
    
    def _on_effect_toggled(self, effect_id: str, enabled: bool):
        """Handle effect toggle from effects widget"""
        # Toggle effect in preview
        if hasattr(self.preview_widget, 'toggle_effect'):
            self.preview_widget.toggle_effect(effect_id, enabled)
        status = "enabled" if enabled else "disabled"
        self.status_bar.showMessage(f"Effect {status}: {effect_id}", 2000)
    
    def _on_preset_applied(self, preset_name: str):
        """Handle preset application from effects widget"""
        # Apply preset to preview
        if hasattr(self.preview_widget, 'apply_effect_preset'):
            self.preview_widget.apply_effect_preset(preset_name)
        self.status_bar.showMessage(f"Preset applied: {preset_name}", 2000)
    
    def _on_subtitle_selected(self, index: int):
        """Handle subtitle selection from editor widget"""
        # Could be used to highlight selected subtitle in preview
        self.status_bar.showMessage(f"Subtitle {index + 1} selected", 1000)
    
    def _update_preview_effects(self, effect_id: str, parameters: dict):
        """Update preview with effect changes"""
        # This is called when effects parameters change
        if hasattr(self.preview_widget, 'update_effect_parameters'):
            self.preview_widget.update_effect_parameters(effect_id, parameters)
        
        # Force preview update to show effect changes
        if hasattr(self.preview_widget, 'synchronizer') and self.preview_widget.synchronizer:
            self.preview_widget.synchronizer._update_sync()
    
    def _on_export_completed(self, output_path):
        """Handle export completion"""
        self.status_bar.showMessage(f"Export completed: {output_path}", 5000)
    
    def _on_export_failed(self, error_message):
        """Handle export failure"""
        self.status_bar.showMessage(f"Export failed: {error_message}", 5000)
        
    def _show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Karaoke Video Creator",
            "Karaoke Video Creator v1.0.0\n\n"
            "Create professional karaoke videos with synchronized subtitles and effects.\n\n"
            "Built with PyQt6 and OpenGL"
        )
    
    def _on_preview_play(self):
        """Handle preview play request"""
        # Update status
        self.status_bar.showMessage("Playing preview...", 2000)
        
    def _on_preview_pause(self):
        """Handle preview pause request"""
        # Update status
        self.status_bar.showMessage("Preview paused", 2000)
        
    def _on_preview_seek(self, position: float):
        """Handle preview seek request"""
        # Update status
        self.status_bar.showMessage(f"Seeking to {position:.1%}...", 1000)
        
    def load_project_for_preview(self, project):
        """Load a project into the preview system"""
        # This method would be called by the import widget
        success = self.preview_widget.load_project(project)
        if success:
            self.status_bar.showMessage("Project loaded successfully", 2000)
            # Switch to preview tab
            self.tab_widget.setCurrentIndex(1)  # Preview tab
        else:
            self.status_bar.showMessage("Failed to load project", 3000)
        return success
    
    def _connect_file_manager_signals(self):
        """Connect file manager signals for status updates and warnings"""
        # Connect directory creation signals
        self.file_manager.directory_created.connect(
            lambda path: self.status_bar.showMessage(f"Created directory: {path}", 2000)
        )
        
        # Connect storage warning signals
        self.file_manager.storage_warning.connect(self._on_storage_warning)
        
        # Connect cleanup completion signals
        self.file_manager.cleanup_completed.connect(
            lambda count, files: self.status_bar.showMessage(
                f"Cleaned up {count} temporary files", 2000
            )
        )
        
        # Connect temp file creation/removal for debugging (optional)
        if hasattr(self, 'debug_mode') and self.debug_mode:
            self.file_manager.temp_file_created.connect(
                lambda path: print(f"DEBUG: Temp file created: {path}")
            )
            self.file_manager.temp_file_removed.connect(
                lambda path: print(f"DEBUG: Temp file removed: {path}")
            )
    
    def _on_storage_warning(self, level: str, message: str):
        """Handle storage warning from file manager"""
        if level == "critical":
            QMessageBox.critical(
                self,
                "Critical Storage Warning",
                f"Critical storage issue detected:\n\n{message}\n\n"
                "Please free up disk space before continuing."
            )
        elif level == "low":
            QMessageBox.warning(
                self,
                "Low Storage Warning", 
                f"Low storage space detected:\n\n{message}\n\n"
                "Consider freeing up disk space."
            )
        elif level == "warning":
            self.status_bar.showMessage(f"Storage warning: {message}", 5000)
    
    def get_file_manager(self):
        """Get the file manager instance for use by other components"""
        return self.file_manager
    
    def _connect_settings_signals(self):
        """Connect settings manager signals"""
        # Connect settings change signals for real-time updates
        self.settings_manager.settings_changed.connect(self._on_setting_changed)
        self.settings_manager.export_defaults_changed.connect(self._on_export_defaults_changed)
        self.settings_manager.recent_projects_changed.connect(self._on_recent_projects_changed)
    
    def _restore_window_state(self):
        """Restore window geometry and state from settings"""
        # Restore window geometry
        geometry = self.settings_manager.restore_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state (toolbars, docks, etc.)
        state = self.settings_manager.restore_window_state()
        if state:
            self.restoreState(state)
        
        # Restore last tab index
        last_tab = self.settings_manager.get_last_tab_index()
        if 0 <= last_tab < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(last_tab)
    
    def _save_window_state(self):
        """Save current window geometry and state to settings"""
        # Save window geometry
        self.settings_manager.save_window_geometry(self.saveGeometry())
        
        # Save window state
        self.settings_manager.save_window_state(self.saveState())
        
        # Save current tab index
        self.settings_manager.save_last_tab_index(self.tab_widget.currentIndex())
    
    def _on_settings_applied(self):
        """Handle settings being applied"""
        self.status_bar.showMessage("Settings applied successfully", 2000)
        
        # Update tooltips visibility based on settings
        show_tooltips = self.settings_manager.get_show_tooltips()
        self._update_tooltips_visibility(show_tooltips)
        
        # Update file manager with new temp directory if changed
        temp_dir = self.settings_manager.get_temp_directory()
        if hasattr(self.file_manager, 'set_temp_directory'):
            self.file_manager.set_temp_directory(temp_dir)
    
    def _on_setting_changed(self, key: str, value):
        """Handle individual setting changes"""
        if key == "app/show_tooltips":
            self._update_tooltips_visibility(value)
        elif key.startswith("directories/"):
            # Directory settings changed - could update file manager
            pass
    
    def _on_export_defaults_changed(self, export_settings):
        """Handle export defaults being changed"""
        # Update export widget with new defaults if it exists
        if hasattr(self.export_widget, 'update_default_settings'):
            self.export_widget.update_default_settings(export_settings)
    
    def _on_recent_projects_changed(self, recent_projects):
        """Handle recent projects list changes"""
        # Could update a recent projects menu here
        pass
    
    def _update_tooltips_visibility(self, show_tooltips: bool):
        """Update tooltip visibility for all widgets"""
        # This would recursively update all child widgets
        # For now, just store the preference - individual widgets can check it
        self.show_tooltips = show_tooltips
    
    def get_settings_manager(self):
        """Get the settings manager instance"""
        return self.settings_manager
    
    def _on_preview_detached(self):
        """Handle preview widget being detached"""
        self.status_bar.showMessage("Preview detached to separate window", 2000)
        
    def _on_preview_attached(self):
        """Handle preview widget being reattached"""
        self.status_bar.showMessage("Preview reattached to main window", 2000)
        
    def _on_preview_closed(self):
        """Handle preview widget being closed"""
        self.status_bar.showMessage("Preview closed", 2000)
    
    def closeEvent(self, event):
        """Handle application close event with cleanup and state saving"""
        # Save window state before closing
        self._save_window_state()
        
        # Perform cleanup based on settings
        cleanup_on_exit = self.settings_manager.get_cleanup_temp_on_exit()
        if cleanup_on_exit:
            try:
                results = self.file_manager.emergency_cleanup()
                if results['tracked_files_cleaned'] > 0 or results['orphaned_files_cleaned'] > 0:
                    print(f"Cleanup on exit: {results['tracked_files_cleaned']} tracked files, "
                          f"{results['orphaned_files_cleaned']} orphaned files")
            except Exception as e:
                print(f"Error during cleanup: {e}")
        
        # Sync settings to disk
        self.settings_manager.sync()
        
        # Accept the close event
        event.accept()