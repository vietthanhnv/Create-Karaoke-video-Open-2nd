"""
Unit tests for the EffectsManager class.

Tests effect creation, layering, parameter management, and shader generation.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.effects_manager import EffectsManager, EffectType, EffectLayer
from core.models import Effect


class TestEffectsManager(unittest.TestCase):
    """Test cases for EffectsManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = EffectsManager()
    
    def test_initialization(self):
        """Test effects manager initialization."""
        self.assertIsInstance(self.manager, EffectsManager)
        self.assertEqual(len(self.manager.effect_layers), 0)
        self.assertGreater(len(self.manager.default_effects), 0)
        self.assertGreater(len(self.manager.effect_presets), 0)
    
    def test_create_effect(self):
        """Test effect creation with parameters."""
        # Test glow effect creation
        glow_params = {'radius': 8.0, 'color': [0.0, 1.0, 1.0]}
        glow_effect = self.manager.create_effect(EffectType.GLOW, glow_params)
        
        self.assertIsInstance(glow_effect, Effect)
        self.assertEqual(glow_effect.type, EffectType.GLOW.value)
        self.assertEqual(glow_effect.parameters['radius'], 8.0)
        self.assertEqual(glow_effect.parameters['color'], [0.0, 1.0, 1.0])
        
        # Test outline effect creation
        outline_params = {'width': 3.0, 'color': [1.0, 0.0, 0.0]}
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, outline_params)
        
        self.assertEqual(outline_effect.type, EffectType.OUTLINE.value)
        self.assertEqual(outline_effect.parameters['width'], 3.0)
    
    def test_add_effect_layer(self):
        """Test adding effect layers."""
        # Create and add effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        
        layer1 = self.manager.add_effect_layer(glow_effect)
        layer2 = self.manager.add_effect_layer(outline_effect)
        
        self.assertEqual(len(self.manager.effect_layers), 2)
        self.assertEqual(layer1.order, 0)
        self.assertEqual(layer2.order, 1)
        self.assertTrue(layer1.enabled)
        self.assertTrue(layer2.enabled)
    
    def test_remove_effect_layer(self):
        """Test removing effect layers."""
        # Add effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        
        self.manager.add_effect_layer(glow_effect)
        self.manager.add_effect_layer(outline_effect)
        
        # Remove first effect
        success = self.manager.remove_effect_layer(glow_effect.id)
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.effect_layers), 1)
        self.assertEqual(self.manager.effect_layers[0].effect.id, outline_effect.id)
        
        # Try to remove non-existent effect
        success = self.manager.remove_effect_layer("non_existent_id")
        self.assertFalse(success)
    
    def test_reorder_effect_layer(self):
        """Test reordering effect layers."""
        # Add multiple effects
        effects = []
        for i in range(3):
            effect = self.manager.create_effect(EffectType.GLOW, {'radius': i + 1})
            effects.append(effect)
            self.manager.add_effect_layer(effect)
        
        # Reorder middle effect to first position
        success = self.manager.reorder_effect_layer(effects[1].id, 0)
        
        self.assertTrue(success)
        # Check that layers are sorted by order
        orders = [layer.order for layer in self.manager.effect_layers]
        self.assertEqual(orders, sorted(orders))
    
    def test_update_effect_parameters(self):
        """Test updating effect parameters."""
        glow_effect = self.manager.create_effect(EffectType.GLOW, {'radius': 5.0})
        self.manager.add_effect_layer(glow_effect)
        
        # Update parameters
        new_params = {'radius': 10.0, 'intensity': 0.9}
        success = self.manager.update_effect_parameters(glow_effect.id, new_params)
        
        self.assertTrue(success)
        
        # Verify parameters were updated
        layer = self.manager.get_effect_layer(glow_effect.id)
        self.assertEqual(layer.effect.parameters['radius'], 10.0)
        self.assertEqual(layer.effect.parameters['intensity'], 0.9)
    
    def test_toggle_effect_layer(self):
        """Test toggling effect layer enabled state."""
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        self.manager.add_effect_layer(glow_effect)
        
        # Toggle off
        success = self.manager.toggle_effect_layer(glow_effect.id, False)
        self.assertTrue(success)
        
        layer = self.manager.get_effect_layer(glow_effect.id)
        self.assertFalse(layer.enabled)
        
        # Toggle on
        success = self.manager.toggle_effect_layer(glow_effect.id, True)
        self.assertTrue(success)
        self.assertTrue(layer.enabled)
        
        # Auto-toggle
        success = self.manager.toggle_effect_layer(glow_effect.id)
        self.assertTrue(success)
        self.assertFalse(layer.enabled)
    
    def test_get_active_effects(self):
        """Test getting only enabled effects."""
        # Add multiple effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        shadow_effect = self.manager.create_effect(EffectType.SHADOW, {})
        
        self.manager.add_effect_layer(glow_effect)
        self.manager.add_effect_layer(outline_effect)
        self.manager.add_effect_layer(shadow_effect)
        
        # Disable middle effect
        self.manager.toggle_effect_layer(outline_effect.id, False)
        
        active_effects = self.manager.get_active_effects()
        
        self.assertEqual(len(active_effects), 2)
        active_ids = [layer.effect.id for layer in active_effects]
        self.assertIn(glow_effect.id, active_ids)
        self.assertIn(shadow_effect.id, active_ids)
        self.assertNotIn(outline_effect.id, active_ids)
    
    def test_apply_preset(self):
        """Test applying effect presets."""
        # Apply karaoke classic preset
        success = self.manager.apply_preset('karaoke_classic')
        
        self.assertTrue(success)
        self.assertGreater(len(self.manager.effect_layers), 0)
        
        # Check that preset effects were added
        effect_types = [layer.effect.type for layer in self.manager.effect_layers]
        self.assertIn(EffectType.OUTLINE.value, effect_types)
        self.assertIn(EffectType.GLOW.value, effect_types)
    
    def test_clear_all_effects(self):
        """Test clearing all effects."""
        # Add some effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        
        self.manager.add_effect_layer(glow_effect)
        self.manager.add_effect_layer(outline_effect)
        
        # Clear all
        self.manager.clear_all_effects()
        
        self.assertEqual(len(self.manager.effect_layers), 0)
    
    def test_get_available_presets(self):
        """Test getting available presets."""
        presets = self.manager.get_available_presets()
        
        self.assertIsInstance(presets, list)
        self.assertGreater(len(presets), 0)
        self.assertIn('karaoke_classic', presets)
        self.assertIn('neon_style', presets)
    
    def test_generate_shader_code(self):
        """Test shader code generation."""
        # Add effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        
        self.manager.add_effect_layer(glow_effect)
        self.manager.add_effect_layer(outline_effect)
        
        # Generate shaders
        vertex_shader, fragment_shader = self.manager.generate_shader_code()
        
        self.assertIsInstance(vertex_shader, str)
        self.assertIsInstance(fragment_shader, str)
        self.assertGreater(len(vertex_shader), 0)
        self.assertGreater(len(fragment_shader), 0)
        
        # Check that shader contains effect-specific code
        self.assertIn('glow', fragment_shader.lower())
        self.assertIn('outline', fragment_shader.lower())
    
    def test_get_effect_uniforms(self):
        """Test getting effect uniforms."""
        # Add glow effect
        glow_effect = self.manager.create_effect(EffectType.GLOW, {
            'radius': 8.0,
            'color': [1.0, 0.0, 1.0],
            'intensity': 0.9
        })
        self.manager.add_effect_layer(glow_effect)
        
        # Get uniforms
        uniforms = self.manager.get_effect_uniforms()
        
        self.assertIsInstance(uniforms, dict)
        self.assertIn('enableGlow', uniforms)
        self.assertIn('glowColor', uniforms)
        self.assertIn('glowRadius', uniforms)
        self.assertIn('glowIntensity', uniforms)
        
        self.assertTrue(uniforms['enableGlow'])
        self.assertEqual(uniforms['glowRadius'], 8.0)
        self.assertEqual(uniforms['glowColor'], [1.0, 0.0, 1.0])
        self.assertEqual(uniforms['glowIntensity'], 0.9)
    
    def test_export_import_configuration(self):
        """Test exporting and importing effect configurations."""
        # Add effects
        glow_effect = self.manager.create_effect(EffectType.GLOW, {'radius': 10.0})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {'width': 3.0})
        
        self.manager.add_effect_layer(glow_effect)
        self.manager.add_effect_layer(outline_effect)
        
        # Export configuration
        config = self.manager.export_configuration()
        
        self.assertIsInstance(config, dict)
        self.assertIn('effect_layers', config)
        self.assertEqual(len(config['effect_layers']), 2)
        
        # Clear and import
        self.manager.clear_all_effects()
        success = self.manager.import_configuration(config)
        
        self.assertTrue(success)
        self.assertEqual(len(self.manager.effect_layers), 2)
        
        # Verify imported effects
        imported_types = [layer.effect.type for layer in self.manager.effect_layers]
        self.assertIn(EffectType.GLOW.value, imported_types)
        self.assertIn(EffectType.OUTLINE.value, imported_types)
    
    def test_animation_effects(self):
        """Test animation-specific effects."""
        # Test bounce effect
        bounce_effect = self.manager.create_effect(EffectType.BOUNCE, {
            'amplitude': 15.0,
            'frequency': 3.0
        })
        self.manager.add_effect_layer(bounce_effect)
        
        # Generate shader with animation
        vertex_shader, fragment_shader = self.manager.generate_shader_code()
        
        # Check for animation uniforms in vertex shader
        self.assertIn('bounceAmplitude', vertex_shader)
        self.assertIn('bounceFrequency', vertex_shader)
        
        # Test wave effect
        wave_effect = self.manager.create_effect(EffectType.WAVE, {
            'amplitude': 8.0,
            'frequency': 1.5
        })
        self.manager.add_effect_layer(wave_effect)
        
        vertex_shader, fragment_shader = self.manager.generate_shader_code()
        self.assertIn('waveAmplitude', vertex_shader)
        self.assertIn('waveFrequency', vertex_shader)
    
    def test_effect_layering_order(self):
        """Test that effects are applied in correct order."""
        # Add effects in specific order
        shadow_effect = self.manager.create_effect(EffectType.SHADOW, {})
        outline_effect = self.manager.create_effect(EffectType.OUTLINE, {})
        glow_effect = self.manager.create_effect(EffectType.GLOW, {})
        
        # Add in reverse order to test sorting
        self.manager.add_effect_layer(glow_effect, order=2)
        self.manager.add_effect_layer(outline_effect, order=1)
        self.manager.add_effect_layer(shadow_effect, order=0)
        
        # Verify layers are sorted by order
        orders = [layer.order for layer in self.manager.effect_layers]
        self.assertEqual(orders, [0, 1, 2])
        
        # Verify effect types are in correct order
        types = [layer.effect.type for layer in self.manager.effect_layers]
        self.assertEqual(types, [EffectType.SHADOW.value, EffectType.OUTLINE.value, EffectType.GLOW.value])


class TestEffectLayer(unittest.TestCase):
    """Test cases for EffectLayer functionality."""
    
    def test_effect_layer_creation(self):
        """Test creating effect layers."""
        effect = Effect(
            id="test_effect",
            name="Test Effect",
            type=EffectType.GLOW.value,
            parameters={'radius': 5.0}
        )
        
        layer = EffectLayer(effect=effect, order=1, opacity=0.8)
        
        self.assertEqual(layer.effect, effect)
        self.assertEqual(layer.order, 1)
        self.assertEqual(layer.opacity, 0.8)
        self.assertEqual(layer.blend_mode, "normal")
        self.assertTrue(layer.enabled)


if __name__ == '__main__':
    unittest.main()