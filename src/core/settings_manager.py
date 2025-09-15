"""
Settings Manager for Karaoke Video Creator Application

This module provides QSettings-based configuration management for user preferences,
application state persistence, and default settings.
"""

from PyQt6.QtCore import QSettings, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from dataclasses import asdict

from src.core.models import ExportSettings


class SettingsManager(QObject):
    """
    Manages application settings using QSettings for persistence.
    
    Handles:
    - User preferences (default quality settings, directories)
    - Application state (recent projects, window layout)
    - Export settings defaults
    - UI preferences
    """
    
    # Signals for settings changes
    settings_changed = pyqtSignal(str, object)  # setting_key, new_value
    export_defaults_changed = pyqtSignal(ExportSettings)
    recent_projects_changed = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        
        # Initialize QSettings with organization and application name
        self.settings = QSettings("KaraokeVideoCreator", "KaraokeVideoCreator")
        
        # Initialize default settings if not present
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default settings if they don't exist"""
        
        # Default directories
        if not self.settings.contains("directories/input"):
            self.settings.setValue("directories/input", str(Path("input").resolve()))
        if not self.settings.contains("directories/output"):
            self.settings.setValue("directories/output", str(Path("output").resolve()))
        if not self.settings.contains("directories/temp"):
            self.settings.setValue("directories/temp", str(Path("temp").resolve()))
        
        # Default export settings
        if not self.settings.contains("export/default_resolution_width"):
            self.settings.setValue("export/default_resolution_width", 1920)
        if not self.settings.contains("export/default_resolution_height"):
            self.settings.setValue("export/default_resolution_height", 1080)
        if not self.settings.contains("export/default_bitrate"):
            self.settings.setValue("export/default_bitrate", 5000)
        if not self.settings.contains("export/default_quality"):
            self.settings.setValue("export/default_quality", "high")
        if not self.settings.contains("export/default_frame_rate"):
            self.settings.setValue("export/default_frame_rate", 30.0)
        if not self.settings.contains("export/default_audio_bitrate"):
            self.settings.setValue("export/default_audio_bitrate", 192)
        
        # UI preferences
        if not self.settings.contains("ui/window_geometry"):
            # Will be set when window is first shown
            pass
        if not self.settings.contains("ui/window_state"):
            # Will be set when window state changes
            pass
        if not self.settings.contains("ui/last_tab_index"):
            self.settings.setValue("ui/last_tab_index", 0)
        
        # Application preferences
        if not self.settings.contains("app/auto_save_projects"):
            self.settings.setValue("app/auto_save_projects", True)
        if not self.settings.contains("app/cleanup_temp_on_exit"):
            self.settings.setValue("app/cleanup_temp_on_exit", True)
        if not self.settings.contains("app/show_tooltips"):
            self.settings.setValue("app/show_tooltips", True)
        
        # Recent projects (empty list initially)
        if not self.settings.contains("projects/recent"):
            self.settings.setValue("projects/recent", [])
        
        # Sync settings to disk
        self.settings.sync()
    
    # Directory Settings
    def get_input_directory(self) -> str:
        """Get the default input directory"""
        return self.settings.value("directories/input", str(Path("input").resolve()))
    
    def set_input_directory(self, path: str):
        """Set the default input directory"""
        self.settings.setValue("directories/input", str(Path(path).resolve()))
        self.settings_changed.emit("directories/input", path)
    
    def get_output_directory(self) -> str:
        """Get the default output directory"""
        return self.settings.value("directories/output", str(Path("output").resolve()))
    
    def set_output_directory(self, path: str):
        """Set the default output directory"""
        self.settings.setValue("directories/output", str(Path(path).resolve()))
        self.settings_changed.emit("directories/output", path)
    
    def get_temp_directory(self) -> str:
        """Get the temporary files directory"""
        return self.settings.value("directories/temp", str(Path("temp").resolve()))
    
    def set_temp_directory(self, path: str):
        """Set the temporary files directory"""
        self.settings.setValue("directories/temp", str(Path(path).resolve()))
        self.settings_changed.emit("directories/temp", path)
    
    # Export Settings
    def get_default_export_settings(self) -> ExportSettings:
        """Get default export settings"""
        return ExportSettings(
            resolution={
                "width": self.settings.value("export/default_resolution_width", 1920, type=int),
                "height": self.settings.value("export/default_resolution_height", 1080, type=int)
            },
            bitrate=self.settings.value("export/default_bitrate", 5000, type=int),
            format="mp4",  # Always MP4 for now
            quality=self.settings.value("export/default_quality", "high"),
            frame_rate=self.settings.value("export/default_frame_rate", 30.0, type=float),
            audio_bitrate=self.settings.value("export/default_audio_bitrate", 192, type=int),
            output_directory=self.get_output_directory()
        )
    
    def set_default_export_settings(self, export_settings: ExportSettings):
        """Set default export settings"""
        self.settings.setValue("export/default_resolution_width", export_settings.resolution["width"])
        self.settings.setValue("export/default_resolution_height", export_settings.resolution["height"])
        self.settings.setValue("export/default_bitrate", export_settings.bitrate)
        self.settings.setValue("export/default_quality", export_settings.quality)
        self.settings.setValue("export/default_frame_rate", export_settings.frame_rate)
        self.settings.setValue("export/default_audio_bitrate", export_settings.audio_bitrate)
        
        self.export_defaults_changed.emit(export_settings)
        self.settings_changed.emit("export_defaults", export_settings)
    
    # UI State Persistence
    def save_window_geometry(self, geometry: bytes):
        """Save main window geometry"""
        self.settings.setValue("ui/window_geometry", geometry)
    
    def restore_window_geometry(self) -> Optional[bytes]:
        """Restore main window geometry"""
        return self.settings.value("ui/window_geometry", None)
    
    def save_window_state(self, state: bytes):
        """Save main window state (toolbars, docks, etc.)"""
        self.settings.setValue("ui/window_state", state)
    
    def restore_window_state(self) -> Optional[bytes]:
        """Restore main window state"""
        return self.settings.value("ui/window_state", None)
    
    def save_last_tab_index(self, index: int):
        """Save the last active tab index"""
        self.settings.setValue("ui/last_tab_index", index)
    
    def get_last_tab_index(self) -> int:
        """Get the last active tab index"""
        return self.settings.value("ui/last_tab_index", 0, type=int)
    
    # Recent Projects Management
    def get_recent_projects(self) -> List[Dict[str, Any]]:
        """Get list of recent projects"""
        recent = self.settings.value("projects/recent", [])
        if isinstance(recent, str):
            # Handle case where QSettings returns a string
            try:
                return json.loads(recent)
            except json.JSONDecodeError:
                return []
        return recent if recent else []
    
    def add_recent_project(self, project_path: str, project_name: str):
        """Add a project to recent projects list"""
        recent = self.get_recent_projects()
        
        # Create project entry
        app_instance = QApplication.instance()
        last_opened = "unknown"
        if app_instance:
            last_opened = app_instance.property("current_time") or "unknown"
        
        project_entry = {
            "path": str(Path(project_path).resolve()),
            "name": project_name,
            "last_opened": last_opened
        }
        
        # Remove if already exists (to move to top)
        recent = [p for p in recent if p.get("path") != project_entry["path"]]
        
        # Add to beginning
        recent.insert(0, project_entry)
        
        # Keep only last 10 projects
        recent = recent[:10]
        
        # Save back to settings
        self.settings.setValue("projects/recent", recent)
        self.recent_projects_changed.emit(recent)
    
    def remove_recent_project(self, project_path: str):
        """Remove a project from recent projects list"""
        recent = self.get_recent_projects()
        recent = [p for p in recent if p.get("path") != str(Path(project_path).resolve())]
        
        self.settings.setValue("projects/recent", recent)
        self.recent_projects_changed.emit(recent)
    
    def clear_recent_projects(self):
        """Clear all recent projects"""
        self.settings.setValue("projects/recent", [])
        self.recent_projects_changed.emit([])
    
    # Application Preferences
    def get_auto_save_projects(self) -> bool:
        """Get auto-save projects preference"""
        return self.settings.value("app/auto_save_projects", True, type=bool)
    
    def set_auto_save_projects(self, enabled: bool):
        """Set auto-save projects preference"""
        self.settings.setValue("app/auto_save_projects", enabled)
        self.settings_changed.emit("app/auto_save_projects", enabled)
    
    def get_cleanup_temp_on_exit(self) -> bool:
        """Get cleanup temp files on exit preference"""
        return self.settings.value("app/cleanup_temp_on_exit", True, type=bool)
    
    def set_cleanup_temp_on_exit(self, enabled: bool):
        """Set cleanup temp files on exit preference"""
        self.settings.setValue("app/cleanup_temp_on_exit", enabled)
        self.settings_changed.emit("app/cleanup_temp_on_exit", enabled)
    
    def get_show_tooltips(self) -> bool:
        """Get show tooltips preference"""
        return self.settings.value("app/show_tooltips", True, type=bool)
    
    def set_show_tooltips(self, enabled: bool):
        """Set show tooltips preference"""
        self.settings.setValue("app/show_tooltips", enabled)
        self.settings_changed.emit("app/show_tooltips", enabled)
    
    # Generic Settings Access
    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """Get a setting value by key"""
        return self.settings.value(key, default_value)
    
    def set_setting(self, key: str, value: Any):
        """Set a setting value by key"""
        self.settings.setValue(key, value)
        self.settings_changed.emit(key, value)
    
    def has_setting(self, key: str) -> bool:
        """Check if a setting exists"""
        return self.settings.contains(key)
    
    def remove_setting(self, key: str):
        """Remove a setting"""
        self.settings.remove(key)
    
    # Settings Export/Import
    def export_settings(self, file_path: str) -> bool:
        """Export all settings to a file"""
        try:
            settings_dict = {}
            
            # Export all settings
            for key in self.settings.allKeys():
                settings_dict[key] = self.settings.value(key)
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(settings_dict, f, indent=2, default=str)
            
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Import settings from a file"""
        try:
            with open(file_path, 'r') as f:
                settings_dict = json.load(f)
            
            # Import all settings
            for key, value in settings_dict.items():
                self.settings.setValue(key, value)
            
            # Sync to disk
            self.settings.sync()
            
            # Emit change signals for major settings
            self.export_defaults_changed.emit(self.get_default_export_settings())
            self.recent_projects_changed.emit(self.get_recent_projects())
            
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        # Clear all settings
        self.settings.clear()
        
        # Reinitialize defaults
        self._initialize_defaults()
        
        # Emit change signals
        self.export_defaults_changed.emit(self.get_default_export_settings())
        self.recent_projects_changed.emit([])
        self.settings_changed.emit("reset", "all")
    
    def sync(self):
        """Sync settings to disk"""
        self.settings.sync()