"""
Unit tests for the Effects Rendering Pipeline.

Tests the effects rendering pipeline including shader program coordination,
effect layering and composition, real-time parameter adjustment, and
karaoke timing integration.
"""

import unittest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.effects_rendering_pipeline import (
    EffectsRenderingPipeline, RenderingStage, ParameterUpdateMode,
    RenderingPass, AnimationState, ParameterUpdate,
    create_effects_pipeline, create_karaoke_effects_pipeline
)
from core.effects_manager import EffectType
from core.models import KaraokeTimingInfo


class TestAnimationState(unittest.TestCase):
    """Test AnimationState functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.animation_state = AnimationState()
    
    def test_initialization(self):
        """Test animation state initialization"""
        self.assertEqual(self.animation_state.current_time, 0.0)
        self.assertEqual(self.animation_state.karaoke_progress, 0.0)
        self.assertEqual(self.animation_state.syllable_index, 0)
        self.assertEqual(self.animation_state.syllable_progress, 0.0)
        self.assertFalse(self.animation_state.is_active)
    
    def test_update_from_karaoke_timing(self):
        """Test updating animation state from karaoke timing"""
        # Create test karaoke timing
        timing_info = KaraokeTimingInfo(
            start_time=1.0,
            end_time=4.0,
            text="Test karaoke",
            syllable_count=3,
            syllable_timings=[1.0, 1.0, 1.0],
            style_overrides=""
        )
        
        # Test time before start
        self.animation_state.update_from_karaoke_timing(timing_info, 0.5)
        self.assertFalse(self.animation_state.is_active)
        
        # Test time during first syllable
        self.animation_state.update_from_karaoke_timing(timing_info, 1.5)
        self.assertTrue(self.animation_state.is_active)
        self.assertEqual(self.animation_state.syllable_index, 0)
        self.assertAlmostEqual(self.animation_state.syllable_progress, 0.5, places=2)
        self.assertAlmostEqual(self.animation_state.karaoke_progress, 0.167, places=2)
        
        # Test time during second syllable
        self.animation_state.update_from_karaoke_timing(timing_info, 2.5)
        self.assertEqual(self.animation_state.syllable_index, 1)
        self.assertAlmostEqual(self.animation_state.syllable_progress, 0.5, places=2)
        
        # Test time after end
        self.animation_state.update_from_karaoke_timing(timing_info, 5.0)
        self.assertFalse(self.animation_state.is_active)
    
    def test_update_with_no_timing(self):
        """Test updating with no karaoke timing"""
        self.animation_state.update_from_karaoke_timing(None, 2.0)
        self.assertFalse(self.animation_state.is_active)
        self.assertEqual(self.animation_state.current_time, 2.0)


class TestParameterUpdate(unittest.TestCase):
    """Test ParameterUpdate functionality"""
    
    def test_parameter_update_creation(self):
        """Test creating parameter updates"""
        update = ParameterUpdate(
            layer_id="test_layer",
            parameter_name="radius",
            new_value=10.0,
            mode=ParameterUpdateMode.IMMEDIATE
        )
        
        self.assertEqual(update.layer_id, "test_layer")
        self.assertEqual(update.parameter_name, "radius")
        self.assertEqual(update.new_value, 10.0)
        self.assertEqual(update.mode, ParameterUpdateMode.IMMEDIATE)
        self.assertIsInstance(update.timestamp, float)
    
    def test_apply_to_layer(self):
        """Test applying parameter update to layer"""
        # Create mock layer with proper structure
        mock_layer = Mock()
        mock_layer.effect = Mock()
        mock_layer.effect.parameters = {}
        
        # Create and apply update
        update = ParameterUpdate("test", "radius", 15.0)
        update.apply_to_layer(mock_layer)
        
        # Verify update was applied
        self.assertEqual(mock_layer.effect.parameters["radius"], 15.0)


class TestRenderingPass(unittest.TestCase):
    """Test RenderingPass functionality"""
    
    def test_rendering_pass_creation(self):
        """Test creating rendering passes"""
        render_pass = RenderingPass(
            stage=RenderingStage.GLOW,
            shader_program=None,
            effect_layers=[],
            uniforms={'test': 1.0},
            enabled=True,
            order=2
        )
        
        self.assertEqual(render_pass.stage, RenderingStage.GLOW)
        self.assertIsNone(render_pass.shader_program)
        self.assertEqual(len(render_pass.effect_layers), 0)
        self.assertEqual(render_pass.uniforms['test'], 1.0)
        self.assertTrue(render_pass.enabled)
        self.assertEqual(render_pass.order, 2)


class TestEffectsRenderingPipeline(unittest.TestCase):
    """Test EffectsRenderingPipeline functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock OpenGL context
        self.mock_opengl_context = Mock()
        self.mock_opengl_context.backend = Mock()
        self.mock_opengl_context.backend.value = "mock"
        
        # Create pipeline in mock mode
        self.pipeline = EffectsRenderingPipeline(self.mock_opengl_context, mock_mode=True)
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        self.assertIsNotNone(self.pipeline.effects_manager)
        self.assertIsNotNone(self.pipeline.shader_system)
        self.assertIsNotNone(self.pipeline.animation_state)
        self.assertEqual(len(self.pipeline.rendering_passes), 8)  # All rendering stages
        self.assertEqual(self.pipeline.frame_count, 0)
        self.assertTrue(self.pipeline.mock_mode)
    
    def test_rendering_passes_initialization(self):
        """Test that rendering passes are properly initialized"""
        expected_stages = [
            RenderingStage.BACKGROUND,
            RenderingStage.SHADOW,
            RenderingStage.OUTLINE,
            RenderingStage.FILL,
            RenderingStage.GLOW,
            RenderingStage.OVERLAY,
            RenderingStage.ANIMATION,
            RenderingStage.COMPOSITION
        ]
        
        actual_stages = [pass_.stage for pass_ in self.pipeline.rendering_passes]
        self.assertEqual(actual_stages, expected_stages)
        
        # Check that passes are ordered correctly
        orders = [pass_.order for pass_ in self.pipeline.rendering_passes]
        self.assertEqual(orders, list(range(len(expected_stages))))
    
    def test_add_effect_layer(self):
        """Test adding effect layers"""
        # Add glow effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {
            'radius': 8.0,
            'intensity': 0.9
        })
        
        self.assertIsNotNone(glow_id)
        self.assertNotEqual(glow_id, "")
        
        # Check that effect was added to appropriate stage
        glow_pass = self.pipeline._get_render_pass_for_stage(RenderingStage.GLOW)
        self.assertEqual(len(glow_pass.effect_layers), 1)
        self.assertEqual(glow_pass.effect_layers[0].effect.id, glow_id)
        
        # Add outline effect
        outline_id = self.pipeline.add_effect_layer(EffectType.OUTLINE, {
            'width': 3.0
        })
        
        # Check that outline was added to outline stage
        outline_pass = self.pipeline._get_render_pass_for_stage(RenderingStage.OUTLINE)
        self.assertEqual(len(outline_pass.effect_layers), 1)
        self.assertEqual(outline_pass.effect_layers[0].effect.id, outline_id)
    
    def test_remove_effect_layer(self):
        """Test removing effect layers"""
        # Add effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {'radius': 5.0})
        
        # Verify it was added
        glow_pass = self.pipeline._get_render_pass_for_stage(RenderingStage.GLOW)
        self.assertEqual(len(glow_pass.effect_layers), 1)
        
        # Remove effect
        success = self.pipeline.remove_effect_layer(glow_id)
        self.assertTrue(success)
        
        # Verify it was removed
        self.assertEqual(len(glow_pass.effect_layers), 0)
        
        # Try to remove non-existent effect
        success = self.pipeline.remove_effect_layer("non_existent")
        self.assertFalse(success)
    
    def test_update_effect_parameters_immediate(self):
        """Test immediate parameter updates"""
        # Add effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {'radius': 5.0})
        
        # Update parameters immediately
        success = self.pipeline.update_effect_parameters(
            glow_id, 
            {'radius': 10.0, 'intensity': 1.2},
            ParameterUpdateMode.IMMEDIATE
        )
        
        self.assertTrue(success)
        
        # Verify parameters were updated
        layer = self.pipeline.effects_manager.get_effect_layer(glow_id)
        self.assertEqual(layer.effect.parameters['radius'], 10.0)
        self.assertEqual(layer.effect.parameters['intensity'], 1.2)
    
    def test_update_effect_parameters_buffered(self):
        """Test buffered parameter updates"""
        # Add effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {'radius': 5.0})
        
        # Update parameters in buffered mode
        success = self.pipeline.update_effect_parameters(
            glow_id,
            {'radius': 15.0},
            ParameterUpdateMode.BUFFERED
        )
        
        self.assertTrue(success)
        
        # Parameters should not be applied yet
        layer = self.pipeline.effects_manager.get_effect_layer(glow_id)
        self.assertEqual(layer.effect.parameters['radius'], 5.0)  # Original value
        
        # Check that update is buffered
        self.assertEqual(len(self.pipeline.parameter_updates), 1)
        self.assertEqual(self.pipeline.parameter_updates[0].layer_id, glow_id)
        self.assertEqual(self.pipeline.parameter_updates[0].new_value, 15.0)
        
        # Process buffered updates
        self.pipeline._process_buffered_updates()
        
        # Now parameters should be applied
        self.assertEqual(layer.effect.parameters['radius'], 15.0)
        self.assertEqual(len(self.pipeline.parameter_updates), 0)
    
    def test_karaoke_timing_integration(self):
        """Test karaoke timing integration"""
        # Create karaoke timing
        timing_info = KaraokeTimingInfo(
            start_time=1.0,
            end_time=4.0,
            text="Test karaoke",
            syllable_count=2,
            syllable_timings=[1.5, 1.5],
            style_overrides=""
        )
        
        # Set karaoke timing
        self.pipeline.set_karaoke_timing(timing_info)
        self.assertEqual(self.pipeline.current_karaoke_timing, timing_info)
        
        # Update animation time
        self.pipeline.update_animation_time(2.0)
        
        # Check animation state
        self.assertEqual(self.pipeline.animation_state.current_time, 2.0)
        self.assertTrue(self.pipeline.animation_state.is_active)
        self.assertAlmostEqual(self.pipeline.animation_state.karaoke_progress, 0.333, places=2)
    
    def test_render_frame(self):
        """Test frame rendering"""
        # Add some effects
        self.pipeline.add_effect_layer(EffectType.GLOW, {'radius': 6.0})
        self.pipeline.add_effect_layer(EffectType.OUTLINE, {'width': 2.0})
        
        # Render frame
        success = self.pipeline.render_frame(1.5)
        self.assertTrue(success)
        
        # Check that frame count increased
        self.assertEqual(self.pipeline.frame_count, 1)
        
        # Check that animation time was updated
        self.assertEqual(self.pipeline.animation_state.current_time, 1.5)
    
    def test_render_frame_with_buffered_updates(self):
        """Test frame rendering with buffered parameter updates"""
        # Add effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {'radius': 5.0})
        
        # Add buffered update
        self.pipeline.update_effect_parameters(
            glow_id, {'radius': 12.0}, ParameterUpdateMode.BUFFERED
        )
        
        # Render frame (should process buffered updates)
        success = self.pipeline.render_frame(2.0)
        self.assertTrue(success)
        
        # Check that buffered update was applied
        layer = self.pipeline.effects_manager.get_effect_layer(glow_id)
        self.assertEqual(layer.effect.parameters['radius'], 12.0)
        self.assertEqual(len(self.pipeline.parameter_updates), 0)
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        # Enable performance monitoring
        self.pipeline.enable_performance_monitoring = True
        
        # Render some frames
        for i in range(5):
            self.pipeline.render_frame(float(i))
        
        # Check performance stats
        stats = self.pipeline.get_performance_stats()
        
        self.assertEqual(stats['frame_count'], 5)
        self.assertGreater(stats['average_render_time'], 0.0)
        self.assertGreater(stats['fps_estimate'], 0.0)
        self.assertGreaterEqual(stats['max_render_time'], stats['min_render_time'])
    
    def test_pipeline_state(self):
        """Test getting pipeline state"""
        # Add some effects
        self.pipeline.add_effect_layer(EffectType.GLOW, {})
        self.pipeline.add_effect_layer(EffectType.OUTLINE, {})
        
        # Get pipeline state
        state = self.pipeline.get_pipeline_state()
        
        self.assertIn('animation_state', state)
        self.assertIn('rendering_passes', state)
        self.assertIn('performance', state)
        
        # Check animation state
        anim_state = state['animation_state']
        self.assertIn('current_time', anim_state)
        self.assertIn('karaoke_progress', anim_state)
        self.assertIn('is_active', anim_state)
        
        # Check rendering passes
        passes = state['rendering_passes']
        self.assertEqual(len(passes), 8)  # All stages
        
        # Find passes with effects
        passes_with_effects = [p for p in passes if p['effect_count'] > 0]
        self.assertEqual(len(passes_with_effects), 2)  # Glow and outline
    
    def test_enable_disable_pass(self):
        """Test enabling and disabling rendering passes"""
        # Initially all passes should be enabled
        glow_pass = self.pipeline._get_render_pass_for_stage(RenderingStage.GLOW)
        self.assertTrue(glow_pass.enabled)
        
        # Disable glow pass
        self.pipeline.enable_pass(RenderingStage.GLOW, False)
        self.assertFalse(glow_pass.enabled)
        
        # Re-enable glow pass
        self.pipeline.enable_pass(RenderingStage.GLOW, True)
        self.assertTrue(glow_pass.enabled)
    
    def test_clear_all_effects(self):
        """Test clearing all effects"""
        # Add effects
        self.pipeline.add_effect_layer(EffectType.GLOW, {})
        self.pipeline.add_effect_layer(EffectType.OUTLINE, {})
        
        # Verify effects were added
        total_effects = sum(len(p.effect_layers) for p in self.pipeline.rendering_passes)
        self.assertEqual(total_effects, 2)
        
        # Clear all effects
        self.pipeline.clear_all_effects()
        
        # Verify all effects were cleared
        total_effects = sum(len(p.effect_layers) for p in self.pipeline.rendering_passes)
        self.assertEqual(total_effects, 0)
    
    def test_apply_effect_preset(self):
        """Test applying effect presets"""
        # Apply karaoke classic preset
        success = self.pipeline.apply_effect_preset('karaoke_classic')
        self.assertTrue(success)
        
        # Check that effects were applied
        total_effects = sum(len(p.effect_layers) for p in self.pipeline.rendering_passes)
        self.assertGreater(total_effects, 0)
        
        # Try to apply non-existent preset
        success = self.pipeline.apply_effect_preset('non_existent_preset')
        self.assertFalse(success)
    
    def test_stage_for_effect_type_mapping(self):
        """Test effect type to stage mapping"""
        # Test known mappings
        self.assertEqual(
            self.pipeline._get_stage_for_effect_type(EffectType.SHADOW),
            RenderingStage.SHADOW
        )
        self.assertEqual(
            self.pipeline._get_stage_for_effect_type(EffectType.OUTLINE),
            RenderingStage.OUTLINE
        )
        self.assertEqual(
            self.pipeline._get_stage_for_effect_type(EffectType.GLOW),
            RenderingStage.GLOW
        )
        self.assertEqual(
            self.pipeline._get_stage_for_effect_type(EffectType.BOUNCE),
            RenderingStage.ANIMATION
        )
        
        # Test unknown effect type (should default to OVERLAY)
        # Create a mock effect type that's not in the mapping
        unknown_effect = Mock()
        unknown_effect.value = "unknown_effect"
        stage = self.pipeline._get_stage_for_effect_type(unknown_effect)
        self.assertEqual(stage, RenderingStage.OVERLAY)
    
    def test_parameter_update_buffer_limit(self):
        """Test parameter update buffer size limit"""
        # Set small buffer limit for testing
        self.pipeline.max_buffered_updates = 3
        
        # Add effect
        glow_id = self.pipeline.add_effect_layer(EffectType.GLOW, {})
        
        # Add more updates than the limit
        for i in range(5):
            self.pipeline.update_effect_parameters(
                glow_id, {f'param_{i}': i}, ParameterUpdateMode.BUFFERED
            )
        
        # Buffer should be limited to max size
        self.assertEqual(len(self.pipeline.parameter_updates), 3)
    
    def test_cleanup(self):
        """Test pipeline cleanup"""
        # Add effects and render frames
        self.pipeline.add_effect_layer(EffectType.GLOW, {})
        self.pipeline.render_frame(1.0)
        
        # Add buffered updates
        self.pipeline.update_effect_parameters(
            "test", {'param': 1}, ParameterUpdateMode.BUFFERED
        )
        
        # Cleanup
        self.pipeline.cleanup()
        
        # Verify cleanup
        self.assertEqual(len(self.pipeline.parameter_updates), 0)
        self.assertEqual(len(self.pipeline.render_times), 0)
        
        # All effect layers should be cleared
        total_effects = sum(len(p.effect_layers) for p in self.pipeline.rendering_passes)
        self.assertEqual(total_effects, 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_opengl_context = Mock()
        self.mock_opengl_context.backend = Mock()
        self.mock_opengl_context.backend.value = "mock"
    
    def test_create_effects_pipeline(self):
        """Test creating effects pipeline"""
        pipeline = create_effects_pipeline(self.mock_opengl_context, mock_mode=True)
        
        self.assertIsInstance(pipeline, EffectsRenderingPipeline)
        self.assertEqual(pipeline.opengl_context, self.mock_opengl_context)
        self.assertTrue(pipeline.mock_mode)
    
    def test_create_karaoke_effects_pipeline(self):
        """Test creating karaoke-optimized pipeline"""
        pipeline = create_karaoke_effects_pipeline(self.mock_opengl_context)
        
        self.assertIsInstance(pipeline, EffectsRenderingPipeline)
        self.assertTrue(pipeline.enable_parameter_buffering)
        self.assertTrue(pipeline.enable_performance_monitoring)
        
        # Should have common karaoke effects pre-loaded
        total_effects = sum(len(p.effect_layers) for p in pipeline.rendering_passes)
        self.assertGreater(total_effects, 0)
        
        # Should have outline and glow effects
        effect_types = []
        for pass_ in pipeline.rendering_passes:
            for layer in pass_.effect_layers:
                effect_types.append(layer.effect.type)
        
        self.assertIn('outline', effect_types)
        self.assertIn('glow', effect_types)


class TestRenderingStageEnum(unittest.TestCase):
    """Test RenderingStage enum"""
    
    def test_rendering_stages(self):
        """Test rendering stage values"""
        self.assertEqual(RenderingStage.BACKGROUND.value, "background")
        self.assertEqual(RenderingStage.SHADOW.value, "shadow")
        self.assertEqual(RenderingStage.OUTLINE.value, "outline")
        self.assertEqual(RenderingStage.FILL.value, "fill")
        self.assertEqual(RenderingStage.GLOW.value, "glow")
        self.assertEqual(RenderingStage.OVERLAY.value, "overlay")
        self.assertEqual(RenderingStage.ANIMATION.value, "animation")
        self.assertEqual(RenderingStage.COMPOSITION.value, "composition")


class TestParameterUpdateModeEnum(unittest.TestCase):
    """Test ParameterUpdateMode enum"""
    
    def test_parameter_update_modes(self):
        """Test parameter update mode values"""
        self.assertEqual(ParameterUpdateMode.IMMEDIATE.value, "immediate")
        self.assertEqual(ParameterUpdateMode.BUFFERED.value, "buffered")
        self.assertEqual(ParameterUpdateMode.SYNCHRONIZED.value, "synchronized")


if __name__ == '__main__':
    unittest.main(verbosity=2)