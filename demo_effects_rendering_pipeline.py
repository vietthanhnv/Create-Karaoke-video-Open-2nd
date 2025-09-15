"""
Demo script for the Effects Rendering Pipeline

This script demonstrates the comprehensive effects rendering pipeline including:
- Shader program coordination
- Effect layering and composition
- Real-time parameter adjustment
- Karaoke timing integration
- Performance monitoring
"""

import sys
import os
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.effects_rendering_pipeline import (
    EffectsRenderingPipeline, RenderingStage, ParameterUpdateMode,
    create_effects_pipeline, create_karaoke_effects_pipeline
)
from core.effects_manager import EffectType
from core.opengl_context import create_offscreen_context
from core.models import KaraokeTimingInfo


def demo_basic_pipeline():
    """Demonstrate basic pipeline functionality"""
    print("=== Basic Effects Rendering Pipeline Demo ===")
    
    # Create mock context for demo (avoid real OpenGL dependencies)
    from unittest.mock import Mock
    context = Mock()
    context.backend = Mock()
    context.backend.value = "mock"
    context.cleanup = Mock()
    
    try:
        # Create effects pipeline in mock mode since we don't have real OpenGL
        pipeline = create_effects_pipeline(context, mock_mode=True)
        print(f"Created pipeline with {len(pipeline.rendering_passes)} rendering passes")
        
        # Add various effects
        print("\n--- Adding Effects ---")
        glow_id = pipeline.add_effect_layer(EffectType.GLOW, {
            'radius': 8.0,
            'intensity': 1.0,
            'color': [1.0, 1.0, 0.0, 1.0]  # Yellow
        })
        print(f"Added glow effect: {glow_id}")
        
        outline_id = pipeline.add_effect_layer(EffectType.OUTLINE, {
            'width': 3.0,
            'color': [0.0, 0.0, 0.0, 1.0],  # Black
            'softness': 0.3
        })
        print(f"Added outline effect: {outline_id}")
        
        shadow_id = pipeline.add_effect_layer(EffectType.SHADOW, {
            'offset_x': 4.0,
            'offset_y': 4.0,
            'blur_radius': 2.0,
            'color': [0.0, 0.0, 0.0, 0.8]
        })
        print(f"Added shadow effect: {shadow_id}")
        
        bounce_id = pipeline.add_effect_layer(EffectType.BOUNCE, {
            'amplitude': 15.0,
            'frequency': 2.0,
            'damping': 0.8
        })
        print(f"Added bounce animation: {bounce_id}")
        
        # Show pipeline state
        state = pipeline.get_pipeline_state()
        print(f"\nPipeline state:")
        print(f"  Active passes: {len([p for p in state['rendering_passes'] if p['effect_count'] > 0])}")
        print(f"  Total effects: {sum(p['effect_count'] for p in state['rendering_passes'])}")
        
        # Test parameter updates
        print("\n--- Parameter Updates ---")
        print("Testing immediate parameter update...")
        success = pipeline.update_effect_parameters(glow_id, {
            'radius': 12.0,
            'intensity': 1.5
        }, ParameterUpdateMode.IMMEDIATE)
        print(f"Immediate update: {'Success' if success else 'Failed'}")
        
        print("Testing buffered parameter update...")
        success = pipeline.update_effect_parameters(outline_id, {
            'width': 5.0,
            'softness': 0.5
        }, ParameterUpdateMode.BUFFERED)
        print(f"Buffered update: {'Success' if success else 'Failed'}")
        
        # Test rendering
        print("\n--- Frame Rendering ---")
        for i in range(5):
            timestamp = float(i) * 0.5
            success = pipeline.render_frame(timestamp)
            print(f"Frame {i+1} at {timestamp}s: {'Success' if success else 'Failed'}")
        
        # Show performance stats
        stats = pipeline.get_performance_stats()
        print(f"\nPerformance Statistics:")
        print(f"  Frames rendered: {stats['frame_count']}")
        print(f"  Average render time: {stats['average_render_time']:.4f}s")
        print(f"  Estimated FPS: {stats['fps_estimate']:.1f}")
        print(f"  Active passes: {stats['active_passes']}")
        print(f"  Total effect layers: {stats['total_effect_layers']}")
        
    finally:
        pipeline.cleanup()
        context.cleanup()


def demo_karaoke_integration():
    """Demonstrate karaoke timing integration"""
    print("\n=== Karaoke Timing Integration Demo ===")
    
    # Create mock context for demo
    from unittest.mock import Mock
    context = Mock()
    context.backend = Mock()
    context.backend.value = "mock"
    context.cleanup = Mock()
    
    try:
        # Create karaoke-optimized pipeline in mock mode
        pipeline = EffectsRenderingPipeline(context, mock_mode=True)
        # Add karaoke effects manually
        pipeline.add_effect_layer(EffectType.OUTLINE, {
            'width': 3.0,
            'color': [0.0, 0.0, 0.0, 1.0],
            'softness': 0.3
        })
        pipeline.add_effect_layer(EffectType.GLOW, {
            'radius': 6.0,
            'intensity': 0.8,
            'color': [1.0, 1.0, 0.0, 1.0]
        })
        print("Created karaoke-optimized pipeline")
        
        # Create karaoke timing data
        timing_info = KaraokeTimingInfo(
            start_time=1.0,
            end_time=5.0,
            text="Hello karaoke world",
            syllable_count=4,
            syllable_timings=[1.0, 1.0, 1.0, 1.0],  # 4 syllables, 1 second each
            style_overrides=""
        )
        
        # Set karaoke timing
        pipeline.set_karaoke_timing(timing_info)
        print(f"Set karaoke timing: {timing_info.start_time}s - {timing_info.end_time}s")
        print(f"Syllables: {timing_info.syllable_count}")
        
        # Simulate karaoke playback
        print("\n--- Karaoke Playback Simulation ---")
        timestamps = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]  # Before, during syllables, after
        
        for timestamp in timestamps:
            pipeline.update_animation_time(timestamp)
            
            anim_state = pipeline.animation_state
            print(f"Time {timestamp}s:")
            print(f"  Active: {anim_state.is_active}")
            if anim_state.is_active:
                print(f"  Karaoke progress: {anim_state.karaoke_progress:.2f}")
                print(f"  Current syllable: {anim_state.syllable_index}")
                print(f"  Syllable progress: {anim_state.syllable_progress:.2f}")
            
            # Render frame
            success = pipeline.render_frame(timestamp)
            print(f"  Render: {'Success' if success else 'Failed'}")
        
        # Show final stats
        final_stats = pipeline.get_performance_stats()
        print(f"\nFinal Performance:")
        print(f"  Total frames: {final_stats['frame_count']}")
        print(f"  Average FPS: {final_stats['fps_estimate']:.1f}")
        
    finally:
        pipeline.cleanup()
        context.cleanup()


def demo_effect_presets():
    """Demonstrate effect presets"""
    print("\n=== Effect Presets Demo ===")
    
    # Create mock context for demo
    from unittest.mock import Mock
    context = Mock()
    context.backend = Mock()
    context.backend.value = "mock"
    context.cleanup = Mock()
    
    try:
        pipeline = create_effects_pipeline(context, mock_mode=True)
        
        # Get available presets
        presets = pipeline.effects_manager.get_available_presets()
        print(f"Available presets: {presets}")
        
        # Test each preset
        for preset_name in presets[:3]:  # Test first 3 presets
            print(f"\n--- Testing preset: {preset_name} ---")
            
            # Apply preset
            success = pipeline.apply_effect_preset(preset_name)
            print(f"Applied preset: {'Success' if success else 'Failed'}")
            
            if success:
                # Show effects in preset
                state = pipeline.get_pipeline_state()
                total_effects = sum(p['effect_count'] for p in state['rendering_passes'])
                print(f"Effects in preset: {total_effects}")
                
                # Render a frame
                success = pipeline.render_frame(1.0)
                print(f"Rendered frame: {'Success' if success else 'Failed'}")
                
                # Clear for next preset
                pipeline.clear_all_effects()
        
    finally:
        pipeline.cleanup()
        context.cleanup()


def demo_real_time_parameter_adjustment():
    """Demonstrate real-time parameter adjustment"""
    print("\n=== Real-time Parameter Adjustment Demo ===")
    
    # Create mock context for demo
    from unittest.mock import Mock
    context = Mock()
    context.backend = Mock()
    context.backend.value = "mock"
    context.cleanup = Mock()
    
    try:
        pipeline = create_effects_pipeline(context, mock_mode=True)
        
        # Add a glow effect
        glow_id = pipeline.add_effect_layer(EffectType.GLOW, {
            'radius': 5.0,
            'intensity': 0.5
        })
        
        print("Simulating real-time parameter changes...")
        
        # Simulate parameter changes over time
        for frame in range(10):
            timestamp = frame * 0.1
            
            # Animate glow radius
            radius = 5.0 + 3.0 * (frame / 9.0)  # 5.0 to 8.0
            intensity = 0.5 + 0.5 * (frame / 9.0)  # 0.5 to 1.0
            
            # Update parameters in buffered mode
            pipeline.update_effect_parameters(glow_id, {
                'radius': radius,
                'intensity': intensity
            }, ParameterUpdateMode.BUFFERED)
            
            # Render frame (will process buffered updates)
            success = pipeline.render_frame(timestamp)
            
            print(f"Frame {frame+1}: radius={radius:.1f}, intensity={intensity:.1f}, render={'OK' if success else 'FAIL'}")
        
        # Show buffering stats
        stats = pipeline.get_performance_stats()
        print(f"\nBuffering stats:")
        print(f"  Buffered updates processed: {stats['frame_count']} frames")
        print(f"  Current buffer size: {stats['buffered_updates']}")
        
    finally:
        pipeline.cleanup()
        context.cleanup()


def demo_performance_monitoring():
    """Demonstrate performance monitoring"""
    print("\n=== Performance Monitoring Demo ===")
    
    # Create mock context for demo
    from unittest.mock import Mock
    context = Mock()
    context.backend = Mock()
    context.backend.value = "mock"
    context.cleanup = Mock()
    
    try:
        pipeline = create_effects_pipeline(context, mock_mode=True)
        
        # Enable performance monitoring
        pipeline.enable_performance_monitoring = True
        
        # Add multiple effects to stress test
        effects = [
            (EffectType.SHADOW, {'offset_x': 3.0, 'offset_y': 3.0}),
            (EffectType.OUTLINE, {'width': 2.0}),
            (EffectType.GLOW, {'radius': 6.0}),
            (EffectType.BOUNCE, {'amplitude': 10.0}),
            (EffectType.WAVE, {'amplitude': 5.0}),
        ]
        
        print("Adding effects for performance test...")
        for effect_type, params in effects:
            effect_id = pipeline.add_effect_layer(effect_type, params)
            print(f"  Added {effect_type.value}: {effect_id}")
        
        # Render many frames
        print("\nRendering frames for performance measurement...")
        start_time = time.time()
        
        for i in range(50):
            timestamp = i * 0.02  # 50 FPS simulation
            success = pipeline.render_frame(timestamp)
            
            if i % 10 == 0:
                print(f"  Rendered frame {i+1}/50")
        
        total_time = time.time() - start_time
        
        # Get detailed performance stats
        stats = pipeline.get_performance_stats()
        
        print(f"\nPerformance Results:")
        print(f"  Total frames: {stats['frame_count']}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average render time: {stats['average_render_time']:.4f}s")
        print(f"  Min render time: {stats['min_render_time']:.4f}s")
        print(f"  Max render time: {stats['max_render_time']:.4f}s")
        print(f"  Estimated FPS: {stats['fps_estimate']:.1f}")
        print(f"  Active rendering passes: {stats['active_passes']}")
        print(f"  Total effect layers: {stats['total_effect_layers']}")
        
    finally:
        pipeline.cleanup()
        context.cleanup()


def main():
    """Run all demos"""
    print("Effects Rendering Pipeline Demo")
    print("=" * 50)
    
    try:
        demo_basic_pipeline()
        demo_karaoke_integration()
        demo_effect_presets()
        demo_real_time_parameter_adjustment()
        demo_performance_monitoring()
        
        print("\n" + "=" * 50)
        print("All demos completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()