#!/usr/bin/env python3
"""
Demo script for the Configuration System

This script demonstrates the comprehensive configuration management system
including JSON/YAML parsing, effects parameter management, project templates,
and user preferences.
"""

import json
import yaml
from pathlib import Path
import tempfile
import shutil

from src.core.config_manager import ConfigManager, ConfigTemplate
from src.core.models import EffectsConfig, ExportSettings, ProjectConfig


def demo_basic_configuration():
    """Demonstrate basic configuration operations."""
    print("=== Basic Configuration Demo ===")
    
    # Create temporary directory for demo
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Initialize configuration manager
        config_manager = ConfigManager(config_dir=temp_dir)
        print("✓ Configuration manager initialized")
        
        # List available templates
        templates = config_manager.list_templates()
        print(f"✓ Available templates: {templates}")
        
        # Create project configuration from template
        project_config = config_manager.create_project_config("Basic Karaoke")
        print(f"✓ Created project config: {project_config.width}x{project_config.height} @ {project_config.fps}fps")
        
        # Create effects configuration
        effects_config = config_manager.create_effects_config("Advanced Effects")
        print(f"✓ Created effects config with glow: {effects_config.glow_enabled}")
        
        return config_manager, temp_dir
        
    except Exception as e:
        print(f"✗ Error in basic configuration: {e}")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return None, None


def demo_file_operations(config_manager, temp_dir):
    """Demonstrate JSON/YAML file operations."""
    print("\n=== File Operations Demo ===")
    
    try:
        # Create sample configuration data
        sample_config = {
            "version": "1.1",
            "project": {
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "background_color": [0.0, 0.0, 0.0, 1.0]
            },
            "effects": {
                "glow_enabled": True,
                "glow_intensity": 1.5,
                "glow_radius": 4.0,
                "glow_color": [1.0, 1.0, 0.0],
                "particles_enabled": True,
                "particle_count": 75
            }
        }
        
        # Save as JSON
        json_file = temp_dir / "sample_config.json"
        config_manager.save_config_file(sample_config, json_file)
        print(f"✓ Saved JSON config to: {json_file}")
        
        # Save as YAML
        yaml_file = temp_dir / "sample_config.yaml"
        config_manager.save_config_file(sample_config, yaml_file)
        print(f"✓ Saved YAML config to: {yaml_file}")
        
        # Load and verify JSON
        loaded_json = config_manager.load_config_file(json_file)
        print(f"✓ Loaded JSON config: {loaded_json['project']['width']}x{loaded_json['project']['height']}")
        
        # Load and verify YAML
        loaded_yaml = config_manager.load_config_file(yaml_file)
        print(f"✓ Loaded YAML config: {loaded_yaml['effects']['particle_count']} particles")
        
        return sample_config
        
    except Exception as e:
        print(f"✗ Error in file operations: {e}")
        return None


def demo_validation(config_manager):
    """Demonstrate configuration validation."""
    print("\n=== Configuration Validation Demo ===")
    
    try:
        # Valid project configuration
        valid_project = {
            "width": 1920,
            "height": 1080,
            "fps": 30.0
        }
        errors = config_manager.validate_config(valid_project, "project")
        print(f"✓ Valid project config: {len(errors)} errors")
        
        # Invalid project configuration
        invalid_project = {
            "width": -1920,  # Invalid negative width
            "height": 0,     # Invalid zero height
            "fps": -30.0     # Invalid negative fps
        }
        errors = config_manager.validate_config(invalid_project, "project")
        print(f"✓ Invalid project config: {len(errors)} errors detected")
        for error in errors:
            print(f"  - {error.field}: {error.message}")
        
        # Valid effects configuration
        valid_effects = {
            "glow_intensity": 1.0,
            "glow_radius": 3.0,
            "glow_color": [1.0, 1.0, 0.0],
            "particle_count": 50
        }
        errors = config_manager.validate_config(valid_effects, "effects")
        print(f"✓ Valid effects config: {len(errors)} errors")
        
        # Invalid effects configuration
        invalid_effects = {
            "glow_intensity": -1.0,        # Invalid negative intensity
            "glow_color": [2.0, -0.5, 1.0], # Invalid color values
            "particle_count": -50          # Invalid negative count
        }
        errors = config_manager.validate_config(invalid_effects, "effects")
        print(f"✓ Invalid effects config: {len(errors)} errors detected")
        for error in errors:
            print(f"  - {error.field}: {error.message}")
        
    except Exception as e:
        print(f"✗ Error in validation demo: {e}")


def demo_user_preferences(config_manager):
    """Demonstrate user preference management."""
    print("\n=== User Preferences Demo ===")
    
    try:
        # Get default preferences
        auto_save = config_manager.get_user_preference("auto_save")
        print(f"✓ Default auto_save: {auto_save}")
        
        # Set custom preferences
        config_manager.set_user_preference("auto_save", False)
        config_manager.set_user_preference("max_recent_projects", 15)
        config_manager.set_user_preference("show_advanced_options", True)
        print("✓ Set custom preferences")
        
        # Verify preferences were saved
        auto_save = config_manager.get_user_preference("auto_save")
        max_recent = config_manager.get_user_preference("max_recent_projects")
        show_advanced = config_manager.get_user_preference("show_advanced_options")
        print(f"✓ Updated preferences: auto_save={auto_save}, max_recent={max_recent}, advanced={show_advanced}")
        
        # Directory settings
        config_manager.set_directory_setting("input", "custom_input")
        config_manager.set_directory_setting("output", "custom_output")
        input_dir = config_manager.get_directory_setting("input")
        output_dir = config_manager.get_directory_setting("output")
        print(f"✓ Directory settings: input={Path(input_dir).name}, output={Path(output_dir).name}")
        
        # Performance settings
        config_manager.set_performance_setting("max_texture_size", 8192)
        config_manager.set_performance_setting("enable_gpu_acceleration", True)
        texture_size = config_manager.get_performance_setting("max_texture_size")
        gpu_accel = config_manager.get_performance_setting("enable_gpu_acceleration")
        print(f"✓ Performance settings: texture_size={texture_size}, gpu_accel={gpu_accel}")
        
    except Exception as e:
        print(f"✗ Error in user preferences demo: {e}")


def demo_effects_presets(config_manager):
    """Demonstrate effects preset management."""
    print("\n=== Effects Presets Demo ===")
    
    try:
        # Get existing presets
        glow_basic = config_manager.get_effects_preset("shader", "glow_basic")
        print(f"✓ Glow basic preset: intensity={glow_basic['intensity']}, radius={glow_basic['radius']}")
        
        particles_sparkle = config_manager.get_effects_preset("shader", "particles_sparkle")
        print(f"✓ Particles sparkle preset: count={particles_sparkle['count']}, size={particles_sparkle['size']}")
        
        # Create custom preset
        custom_glow = {
            "intensity": 2.5,
            "radius": 8.0,
            "color": [0.0, 1.0, 0.0],  # Green
            "blur_passes": 4
        }
        config_manager.set_effects_preset("shader", "custom_green_glow", custom_glow)
        print("✓ Created custom green glow preset")
        
        # Verify custom preset
        loaded_custom = config_manager.get_effects_preset("shader", "custom_green_glow")
        print(f"✓ Custom preset loaded: color={loaded_custom['color']}, intensity={loaded_custom['intensity']}")
        
        # Color schemes
        classic_colors = config_manager.get_effects_preset("color_schemes", "classic")
        modern_colors = config_manager.get_effects_preset("color_schemes", "modern")
        if classic_colors and modern_colors:
            print(f"✓ Color schemes - Classic active: {classic_colors['active']}, Modern active: {modern_colors['active']}")
        else:
            print("✓ Color schemes available in effects config")
        
    except Exception as e:
        print(f"✗ Error in effects presets demo: {e}")


def demo_templates(config_manager):
    """Demonstrate template management."""
    print("\n=== Template Management Demo ===")
    
    try:
        # Create custom template
        custom_effects = EffectsConfig(
            glow_enabled=True,
            glow_intensity=1.8,
            glow_radius=6.0,
            glow_color=[1.0, 0.0, 1.0],  # Magenta
            particles_enabled=True,
            particle_count=150,
            particle_size=4.0,
            text_animation_enabled=True,
            scale_factor=1.3,
            color_transition_enabled=True,
            start_color=[1.0, 1.0, 1.0],
            end_color=[1.0, 0.0, 1.0],
            background_blur_enabled=True,
            blur_radius=3.0
        )
        
        custom_export = ExportSettings(
            resolution={"width": 2560, "height": 1440},
            bitrate=10000,
            quality="high",
            frame_rate=60.0
        )
        
        custom_template = ConfigTemplate(
            name="Custom Magenta",
            description="High-quality template with magenta effects",
            config={
                "width": 2560,
                "height": 1440,
                "fps": 60.0,
                "background_color": [0.05, 0.0, 0.1, 1.0]  # Dark purple
            },
            effects=custom_effects,
            export_settings=custom_export
        )
        
        # Save custom template
        config_manager._save_template(custom_template)
        print("✓ Created custom magenta template")
        
        # List all templates
        templates = config_manager.list_templates()
        print(f"✓ Available templates: {templates}")
        
        # Load and verify custom template
        loaded_template = config_manager.get_template("Custom Magenta")
        print(f"✓ Loaded custom template: {loaded_template.config['width']}x{loaded_template.config['height']} @ {loaded_template.config['fps']}fps")
        print(f"  - Glow color: {loaded_template.effects.glow_color}")
        print(f"  - Particle count: {loaded_template.effects.particle_count}")
        print(f"  - Export bitrate: {loaded_template.export_settings.bitrate}")
        
        # Create configurations from custom template
        project_config = config_manager.create_project_config("Custom Magenta")
        effects_config = config_manager.create_effects_config("Custom Magenta")
        print(f"✓ Created configs from template: {project_config.width}x{project_config.height}, glow={effects_config.glow_enabled}")
        
    except Exception as e:
        print(f"✗ Error in template demo: {e}")


def demo_export_import(config_manager, temp_dir):
    """Demonstrate configuration export and import."""
    print("\n=== Export/Import Demo ===")
    
    try:
        # Modify some settings for export
        config_manager.set_user_preference("auto_save", False)
        config_manager.set_user_preference("custom_setting", "demo_value")
        config_manager.set_performance_setting("max_texture_size", 8192)
        
        # Export configuration
        export_file = temp_dir / "exported_config.json"
        success = config_manager.export_configuration(export_file, include_templates=True)
        print(f"✓ Exported configuration: {success}")
        print(f"  - Export file size: {export_file.stat().st_size} bytes")
        
        # Show export file structure
        with open(export_file, 'r') as f:
            export_data = json.load(f)
        print(f"  - Export contains: {list(export_data.keys())}")
        print(f"  - Templates included: {len(export_data.get('templates', {}))}")
        
        # Reset configuration
        original_auto_save = config_manager.get_user_preference("auto_save")
        original_texture_size = config_manager.get_performance_setting("max_texture_size")
        config_manager.reset_to_defaults()
        print("✓ Reset configuration to defaults")
        
        # Verify reset
        reset_auto_save = config_manager.get_user_preference("auto_save")
        reset_texture_size = config_manager.get_performance_setting("max_texture_size")
        print(f"  - After reset: auto_save={reset_auto_save}, texture_size={reset_texture_size}")
        
        # Import configuration
        success = config_manager.import_configuration(export_file)
        print(f"✓ Imported configuration: {success}")
        
        # Verify import
        imported_auto_save = config_manager.get_user_preference("auto_save")
        imported_texture_size = config_manager.get_performance_setting("max_texture_size")
        imported_custom = config_manager.get_user_preference("custom_setting")
        print(f"  - After import: auto_save={imported_auto_save}, texture_size={imported_texture_size}")
        print(f"  - Custom setting: {imported_custom}")
        
        # Verify templates were imported
        templates = config_manager.list_templates()
        print(f"  - Templates after import: {len(templates)}")
        
    except Exception as e:
        print(f"✗ Error in export/import demo: {e}")


def demo_migration():
    """Demonstrate configuration migration."""
    print("\n=== Configuration Migration Demo ===")
    
    try:
        # Create temporary directory for migration demo
        temp_dir = Path(tempfile.mkdtemp())
        config_manager = ConfigManager(config_dir=temp_dir)
        
        # Create old version config
        old_config = {
            "version": "1.0",
            "preferences": {
                "auto_save": True,
                "backup_projects": True,
                "max_recent_projects": 5
            },
            "directories": {
                "input": "input",
                "output": "output"
            }
        }
        
        print(f"✓ Created old config (v1.0): {list(old_config.keys())}")
        
        # Migrate configuration
        migrated_config = config_manager._migrate_config(old_config)
        print(f"✓ Migrated to v{migrated_config['version']}")
        print(f"  - New sections added: {[k for k in migrated_config.keys() if k not in old_config.keys()]}")
        print(f"  - Performance settings: {list(migrated_config.get('performance', {}).keys())}")
        print(f"  - New preferences: {[k for k in migrated_config['preferences'].keys() if k not in old_config['preferences'].keys()]}")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"✗ Error in migration demo: {e}")


def main():
    """Run all configuration system demos."""
    print("🎵 Karaoke Video Creator - Configuration System Demo 🎵")
    print("=" * 60)
    
    # Basic configuration demo
    config_manager, temp_dir = demo_basic_configuration()
    if not config_manager:
        return
    
    try:
        # File operations demo
        sample_config = demo_file_operations(config_manager, temp_dir)
        
        # Validation demo
        demo_validation(config_manager)
        
        # User preferences demo
        demo_user_preferences(config_manager)
        
        # Effects presets demo
        demo_effects_presets(config_manager)
        
        # Template management demo
        demo_templates(config_manager)
        
        # Export/import demo
        demo_export_import(config_manager, temp_dir)
        
        # Migration demo
        demo_migration()
        
        print("\n" + "=" * 60)
        print("✅ All configuration system demos completed successfully!")
        print(f"📁 Demo files created in: {temp_dir}")
        print("🔧 Configuration system is ready for use!")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        
    finally:
        # Clean up temporary directory
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                print(f"🧹 Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"⚠️  Could not clean up {temp_dir}: {e}")


if __name__ == "__main__":
    main()