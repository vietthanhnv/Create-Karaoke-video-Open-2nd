"""
Enhanced Text Effects Manager with Advanced Font Styling and Visual Effects

This module provides a comprehensive effects system with support for:
- Font styling (color, size, family, weight, style)
- Advanced visual effects (glow, outline, shadow, animations)
- Real-time parameter adjustment
- Effect layering and blending
- Performance optimization
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import math

try:
    from .models import Effect
except ImportError:
    from models import Effect


class FontWeight(Enum):
    """Font weight options."""
    THIN = 100
    EXTRA_LIGHT = 200
    LIGHT = 300
    NORMAL = 400
    MEDIUM = 500
    SEMI_BOLD = 600
    BOLD = 700
    EXTRA_BOLD = 800
    BLACK = 900


class FontStyle(Enum):
    """Font style options."""
    NORMAL = "normal"
    ITALIC = "italic"
    OBLIQUE = "oblique"


class TextAlignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class EffectType(Enum):
    """Types of available text effects."""
    # Font styling
    FONT_COLOR = "font_color"
    FONT_SIZE = "font_size"
    FONT_FAMILY = "font_family"
    FONT_WEIGHT = "font_weight"
    FONT_STYLE = "font_style"
    
    # Visual effects
    GLOW = "glow"
    OUTLINE = "outline"
    SHADOW = "shadow"
    GRADIENT = "gradient"
    TEXTURE = "texture"
    
    # Animation effects
    FADE = "fade"
    BOUNCE = "bounce"
    WAVE = "wave"
    TYPEWRITER = "typewriter"
    ZOOM = "zoom"
    ROTATE = "rotate"
    SLIDE = "slide"
    
    # Advanced effects
    NEON = "neon"
    FIRE = "fire"
    ICE = "ice"
    METAL = "metal"
    GLASS = "glass"
    RAINBOW = "rainbow"


class BlendMode(Enum):
    """Blending modes for effect layers."""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"


@dataclass
class FontProperties:
    """Font styling properties."""
    family: str = "Arial"
    size: float = 24.0
    weight: FontWeight = FontWeight.NORMAL
    style: FontStyle = FontStyle.NORMAL
    color: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0])  # RGBA
    alignment: TextAlignment = TextAlignment.CENTER
    line_spacing: float = 1.2
    letter_spacing: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'family': self.family,
            'size': self.size,
            'weight': self.weight.value if hasattr(self.weight, 'value') else self.weight,
            'style': self.style.value if hasattr(self.style, 'value') else self.style,
            'color': self.color,
            'alignment': self.alignment.value if hasattr(self.alignment, 'value') else self.alignment,
            'line_spacing': self.line_spacing,
            'letter_spacing': self.letter_spacing
        }


@dataclass
class EffectParameters:
    """Parameters for a specific effect."""
    # Common parameters
    enabled: bool = True
    opacity: float = 1.0
    blend_mode: BlendMode = BlendMode.NORMAL
    
    # Effect-specific parameters (stored as dict for flexibility)
    params: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter value with default."""
        return self.params.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set parameter value."""
        self.params[key] = value
    
    def update(self, params: Dict[str, Any]):
        """Update multiple parameters."""
        self.params.update(params)


@dataclass
class EffectLayer:
    """Represents a single effect layer with ordering and blending."""
    effect_type: EffectType
    parameters: EffectParameters
    order: int = 0
    name: str = ""
    id: str = ""
    
    def __post_init__(self):
        """Initialize after creation."""
        if not self.name:
            self.name = self.effect_type.value.replace('_', ' ').title()
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())


@dataclass
class EffectPreset:
    """Predefined effect configuration."""
    name: str
    description: str
    font_properties: FontProperties
    effect_layers: List[EffectLayer]
    preview_text: str = "Sample Text"
    category: str = "General"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'font_properties': self.font_properties.to_dict(),
            'effect_layers': [
                {
                    'effect_type': layer.effect_type.value,
                    'parameters': {
                        'enabled': layer.parameters.enabled,
                        'opacity': layer.parameters.opacity,
                        'blend_mode': layer.parameters.blend_mode.value,
                        'params': layer.parameters.params
                    },
                    'order': layer.order,
                    'name': layer.name,
                    'id': layer.id
                }
                for layer in self.effect_layers
            ],
            'preview_text': self.preview_text,
            'category': self.category
        }


class EnhancedEffectsManager:
    """
    Enhanced effects manager with comprehensive font styling and visual effects.
    
    Provides advanced text styling capabilities including:
    - Font properties (family, size, weight, style, color)
    - Visual effects (glow, outline, shadow, gradient, texture)
    - Animation effects (fade, bounce, wave, typewriter, etc.)
    - Advanced effects (neon, fire, ice, metal, glass, rainbow)
    - Effect layering and blending
    - Performance optimization
    """
    
    def __init__(self):
        self.font_properties = FontProperties()
        self.effect_layers: List[EffectLayer] = []
        self.effect_presets: Dict[str, EffectPreset] = {}
        self.shader_cache: Dict[str, str] = {}
        self.animation_time = 0.0
        
        self._initialize_default_effects()
        self._initialize_presets()
    
    def _initialize_default_effects(self):
        """Initialize default effect templates with comprehensive parameters."""
        self.default_effects = {
            # Font styling effects
            EffectType.FONT_COLOR: {
                'name': 'Font Color',
                'parameters': {
                    'color': [1.0, 1.0, 1.0, 1.0],  # RGBA
                    'gradient_enabled': False,
                    'gradient_colors': [[1.0, 1.0, 1.0, 1.0], [0.8, 0.8, 0.8, 1.0]],
                    'gradient_direction': 0.0,  # Angle in degrees
                    'gradient_type': 'linear'  # linear, radial, conic
                }
            },
            
            EffectType.FONT_SIZE: {
                'name': 'Font Size',
                'parameters': {
                    'size': 24.0,
                    'scale_x': 1.0,
                    'scale_y': 1.0,
                    'adaptive_scaling': True,
                    'min_size': 8.0,
                    'max_size': 72.0
                }
            },
            
            EffectType.FONT_FAMILY: {
                'name': 'Font Family',
                'parameters': {
                    'family': 'Arial',
                    'fallback_fonts': ['Helvetica', 'sans-serif'],
                    'custom_font_path': None
                }
            },
            
            EffectType.FONT_WEIGHT: {
                'name': 'Font Weight',
                'parameters': {
                    'weight': FontWeight.NORMAL.value,
                    'synthetic_bold': False,
                    'bold_strength': 1.0
                }
            },
            
            EffectType.FONT_STYLE: {
                'name': 'Font Style',
                'parameters': {
                    'style': FontStyle.NORMAL.value,
                    'italic_angle': 15.0,
                    'synthetic_italic': False
                }
            },
            
            # Visual effects
            EffectType.GLOW: {
                'name': 'Glow Effect',
                'parameters': {
                    'radius': 8.0,
                    'intensity': 1.0,
                    'color': [1.0, 1.0, 0.0, 1.0],  # Yellow
                    'falloff': 2.0,
                    'quality': 16,  # Number of samples
                    'inner_glow': False,
                    'outer_glow': True,
                    'glow_type': 'gaussian'  # gaussian, box, motion
                }
            },
            
            EffectType.OUTLINE: {
                'name': 'Outline Effect',
                'parameters': {
                    'width': 3.0,
                    'color': [0.0, 0.0, 0.0, 1.0],  # Black
                    'softness': 0.5,
                    'quality': 16,
                    'outline_type': 'uniform',  # uniform, gradient, textured
                    'gradient_colors': [[0.0, 0.0, 0.0, 1.0], [0.3, 0.3, 0.3, 1.0]],
                    'texture_path': None
                }
            },
            
            EffectType.SHADOW: {
                'name': 'Drop Shadow',
                'parameters': {
                    'offset_x': 4.0,
                    'offset_y': 4.0,
                    'blur_radius': 3.0,
                    'color': [0.0, 0.0, 0.0, 0.8],
                    'distance': 5.0,
                    'angle': 135.0,  # Degrees
                    'spread': 0.0,
                    'inner_shadow': False
                }
            },
            
            EffectType.GRADIENT: {
                'name': 'Gradient Fill',
                'parameters': {
                    'colors': [
                        [1.0, 0.0, 0.0, 1.0],  # Red
                        [0.0, 0.0, 1.0, 1.0]   # Blue
                    ],
                    'stops': [0.0, 1.0],
                    'type': 'linear',  # linear, radial, conic, diamond
                    'angle': 0.0,
                    'center_x': 0.5,
                    'center_y': 0.5,
                    'scale': 1.0,
                    'repeat': False
                }
            },
            
            # Animation effects
            EffectType.FADE: {
                'name': 'Fade Animation',
                'parameters': {
                    'fade_in_duration': 0.5,
                    'fade_out_duration': 0.5,
                    'fade_in_curve': 'ease_in_out',  # linear, ease_in, ease_out, ease_in_out
                    'fade_out_curve': 'ease_in_out',
                    'start_opacity': 0.0,
                    'end_opacity': 1.0
                }
            },
            
            EffectType.BOUNCE: {
                'name': 'Bounce Animation',
                'parameters': {
                    'amplitude': 20.0,
                    'frequency': 2.0,
                    'damping': 0.8,
                    'direction': 'vertical',  # vertical, horizontal, both
                    'bounce_type': 'elastic',  # elastic, spring, sine
                    'duration': 1.0
                }
            },
            
            EffectType.WAVE: {
                'name': 'Wave Animation',
                'parameters': {
                    'amplitude': 10.0,
                    'frequency': 1.0,
                    'speed': 2.0,
                    'direction': 'horizontal',  # horizontal, vertical, circular
                    'wave_type': 'sine',  # sine, square, triangle, sawtooth
                    'phase_offset': 0.0
                }
            },
            
            EffectType.TYPEWRITER: {
                'name': 'Typewriter Effect',
                'parameters': {
                    'speed': 10.0,  # Characters per second
                    'cursor_visible': True,
                    'cursor_blink_rate': 1.0,
                    'cursor_character': '|',
                    'sound_enabled': False,
                    'sound_path': None
                }
            },
            
            EffectType.ZOOM: {
                'name': 'Zoom Animation',
                'parameters': {
                    'start_scale': 0.1,
                    'end_scale': 1.0,
                    'duration': 1.0,
                    'curve': 'ease_out',
                    'center_x': 0.5,
                    'center_y': 0.5,
                    'zoom_type': 'uniform'  # uniform, horizontal, vertical
                }
            },
            
            EffectType.ROTATE: {
                'name': 'Rotation Animation',
                'parameters': {
                    'start_angle': 0.0,
                    'end_angle': 360.0,
                    'duration': 2.0,
                    'curve': 'linear',
                    'center_x': 0.5,
                    'center_y': 0.5,
                    'rotation_type': 'continuous'  # continuous, oscillate
                }
            },
            
            EffectType.SLIDE: {
                'name': 'Slide Animation',
                'parameters': {
                    'start_x': -100.0,
                    'start_y': 0.0,
                    'end_x': 0.0,
                    'end_y': 0.0,
                    'duration': 1.0,
                    'curve': 'ease_out',
                    'slide_type': 'position'  # position, offset
                }
            },
            
            # Advanced effects
            EffectType.NEON: {
                'name': 'Neon Effect',
                'parameters': {
                    'glow_color': [0.0, 1.0, 1.0, 1.0],  # Cyan
                    'core_color': [1.0, 1.0, 1.0, 1.0],  # White
                    'glow_radius': 12.0,
                    'glow_intensity': 2.0,
                    'flicker_enabled': True,
                    'flicker_speed': 5.0,
                    'flicker_intensity': 0.3,
                    'tube_width': 2.0
                }
            },
            
            EffectType.FIRE: {
                'name': 'Fire Effect',
                'parameters': {
                    'flame_height': 30.0,
                    'flame_width': 20.0,
                    'flame_colors': [
                        [1.0, 0.0, 0.0, 1.0],  # Red
                        [1.0, 0.5, 0.0, 1.0],  # Orange
                        [1.0, 1.0, 0.0, 1.0]   # Yellow
                    ],
                    'animation_speed': 3.0,
                    'turbulence': 0.5,
                    'heat_distortion': True
                }
            },
            
            EffectType.ICE: {
                'name': 'Ice Effect',
                'parameters': {
                    'ice_color': [0.7, 0.9, 1.0, 0.8],  # Light blue
                    'frost_intensity': 0.6,
                    'crystal_size': 2.0,
                    'refraction_strength': 0.3,
                    'sparkle_enabled': True,
                    'sparkle_density': 0.1
                }
            },
            
            EffectType.METAL: {
                'name': 'Metal Effect',
                'parameters': {
                    'metal_type': 'chrome',  # chrome, gold, silver, copper, steel
                    'reflection_strength': 0.8,
                    'roughness': 0.1,
                    'metallic': 1.0,
                    'environment_map': None,
                    'anisotropy': 0.0
                }
            },
            
            EffectType.GLASS: {
                'name': 'Glass Effect',
                'parameters': {
                    'transparency': 0.3,
                    'refraction_index': 1.5,
                    'thickness': 5.0,
                    'surface_roughness': 0.05,
                    'tint_color': [1.0, 1.0, 1.0, 1.0],
                    'caustics_enabled': True
                }
            },
            
            EffectType.RAINBOW: {
                'name': 'Rainbow Effect',
                'parameters': {
                    'hue_shift_speed': 1.0,
                    'saturation': 1.0,
                    'brightness': 1.0,
                    'rainbow_width': 1.0,
                    'direction': 'horizontal',  # horizontal, vertical, diagonal, radial
                    'cycle_duration': 3.0
                }
            }
        }
    
    def _initialize_presets(self):
        """Initialize built-in effect presets."""
        # Karaoke presets
        self.effect_presets['karaoke_classic'] = EffectPreset(
            name="Classic Karaoke",
            description="Traditional karaoke style with yellow text and black outline",
            font_properties=FontProperties(
                family="Arial",
                size=32.0,
                weight=FontWeight.BOLD,
                color=[1.0, 1.0, 0.0, 1.0]  # Yellow
            ),
            effect_layers=[
                EffectLayer(
                    effect_type=EffectType.OUTLINE,
                    parameters=EffectParameters(params={
                        'width': 3.0,
                        'color': [0.0, 0.0, 0.0, 1.0],
                        'softness': 0.3
                    }),
                    order=0
                )
            ],
            category="Karaoke"
        )
        
        self.effect_presets['karaoke_neon'] = EffectPreset(
            name="Neon Karaoke",
            description="Modern neon-style karaoke with glow effects",
            font_properties=FontProperties(
                family="Arial",
                size=36.0,
                weight=FontWeight.BOLD,
                color=[1.0, 1.0, 1.0, 1.0]  # White
            ),
            effect_layers=[
                EffectLayer(
                    effect_type=EffectType.NEON,
                    parameters=EffectParameters(params={
                        'glow_color': [0.0, 1.0, 1.0, 1.0],
                        'glow_radius': 15.0,
                        'glow_intensity': 2.5,
                        'flicker_enabled': True
                    }),
                    order=0
                )
            ],
            category="Karaoke"
        )
        
        # Movie subtitle presets
        self.effect_presets['movie_classic'] = EffectPreset(
            name="Classic Movie",
            description="Traditional movie subtitle style",
            font_properties=FontProperties(
                family="Arial",
                size=24.0,
                weight=FontWeight.NORMAL,
                color=[1.0, 1.0, 1.0, 1.0]  # White
            ),
            effect_layers=[
                EffectLayer(
                    effect_type=EffectType.SHADOW,
                    parameters=EffectParameters(params={
                        'offset_x': 2.0,
                        'offset_y': 2.0,
                        'blur_radius': 2.0,
                        'color': [0.0, 0.0, 0.0, 0.8]
                    }),
                    order=0
                )
            ],
            category="Movie"
        )
        
        # Gaming presets
        self.effect_presets['gaming_fire'] = EffectPreset(
            name="Fire Gaming",
            description="Fiery text effect for gaming content",
            font_properties=FontProperties(
                family="Impact",
                size=40.0,
                weight=FontWeight.BOLD,
                color=[1.0, 0.3, 0.0, 1.0]  # Orange-red
            ),
            effect_layers=[
                EffectLayer(
                    effect_type=EffectType.FIRE,
                    parameters=EffectParameters(params={
                        'flame_height': 25.0,
                        'animation_speed': 4.0,
                        'turbulence': 0.7
                    }),
                    order=0
                ),
                EffectLayer(
                    effect_type=EffectType.OUTLINE,
                    parameters=EffectParameters(params={
                        'width': 2.0,
                        'color': [0.0, 0.0, 0.0, 1.0]
                    }),
                    order=1
                )
            ],
            category="Gaming"
        )
        
        # Elegant presets
        self.effect_presets['elegant_gold'] = EffectPreset(
            name="Elegant Gold",
            description="Luxurious gold text with subtle effects",
            font_properties=FontProperties(
                family="Times New Roman",
                size=28.0,
                weight=FontWeight.SEMI_BOLD,
                style=FontStyle.ITALIC,
                color=[1.0, 0.8, 0.0, 1.0]  # Gold
            ),
            effect_layers=[
                EffectLayer(
                    effect_type=EffectType.METAL,
                    parameters=EffectParameters(params={
                        'metal_type': 'gold',
                        'reflection_strength': 0.6
                    }),
                    order=0
                ),
                EffectLayer(
                    effect_type=EffectType.SHADOW,
                    parameters=EffectParameters(params={
                        'offset_x': 3.0,
                        'offset_y': 3.0,
                        'blur_radius': 4.0,
                        'color': [0.0, 0.0, 0.0, 0.5]
                    }),
                    order=1
                )
            ],
            category="Elegant"
        )
    
    # Font property methods
    def set_font_family(self, family: str):
        """Set font family."""
        self.font_properties.family = family
    
    def set_font_size(self, size: float):
        """Set font size."""
        self.font_properties.size = max(8.0, min(144.0, size))
    
    def set_font_weight(self, weight: FontWeight):
        """Set font weight."""
        self.font_properties.weight = weight
    
    def set_font_style(self, style: FontStyle):
        """Set font style."""
        self.font_properties.style = style
    
    def set_font_color(self, color: List[float]):
        """Set font color (RGBA)."""
        self.font_properties.color = color[:4]  # Ensure RGBA
    
    def set_text_alignment(self, alignment: TextAlignment):
        """Set text alignment."""
        self.font_properties.alignment = alignment
    
    def set_line_spacing(self, spacing: float):
        """Set line spacing multiplier."""
        self.font_properties.line_spacing = max(0.5, min(3.0, spacing))
    
    def set_letter_spacing(self, spacing: float):
        """Set letter spacing in pixels."""
        self.font_properties.letter_spacing = spacing
    
    # Effect layer methods
    def add_effect_layer(self, effect_type: EffectType, parameters: Dict[str, Any] = None) -> EffectLayer:
        """Add a new effect layer."""
        if parameters is None:
            parameters = self.default_effects.get(effect_type, {}).get('parameters', {})
        
        effect_params = EffectParameters()
        effect_params.update(parameters)
        
        layer = EffectLayer(
            effect_type=effect_type,
            parameters=effect_params,
            order=len(self.effect_layers)
        )
        
        self.effect_layers.append(layer)
        return layer
    
    def remove_effect_layer(self, layer_id: str) -> bool:
        """Remove an effect layer by ID."""
        for i, layer in enumerate(self.effect_layers):
            if layer.id == layer_id:
                del self.effect_layers[i]
                self._reorder_layers()
                return True
        return False
    
    def get_effect_layer(self, layer_id: str) -> Optional[EffectLayer]:
        """Get effect layer by ID."""
        for layer in self.effect_layers:
            if layer.id == layer_id:
                return layer
        return None
    
    def update_effect_parameters(self, layer_id: str, parameters: Dict[str, Any]):
        """Update parameters for an effect layer."""
        layer = self.get_effect_layer(layer_id)
        if layer:
            layer.parameters.update(parameters)
    
    def toggle_effect_layer(self, layer_id: str, enabled: bool = None) -> bool:
        """Toggle or set enabled state of an effect layer."""
        layer = self.get_effect_layer(layer_id)
        if layer:
            if enabled is None:
                layer.parameters.enabled = not layer.parameters.enabled
            else:
                layer.parameters.enabled = enabled
            return layer.parameters.enabled
        return False
    
    def reorder_effect_layer(self, layer_id: str, new_order: int):
        """Change the order of an effect layer."""
        layer = self.get_effect_layer(layer_id)
        if layer:
            # Remove the layer from its current position
            self.effect_layers.remove(layer)
            
            # Insert at the new position
            new_order = max(0, min(new_order, len(self.effect_layers)))
            self.effect_layers.insert(new_order, layer)
            
            # Reassign orders to be sequential
            self._reorder_layers()
    
    def _reorder_layers(self):
        """Reassign orders to ensure they're sequential."""
        for i, layer in enumerate(self.effect_layers):
            layer.order = i
    
    def clear_all_effects(self):
        """Remove all effect layers."""
        self.effect_layers.clear()
    
    # Preset methods
    def apply_preset(self, preset_name: str) -> bool:
        """Apply an effect preset."""
        if preset_name in self.effect_presets:
            preset = self.effect_presets[preset_name]
            
            # Apply font properties
            self.font_properties = FontProperties(**preset.font_properties.to_dict())
            
            # Clear existing effects and apply preset effects
            self.clear_all_effects()
            for layer_data in preset.effect_layers:
                layer = EffectLayer(
                    effect_type=layer_data.effect_type,
                    parameters=EffectParameters(
                        enabled=layer_data.parameters.enabled,
                        opacity=layer_data.parameters.opacity,
                        blend_mode=layer_data.parameters.blend_mode,
                        params=layer_data.parameters.params.copy()
                    ),
                    order=layer_data.order,
                    name=layer_data.name
                )
                self.effect_layers.append(layer)
            
            return True
        return False
    
    def get_available_presets(self) -> List[str]:
        """Get list of available preset names."""
        return list(self.effect_presets.keys())
    
    def get_preset_info(self, preset_name: str) -> Optional[EffectPreset]:
        """Get preset information."""
        return self.effect_presets.get(preset_name)
    
    def save_preset(self, name: str, description: str, category: str = "Custom") -> bool:
        """Save current configuration as a preset."""
        preset = EffectPreset(
            name=name,
            description=description,
            font_properties=FontProperties(**self.font_properties.to_dict()),
            effect_layers=[
                EffectLayer(
                    effect_type=layer.effect_type,
                    parameters=EffectParameters(
                        enabled=layer.parameters.enabled,
                        opacity=layer.parameters.opacity,
                        blend_mode=layer.parameters.blend_mode,
                        params=layer.parameters.params.copy()
                    ),
                    order=layer.order,
                    name=layer.name,
                    id=layer.id
                )
                for layer in self.effect_layers
            ],
            category=category
        )
        
        self.effect_presets[name] = preset
        return True
    
    # Animation methods
    def update_animation_time(self, time: float):
        """Update animation time for time-based effects."""
        self.animation_time = time
    
    def get_animated_parameters(self, layer: EffectLayer, current_time: float) -> Dict[str, Any]:
        """Get parameters with animation applied."""
        params = layer.parameters.params.copy()
        
        if layer.effect_type in [EffectType.BOUNCE, EffectType.WAVE, EffectType.ROTATE]:
            # Apply time-based animations
            if layer.effect_type == EffectType.BOUNCE:
                amplitude = params.get('amplitude', 20.0)
                frequency = params.get('frequency', 2.0)
                damping = params.get('damping', 0.8)
                
                bounce_value = amplitude * math.sin(current_time * frequency * 2 * math.pi)
                bounce_value *= math.exp(-damping * current_time)
                
                params['current_offset_y'] = bounce_value
            
            elif layer.effect_type == EffectType.WAVE:
                amplitude = params.get('amplitude', 10.0)
                frequency = params.get('frequency', 1.0)
                speed = params.get('speed', 2.0)
                
                wave_value = amplitude * math.sin(current_time * speed * 2 * math.pi)
                params['current_wave_offset'] = wave_value
            
            elif layer.effect_type == EffectType.ROTATE:
                start_angle = params.get('start_angle', 0.0)
                end_angle = params.get('end_angle', 360.0)
                duration = params.get('duration', 2.0)
                
                progress = (current_time % duration) / duration
                current_angle = start_angle + (end_angle - start_angle) * progress
                params['current_angle'] = current_angle
        
        return params
    
    # Utility methods
    def get_active_effects(self) -> List[EffectLayer]:
        """Get list of enabled effect layers."""
        return [layer for layer in self.effect_layers if layer.parameters.enabled]
    
    def get_effect_count(self) -> int:
        """Get total number of effect layers."""
        return len(self.effect_layers)
    
    def get_enabled_effect_count(self) -> int:
        """Get number of enabled effect layers."""
        return len(self.get_active_effects())
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration to dictionary."""
        return {
            'font_properties': self.font_properties.to_dict(),
            'effect_layers': [
                {
                    'effect_type': layer.effect_type.value,
                    'parameters': {
                        'enabled': layer.parameters.enabled,
                        'opacity': layer.parameters.opacity,
                        'blend_mode': layer.parameters.blend_mode.value,
                        'params': layer.parameters.params
                    },
                    'order': layer.order,
                    'name': layer.name,
                    'id': layer.id
                }
                for layer in self.effect_layers
            ]
        }
    
    def import_configuration(self, config: Dict[str, Any]) -> bool:
        """Import configuration from dictionary."""
        try:
            # Import font properties
            if 'font_properties' in config:
                font_data = config['font_properties']
                self.font_properties = FontProperties(
                    family=font_data.get('family', 'Arial'),
                    size=font_data.get('size', 24.0),
                    weight=FontWeight(font_data.get('weight', FontWeight.NORMAL.value)),
                    style=FontStyle(font_data.get('style', FontStyle.NORMAL.value)),
                    color=font_data.get('color', [1.0, 1.0, 1.0, 1.0]),
                    alignment=TextAlignment(font_data.get('alignment', TextAlignment.CENTER.value)),
                    line_spacing=font_data.get('line_spacing', 1.2),
                    letter_spacing=font_data.get('letter_spacing', 0.0)
                )
            
            # Import effect layers
            if 'effect_layers' in config:
                self.effect_layers.clear()
                for layer_data in config['effect_layers']:
                    effect_type = EffectType(layer_data['effect_type'])
                    params_data = layer_data['parameters']
                    
                    parameters = EffectParameters(
                        enabled=params_data.get('enabled', True),
                        opacity=params_data.get('opacity', 1.0),
                        blend_mode=BlendMode(params_data.get('blend_mode', BlendMode.NORMAL.value)),
                        params=params_data.get('params', {})
                    )
                    
                    layer = EffectLayer(
                        effect_type=effect_type,
                        parameters=parameters,
                        order=layer_data.get('order', 0),
                        name=layer_data.get('name', ''),
                        id=layer_data.get('id', '')
                    )
                    
                    self.effect_layers.append(layer)
                
                self._reorder_layers()
            
            return True
        except Exception as e:
            print(f"Error importing configuration: {e}")
            return False