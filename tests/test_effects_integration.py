"""
Integration tests for the text effects system.

Tests the integration between EffectsManager and OpenGLSubtitleRenderer.
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.effects_manager import EffectsManager, EffectType
from core.opengl_subtitle_renderer import OpenGLSubtitleRenderer
from core.models import SubtitleLine, SubtitleStyle


class TestEffectsIntegration(unittest.TestCase):
    """Integration tests for effects system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.effects_manager = EffectsManager()
        self.renderer = OpenGLSubtitleRenderer()
    
    def test_effects_manager_integration(self):
        """Test effects manager integration with renderer."""
        # Add glow effect
        glow_effect = self.effects_manager.create_effect(EffectType.GLOW, {
            'radius': 8.0,
            'intensity': 0.9,
            'color': [1.0, 0.0, 1.0]
        })
        self.effects_manager.add_effect_layer(glow_effect)
        
        # Add outline effect
        outline_effect = self.effects_manager.create_effect(EffectType.OUTLINE, {
            'width': 3.0,
            'color': [0.0, 0.0, 0.0]
        })
        self.effects_manager.add_effect_layer(outline_effect)
        
        # Test shader generation
        vertex_shader, fragment_shader = self.effects_manager.generate_shader_code()
        
        self.assertIsInstance(vertex_shader, str)
        self.assertIsInstance(fragment_shader, str)
        self.assertGreater(len(vertex_shader), 100)
        self.assertGreater(len(fragment_shader), 100)
        
        # Check shader contains effect code
        self.assertIn('glow', fragment_shader.lower())
        self.assertIn('outline', fragment_shader.lower())
        
        # Test uniforms generation
        uniforms = self.effects_manager.get_effect_uniforms()
        
        self.assertIn('enableGlow', uniforms)
        self.assertIn('enableOutline', uniforms)
        self.assertTrue(uniforms['enableGlow'])
        self.assertTrue(uniforms['enableOutline'])
        self.assertEqual(uniforms['glowRadius'], 8.0)
        self.assertEqual(uniforms['outlineWidth'], 3.0)
    
    def test_renderer_effects_integration(self):
        """Test renderer integration with effects manager."""
        # Add effect to renderer
        effect_id = self.renderer.add_effect('glow', {
            'radius': 10.0,
            'color': [0.0, 1.0, 0.0]
        })
        
        self.assertIsNotNone(effect_id)
        self.assertNotEqual(effect_id, "")
        
        # Check effect was added
        active_effects = self.renderer.get_active_effects()
        self.assertEqual(len(active_effects), 1)
        self.assertEqual(active_effects[0]['type'], 'glow')
        self.assertEqual(active_effects[0]['parameters']['radius'], 10.0)
        
        # Update effect parameters
        success = self.renderer.update_effect_parameters(effect_id, {'radius': 15.0})
        self.assertTrue(success)
        
        # Verify parameter update
        updated_effects = self.renderer.get_active_effects()
        self.assertEqual(updated_effects[0]['parameters']['radius'], 15.0)
        
        # Remove effect
        success = self.renderer.remove_effect(effect_id)
        self.assertTrue(success)
        
        # Verify removal
        final_effects = self.renderer.get_active_effects()
        self.assertEqual(len(final_effects), 0)
    
    def test_effect_layering(self):
        """Test effect layering and ordering."""
        # Add multiple effects in specific order
        shadow_id = self.renderer.add_effect('shadow', {'offset_x': 5.0})
        outline_id = self.renderer.add_effect('outline', {'width': 2.0})
        glow_id = self.renderer.add_effect('glow', {'radius': 6.0})
        
        # Check initial order
        effects = self.renderer.get_active_effects()
        self.assertEqual(len(effects), 3)
        
        # Effects should be in order of addition
        effect_ids = [effect['id'] for effect in effects]
        self.assertEqual(effect_ids, [shadow_id, outline_id, glow_id])
        
        # Test reordering
        success = self.renderer.reorder_effects(glow_id, 0)
        self.assertTrue(success)
        
        # Verify new order
        reordered_effects = self.renderer.get_active_effects()
        reordered_ids = [effect['id'] for effect in reordered_effects]
        self.assertEqual(reordered_ids[0], glow_id)
    
    def test_effect_presets(self):
        """Test effect preset application."""
        # Get available presets
        presets = self.renderer.get_available_presets()
        self.assertIsInstance(presets, list)
        self.assertGreater(len(presets), 0)
        
        # Apply a preset
        success = self.renderer.apply_effect_preset('karaoke_classic')
        self.assertTrue(success)
        
        # Check effects were applied
        effects = self.renderer.get_active_effects()
        self.assertGreater(len(effects), 0)
        
        # Should have outline and glow effects
        effect_types = [effect['type'] for effect in effects]
        self.assertIn('outline', effect_types)
        self.assertIn('glow', effect_types)
    
    def test_animation_effects(self):
        """Test animation effects shader generation."""
        # Add bounce effect
        bounce_id = self.renderer.add_effect('bounce', {
            'amplitude': 12.0,
            'frequency': 2.5
        })
        
        # Add wave effect
        wave_id = self.renderer.add_effect('wave', {
            'amplitude': 8.0,
            'frequency': 1.5
        })
        
        # Generate shaders
        vertex_shader, fragment_shader = self.renderer.effects_manager.generate_shader_code()
        
        # Check for animation uniforms
        self.assertIn('bounceAmplitude', vertex_shader)
        self.assertIn('bounceFrequency', vertex_shader)
        self.assertIn('waveAmplitude', vertex_shader)
        self.assertIn('waveFrequency', vertex_shader)
        
        # Check uniforms
        uniforms = self.renderer.effects_manager.get_effect_uniforms()
        self.assertEqual(uniforms['bounceAmplitude'], 12.0)
        self.assertEqual(uniforms['waveFrequency'], 1.5)
    
    def test_effect_toggle(self):
        """Test toggling effects on and off."""
        # Add effect
        glow_id = self.renderer.add_effect('glow', {'radius': 5.0})
        
        # Initially enabled
        effects = self.renderer.get_active_effects()
        self.assertEqual(len(effects), 1)
        
        # Toggle off
        success = self.renderer.toggle_effect(glow_id, False)
        self.assertTrue(success)
        
        # Should not be in active effects
        effects = self.renderer.get_active_effects()
        self.assertEqual(len(effects), 0)
        
        # Toggle back on
        success = self.renderer.toggle_effect(glow_id, True)
        self.assertTrue(success)
        
        # Should be active again
        effects = self.renderer.get_active_effects()
        self.assertEqual(len(effects), 1)
    
    def test_complex_effect_stack(self):
        """Test complex effect combinations."""
        # Create a complex effect stack
        effects_config = [
            ('shadow', {'offset_x': 3.0, 'offset_y': 3.0, 'color': [0.0, 0.0, 0.0]}),
            ('outline', {'width': 2.0, 'color': [1.0, 1.0, 1.0]}),
            ('glow', {'radius': 6.0, 'color': [1.0, 1.0, 0.0], 'intensity': 0.8}),
            ('bounce', {'amplitude': 8.0, 'frequency': 2.0})
        ]
        
        effect_ids = []
        for effect_type, params in effects_config:
            effect_id = self.renderer.add_effect(effect_type, params)
            effect_ids.append(effect_id)
        
        # Generate shaders for complex stack
        vertex_shader, fragment_shader = self.renderer.effects_manager.generate_shader_code()
        
        # Verify all effects are represented
        self.assertIn('shadow', fragment_shader.lower())
        self.assertIn('outline', fragment_shader.lower())
        self.assertIn('glow', fragment_shader.lower())
        self.assertIn('bounce', vertex_shader.lower())
        
        # Test uniforms for all effects
        uniforms = self.renderer.effects_manager.get_effect_uniforms()
        
        self.assertIn('enableShadow', uniforms)
        self.assertIn('enableOutline', uniforms)
        self.assertIn('enableGlow', uniforms)
        self.assertIn('bounceAmplitude', uniforms)
        
        # Verify parameter values
        self.assertEqual(uniforms['shadowOffset'], [3.0, 3.0])
        self.assertEqual(uniforms['outlineWidth'], 2.0)
        self.assertEqual(uniforms['glowRadius'], 6.0)
        self.assertEqual(uniforms['bounceAmplitude'], 8.0)
    
    def test_effect_configuration_export_import(self):
        """Test exporting and importing effect configurations."""
        # Create effect configuration
        glow_id = self.renderer.add_effect('glow', {'radius': 10.0, 'color': [1.0, 0.0, 1.0]})
        outline_id = self.renderer.add_effect('outline', {'width': 3.0})
        
        # Export configuration
        config = self.renderer.effects_manager.export_configuration()
        
        self.assertIsInstance(config, dict)
        self.assertIn('effect_layers', config)
        self.assertEqual(len(config['effect_layers']), 2)
        
        # Clear effects
        self.renderer.effects_manager.clear_all_effects()
        self.assertEqual(len(self.renderer.get_active_effects()), 0)
        
        # Import configuration
        success = self.renderer.effects_manager.import_configuration(config)
        self.assertTrue(success)
        
        # Verify effects were restored
        restored_effects = self.renderer.get_active_effects()
        self.assertEqual(len(restored_effects), 2)
        
        # Check effect types
        effect_types = [effect['type'] for effect in restored_effects]
        self.assertIn('glow', effect_types)
        self.assertIn('outline', effect_types)
    
    def test_performance_stats(self):
        """Test performance statistics."""
        # Get initial stats
        stats = self.renderer.get_performance_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('cache_size', stats)
        self.assertIn('initialized', stats)
        
        # Add some effects and check stats
        self.renderer.add_effect('glow', {})
        self.renderer.add_effect('outline', {})
        
        # Stats should still be accessible
        updated_stats = self.renderer.get_performance_stats()
        self.assertIsInstance(updated_stats, dict)


if __name__ == '__main__':
    unittest.main()