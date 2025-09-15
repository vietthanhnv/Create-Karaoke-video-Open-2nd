"""
Configuration Manager for Karaoke Video Creator

This module provides comprehensive configuration management including:
- JSON/YAML configuration file parsing and validation
- Effects parameter loading and validation
- Project configuration management with templates
- User preference handling and settings persistence
- Configuration migration and version compatibility
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from copy import deepcopy

from src.core.models import (
    ProjectConfig, EffectsConfig, ExportSettings, 
    AudioFile, SubtitleFile, VideoFile, ImageFile
)


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    YML = "yml"


class ConfigVersion(Enum):
    """Configuration file version for migration support."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = "1.1"


@dataclass
class ConfigTemplate:
    """Template for project configurations."""
    name: str
    description: str
    config: Dict[str, Any]
    effects: EffectsConfig
    export_settings: ExportSettings
    version: str = ConfigVersion.CURRENT.value


@dataclass
class ConfigValidationError:
    """Represents a configuration validation error."""
    field: str
    message: str
    severity: str = "error"  # "error", "warning", "info"


class ConfigManager:
    """
    Manages all configuration aspects of the application.
    
    Features:
    - JSON/YAML file parsing with validation
    - Effects parameter management
    - Project configuration templates
    - User preferences integration
    - Configuration migration support
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory for configuration files (defaults to .kiro/config)
        """
        self.config_dir = config_dir or Path(".kiro/config")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates_dir = self.config_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        self.user_config_file = self.config_dir / "user_config.json"
        self.effects_config_file = self.config_dir / "effects_config.json"
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize default templates
        self._initialize_default_templates()
        
        # Load user configuration
        self.user_config = self._load_user_config()
        
        # Load effects configuration
        self.effects_config = self._load_effects_config()
    
    def _initialize_default_templates(self):
        """Initialize default configuration templates."""
        
        # Basic karaoke template
        basic_template = ConfigTemplate(
            name="Basic Karaoke",
            description="Simple karaoke video with basic text effects",
            config={
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "background_color": [0.0, 0.0, 0.0, 1.0]  # Black background
            },
            effects=EffectsConfig(
                glow_enabled=True,
                glow_intensity=0.8,
                glow_radius=3.0,
                glow_color=[1.0, 1.0, 0.0],  # Yellow glow
                color_transition_enabled=True,
                start_color=[1.0, 1.0, 1.0],  # White
                end_color=[1.0, 1.0, 0.0],    # Yellow
                transition_speed=1.0
            ),
            export_settings=ExportSettings(
                resolution={"width": 1920, "height": 1080},
                bitrate=5000,
                quality="high",
                frame_rate=30.0
            )
        )
        
        # Advanced effects template
        advanced_template = ConfigTemplate(
            name="Advanced Effects",
            description="Karaoke video with advanced visual effects",
            config={
                "width": 1920,
                "height": 1080,
                "fps": 30.0,
                "background_color": [0.1, 0.1, 0.2, 1.0]  # Dark blue background
            },
            effects=EffectsConfig(
                glow_enabled=True,
                glow_intensity=1.2,
                glow_radius=5.0,
                glow_color=[0.0, 1.0, 1.0],  # Cyan glow
                particles_enabled=True,
                particle_count=100,
                particle_size=3.0,
                particle_lifetime=2.5,
                text_animation_enabled=True,
                scale_factor=1.1,
                fade_duration=0.3,
                color_transition_enabled=True,
                start_color=[1.0, 1.0, 1.0],
                end_color=[0.0, 1.0, 1.0],
                transition_speed=1.5,
                background_blur_enabled=True,
                blur_radius=2.0,
                blur_intensity=0.5
            ),
            export_settings=ExportSettings(
                resolution={"width": 1920, "height": 1080},
                bitrate=8000,
                quality="high",
                frame_rate=30.0
            )
        )
        
        # Save templates
        self._save_template(basic_template)
        self._save_template(advanced_template)
    
    def _save_template(self, template: ConfigTemplate):
        """Save a configuration template to disk."""
        template_file = self.templates_dir / f"{template.name.lower().replace(' ', '_')}.json"
        
        template_data = {
            "name": template.name,
            "description": template.description,
            "version": template.version,
            "config": template.config,
            "effects": asdict(template.effects),
            "export_settings": asdict(template.export_settings)
        }
        
        try:
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save template {template.name}: {e}")
    
    def _load_user_config(self) -> Dict[str, Any]:
        """Load user configuration from file."""
        if not self.user_config_file.exists():
            # Create default user config
            default_config = {
                "version": ConfigVersion.CURRENT.value,
                "preferences": {
                    "auto_save": True,
                    "backup_projects": True,
                    "max_recent_projects": 10,
                    "default_template": "Basic Karaoke",
                    "show_advanced_options": False
                },
                "directories": {
                    "input": "input",
                    "output": "output",
                    "temp": "temp",
                    "projects": "projects"
                },
                "performance": {
                    "max_texture_size": 4096,
                    "enable_gpu_acceleration": True,
                    "max_memory_usage_mb": 2048,
                    "enable_shader_cache": True
                }
            }
            
            self._save_user_config(default_config)
            return default_config
        
        try:
            with open(self.user_config_file, 'r') as f:
                config = json.load(f)
            
            # Migrate if necessary
            config = self._migrate_config(config)
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load user config: {e}")
            return {}
    
    def _save_user_config(self, config: Dict[str, Any]):
        """Save user configuration to file."""
        try:
            with open(self.user_config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save user config: {e}")
    
    def _load_effects_config(self) -> Dict[str, Any]:
        """Load effects configuration from file."""
        if not self.effects_config_file.exists():
            # Create default effects config
            default_effects = {
                "version": ConfigVersion.CURRENT.value,
                "shader_presets": {
                    "glow_basic": {
                        "intensity": 1.0,
                        "radius": 3.0,
                        "color": [1.0, 1.0, 0.0],
                        "blur_passes": 2
                    },
                    "glow_intense": {
                        "intensity": 1.5,
                        "radius": 5.0,
                        "color": [0.0, 1.0, 1.0],
                        "blur_passes": 3
                    },
                    "particles_sparkle": {
                        "count": 50,
                        "size": 2.0,
                        "lifetime": 2.0,
                        "spawn_rate": 25.0,
                        "velocity_range": [50.0, 100.0]
                    },
                    "particles_confetti": {
                        "count": 100,
                        "size": 3.0,
                        "lifetime": 3.0,
                        "spawn_rate": 33.0,
                        "velocity_range": [75.0, 150.0]
                    }
                },
                "animation_presets": {
                    "fade_smooth": {
                        "duration": 0.5,
                        "easing": "ease_in_out"
                    },
                    "scale_bounce": {
                        "scale_factor": 1.2,
                        "duration": 0.3,
                        "easing": "bounce"
                    },
                    "rotate_spin": {
                        "rotation_speed": 180.0,
                        "duration": 1.0,
                        "easing": "linear"
                    }
                },
                "color_schemes": {
                    "classic": {
                        "inactive": [1.0, 1.0, 1.0],
                        "active": [1.0, 1.0, 0.0],
                        "glow": [1.0, 1.0, 0.0]
                    },
                    "modern": {
                        "inactive": [0.8, 0.8, 0.8],
                        "active": [0.0, 1.0, 1.0],
                        "glow": [0.0, 1.0, 1.0]
                    },
                    "vibrant": {
                        "inactive": [1.0, 1.0, 1.0],
                        "active": [1.0, 0.0, 1.0],
                        "glow": [1.0, 0.0, 1.0]
                    }
                }
            }
            
            self._save_effects_config(default_effects)
            return default_effects
        
        try:
            with open(self.effects_config_file, 'r') as f:
                config = json.load(f)
            
            # Migrate if necessary
            config = self._migrate_config(config)
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load effects config: {e}")
            return {}
    
    def _save_effects_config(self, config: Dict[str, Any]):
        """Save effects configuration to file."""
        try:
            with open(self.effects_config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save effects config: {e}")
    
    def _migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration to current version."""
        current_version = config.get("version", "1.0")
        
        if current_version == ConfigVersion.CURRENT.value:
            return config
        
        # Migration from v1.0 to v1.1
        if current_version == "1.0":
            config = self._migrate_v1_0_to_v1_1(config)
        
        config["version"] = ConfigVersion.CURRENT.value
        return config
    
    def _migrate_v1_0_to_v1_1(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate configuration from v1.0 to v1.1."""
        # Add new performance settings
        if "performance" not in config:
            config["performance"] = {
                "max_texture_size": 4096,
                "enable_gpu_acceleration": True,
                "max_memory_usage_mb": 2048,
                "enable_shader_cache": True
            }
        
        # Update preferences with new options
        if "preferences" in config:
            prefs = config["preferences"]
            if "show_advanced_options" not in prefs:
                prefs["show_advanced_options"] = False
        
        return config
    
    def load_config_file(self, file_path: Union[str, Path], 
                        format_hint: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """
        Load configuration from JSON or YAML file.
        
        Args:
            file_path: Path to configuration file
            format_hint: Optional format hint (auto-detected if None)
            
        Returns:
            Dictionary containing configuration data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is unsupported or invalid
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Determine format
        if format_hint is None:
            suffix = file_path.suffix.lower()
            if suffix == ".json":
                format_hint = ConfigFormat.JSON
            elif suffix in [".yaml", ".yml"]:
                format_hint = ConfigFormat.YAML
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if format_hint == ConfigFormat.JSON:
                    data = json.load(f)
                else:  # YAML
                    data = yaml.safe_load(f)
            
            # Validate and migrate if necessary
            if isinstance(data, dict) and "version" in data:
                data = self._migrate_config(data)
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading {file_path}: {e}")
    
    def save_config_file(self, data: Dict[str, Any], file_path: Union[str, Path],
                        format_hint: Optional[ConfigFormat] = None):
        """
        Save configuration to JSON or YAML file.
        
        Args:
            data: Configuration data to save
            file_path: Path to save configuration file
            format_hint: Optional format hint (auto-detected if None)
        """
        file_path = Path(file_path)
        
        # Determine format
        if format_hint is None:
            suffix = file_path.suffix.lower()
            if suffix == ".json":
                format_hint = ConfigFormat.JSON
            elif suffix in [".yaml", ".yml"]:
                format_hint = ConfigFormat.YAML
            else:
                format_hint = ConfigFormat.JSON  # Default to JSON
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format_hint == ConfigFormat.JSON:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:  # YAML
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
                    
        except Exception as e:
            raise ValueError(f"Error saving {file_path}: {e}")
    
    def validate_config(self, config: Dict[str, Any], 
                       config_type: str = "project") -> List[ConfigValidationError]:
        """
        Validate configuration data.
        
        Args:
            config: Configuration data to validate
            config_type: Type of configuration ("project", "effects", "export")
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if config_type == "project":
            errors.extend(self._validate_project_config(config))
        elif config_type == "effects":
            errors.extend(self._validate_effects_config(config))
        elif config_type == "export":
            errors.extend(self._validate_export_config(config))
        
        return errors
    
    def _validate_project_config(self, config: Dict[str, Any]) -> List[ConfigValidationError]:
        """Validate project configuration."""
        errors = []
        
        # Required fields
        required_fields = ["width", "height", "fps"]
        for field in required_fields:
            if field not in config:
                errors.append(ConfigValidationError(
                    field=field,
                    message=f"Required field '{field}' is missing"
                ))
        
        # Validate dimensions
        if "width" in config:
            width = config["width"]
            if not isinstance(width, int) or width <= 0:
                errors.append(ConfigValidationError(
                    field="width",
                    message="Width must be a positive integer"
                ))
            elif width > 7680:  # 8K limit
                errors.append(ConfigValidationError(
                    field="width",
                    message="Width exceeds maximum supported resolution (7680)",
                    severity="warning"
                ))
        
        if "height" in config:
            height = config["height"]
            if not isinstance(height, int) or height <= 0:
                errors.append(ConfigValidationError(
                    field="height",
                    message="Height must be a positive integer"
                ))
            elif height > 4320:  # 8K limit
                errors.append(ConfigValidationError(
                    field="height",
                    message="Height exceeds maximum supported resolution (4320)",
                    severity="warning"
                ))
        
        # Validate frame rate
        if "fps" in config:
            fps = config["fps"]
            if not isinstance(fps, (int, float)) or fps <= 0:
                errors.append(ConfigValidationError(
                    field="fps",
                    message="FPS must be a positive number"
                ))
            elif fps > 120:
                errors.append(ConfigValidationError(
                    field="fps",
                    message="FPS exceeds recommended maximum (120)",
                    severity="warning"
                ))
        
        return errors
    
    def _validate_effects_config(self, config: Dict[str, Any]) -> List[ConfigValidationError]:
        """Validate effects configuration."""
        errors = []
        
        # Validate glow settings
        if "glow_intensity" in config:
            intensity = config["glow_intensity"]
            if not isinstance(intensity, (int, float)) or intensity < 0:
                errors.append(ConfigValidationError(
                    field="glow_intensity",
                    message="Glow intensity must be a non-negative number"
                ))
        
        if "glow_radius" in config:
            radius = config["glow_radius"]
            if not isinstance(radius, (int, float)) or radius < 0:
                errors.append(ConfigValidationError(
                    field="glow_radius",
                    message="Glow radius must be a non-negative number"
                ))
        
        # Validate color arrays
        color_fields = ["glow_color", "start_color", "end_color"]
        for field in color_fields:
            if field in config:
                color = config[field]
                if not isinstance(color, list) or len(color) != 3:
                    errors.append(ConfigValidationError(
                        field=field,
                        message=f"{field} must be an array of 3 numbers (RGB)"
                    ))
                elif not all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in color):
                    errors.append(ConfigValidationError(
                        field=field,
                        message=f"{field} values must be between 0 and 1"
                    ))
        
        # Validate particle settings
        if "particle_count" in config:
            count = config["particle_count"]
            if not isinstance(count, int) or count < 0:
                errors.append(ConfigValidationError(
                    field="particle_count",
                    message="Particle count must be a non-negative integer"
                ))
            elif count > 1000:
                errors.append(ConfigValidationError(
                    field="particle_count",
                    message="Particle count exceeds recommended maximum (1000)",
                    severity="warning"
                ))
        
        return errors
    
    def _validate_export_config(self, config: Dict[str, Any]) -> List[ConfigValidationError]:
        """Validate export configuration."""
        errors = []
        
        # Validate bitrate
        if "bitrate" in config:
            bitrate = config["bitrate"]
            if not isinstance(bitrate, int) or bitrate <= 0:
                errors.append(ConfigValidationError(
                    field="bitrate",
                    message="Bitrate must be a positive integer"
                ))
        
        # Validate quality setting
        if "quality" in config:
            quality = config["quality"]
            valid_qualities = ["low", "medium", "high", "custom"]
            if quality not in valid_qualities:
                errors.append(ConfigValidationError(
                    field="quality",
                    message=f"Quality must be one of: {', '.join(valid_qualities)}"
                ))
        
        return errors
    
    def create_project_config(self, template_name: Optional[str] = None) -> ProjectConfig:
        """
        Create a new project configuration from template.
        
        Args:
            template_name: Name of template to use (uses default if None)
            
        Returns:
            New ProjectConfig instance
        """
        if template_name is None:
            template_name = self.user_config.get("preferences", {}).get("default_template", "Basic Karaoke")
        
        template = self.get_template(template_name)
        if template is None:
            # Fallback to basic configuration
            return ProjectConfig()
        
        return ProjectConfig(
            width=template.config.get("width", 1920),
            height=template.config.get("height", 1080),
            fps=template.config.get("fps", 30.0)
        )
    
    def create_effects_config(self, template_name: Optional[str] = None) -> EffectsConfig:
        """
        Create a new effects configuration from template.
        
        Args:
            template_name: Name of template to use (uses default if None)
            
        Returns:
            New EffectsConfig instance
        """
        if template_name is None:
            template_name = self.user_config.get("preferences", {}).get("default_template", "Basic Karaoke")
        
        template = self.get_template(template_name)
        if template is None:
            return EffectsConfig()
        
        return template.effects
    
    def get_template(self, name: str) -> Optional[ConfigTemplate]:
        """Get a configuration template by name."""
        template_file = self.templates_dir / f"{name.lower().replace(' ', '_')}.json"
        
        if not template_file.exists():
            return None
        
        try:
            with open(template_file, 'r') as f:
                data = json.load(f)
            
            return ConfigTemplate(
                name=data["name"],
                description=data["description"],
                config=data["config"],
                effects=EffectsConfig(**data["effects"]),
                export_settings=ExportSettings(**data["export_settings"]),
                version=data.get("version", "1.0")
            )
        except Exception as e:
            self.logger.error(f"Failed to load template {name}: {e}")
            return None
    
    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        templates = []
        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    data = json.load(f)
                templates.append(data["name"])
            except Exception:
                continue
        return sorted(templates)
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference value."""
        return self.user_config.get("preferences", {}).get(key, default)
    
    def set_user_preference(self, key: str, value: Any):
        """Set a user preference value."""
        if "preferences" not in self.user_config:
            self.user_config["preferences"] = {}
        
        self.user_config["preferences"][key] = value
        self._save_user_config(self.user_config)
    
    def get_directory_setting(self, key: str) -> str:
        """Get a directory setting."""
        return self.user_config.get("directories", {}).get(key, key)
    
    def set_directory_setting(self, key: str, path: str):
        """Set a directory setting."""
        if "directories" not in self.user_config:
            self.user_config["directories"] = {}
        
        self.user_config["directories"][key] = str(Path(path).resolve())
        self._save_user_config(self.user_config)
    
    def get_performance_setting(self, key: str, default: Any = None) -> Any:
        """Get a performance setting."""
        return self.user_config.get("performance", {}).get(key, default)
    
    def set_performance_setting(self, key: str, value: Any):
        """Set a performance setting."""
        if "performance" not in self.user_config:
            self.user_config["performance"] = {}
        
        self.user_config["performance"][key] = value
        self._save_user_config(self.user_config)
    
    def get_effects_preset(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get an effects preset by category and name."""
        return self.effects_config.get(f"{category}_presets", {}).get(name)
    
    def set_effects_preset(self, category: str, name: str, preset: Dict[str, Any]):
        """Set an effects preset."""
        preset_key = f"{category}_presets"
        if preset_key not in self.effects_config:
            self.effects_config[preset_key] = {}
        
        self.effects_config[preset_key][name] = preset
        self._save_effects_config(self.effects_config)
    
    def export_configuration(self, file_path: Union[str, Path], 
                           include_templates: bool = True) -> bool:
        """
        Export all configuration to a file.
        
        Args:
            file_path: Path to save configuration
            include_templates: Whether to include templates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            export_data = {
                "version": ConfigVersion.CURRENT.value,
                "exported_at": str(Path().cwd()),
                "user_config": self.user_config,
                "effects_config": self.effects_config
            }
            
            if include_templates:
                templates = {}
                for template_name in self.list_templates():
                    template = self.get_template(template_name)
                    if template:
                        # Convert template to dict manually to handle dataclasses
                        template_dict = {
                            "name": template.name,
                            "description": template.description,
                            "version": template.version,
                            "config": template.config,
                            "effects": asdict(template.effects),
                            "export_settings": asdict(template.export_settings)
                        }
                        templates[template_name] = template_dict
                export_data["templates"] = templates
            
            self.save_config_file(export_data, file_path)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_configuration(self, file_path: Union[str, Path], 
                           merge: bool = True) -> bool:
        """
        Import configuration from a file.
        
        Args:
            file_path: Path to configuration file
            merge: Whether to merge with existing config (True) or replace (False)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import_data = self.load_config_file(file_path)
            
            if not merge:
                # Replace existing configuration
                if "user_config" in import_data:
                    self.user_config = import_data["user_config"]
                    self._save_user_config(self.user_config)
                
                if "effects_config" in import_data:
                    self.effects_config = import_data["effects_config"]
                    self._save_effects_config(self.effects_config)
            else:
                # Merge with existing configuration
                if "user_config" in import_data:
                    self._merge_dict(self.user_config, import_data["user_config"])
                    self._save_user_config(self.user_config)
                
                if "effects_config" in import_data:
                    self._merge_dict(self.effects_config, import_data["effects_config"])
                    self._save_effects_config(self.effects_config)
            
            # Import templates
            if "templates" in import_data:
                for template_name, template_data in import_data["templates"].items():
                    # Reconstruct template with proper dataclass instances
                    template = ConfigTemplate(
                        name=template_data["name"],
                        description=template_data["description"],
                        version=template_data.get("version", "1.0"),
                        config=template_data["config"],
                        effects=EffectsConfig(**template_data["effects"]),
                        export_settings=ExportSettings(**template_data["export_settings"])
                    )
                    self._save_template(template)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import configuration: {e}")
            return False
    
    def _merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Recursively merge source dictionary into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value
    
    def reset_to_defaults(self):
        """Reset all configuration to defaults."""
        # Remove existing config files
        if self.user_config_file.exists():
            self.user_config_file.unlink()
        if self.effects_config_file.exists():
            self.effects_config_file.unlink()
        
        # Reload defaults
        self.user_config = self._load_user_config()
        self.effects_config = self._load_effects_config()
        
        # Reinitialize templates
        self._initialize_default_templates()