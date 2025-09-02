"""
Text Effects Manager for OpenGL-based subtitle effects.

This module provides a comprehensive effects system with support for multiple
effect types, parameter management, layering, and real-time preview.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

try:
    from .models import Effect
except ImportError:
    from models import Effect


class EffectType(Enum):
    """Types of available text effects."""
    GLOW = "glow"
    OUTLINE = "outline"
    SHADOW = "shadow"
    FADE = "fade"
    BOUNCE = "bounce"
    COLOR_TRANSITION = "color_transition"
    TYPEWRITER = "typewriter"
    WAVE = "wave"


@dataclass
class EffectLayer:
    """Represents a single effect layer with ordering and blending."""
    effect: Effect
    order: int = 0
    blend_mode: str = "normal"  # normal, multiply, screen, overlay
    opacity: float = 1.0
    enabled: bool = True


@dataclass
class EffectPreset:
    """Predefined effect configuration."""
    name: str
    description: str
    effects: List[Effect]
    preview_text: str = "Sample Text"


class EffectsManager:
    """
    Manages text effects for subtitle rendering with OpenGL shaders.
    
    Provides effect creation, parameter management, layering, and
    real-time preview capabilities.
    """
    
    def __init__(self):
        self.effect_layers: List[EffectLayer] = []
        self.effect_presets: Dict[str, EffectPreset] = {}
        self.shader_cache: Dict[str, str] = {}
        self._initialize_default_effects()
        self._initialize_presets()
    
    def _initialize_default_effects(self):
        """Initialize default effect templates."""
        self.default_effects = {
            EffectType.GLOW: {
                'name': 'Glow Effect',
                'parameters': {
                    'radius': 5.0,
                    'intensity': 0.8,
                    'color': [1.0, 1.0, 0.0],  # Yellow
                    'falloff': 2.0
                }
            },
            EffectType.OUTLINE: {
                'name': 'Outline Effect',
                'parameters': {
                    'width': 2.0,
                    'color': [0.0, 0.0, 0.0],  # Black
                    'softness': 0.5,
                    'quality': 8  # Number of samples
                }
            },
            EffectType.SHADOW: {
                'name': 'Shadow Effect',
                'parameters': {
                    'offset_x': 3.0,
                    'offset_y': 3.0,
                    'blur_radius': 2.0,
                    'color': [0.0, 0.0, 0.0],  # Black
                    'opacity': 0.7
                }
            },
            EffectType.FADE: {
                'name': 'Fade In/Out',
                'parameters': {
                    'fade_in_duration': 0.5,
                    'fade_out_duration': 0.5,
                    'fade_type': 'linear'  # linear, ease_in, ease_out, ease_in_out
                }
            },
            EffectType.BOUNCE: {
                'name': 'Bounce Animation',
                'parameters': {
                    'amplitude': 10.0,
                    'frequency': 2.0,
                    'damping': 0.8,
                    'duration': 1.0
                }
            },
            EffectType.COLOR_TRANSITION: {
                'name': 'Color Transition',
                'parameters': {
                    'start_color': [1.0, 1.0, 1.0],  # White
                    'end_color': [1.0, 0.0, 0.0],    # Red
                    'duration': 2.0,
                    'transition_type': 'smooth'  # smooth, pulse, flash
                }
            },
            EffectType.WAVE: {
                'name': 'Wave Animation',
                'parameters': {
                    'amplitude': 5.0,
                    'frequency': 1.0,
                    'speed': 2.0
                }
            },
            EffectType.TYPEWRITER: {
                'name': 'Typewriter Effect',
                'parameters': {
                    'speed': 1.0,
                    'character_delay': 0.1
                }
            }
        }
    
    def _initialize_presets(self):
        """Initialize effect presets."""
        # Karaoke Classic preset
        classic_effects = [
            self.create_effect(EffectType.OUTLINE, {
                'width': 3.0,
                'color': [0.0, 0.0, 0.0],
                'softness': 0.3
            }),
            self.create_effect(EffectType.GLOW, {
                'radius': 4.0,
                'intensity': 0.6,
                'color': [1.0, 1.0, 0.0]
            })
        ]
        
        self.effect_presets['karaoke_classic'] = EffectPreset(
            name="Karaoke Classic",
            description="Traditional karaoke text with black outline and yellow glow",
            effects=classic_effects
        )
        
        # Neon Style preset
        neon_effects = [
            self.create_effect(EffectType.GLOW, {
                'radius': 8.0,
                'intensity': 1.0,
                'color': [0.0, 1.0, 1.0]  # Cyan
            }),
            self.create_effect(EffectType.OUTLINE, {
                'width': 1.0,
                'color': [0.0, 0.5, 1.0],
                'softness': 0.8
            })
        ]
        
        self.effect_presets['neon_style'] = EffectPreset(
            name="Neon Style",
            description="Bright neon effect with cyan glow and blue outline",
            effects=neon_effects
        )
        
        # Dramatic Shadow preset
        shadow_effects = [
            self.create_effect(EffectType.SHADOW, {
                'offset_x': 5.0,
                'offset_y': 5.0,
                'blur_radius': 3.0,
                'color': [0.0, 0.0, 0.0],
                'opacity': 0.8
            }),
            self.create_effect(EffectType.OUTLINE, {
                'width': 2.0,
                'color': [1.0, 1.0, 1.0],
                'softness': 0.2
            })
        ]
        
        self.effect_presets['dramatic_shadow'] = EffectPreset(
            name="Dramatic Shadow",
            description="Bold text with strong shadow and white outline",
            effects=shadow_effects
        )
    
    def create_effect(self, effect_type: EffectType, parameters: Dict[str, Any]) -> Effect:
        """Create a new effect with specified parameters."""
        effect_id = f"{effect_type.value}_{len(self.effect_layers)}"
        default_params = self.default_effects[effect_type]['parameters'].copy()
        default_params.update(parameters)
        
        return Effect(
            id=effect_id,
            name=self.default_effects[effect_type]['name'],
            type=effect_type.value,
            parameters=default_params
        )
    
    def add_effect_layer(self, effect: Effect, order: Optional[int] = None) -> EffectLayer:
        """Add an effect as a new layer."""
        if order is None:
            order = len(self.effect_layers)
        
        layer = EffectLayer(effect=effect, order=order)
        self.effect_layers.append(layer)
        self._sort_layers()
        return layer
    
    def remove_effect_layer(self, effect_id: str) -> bool:
        """Remove an effect layer by effect ID."""
        for i, layer in enumerate(self.effect_layers):
            if layer.effect.id == effect_id:
                self.effect_layers.pop(i)
                self._reorder_layers()
                return True
        return False
    
    def reorder_effect_layer(self, effect_id: str, new_order: int) -> bool:
        """Change the order of an effect layer."""
        target_layer = None
        for layer in self.effect_layers:
            if layer.effect.id == effect_id:
                target_layer = layer
                break
        
        if not target_layer:
            return False
        
        old_order = target_layer.order
        
        # Adjust orders of other layers
        if new_order < old_order:
            # Moving up - shift others down
            for layer in self.effect_layers:
                if layer != target_layer and new_order <= layer.order < old_order:
                    layer.order += 1
        else:
            # Moving down - shift others up
            for layer in self.effect_layers:
                if layer != target_layer and old_order < layer.order <= new_order:
                    layer.order -= 1
        
        # Set new order for target layer
        target_layer.order = new_order
        self._sort_layers()
        return True
    
    def update_effect_parameters(self, effect_id: str, parameters: Dict[str, Any]) -> bool:
        """Update parameters for an existing effect."""
        for layer in self.effect_layers:
            if layer.effect.id == effect_id:
                layer.effect.parameters.update(parameters)
                return True
        return False
    
    def toggle_effect_layer(self, effect_id: str, enabled: Optional[bool] = None) -> bool:
        """Toggle or set the enabled state of an effect layer."""
        for layer in self.effect_layers:
            if layer.effect.id == effect_id:
                if enabled is None:
                    layer.enabled = not layer.enabled
                else:
                    layer.enabled = enabled
                return True
        return False
    
    def get_effect_layer(self, effect_id: str) -> Optional[EffectLayer]:
        """Get an effect layer by ID."""
        for layer in self.effect_layers:
            if layer.effect.id == effect_id:
                return layer
        return None
    
    def get_active_effects(self) -> List[EffectLayer]:
        """Get all enabled effect layers in order."""
        return [layer for layer in self.effect_layers if layer.enabled]
    
    def apply_preset(self, preset_name: str) -> bool:
        """Apply a predefined effect preset."""
        if preset_name not in self.effect_presets:
            return False
        
        preset = self.effect_presets[preset_name]
        self.clear_all_effects()
        
        for effect in preset.effects:
            self.add_effect_layer(effect)
        
        return True
    
    def clear_all_effects(self):
        """Remove all effect layers."""
        self.effect_layers.clear()
    
    def get_available_presets(self) -> List[str]:
        """Get list of available effect preset names."""
        return list(self.effect_presets.keys())
    
    def get_preset_info(self, preset_name: str) -> Optional[EffectPreset]:
        """Get information about a specific preset."""
        return self.effect_presets.get(preset_name)
    
    def _sort_layers(self):
        """Sort effect layers by order."""
        self.effect_layers.sort(key=lambda layer: layer.order)
    
    def _reorder_layers(self):
        """Reorder layers after removal."""
        for i, layer in enumerate(self.effect_layers):
            layer.order = i
    
    def generate_shader_code(self, effect_layers: Optional[List[EffectLayer]] = None) -> Tuple[str, str]:
        """
        Generate OpenGL shader code for the current effect stack.
        
        Returns:
            Tuple of (vertex_shader_source, fragment_shader_source)
        """
        if effect_layers is None:
            effect_layers = self.get_active_effects()
        
        vertex_shader = self._generate_vertex_shader(effect_layers)
        fragment_shader = self._generate_fragment_shader(effect_layers)
        
        return vertex_shader, fragment_shader
    
    def _generate_vertex_shader(self, effect_layers: List[EffectLayer]) -> str:
        """Generate vertex shader with animation support."""
        has_animation = any(
            layer.effect.type in ['bounce', 'wave', 'typewriter'] 
            for layer in effect_layers
        )
        
        vertex_shader = """
        #version 330 core
        
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 texCoord;
        
        out vec2 TexCoord;
        out vec2 WorldPos;
        
        uniform mat4 projection;
        uniform mat4 model;
        uniform float time;
        uniform vec2 textSize;
        """
        
        if has_animation:
            vertex_shader += """
        // Animation uniforms
        uniform float bounceAmplitude;
        uniform float bounceFrequency;
        uniform float waveAmplitude;
        uniform float waveFrequency;
        """
        
        vertex_shader += """
        void main()
        {
            vec3 animatedPos = position;
            WorldPos = position.xy;
        """
        
        # Add animation calculations
        for layer in effect_layers:
            if layer.effect.type == 'bounce':
                vertex_shader += """
            // Bounce animation
            float bounceOffset = sin(time * bounceFrequency) * bounceAmplitude;
            animatedPos.y += bounceOffset * 0.01;
                """
            elif layer.effect.type == 'wave':
                vertex_shader += """
            // Wave animation
            float waveOffset = sin(time * waveFrequency + position.x * 0.1) * waveAmplitude;
            animatedPos.y += waveOffset * 0.01;
                """
        
        vertex_shader += """
            gl_Position = projection * model * vec4(animatedPos, 1.0);
            TexCoord = texCoord;
        }
        """
        
        return vertex_shader
    
    def _generate_fragment_shader(self, effect_layers: List[EffectLayer]) -> str:
        """Generate fragment shader with all effects."""
        fragment_shader = """
        #version 330 core
        
        in vec2 TexCoord;
        in vec2 WorldPos;
        out vec4 FragColor;
        
        uniform sampler2D textTexture;
        uniform vec3 textColor;
        uniform float alpha;
        uniform float time;
        uniform vec2 textureSize;
        
        // Effect uniforms
        """
        
        # Add uniforms for each effect type
        effect_types = set(layer.effect.type for layer in effect_layers)
        
        if 'glow' in effect_types:
            fragment_shader += """
        uniform bool enableGlow;
        uniform vec3 glowColor;
        uniform float glowRadius;
        uniform float glowIntensity;
        uniform float glowFalloff;
            """
        
        if 'outline' in effect_types:
            fragment_shader += """
        uniform bool enableOutline;
        uniform vec3 outlineColor;
        uniform float outlineWidth;
        uniform float outlineSoftness;
        uniform int outlineQuality;
            """
        
        if 'shadow' in effect_types:
            fragment_shader += """
        uniform bool enableShadow;
        uniform vec3 shadowColor;
        uniform vec2 shadowOffset;
        uniform float shadowBlur;
        uniform float shadowOpacity;
            """
        
        if 'fade' in effect_types:
            fragment_shader += """
        uniform float fadeAlpha;
            """
        
        if 'color_transition' in effect_types:
            fragment_shader += """
        uniform vec3 startColor;
        uniform vec3 endColor;
        uniform float transitionProgress;
            """
        
        # Add helper functions
        fragment_shader += """
        
        // Gaussian blur function for effects
        vec4 gaussianBlur(sampler2D tex, vec2 uv, float radius) {
            vec4 color = vec4(0.0);
            float total = 0.0;
            
            for (float x = -radius; x <= radius; x += 1.0) {
                for (float y = -radius; y <= radius; y += 1.0) {
                    vec2 offset = vec2(x, y) / textureSize;
                    float weight = exp(-(x*x + y*y) / (2.0 * radius * radius));
                    color += texture(tex, uv + offset) * weight;
                    total += weight;
                }
            }
            
            return color / total;
        }
        
        // Distance field function for smooth outlines
        float getDistanceField(sampler2D tex, vec2 uv, float width) {
            float dist = 0.0;
            int samples = int(width * 2.0);
            
            for (int x = -samples; x <= samples; x++) {
                for (int y = -samples; y <= samples; y++) {
                    vec2 offset = vec2(float(x), float(y)) / textureSize;
                    float d = length(offset);
                    if (d <= width) {
                        dist = max(dist, texture(tex, uv + offset).r);
                    }
                }
            }
            
            return dist;
        }
        
        void main()
        {
            vec4 textSample = texture(textTexture, TexCoord);
            vec3 finalColor = textColor;
            float finalAlpha = textSample.r * alpha;
            
            // Layer effects in order
        """
        
        # Apply effects in layer order
        for i, layer in enumerate(effect_layers):
            effect_type = layer.effect.type
            
            if effect_type == 'shadow':
                fragment_shader += f"""
            // Shadow effect (layer {i})
            if (enableShadow) {{
                vec2 shadowUV = TexCoord - shadowOffset / textureSize;
                float shadowSample = texture(textTexture, shadowUV).r;
                if (shadowSample > 0.1 && textSample.r < 0.1) {{
                    finalColor = mix(finalColor, shadowColor, shadowOpacity);
                    finalAlpha = max(finalAlpha, shadowSample * shadowOpacity);
                }}
            }}
                """
            
            elif effect_type == 'outline':
                fragment_shader += f"""
            // Outline effect (layer {i})
            if (enableOutline) {{
                float outlineDist = getDistanceField(textTexture, TexCoord, outlineWidth);
                float outlineMask = smoothstep(0.1, 0.1 + outlineSoftness, outlineDist);
                
                if (outlineMask > 0.1 && textSample.r < 0.1) {{
                    finalColor = mix(finalColor, outlineColor, outlineMask);
                    finalAlpha = max(finalAlpha, outlineMask);
                }}
            }}
                """
            
            elif effect_type == 'glow':
                fragment_shader += f"""
            // Glow effect (layer {i})
            if (enableGlow) {{
                vec4 glowSample = gaussianBlur(textTexture, TexCoord, glowRadius);
                float glowMask = pow(glowSample.r, glowFalloff) * glowIntensity;
                finalColor = mix(finalColor, glowColor, glowMask * 0.5);
                finalAlpha = max(finalAlpha, glowMask);
            }}
                """
            
            elif effect_type == 'color_transition':
                fragment_shader += f"""
            // Color transition effect (layer {i})
            vec3 transitionColor = mix(startColor, endColor, transitionProgress);
            finalColor = mix(finalColor, transitionColor, textSample.r);
                """
            
            elif effect_type == 'fade':
                fragment_shader += f"""
            // Fade effect (layer {i})
            finalAlpha *= fadeAlpha;
                """
        
        fragment_shader += """
            
            FragColor = vec4(finalColor, finalAlpha);
        }
        """
        
        return fragment_shader
    
    def get_effect_uniforms(self, effect_layers: Optional[List[EffectLayer]] = None) -> Dict[str, Any]:
        """Get uniform values for the current effect stack."""
        if effect_layers is None:
            effect_layers = self.get_active_effects()
        
        uniforms = {}
        
        for layer in effect_layers:
            effect = layer.effect
            params = effect.parameters
            
            if effect.type == 'glow':
                uniforms.update({
                    'enableGlow': True,
                    'glowColor': params.get('color', [1.0, 1.0, 0.0]),
                    'glowRadius': params.get('radius', 5.0),
                    'glowIntensity': params.get('intensity', 0.8),
                    'glowFalloff': params.get('falloff', 2.0)
                })
            
            elif effect.type == 'outline':
                uniforms.update({
                    'enableOutline': True,
                    'outlineColor': params.get('color', [0.0, 0.0, 0.0]),
                    'outlineWidth': params.get('width', 2.0),
                    'outlineSoftness': params.get('softness', 0.5),
                    'outlineQuality': params.get('quality', 8)
                })
            
            elif effect.type == 'shadow':
                uniforms.update({
                    'enableShadow': True,
                    'shadowColor': params.get('color', [0.0, 0.0, 0.0]),
                    'shadowOffset': [params.get('offset_x', 3.0), params.get('offset_y', 3.0)],
                    'shadowBlur': params.get('blur_radius', 2.0),
                    'shadowOpacity': params.get('opacity', 0.7)
                })
            
            elif effect.type == 'fade':
                # Fade alpha would be calculated based on current time and subtitle timing
                uniforms['fadeAlpha'] = 1.0  # Placeholder
            
            elif effect.type == 'color_transition':
                uniforms.update({
                    'startColor': params.get('start_color', [1.0, 1.0, 1.0]),
                    'endColor': params.get('end_color', [1.0, 0.0, 0.0]),
                    'transitionProgress': 0.5  # Placeholder, would be calculated based on time
                })
            
            elif effect.type == 'bounce':
                uniforms.update({
                    'bounceAmplitude': params.get('amplitude', 10.0),
                    'bounceFrequency': params.get('frequency', 2.0)
                })
            
            elif effect.type == 'wave':
                uniforms.update({
                    'waveAmplitude': params.get('amplitude', 5.0),
                    'waveFrequency': params.get('frequency', 1.0)
                })
        
        return uniforms
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current effects configuration to dictionary."""
        return {
            'effect_layers': [
                {
                    'effect': {
                        'id': layer.effect.id,
                        'name': layer.effect.name,
                        'type': layer.effect.type,
                        'parameters': layer.effect.parameters,
                        'enabled': layer.effect.enabled
                    },
                    'order': layer.order,
                    'blend_mode': layer.blend_mode,
                    'opacity': layer.opacity,
                    'enabled': layer.enabled
                }
                for layer in self.effect_layers
            ]
        }
    
    def import_configuration(self, config: Dict[str, Any]) -> bool:
        """Import effects configuration from dictionary."""
        try:
            self.clear_all_effects()
            
            for layer_data in config.get('effect_layers', []):
                effect_data = layer_data['effect']
                effect = Effect(
                    id=effect_data['id'],
                    name=effect_data['name'],
                    type=effect_data['type'],
                    parameters=effect_data['parameters'],
                    enabled=effect_data['enabled']
                )
                
                layer = EffectLayer(
                    effect=effect,
                    order=layer_data['order'],
                    blend_mode=layer_data['blend_mode'],
                    opacity=layer_data['opacity'],
                    enabled=layer_data['enabled']
                )
                
                self.effect_layers.append(layer)
            
            self._sort_layers()
            return True
            
        except Exception as e:
            print(f"Failed to import effects configuration: {e}")
            return False


if __name__ == "__main__":
    # Test the effects manager
    manager = EffectsManager()
    
    # Test creating effects
    glow_effect = manager.create_effect(EffectType.GLOW, {'radius': 8.0, 'color': [0.0, 1.0, 1.0]})
    outline_effect = manager.create_effect(EffectType.OUTLINE, {'width': 3.0})
    
    # Test adding layers
    manager.add_effect_layer(outline_effect, order=0)
    manager.add_effect_layer(glow_effect, order=1)
    
    # Test shader generation
    vertex_shader, fragment_shader = manager.generate_shader_code()
    print("Vertex shader generated:", len(vertex_shader) > 0)
    print("Fragment shader generated:", len(fragment_shader) > 0)
    
    # Test uniforms
    uniforms = manager.get_effect_uniforms()
    print("Uniforms generated:", len(uniforms) > 0)
    
    # Test presets
    presets = manager.get_available_presets()
    print("Available presets:", presets)
    
    print("Effects manager test completed successfully")