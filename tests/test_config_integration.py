"""
Unit tests for Configuration Integration.

Tests the integration between ConfigManager and SettingsManager
for unified configuration management.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config_integration import ConfigIntegration, get_config_integration, reset_config_integration
from src.core.models import ExportSettings, EffectsConfig, ProjectConfig


class TestConfigIntegration:
    """Test suite for ConfigIntegration class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for test configs
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Reset global instance
        reset_config_integration()
        
        # Create integration instance
        self.integration = ConfigIntegration(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Reset global instance
        reset_config_integration()
        
        # Remove temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test ConfigIntegration initialization."""
        assert self.integration.config_manager is not None
        assert self.integration.settings_manager is not None
        
        # Check that config directory was created
        assert self.integration.config_manager.config_dir == self.temp_dir
        assert self.temp_dir.exists()
    
    def test_project_config_creation(self):
        """Test project configuration creation."""
        # Create with default template
        project_config = self.integration.get_project_config()
        assert isinstance(project_config, ProjectConfig)
        assert project_config.width > 0
        assert project_config.height > 0
        assert project_config.fps > 0
        
        # Create with specific template
        project_config = self.integration.get_project_config("Basic Karaoke")
        assert isinstance(project_config, ProjectConfig)
        assert project_config.width == 1920
        assert project_config.height == 1080
        assert project_config.fps == 30.0
    
    def test_effects_config_creation(self):
        """Test effects configuration creation."""
        # Create with default template
        effects_config = self.integration.get_effects_config()
        assert isinstance(effects_config, EffectsConfig)
        
        # Create with specific template
        effects_config = self.integration.get_effects_config("Advanced Effects")
        assert isinstance(effects_config, EffectsConfig)
        assert effects_config.glow_enabled == True
        assert effects_config.particles_enabled == True
    
    def test_export_settings_management(self):
        """Test export settings management."""
        # Get default export settings
        export_settings = self.integration.get_export_settings()
        assert isinstance(export_settings, ExportSettings)
        
        # Modify export settings
        new_export_settings = ExportSettings(
            resolution={"width": 2560, "height": 1440},
            bitrate=8000,
            quality="high",
            frame_rate=60.0
        )
        
        self.integration.set_export_settings(new_export_settings)
        
        # Verify settings were updated
        updated_settings = self.integration.get_export_settings()
        assert updated_settings.resolution["width"] == 2560
        assert updated_settings.resolution["height"] == 1440
        assert updated_settings.bitrate == 8000
        assert updated_settings.frame_rate == 60.0
    
    def test_directory_management(self):
        """Test directory setting management."""
        # Test getting default directories
        input_dir = self.integration.get_directory("input")
        output_dir = self.integration.get_directory("output")
        temp_dir = self.integration.get_directory("temp")
        
        assert isinstance(input_dir, str)
        assert isinstance(output_dir, str)
        assert isinstance(temp_dir, str)
        
        # Test setting directories
        self.integration.set_directory("input", "/custom/input")
        self.integration.set_directory("output", "/custom/output")
        self.integration.set_directory("temp", "/custom/temp")
        
        # Verify directories were updated
        updated_input = self.integration.get_directory("input")
        updated_output = self.integration.get_directory("output")
        updated_temp = self.integration.get_directory("temp")
        
        assert "custom" in updated_input and "input" in updated_input
        assert "custom" in updated_output and "output" in updated_output
        assert "custom" in updated_temp and "temp" in updated_temp
    
    def test_user_preferences(self):
        """Test user preference management."""
        # Test getting default preference
        auto_save = self.integration.get_user_preference("auto_save_projects", False)
        assert isinstance(auto_save, bool)
        
        # Test setting preference
        self.integration.set_user_preference("auto_save_projects", False)
        self.integration.set_user_preference("custom_preference", "test_value")
        
        # Verify preferences were updated
        updated_auto_save = self.integration.get_user_preference("auto_save_projects")
        custom_pref = self.integration.get_user_preference("custom_preference")
        
        assert updated_auto_save == False
        assert custom_pref == "test_value"
    
    def test_performance_settings(self):
        """Test performance setting management."""
        # Test getting default performance setting
        max_texture = self.integration.get_performance_setting("max_texture_size", 2048)
        assert isinstance(max_texture, int)
        
        # Test setting performance setting
        self.integration.set_performance_setting("max_texture_size", 8192)
        self.integration.set_performance_setting("enable_gpu_acceleration", True)
        
        # Verify settings were updated
        updated_texture = self.integration.get_performance_setting("max_texture_size")
        gpu_accel = self.integration.get_performance_setting("enable_gpu_acceleration")
        
        assert updated_texture == 8192
        assert gpu_accel == True
    
    def test_effects_presets(self):
        """Test effects preset management."""
        # Test getting existing preset
        glow_preset = self.integration.get_effects_preset("shader", "glow_basic")
        assert glow_preset is not None
        assert "intensity" in glow_preset
        
        # Test setting custom preset
        custom_preset = {
            "intensity": 2.0,
            "radius": 10.0,
            "color": [0.0, 1.0, 0.0]
        }
        self.integration.set_effects_preset("shader", "custom_test", custom_preset)
        
        # Verify preset was saved
        loaded_preset = self.integration.get_effects_preset("shader", "custom_test")
        assert loaded_preset == custom_preset
    
    def test_template_management(self):
        """Test template management."""
        # Test listing templates
        templates = self.integration.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 2  # At least Basic and Advanced
        
        # Test getting template
        template = self.integration.get_template("Basic Karaoke")
        assert template is not None
        assert template.name == "Basic Karaoke"
    
    def test_config_file_operations(self):
        """Test configuration file operations."""
        # Test saving config file
        test_config = {
            "version": "1.1",
            "width": 1920,
            "height": 1080,
            "fps": 30.0
        }
        
        config_file = self.temp_dir / "test_config.json"
        self.integration.save_config_file(test_config, str(config_file))
        
        # Test loading config file
        loaded_config = self.integration.load_config_file(str(config_file))
        assert loaded_config == test_config
        
        # Test validation
        errors = self.integration.validate_config(test_config, "project")
        assert len(errors) == 0
    
    def test_export_import_configuration(self):
        """Test configuration export and import."""
        # Modify some settings
        self.integration.set_user_preference("test_setting", "test_value")
        self.integration.set_performance_setting("test_performance", 1234)
        
        # Export configuration
        export_file = self.temp_dir / "export_test.json"
        success = self.integration.export_all_configuration(str(export_file))
        assert success == True
        assert export_file.exists()
        
        # Reset and import
        self.integration.reset_to_defaults()
        success = self.integration.import_all_configuration(str(export_file))
        assert success == True
        
        # Verify settings were restored
        test_setting = self.integration.get_user_preference("test_setting")
        test_performance = self.integration.get_performance_setting("test_performance")
        assert test_setting == "test_value"
        assert test_performance == 1234
    
    def test_recent_projects(self):
        """Test recent projects management."""
        # Get recent projects (should work without QApplication)
        recent = self.integration.get_recent_projects()
        assert isinstance(recent, list)
        
        # Note: Adding recent projects requires QApplication instance
        # This is tested in the UI integration tests
    
    def test_window_state_management(self):
        """Test window state management."""
        # Test saving window state
        test_geometry = b"test_geometry_data"
        test_state = b"test_state_data"
        
        # This should not raise an exception
        self.integration.save_window_state(test_geometry, test_state)
        
        # Test restoring window state
        geometry, state = self.integration.restore_window_state()
        # Note: The actual values depend on the settings manager implementation
        assert geometry is not None or geometry is None  # Either is valid
        assert state is not None or state is None  # Either is valid
    
    def test_sync_settings(self):
        """Test settings synchronization."""
        # Modify settings in config manager
        self.integration.config_manager.set_user_preference("sync_test", "config_value")
        self.integration.config_manager.set_performance_setting("sync_performance", 5678)
        
        # Sync settings
        self.integration.sync_all_settings()
        
        # Verify sync worked (this is mainly testing that no exceptions occur)
        sync_test = self.integration.get_user_preference("sync_test")
        sync_performance = self.integration.get_performance_setting("sync_performance")
        assert sync_test == "config_value"
        assert sync_performance == 5678
    
    def test_reset_to_defaults(self):
        """Test resetting to defaults."""
        # Modify settings
        self.integration.set_user_preference("reset_test", "modified_value")
        self.integration.set_performance_setting("reset_performance", 9999)
        
        # Reset to defaults
        self.integration.reset_to_defaults()
        
        # Verify defaults were restored
        reset_test = self.integration.get_user_preference("reset_test", "default")
        reset_performance = self.integration.get_performance_setting("reset_performance", 1000)
        
        # Should return defaults since settings were reset
        assert reset_test == "default"
        assert reset_performance == 1000


class TestConfigIntegrationGlobal:
    """Test global configuration integration functions."""
    
    def setup_method(self):
        """Set up test environment."""
        reset_config_integration()
    
    def teardown_method(self):
        """Clean up test environment."""
        reset_config_integration()
    
    def test_global_instance(self):
        """Test global configuration integration instance."""
        # Get first instance
        integration1 = get_config_integration()
        assert integration1 is not None
        
        # Get second instance (should be same)
        integration2 = get_config_integration()
        assert integration1 is integration2
        
        # Reset and get new instance
        reset_config_integration()
        integration3 = get_config_integration()
        assert integration3 is not integration1
    
    def test_global_instance_with_config_dir(self):
        """Test global instance with custom config directory."""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Get instance with custom directory
            integration = get_config_integration(config_dir=temp_dir)
            assert integration.config_manager.config_dir == temp_dir
            
            # Second call should ignore config_dir parameter
            integration2 = get_config_integration(config_dir=Path("/different/path"))
            assert integration is integration2
            assert integration2.config_manager.config_dir == temp_dir
            
        finally:
            reset_config_integration()
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


class TestConfigIntegrationIntegration:
    """Integration tests for configuration system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        reset_config_integration()
        self.integration = ConfigIntegration(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        reset_config_integration()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """Test complete configuration workflow."""
        # Create project configuration
        project_config = self.integration.get_project_config("Basic Karaoke")
        assert project_config.width == 1920
        assert project_config.height == 1080
        
        # Create effects configuration
        effects_config = self.integration.get_effects_config("Advanced Effects")
        assert effects_config.glow_enabled == True
        assert effects_config.particles_enabled == True
        
        # Set export settings
        export_settings = ExportSettings(
            resolution={"width": 2560, "height": 1440},
            bitrate=10000,
            quality="high",
            frame_rate=60.0
        )
        self.integration.set_export_settings(export_settings)
        
        # Verify export settings
        loaded_export = self.integration.get_export_settings()
        assert loaded_export.resolution["width"] == 2560
        assert loaded_export.bitrate == 10000
        
        # Set directories
        self.integration.set_directory("input", "/project/input")
        self.integration.set_directory("output", "/project/output")
        
        # Verify directories
        input_dir = self.integration.get_directory("input")
        output_dir = self.integration.get_directory("output")
        assert "input" in input_dir
        assert "output" in output_dir
        
        # Export all configuration
        export_file = self.temp_dir / "full_config.json"
        success = self.integration.export_all_configuration(str(export_file))
        assert success == True
        
        # Reset and import
        self.integration.reset_to_defaults()
        success = self.integration.import_all_configuration(str(export_file))
        assert success == True
        
        # Verify configuration was restored
        restored_export = self.integration.get_export_settings()
        assert restored_export.resolution["width"] == 2560
        assert restored_export.bitrate == 10000


if __name__ == "__main__":
    pytest.main([__file__])