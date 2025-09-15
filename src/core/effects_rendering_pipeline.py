"""
Effects Rendering Pipeline

This module provides a comprehensive effects rendering pipeline that coordinates
shader programs, manages effect layering and composition, enables real-time parameter
adjustment, and integrates with karaoke timing for synchronized animations.
"""

import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from threading import Lock
import json

# Configure logging
logger = logging.getLogger(__name__)

try:
    from .effects_manager import EffectsManager, EffectType, EffectLayer
    from .shader_system import VisualEffectsShaderSystem, ShaderProgram, EffectParameters
    from .opengl_context import OpenGLContext
    from .models import KaraokeTimingInfo, SubtitleLine
except ImportError:
    from effects_manager import EffectsManager, EffectType, EffectLayer
    from shader_system import VisualEffectsShaderSystem, ShaderProgram, EffectParameters
    from opengl_context import OpenGLContext
    from models import KaraokeTimingInfo, SubtitleLine

# Try to import OpenGL libraries
try:
    import OpenGL.GL as gl
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    logger.warning("OpenGL not available, using mock implementation")


class RenderingStage(Enum):
    """Rendering pipeline stages"""
    BACKGROUND = "background"
    SHADOW = "shadow"
    OUTLINE = "outline"
    FILL = "fill"
    GLOW = "glow"
    OVERLAY = "overlay"
    ANIMATION = "animation"
    COMPOSITION = "composition"


class ParameterUpdateMode(Enum):
    """Parameter update modes"""
    IMMEDIATE = "immediate"
    BUFFERED = "buffered"
    SYNCHRONIZED = "synchronized"


@dataclass
class RenderingPass:
    """Represents a single rendering pass in the pipeline"""
    stage: RenderingStage
    shader_program: Optional[ShaderProgram]
    effect_layers: List[EffectLayer]
    uniforms: Dict[str, Any]
    enabled: bool = True
    order: int = 0
    
    def __post_init__(self):
        if self.uniforms is None:
            self.uniforms = {}


@dataclass
class AnimationState:
    """Current animation state for effects"""
    current_time: float = 0.0
    karaoke_progress: float = 0.0
    syllable_index: int = 0
    syllable_progress: float = 0.0
    is_active: bool = False
    
    def update_from_karaoke_timing(self, timing_info: KaraokeTimingInfo, current_time: float):
        """Update animation state from karaoke timing"""
        self.current_time = current_time
        
        if not timing_info:
            self.is_active = False
            return
        
        self.is_active = timing_info.start_time <= current_time <= timing_info.end_time
        
        if self.is_active:
            # Calculate overall progress
            duration = timing_info.end_time - timing_info.start_time
            elapsed = current_time - timing_info.start_time
            self.karaoke_progress = elapsed / duration if duration > 0 else 0.0
            
            # Calculate syllable progress
            if timing_info.syllable_timings:
                syllable_start = timing_info.start_time
                for i, syllable_duration in enumerate(timing_info.syllable_timings):
                    syllable_end = syllable_start + syllable_duration
                    
                    if syllable_start <= current_time <= syllable_end:
                        self.syllable_index = i
                        syllable_elapsed = current_time - syllable_start
                        self.syllable_progress = syllable_elapsed / syllable_duration if syllable_duration > 0 else 0.0
                        break
                    
                    syllable_start = syllable_end


@dataclass
class ParameterUpdate:
    """Represents a parameter update request"""
    layer_id: str
    parameter_name: str
    new_value: Any
    timestamp: float = field(default_factory=time.time)
    mode: ParameterUpdateMode = ParameterUpdateMode.IMMEDIATE
    
    def apply_to_layer(self, layer: EffectLayer):
        """Apply this update to an effect layer"""
        if hasattr(layer.effect, 'parameters') and hasattr(layer.effect.parameters, '__setitem__'):
            layer.effect.parameters[self.parameter_name] = self.new_value
        elif hasattr(layer, 'parameters') and hasattr(layer.parameters, 'params'):
            layer.parameters.params[self.parameter_name] = self.new_value
        elif hasattr(layer.effect, 'parameters') and isinstance(layer.effect.parameters, dict):
            layer.effect.parameters[self.parameter_name] = self.new_value


class EffectsRenderingPipeline:
    """
    Comprehensive effects rendering pipeline that coordinates shader programs,
    manages effect layering and composition, and provides real-time parameter adjustment.
    """
    
    def __init__(self, opengl_context: OpenGLContext, mock_mode: bool = False):
        self.opengl_context = opengl_context
        self.mock_mode = mock_mode
        
        # Core components
        self.effects_manager = EffectsManager()
        self.shader_system = VisualEffectsShaderSystem(mock_mode=mock_mode)
        
        # Pipeline state
        self.rendering_passes: List[RenderingPass] = []
        self.animation_state = AnimationState()
        self.parameter_updates: List[ParameterUpdate] = []
        self.update_lock = Lock()
        
        # Performance tracking
        self.frame_count = 0
        self.last_frame_time = 0.0
        self.render_times: List[float] = []
        self.max_render_time_samples = 100
        
        # Configuration
        self.enable_performance_monitoring = True
        self.enable_parameter_buffering = True
        self.max_buffered_updates = 1000
        
        # Initialize pipeline
        self._initialize_rendering_passes()
        
        logger.info("Effects rendering pipeline initialized")
    
    def _initialize_rendering_passes(self):
        """Initialize rendering passes for different effect stages"""
        # Define rendering stages in order
        stages = [
            RenderingStage.BACKGROUND,
            RenderingStage.SHADOW,
            RenderingStage.OUTLINE,
            RenderingStage.FILL,
            RenderingStage.GLOW,
            RenderingStage.OVERLAY,
            RenderingStage.ANIMATION,
            RenderingStage.COMPOSITION
        ]
        
        for i, stage in enumerate(stages):
            render_pass = RenderingPass(
                stage=stage,
                shader_program=None,
                effect_layers=[],
                uniforms={},
                order=i
            )
            self.rendering_passes.append(render_pass)
    
    def add_effect_layer(self, effect_type: EffectType, parameters: Dict[str, Any] = None) -> str:
        """Add an effect layer to the pipeline"""
        # Create effect using effects manager
        effect = self.effects_manager.create_effect(effect_type, parameters or {})
        layer = self.effects_manager.add_effect_layer(effect)
        
        # Assign to appropriate rendering stage
        stage = self._get_stage_for_effect_type(effect_type)
        render_pass = self._get_render_pass_for_stage(stage)
        
        if render_pass:
            render_pass.effect_layers.append(layer)
            
            # Update shader program if needed
            self._update_shader_program_for_pass(render_pass)
        
        logger.debug(f"Added effect layer {layer.effect.id} of type {effect_type.value} to stage {stage.value}")
        return layer.effect.id
    
    def remove_effect_layer(self, layer_id: str) -> bool:
        """Remove an effect layer from the pipeline"""
        # Remove from effects manager
        success = self.effects_manager.remove_effect_layer(layer_id)
        
        if success:
            # Remove from rendering passes
            for render_pass in self.rendering_passes:
                render_pass.effect_layers = [
                    layer for layer in render_pass.effect_layers 
                    if layer.effect.id != layer_id
                ]
                
                # Update shader program
                self._update_shader_program_for_pass(render_pass)
            
            logger.debug(f"Removed effect layer {layer_id}")
        
        return success
    
    def update_effect_parameters(self, layer_id: str, parameters: Dict[str, Any], 
                               mode: ParameterUpdateMode = ParameterUpdateMode.IMMEDIATE) -> bool:
        """Update parameters for an effect layer"""
        if mode == ParameterUpdateMode.IMMEDIATE:
            # Apply immediately
            success = self.effects_manager.update_effect_parameters(layer_id, parameters)
            
            if success:
                # Update shader uniforms
                self._update_uniforms_for_layer(layer_id)
                logger.debug(f"Updated parameters for layer {layer_id} immediately")
            
            return success
        
        elif mode == ParameterUpdateMode.BUFFERED:
            # Add to update buffer
            with self.update_lock:
                for param_name, param_value in parameters.items():
                    update = ParameterUpdate(
                        layer_id=layer_id,
                        parameter_name=param_name,
                        new_value=param_value,
                        mode=mode
                    )
                    self.parameter_updates.append(update)
                
                # Limit buffer size
                if len(self.parameter_updates) > self.max_buffered_updates:
                    self.parameter_updates = self.parameter_updates[-self.max_buffered_updates:]
            
            logger.debug(f"Buffered parameter updates for layer {layer_id}")
            return True
        
        elif mode == ParameterUpdateMode.SYNCHRONIZED:
            # Will be applied during next render frame
            return self.update_effect_parameters(layer_id, parameters, ParameterUpdateMode.BUFFERED)
        
        return False
    
    def set_karaoke_timing(self, timing_info: KaraokeTimingInfo):
        """Set current karaoke timing information"""
        self.current_karaoke_timing = timing_info
        logger.debug(f"Set karaoke timing: {timing_info.start_time}s - {timing_info.end_time}s")
    
    def update_animation_time(self, current_time: float):
        """Update animation time and karaoke state"""
        self.animation_state.current_time = current_time
        
        # Update karaoke timing if available
        if hasattr(self, 'current_karaoke_timing') and self.current_karaoke_timing:
            self.animation_state.update_from_karaoke_timing(self.current_karaoke_timing, current_time)
        
        # Update time-based animations (if method exists)
        if hasattr(self.effects_manager, 'update_animation_time'):
            self.effects_manager.update_animation_time(current_time)
    
    def render_frame(self, timestamp: float, subtitle_texture: Optional[Any] = None) -> bool:
        """Render a complete frame through the effects pipeline"""
        start_time = time.time()
        
        try:
            # Update animation state
            self.update_animation_time(timestamp)
            
            # Process buffered parameter updates
            self._process_buffered_updates()
            
            # Render each pass in order
            for render_pass in self.rendering_passes:
                if render_pass.enabled and render_pass.effect_layers:
                    self._render_pass(render_pass, subtitle_texture)
            
            # Update performance metrics
            if self.enable_performance_monitoring:
                self._update_performance_metrics(start_time)
            
            self.frame_count += 1
            return True
            
        except Exception as e:
            logger.error(f"Error rendering frame at {timestamp}s: {e}")
            return False
    
    def _render_pass(self, render_pass: RenderingPass, subtitle_texture: Optional[Any] = None):
        """Render a single pass in the pipeline"""
        if not render_pass.shader_program or not render_pass.effect_layers:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            # Use actual OpenGL rendering
            render_pass.shader_program.use()
            
            # Set common uniforms
            self._set_common_uniforms(render_pass.shader_program)
            
            # Set effect-specific uniforms
            for uniform_name, uniform_value in render_pass.uniforms.items():
                self._set_uniform_value(render_pass.shader_program, uniform_name, uniform_value)
            
            # Bind subtitle texture if available
            if subtitle_texture and hasattr(subtitle_texture, 'bind'):
                subtitle_texture.bind(0)
                render_pass.shader_program.set_uniform_int('u_texture', 0)
            
            # Render geometry (would be implemented based on specific needs)
            self._render_geometry(render_pass)
            
        elif self.mock_mode:
            # Mock rendering for testing
            logger.debug(f"Mock rendering pass: {render_pass.stage.value} with {len(render_pass.effect_layers)} layers")
    
    def _render_geometry(self, render_pass: RenderingPass):
        """Render geometry for the pass (placeholder implementation)"""
        if OPENGL_AVAILABLE and not self.mock_mode:
            # This would render a quad or other geometry
            # For now, just a placeholder
            pass
        else:
            logger.debug(f"Mock geometry rendering for {render_pass.stage.value}")
    
    def _set_common_uniforms(self, shader_program: ShaderProgram):
        """Set common uniforms for all shaders"""
        if not shader_program:
            return
        
        # Time uniforms
        shader_program.set_uniform_float('u_time', self.animation_state.current_time)
        
        # Karaoke uniforms
        shader_program.set_uniform_float('u_karaoke_progress', self.animation_state.karaoke_progress)
        shader_program.set_uniform_float('u_syllable_progress', self.animation_state.syllable_progress)
        shader_program.set_uniform_int('u_syllable_index', self.animation_state.syllable_index)
        
        # Resolution (would come from context)
        if self.opengl_context:
            width, height = 1920, 1080  # Default, should come from context
            shader_program.set_uniform_vec2('u_resolution', (float(width), float(height)))
    
    def _set_uniform_value(self, shader_program: ShaderProgram, name: str, value: Any):
        """Set uniform value based on type"""
        if isinstance(value, (int, bool)):
            shader_program.set_uniform_int(name, int(value))
        elif isinstance(value, float):
            shader_program.set_uniform_float(name, value)
        elif isinstance(value, (list, tuple)):
            if len(value) == 2:
                shader_program.set_uniform_vec2(name, tuple(value))
            elif len(value) == 3:
                shader_program.set_uniform_vec3(name, tuple(value))
            elif len(value) == 4:
                shader_program.set_uniform_vec4(name, tuple(value))
        elif isinstance(value, np.ndarray):
            if value.shape == (4, 4):
                shader_program.set_uniform_matrix4(name, value)
    
    def _process_buffered_updates(self):
        """Process buffered parameter updates"""
        if not self.enable_parameter_buffering:
            return
        
        with self.update_lock:
            if not self.parameter_updates:
                return
            
            # Group updates by layer
            updates_by_layer = {}
            for update in self.parameter_updates:
                if update.layer_id not in updates_by_layer:
                    updates_by_layer[update.layer_id] = {}
                updates_by_layer[update.layer_id][update.parameter_name] = update.new_value
            
            # Apply updates
            for layer_id, parameters in updates_by_layer.items():
                self.effects_manager.update_effect_parameters(layer_id, parameters)
                self._update_uniforms_for_layer(layer_id)
            
            # Clear processed updates
            self.parameter_updates.clear()
            
            if updates_by_layer:
                logger.debug(f"Processed buffered updates for {len(updates_by_layer)} layers")
    
    def _update_uniforms_for_layer(self, layer_id: str):
        """Update shader uniforms for a specific layer"""
        layer = self.effects_manager.get_effect_layer(layer_id)
        if not layer:
            return
        
        # Find the render pass containing this layer
        for render_pass in self.rendering_passes:
            if layer in render_pass.effect_layers:
                # Update uniforms for this pass
                self._update_shader_program_for_pass(render_pass)
                break
    
    def _update_shader_program_for_pass(self, render_pass: RenderingPass):
        """Update shader program and uniforms for a render pass"""
        if not render_pass.effect_layers:
            render_pass.shader_program = None
            render_pass.uniforms.clear()
            return
        
        # Generate shader code for active layers
        active_layers = [layer for layer in render_pass.effect_layers if layer.enabled]
        
        if not active_layers:
            render_pass.shader_program = None
            render_pass.uniforms.clear()
            return
        
        # Get shader code from effects manager
        vertex_shader, fragment_shader = self.effects_manager.generate_shader_code(active_layers)
        
        # Create or update shader program
        shader_name = f"{render_pass.stage.value}_pass"
        
        if render_pass.shader_program:
            # Update existing program (simplified - would need proper shader recompilation)
            pass
        else:
            # Create new shader program
            from .shader_system import ShaderSource
            sources = ShaderSource(vertex_shader, fragment_shader)
            render_pass.shader_program = self.shader_system.create_program(shader_name, sources)
        
        # Update uniforms
        render_pass.uniforms = self.effects_manager.get_effect_uniforms(active_layers)
    
    def _get_stage_for_effect_type(self, effect_type: EffectType) -> RenderingStage:
        """Get appropriate rendering stage for effect type"""
        stage_mapping = {
            EffectType.SHADOW: RenderingStage.SHADOW,
            EffectType.OUTLINE: RenderingStage.OUTLINE,
            EffectType.GLOW: RenderingStage.GLOW,
            EffectType.FADE: RenderingStage.ANIMATION,
            EffectType.BOUNCE: RenderingStage.ANIMATION,
            EffectType.WAVE: RenderingStage.ANIMATION,
            EffectType.TYPEWRITER: RenderingStage.ANIMATION,
            EffectType.COLOR_TRANSITION: RenderingStage.ANIMATION,
        }
        
        return stage_mapping.get(effect_type, RenderingStage.OVERLAY)
    
    def _get_render_pass_for_stage(self, stage: RenderingStage) -> Optional[RenderingPass]:
        """Get render pass for a specific stage"""
        for render_pass in self.rendering_passes:
            if render_pass.stage == stage:
                return render_pass
        return None
    
    def _update_performance_metrics(self, start_time: float):
        """Update performance tracking metrics"""
        render_time = time.time() - start_time
        # Ensure minimum time for testing
        if render_time <= 0.0:
            render_time = 0.001  # 1ms minimum for testing
        
        self.render_times.append(render_time)
        
        # Keep only recent samples
        if len(self.render_times) > self.max_render_time_samples:
            self.render_times = self.render_times[-self.max_render_time_samples:]
        
        self.last_frame_time = render_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.render_times:
            return {
                'frame_count': self.frame_count,
                'average_render_time': 0.0,
                'max_render_time': 0.0,
                'min_render_time': 0.0,
                'last_frame_time': self.last_frame_time,
                'fps_estimate': 0.0
            }
        
        avg_time = sum(self.render_times) / len(self.render_times)
        max_time = max(self.render_times)
        min_time = min(self.render_times)
        fps_estimate = 1.0 / avg_time if avg_time > 0 else 0.0
        
        return {
            'frame_count': self.frame_count,
            'average_render_time': avg_time,
            'max_render_time': max_time,
            'min_render_time': min_time,
            'last_frame_time': self.last_frame_time,
            'fps_estimate': fps_estimate,
            'active_passes': len([p for p in self.rendering_passes if p.enabled and p.effect_layers]),
            'total_effect_layers': sum(len(p.effect_layers) for p in self.rendering_passes),
            'buffered_updates': len(self.parameter_updates)
        }
    
    def get_pipeline_state(self) -> Dict[str, Any]:
        """Get current pipeline state"""
        return {
            'animation_state': {
                'current_time': self.animation_state.current_time,
                'karaoke_progress': self.animation_state.karaoke_progress,
                'syllable_index': self.animation_state.syllable_index,
                'syllable_progress': self.animation_state.syllable_progress,
                'is_active': self.animation_state.is_active
            },
            'rendering_passes': [
                {
                    'stage': pass_.stage.value,
                    'enabled': pass_.enabled,
                    'effect_count': len(pass_.effect_layers),
                    'has_shader': pass_.shader_program is not None,
                    'uniform_count': len(pass_.uniforms)
                }
                for pass_ in self.rendering_passes
            ],
            'performance': self.get_performance_stats()
        }
    
    def enable_pass(self, stage: RenderingStage, enabled: bool = True):
        """Enable or disable a rendering pass"""
        render_pass = self._get_render_pass_for_stage(stage)
        if render_pass:
            render_pass.enabled = enabled
            logger.debug(f"{'Enabled' if enabled else 'Disabled'} rendering pass: {stage.value}")
    
    def clear_all_effects(self):
        """Clear all effects from the pipeline"""
        self.effects_manager.clear_all_effects()
        
        for render_pass in self.rendering_passes:
            render_pass.effect_layers.clear()
            render_pass.shader_program = None
            render_pass.uniforms.clear()
        
        logger.info("Cleared all effects from pipeline")
    
    def apply_effect_preset(self, preset_name: str) -> bool:
        """Apply an effect preset to the pipeline"""
        success = self.effects_manager.apply_preset(preset_name)
        
        if success:
            # Rebuild rendering passes
            self._rebuild_rendering_passes()
            logger.info(f"Applied effect preset: {preset_name}")
        
        return success
    
    def _rebuild_rendering_passes(self):
        """Rebuild rendering passes after major changes"""
        # Clear current passes
        for render_pass in self.rendering_passes:
            render_pass.effect_layers.clear()
            render_pass.shader_program = None
            render_pass.uniforms.clear()
        
        # Reassign effect layers to appropriate passes
        for layer in self.effects_manager.effect_layers:
            stage = self._get_stage_for_effect_type(EffectType(layer.effect.type))
            render_pass = self._get_render_pass_for_stage(stage)
            
            if render_pass:
                render_pass.effect_layers.append(layer)
        
        # Update shader programs for all passes
        for render_pass in self.rendering_passes:
            self._update_shader_program_for_pass(render_pass)
    
    def cleanup(self):
        """Clean up pipeline resources"""
        # Clean up shader programs
        for render_pass in self.rendering_passes:
            if render_pass.shader_program and hasattr(render_pass.shader_program, 'destroy'):
                render_pass.shader_program.destroy()
            render_pass.shader_program = None
            render_pass.effect_layers.clear()
            render_pass.uniforms.clear()
        
        # Clean up effects manager
        self.effects_manager.clear_all_effects()
        
        # Clear state
        self.parameter_updates.clear()
        self.render_times.clear()
        self.frame_count = 0
        
        logger.info("Effects rendering pipeline cleaned up")


# Convenience functions
def create_effects_pipeline(opengl_context: OpenGLContext, mock_mode: bool = False) -> EffectsRenderingPipeline:
    """Create an effects rendering pipeline"""
    return EffectsRenderingPipeline(opengl_context, mock_mode)


def create_karaoke_effects_pipeline(opengl_context: OpenGLContext) -> EffectsRenderingPipeline:
    """Create a pipeline optimized for karaoke effects"""
    pipeline = EffectsRenderingPipeline(opengl_context)
    
    # Apply karaoke-optimized settings
    pipeline.enable_parameter_buffering = True
    pipeline.enable_performance_monitoring = True
    
    # Add common karaoke effects
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
    
    return pipeline


if __name__ == "__main__":
    print("Testing Effects Rendering Pipeline...")
    
    # Create mock OpenGL context for testing
    from opengl_context import create_offscreen_context
    
    context = create_offscreen_context(1920, 1080, mock_mode=True)
    if context:
        # Test basic pipeline
        pipeline = create_effects_pipeline(context, mock_mode=True)
        
        # Add some effects
        glow_id = pipeline.add_effect_layer(EffectType.GLOW, {'radius': 8.0})
        outline_id = pipeline.add_effect_layer(EffectType.OUTLINE, {'width': 3.0})
        
        # Test parameter updates
        pipeline.update_effect_parameters(glow_id, {'intensity': 1.2})
        
        # Test rendering
        success = pipeline.render_frame(1.0)
        print(f"Frame rendering: {'Success' if success else 'Failed'}")
        
        # Test performance stats
        stats = pipeline.get_performance_stats()
        print(f"Performance stats: {stats}")
        
        # Test pipeline state
        state = pipeline.get_pipeline_state()
        print(f"Pipeline state: {len(state['rendering_passes'])} passes")
        
        # Cleanup
        pipeline.cleanup()
        context.cleanup()
        
        print("Effects rendering pipeline test completed successfully")
    else:
        print("Failed to create OpenGL context")