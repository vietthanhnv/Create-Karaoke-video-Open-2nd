"""
Configuration Integration Module

This module provides integration between the new ConfigManager and the existing
SettingsManager to ensure compatibility and smooth migration of settings.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from src.core.config_manager import ConfigManager
from src.core.settings_manager import SettingsManager
from src.core.models import ExportSettings, EffectsConfig, ProjectConfig


class ConfigIntegration:
    """
    Integrates ConfigManager with SettingsManager for backward compatibility
    and unified configuration management.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration integration.
        
        Args:
            config_dir: Directory for configuration files
        """
        self.config_manager = ConfigManager(config_dir)
        self.settings_manager = SettingsManager()
        
        # Sync settings on initialization
        self._sync_settings_to_config()
    
    def _sync_settings_to_config(self):
        """Sync existing QSettings to ConfigManager."""
        try:
            # Sync directory settings
            input_dir = self.settings_manager.get_input_directory()
            output_dir = self.settings_manager.get_output_directory()
            temp_dir = self.settings_manager.get_temp_directory()
            
            self.config_manager.set_directory_setting("input", input_dir)
            self.config_manager.set_directory_setting("output", output_dir)
            self.config_manager.set_directory_setting("temp", temp_dir)
            
            # Sync export settings
            export_settings = self.settings_manager.get_default_export_settings()
            self.config_manager.set_user_preference("default_resolution_width", export_settings.resolution["width"])
            self.config_manager.set_user_preference("default_resolution_height", export_settings.resolution["height"])
            self.config_manager.set_user_preference("default_bitrate", export_settings.bitrate)
            self.config_manager.set_user_preference("default_quality", export_settings.quality)
            self.config_manager.set_user_preference("default_frame_rate", export_settings.frame_rate)
            
            # Sync application preferences
            auto_save = self.settings_manager.get_auto_save_projects()
            cleanup_temp = self.settings_manager.get_cleanup_temp_on_exit()
            show_tooltips = self.settings_manager.get_show_tooltips()
            
            self.config_manager.set_user_preference("auto_save_projects", auto_save)
            self.config_manager.set_user_preference("cleanup_temp_on_exit", cleanup_temp)
            self.config_manager.set_user_preference("show_tooltips", show_tooltips)
            
        except Exception as e:
            print(f"Warning: Could not sync settings: {e}")
    
    def _sync_config_to_settings(self):
        """Sync ConfigManager settings back to QSettings."""
        try:
            # Sync directory settings
            input_dir = self.config_manager.get_directory_setting("input")
            output_dir = self.config_manager.get_directory_setting("output")
            temp_dir = self.config_manager.get_directory_setting("temp")
            
            self.settings_manager.set_input_directory(input_dir)
            self.settings_manager.set_output_directory(output_dir)
            self.settings_manager.set_temp_directory(temp_dir)
            
            # Sync export settings
            width = self.config_manager.get_user_preference("default_resolution_width", 1920)
            height = self.config_manager.get_user_preference("default_resolution_height", 1080)
            bitrate = self.config_manager.get_user_preference("default_bitrate", 5000)
            quality = self.config_manager.get_user_preference("default_quality", "high")
            frame_rate = self.config_manager.get_user_preference("default_frame_rate", 30.0)
            
            export_settings = ExportSettings(
                resolution={"width": width, "height": height},
                bitrate=bitrate,
                quality=quality,
                frame_rate=frame_rate,
                output_directory=output_dir
            )
            self.settings_manager.set_default_export_settings(export_settings)
            
            # Sync application preferences
            auto_save = self.config_manager.get_user_preference("auto_save_projects", True)
            cleanup_temp = self.config_manager.get_user_preference("cleanup_temp_on_exit", True)
            show_tooltips = self.config_manager.get_user_preference("show_tooltips", True)
            
            self.settings_manager.set_auto_save_projects(auto_save)
            self.settings_manager.set_cleanup_temp_on_exit(cleanup_temp)
            self.settings_manager.set_show_tooltips(show_tooltips)
            
        except Exception as e:
            print(f"Warning: Could not sync config to settings: {e}")
    
    # Unified interface methods
    
    def get_project_config(self, template_name: Optional[str] = None) -> ProjectConfig:
        """Get project configuration from template."""
        return self.config_manager.create_project_config(template_name)
    
    def get_effects_config(self, template_name: Optional[str] = None) -> EffectsConfig:
        """Get effects configuration from template."""
        return self.config_manager.create_effects_config(template_name)
    
    def get_export_settings(self) -> ExportSettings:
        """Get export settings (unified from both managers)."""
        # Use settings manager as primary source for export settings
        return self.settings_manager.get_default_export_settings()
    
    def set_export_settings(self, export_settings: ExportSettings):
        """Set export settings (updates both managers)."""
        self.settings_manager.set_default_export_settings(export_settings)
        
        # Also update config manager
        self.config_manager.set_user_preference("default_resolution_width", export_settings.resolution["width"])
        self.config_manager.set_user_preference("default_resolution_height", export_settings.resolution["height"])
        self.config_manager.set_user_preference("default_bitrate", export_settings.bitrate)
        self.config_manager.set_user_preference("default_quality", export_settings.quality)
        self.config_manager.set_user_preference("default_frame_rate", export_settings.frame_rate)
    
    def get_directory(self, directory_type: str) -> str:
        """Get directory setting."""
        if directory_type == "input":
            return self.settings_manager.get_input_directory()
        elif directory_type == "output":
            return self.settings_manager.get_output_directory()
        elif directory_type == "temp":
            return self.settings_manager.get_temp_directory()
        else:
            return self.config_manager.get_directory_setting(directory_type)
    
    def set_directory(self, directory_type: str, path: str):
        """Set directory setting (updates both managers)."""
        if directory_type == "input":
            self.settings_manager.set_input_directory(path)
        elif directory_type == "output":
            self.settings_manager.set_output_directory(path)
        elif directory_type == "temp":
            self.settings_manager.set_temp_directory(path)
        
        # Also update config manager
        self.config_manager.set_directory_setting(directory_type, path)
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference."""
        return self.config_manager.get_user_preference(key, default)
    
    def set_user_preference(self, key: str, value: Any):
        """Set user preference."""
        self.config_manager.set_user_preference(key, value)
        
        # Sync specific preferences to settings manager
        if key == "auto_save_projects":
            self.settings_manager.set_auto_save_projects(value)
        elif key == "cleanup_temp_on_exit":
            self.settings_manager.set_cleanup_temp_on_exit(value)
        elif key == "show_tooltips":
            self.settings_manager.set_show_tooltips(value)
    
    def get_performance_setting(self, key: str, default: Any = None) -> Any:
        """Get performance setting."""
        return self.config_manager.get_performance_setting(key, default)
    
    def set_performance_setting(self, key: str, value: Any):
        """Set performance setting."""
        self.config_manager.set_performance_setting(key, value)
    
    def get_effects_preset(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get effects preset."""
        return self.config_manager.get_effects_preset(category, name)
    
    def set_effects_preset(self, category: str, name: str, preset: Dict[str, Any]):
        """Set effects preset."""
        self.config_manager.set_effects_preset(category, name, preset)
    
    def list_templates(self) -> list:
        """List available configuration templates."""
        return self.config_manager.list_templates()
    
    def get_template(self, name: str):
        """Get configuration template by name."""
        return self.config_manager.get_template(name)
    
    def load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON/YAML file."""
        return self.config_manager.load_config_file(file_path)
    
    def save_config_file(self, data: Dict[str, Any], file_path: str):
        """Save configuration to JSON/YAML file."""
        self.config_manager.save_config_file(data, file_path)
    
    def validate_config(self, config: Dict[str, Any], config_type: str = "project") -> list:
        """Validate configuration data."""
        return self.config_manager.validate_config(config, config_type)
    
    def export_all_configuration(self, file_path: str, include_templates: bool = True) -> bool:
        """Export all configuration to file."""
        return self.config_manager.export_configuration(file_path, include_templates)
    
    def import_all_configuration(self, file_path: str, merge: bool = True) -> bool:
        """Import configuration from file."""
        success = self.config_manager.import_configuration(file_path, merge)
        if success:
            # Sync imported settings back to QSettings
            self._sync_config_to_settings()
        return success
    
    def reset_to_defaults(self):
        """Reset all configuration to defaults."""
        self.config_manager.reset_to_defaults()
        self.settings_manager.reset_to_defaults()
    
    def get_recent_projects(self) -> list:
        """Get recent projects list."""
        return self.settings_manager.get_recent_projects()
    
    def add_recent_project(self, project_path: str, project_name: str):
        """Add project to recent projects."""
        self.settings_manager.add_recent_project(project_path, project_name)
    
    def save_window_state(self, geometry: bytes, state: bytes):
        """Save window geometry and state."""
        self.settings_manager.save_window_geometry(geometry)
        self.settings_manager.save_window_state(state)
    
    def restore_window_state(self) -> tuple:
        """Restore window geometry and state."""
        geometry = self.settings_manager.restore_window_geometry()
        state = self.settings_manager.restore_window_state()
        return geometry, state
    
    def sync_all_settings(self):
        """Synchronize all settings between managers."""
        self._sync_settings_to_config()
        self._sync_config_to_settings()


# Global instance for easy access
_config_integration = None


def get_config_integration(config_dir: Optional[Path] = None) -> ConfigIntegration:
    """
    Get the global configuration integration instance.
    
    Args:
        config_dir: Directory for configuration files (only used on first call)
        
    Returns:
        ConfigIntegration instance
    """
    global _config_integration
    if _config_integration is None:
        _config_integration = ConfigIntegration(config_dir)
    return _config_integration


def reset_config_integration():
    """Reset the global configuration integration instance."""
    global _config_integration
    _config_integration = None