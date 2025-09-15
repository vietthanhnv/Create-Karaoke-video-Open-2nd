"""
Unit tests for the Configuration Manager.

Tests cover:
- JSON/YAML configuration file parsing and validation
- Effects parameter loading and validation
- Project configuration management with templates
- User preference handling and settings persistence
- Configuration migration and version compatibility
"""

import pytest
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config_manager import (
    ConfigManager, ConfigFormat, ConfigVersion, ConfigTemplate,
    ConfigValidationError
)
from src.core.models import ProjectConfig, EffectsConfig, ExportSettings


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for test configs
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Remove temporary directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test ConfigManager initialization."""
        assert self.config_manager.config_dir == self.temp_dir
        assert self.config_manager.templates_dir.exists()
        assert self.config_manager.user_config_file.exists()
        assert self.config_manager.effects_config_file.exists()
        
        # Check that default templates were created
        templates = self.config_manager.list_templates()
        assert "Basic Karaoke" in templates
        assert "Advanced Effects" in templates
    
    def test_load_json_config(self):
        """Test loading JSON configuration files."""
        # Create test JSON config
        test_config = {
            "version": "1.1",
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "effects": {
                "glow_enabled": True,
                "glow_intensity": 1.0
            }
        }
        
        json_file = self.temp_dir / "test_config.json"
        with open(json_file, 'w') as f:
            json.dump(test_config, f)
        
        # Load and verify
        loaded_config = self.config_manager.load_config_file(json_file)
        assert loaded_config == test_config
    
    def test_load_yaml_config(self):
        """Test loading YAML configuration files."""
        # Create test YAML config
        test_config = {
            "version": "1.1",
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "effects": {
                "glow_enabled": True,
                "glow_intensity": 1.0
            }
        }
        
        yaml_file = self.temp_dir / "test_config.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Load and verify
        loaded_config = self.config_manager.load_config_file(yaml_file)
        assert loaded_config == test_config
    
    def test_save_json_config(self):
        """Test saving JSON configuration files."""
        test_config = {
            "version": "1.1",
            "width": 1920,
            "height": 1080,
            "fps": 30.0
        }
        
        json_file = self.temp_dir / "save_test.json"
        self.config_manager.save_config_file(test_config, json_file)
        
        # Verify file was created and content is correct
        assert json_file.exists()
        with open(json_file, 'r') as f:
            loaded_config = json.load(f)
        assert loaded_config == test_config
    
    def test_save_yaml_config(self):
        """Test saving YAML configuration files."""
        test_config = {
            "version": "1.1",
            "width": 1920,
            "height": 1080,
            "fps": 30.0
        }
        
        yaml_file = self.temp_dir / "save_test.yaml"
        self.config_manager.save_config_file(test_config, yaml_file)
        
        # Verify file was created and content is correct
        assert yaml_file.exists()
        with open(yaml_file, 'r') as f:
            loaded_config = yaml.safe_load(f)
        assert loaded_config == test_config
    
    def test_invalid_config_file(self):
        """Test handling of invalid configuration files."""
        # Test non-existent file
        with pytest.raises(FileNotFoundError):
            self.config_manager.load_config_file("nonexistent.json")
        
        # Test invalid JSON
        invalid_json = self.temp_dir / "invalid.json"
        with open(invalid_json, 'w') as f:
            f.write("{ invalid json }")
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            self.config_manager.load_config_file(invalid_json)
        
        # Test invalid YAML
        invalid_yaml = self.temp_dir / "invalid.yaml"
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            self.config_manager.load_config_file(invalid_yaml)
    
    def test_config_validation_project(self):
        """Test project configuration validation."""
        # Valid config
        valid_config = {
            "width": 1920,
            "height": 1080,
            "fps": 30.0
        }
        errors = self.config_manager.validate_config(valid_config, "project")
        assert len(errors) == 0
        
        # Missing required fields
        invalid_config = {"width": 1920}
        errors = self.config_manager.validate_config(invalid_config, "project")
        assert len(errors) == 2  # Missing height and fps
        assert any(error.field == "height" for error in errors)
        assert any(error.field == "fps" for error in errors)
        
        # Invalid values
        invalid_config = {
            "width": -1920,
            "height": 0,
            "fps": -30.0
        }
        errors = self.config_manager.validate_config(invalid_config, "project")
        assert len(errors) == 3
        assert all(error.severity == "error" for error in errors)
        
        # Warning for high resolution
        high_res_config = {
            "width": 8000,
            "height": 5000,
            "fps": 30.0
        }
        errors = self.config_manager.validate_config(high_res_config, "project")
        assert len(errors) == 2  # Width and height warnings
        assert all(error.severity == "warning" for error in errors)
    
    def test_config_validation_effects(self):
        """Test effects configuration validation."""
        # Valid config
        valid_config = {
            "glow_intensity": 1.0,
            "glow_radius": 3.0,
            "glow_color": [1.0, 1.0, 0.0],
            "particle_count": 50
        }
        errors = self.config_manager.validate_config(valid_config, "effects")
        assert len(errors) == 0
        
        # Invalid values
        invalid_config = {
            "glow_intensity": -1.0,
            "glow_radius": -3.0,
            "glow_color": [1.0, 1.0],  # Wrong length
            "particle_count": -50
        }
        errors = self.config_manager.validate_config(invalid_config, "effects")
        assert len(errors) == 4
        
        # Color validation
        invalid_color_config = {
            "glow_color": [2.0, -0.5, 1.0]  # Values out of range
        }
        errors = self.config_manager.validate_config(invalid_color_config, "effects")
        assert len(errors) == 1
        assert "between 0 and 1" in errors[0].message
        
        # Warning for high particle count
        high_particle_config = {
            "particle_count": 2000
        }
        errors = self.config_manager.validate_config(high_particle_config, "effects")
        assert len(errors) == 1
        assert errors[0].severity == "warning"
    
    def test_config_validation_export(self):
        """Test export configuration validation."""
        # Valid config
        valid_config = {
            "bitrate": 5000,
            "quality": "high"
        }
        errors = self.config_manager.validate_config(valid_config, "export")
        assert len(errors) == 0
        
        # Invalid values
        invalid_config = {
            "bitrate": -5000,
            "quality": "invalid_quality"
        }
        errors = self.config_manager.validate_config(invalid_config, "export")
        assert len(errors) == 2
    
    def test_template_management(self):
        """Test configuration template management."""
        # Test getting existing template
        template = self.config_manager.get_template("Basic Karaoke")
        assert template is not None
        assert template.name == "Basic Karaoke"
        assert isinstance(template.effects, EffectsConfig)
        assert isinstance(template.export_settings, ExportSettings)
        
        # Test getting non-existent template
        template = self.config_manager.get_template("Non-existent")
        assert template is None
        
        # Test listing templates
        templates = self.config_manager.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 2  # At least Basic and Advanced
        assert "Basic Karaoke" in templates
        assert "Advanced Effects" in templates
    
    def test_create_project_config(self):
        """Test creating project configuration from templates."""
        # Create with default template
        project_config = self.config_manager.create_project_config()
        assert isinstance(project_config, ProjectConfig)
        assert project_config.width > 0
        assert project_config.height > 0
        assert project_config.fps > 0
        
        # Create with specific template
        project_config = self.config_manager.create_project_config("Basic Karaoke")
        assert isinstance(project_config, ProjectConfig)
        assert project_config.width == 1920
        assert project_config.height == 1080
        assert project_config.fps == 30.0
        
        # Create with non-existent template (should fallback)
        project_config = self.config_manager.create_project_config("Non-existent")
        assert isinstance(project_config, ProjectConfig)
    
    def test_create_effects_config(self):
        """Test creating effects configuration from templates."""
        # Create with default template
        effects_config = self.config_manager.create_effects_config()
        assert isinstance(effects_config, EffectsConfig)
        
        # Create with specific template
        effects_config = self.config_manager.create_effects_config("Advanced Effects")
        assert isinstance(effects_config, EffectsConfig)
        assert effects_config.glow_enabled == True
        assert effects_config.particles_enabled == True
        assert effects_config.text_animation_enabled == True
        
        # Create with non-existent template (should fallback)
        effects_config = self.config_manager.create_effects_config("Non-existent")
        assert isinstance(effects_config, EffectsConfig)
    
    def test_user_preferences(self):
        """Test user preference management."""
        # Test getting default preference
        auto_save = self.config_manager.get_user_preference("auto_save", False)
        assert auto_save == True  # Default is True
        
        # Test setting preference
        self.config_manager.set_user_preference("auto_save", False)
        auto_save = self.config_manager.get_user_preference("auto_save", True)
        assert auto_save == False
        
        # Test getting non-existent preference with default
        custom_pref = self.config_manager.get_user_preference("custom_pref", "default_value")
        assert custom_pref == "default_value"
    
    def test_directory_settings(self):
        """Test directory setting management."""
        # Test getting default directory
        input_dir = self.config_manager.get_directory_setting("input")
        assert input_dir == "input"
        
        # Test setting directory
        new_path = "/custom/input/path"
        self.config_manager.set_directory_setting("input", new_path)
        input_dir = self.config_manager.get_directory_setting("input")
        assert str(Path(new_path).resolve()) in input_dir
    
    def test_performance_settings(self):
        """Test performance setting management."""
        # Test getting default performance setting
        max_texture = self.config_manager.get_performance_setting("max_texture_size", 2048)
        assert max_texture == 4096  # Default is 4096
        
        # Test setting performance setting
        self.config_manager.set_performance_setting("max_texture_size", 8192)
        max_texture = self.config_manager.get_performance_setting("max_texture_size", 2048)
        assert max_texture == 8192
    
    def test_effects_presets(self):
        """Test effects preset management."""
        # Test getting existing preset
        glow_preset = self.config_manager.get_effects_preset("shader", "glow_basic")
        assert glow_preset is not None
        assert "intensity" in glow_preset
        assert "radius" in glow_preset
        
        # Test setting custom preset
        custom_preset = {
            "intensity": 2.0,
            "radius": 10.0,
            "color": [0.0, 1.0, 0.0]
        }
        self.config_manager.set_effects_preset("shader", "custom_glow", custom_preset)
        
        # Verify preset was saved
        loaded_preset = self.config_manager.get_effects_preset("shader", "custom_glow")
        assert loaded_preset == custom_preset
    
    def test_config_migration(self):
        """Test configuration migration between versions."""
        # Create old version config
        old_config = {
            "version": "1.0",
            "preferences": {
                "auto_save": True,
                "backup_projects": True
            }
        }
        
        # Migrate config
        migrated_config = self.config_manager._migrate_config(old_config)
        
        # Check migration results
        assert migrated_config["version"] == ConfigVersion.CURRENT.value
        assert "performance" in migrated_config
        assert "show_advanced_options" in migrated_config["preferences"]
    
    def test_export_import_configuration(self):
        """Test configuration export and import."""
        # Modify some settings
        self.config_manager.set_user_preference("auto_save", False)
        self.config_manager.set_performance_setting("max_texture_size", 8192)
        
        # Export configuration
        export_file = self.temp_dir / "exported_config.json"
        success = self.config_manager.export_configuration(export_file)
        assert success == True
        assert export_file.exists()
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        # Verify settings were reset
        assert self.config_manager.get_user_preference("auto_save") == True
        assert self.config_manager.get_performance_setting("max_texture_size") == 4096
        
        # Import configuration
        success = self.config_manager.import_configuration(export_file)
        assert success == True
        
        # Verify settings were restored
        assert self.config_manager.get_user_preference("auto_save") == False
        assert self.config_manager.get_performance_setting("max_texture_size") == 8192
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        # Modify settings
        self.config_manager.set_user_preference("auto_save", False)
        self.config_manager.set_performance_setting("max_texture_size", 8192)
        
        # Reset to defaults
        self.config_manager.reset_to_defaults()
        
        # Verify defaults were restored
        assert self.config_manager.get_user_preference("auto_save") == True
        assert self.config_manager.get_performance_setting("max_texture_size") == 4096
        
        # Verify templates are still available
        templates = self.config_manager.list_templates()
        assert len(templates) >= 2
    
    def test_format_detection(self):
        """Test automatic format detection for config files."""
        test_config = {"test": "data"}
        
        # Test JSON format detection
        json_file = self.temp_dir / "test.json"
        self.config_manager.save_config_file(test_config, json_file)
        loaded = self.config_manager.load_config_file(json_file)
        assert loaded == test_config
        
        # Test YAML format detection
        yaml_file = self.temp_dir / "test.yaml"
        self.config_manager.save_config_file(test_config, yaml_file)
        loaded = self.config_manager.load_config_file(yaml_file)
        assert loaded == test_config
        
        # Test YML format detection
        yml_file = self.temp_dir / "test.yml"
        self.config_manager.save_config_file(test_config, yml_file)
        loaded = self.config_manager.load_config_file(yml_file)
        assert loaded == test_config
    
    def test_error_handling(self):
        """Test error handling in configuration operations."""
        # Test loading from invalid path
        with pytest.raises(FileNotFoundError):
            self.config_manager.load_config_file("/invalid/path/config.json")
        
        # Test saving to invalid path (should create directories)
        deep_path = self.temp_dir / "deep" / "nested" / "path" / "config.json"
        test_config = {"test": "data"}
        self.config_manager.save_config_file(test_config, deep_path)
        assert deep_path.exists()
        
        # Test validation with invalid config type
        errors = self.config_manager.validate_config({}, "invalid_type")
        assert len(errors) == 0  # Should handle gracefully
    
    def test_config_validation_error_class(self):
        """Test ConfigValidationError class."""
        error = ConfigValidationError(
            field="test_field",
            message="Test error message",
            severity="warning"
        )
        
        assert error.field == "test_field"
        assert error.message == "Test error message"
        assert error.severity == "warning"
        
        # Test default severity
        error_default = ConfigValidationError(
            field="test_field",
            message="Test error message"
        )
        assert error_default.severity == "error"


class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_full_project_workflow(self):
        """Test complete project configuration workflow."""
        # Create project config from template
        project_config = self.config_manager.create_project_config("Basic Karaoke")
        assert isinstance(project_config, ProjectConfig)
        
        # Create effects config from same template
        effects_config = self.config_manager.create_effects_config("Basic Karaoke")
        assert isinstance(effects_config, EffectsConfig)
        
        # Validate configurations
        project_dict = {
            "width": project_config.width,
            "height": project_config.height,
            "fps": project_config.fps
        }
        project_errors = self.config_manager.validate_config(project_dict, "project")
        assert len(project_errors) == 0
        
        effects_dict = {
            "glow_intensity": effects_config.glow_intensity,
            "glow_radius": effects_config.glow_radius,
            "glow_color": effects_config.glow_color
        }
        effects_errors = self.config_manager.validate_config(effects_dict, "effects")
        assert len(effects_errors) == 0
    
    def test_template_customization(self):
        """Test creating and using custom templates."""
        # Create custom effects config
        custom_effects = EffectsConfig(
            glow_enabled=True,
            glow_intensity=2.0,
            glow_radius=8.0,
            glow_color=[0.0, 1.0, 0.0],  # Green glow
            particles_enabled=True,
            particle_count=200
        )
        
        # Create custom template
        custom_template = ConfigTemplate(
            name="Custom Green",
            description="Custom template with green effects",
            config={"width": 1920, "height": 1080, "fps": 60.0},
            effects=custom_effects,
            export_settings=ExportSettings(frame_rate=60.0)
        )
        
        # Save template
        self.config_manager._save_template(custom_template)
        
        # Verify template is available
        templates = self.config_manager.list_templates()
        assert "Custom Green" in templates
        
        # Load and verify template
        loaded_template = self.config_manager.get_template("Custom Green")
        assert loaded_template is not None
        assert loaded_template.name == "Custom Green"
        assert loaded_template.effects.glow_color == [0.0, 1.0, 0.0]
        assert loaded_template.config["fps"] == 60.0
    
    def test_configuration_persistence(self):
        """Test that configuration changes persist across instances."""
        # Modify settings in first instance
        self.config_manager.set_user_preference("auto_save", False)
        self.config_manager.set_directory_setting("output", "/custom/output")
        
        # Create new instance with same config directory
        new_config_manager = ConfigManager(config_dir=self.temp_dir)
        
        # Verify settings persisted
        assert new_config_manager.get_user_preference("auto_save") == False
        # Check that the path contains the custom part (handling Windows path resolution)
        output_dir = new_config_manager.get_directory_setting("output")
        assert "custom" in output_dir and "output" in output_dir


if __name__ == "__main__":
    pytest.main([__file__])