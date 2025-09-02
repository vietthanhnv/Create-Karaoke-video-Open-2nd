"""
OpenGL-based subtitle rendering system with GPU acceleration.

This module provides hardware-accelerated subtitle rendering using OpenGL shaders,
with support for .ass format styling, text effects, and texture caching.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

try:
    from .models import SubtitleLine, SubtitleStyle
    from .effects_manager import EffectsManager, EffectLayer
except ImportError:
    from models import SubtitleLine, SubtitleStyle
    from effects_manager import EffectsManager, EffectLayer


@dataclass
class RenderedSubtitle:
    """Represents a rendered subtitle with OpenGL texture and positioning."""
    texture: Any
    position: Tuple[float, float]
    size: Tuple[float, float]
    start_time: float
    end_time: float
    text: str
    style_name: str


@dataclass
class TextureCache:
    """Cache for rendered subtitle textures."""
    textures: Dict[str, RenderedSubtitle] = field(default_factory=dict)
    max_size: int = 100
    
    def get_cache_key(self, text: str, style: SubtitleStyle, viewport_size: Tuple[int, int]) -> str:
        """Generate cache key for subtitle texture."""
        return f"{text}_{style.name}_{style.font_size}_{viewport_size[0]}x{viewport_size[1]}"
    
    def get(self, key: str) -> Optional[RenderedSubtitle]:
        """Get cached texture."""
        return self.textures.get(key)
    
    def put(self, key: str, rendered: RenderedSubtitle):
        """Store texture in cache."""
        if len(self.textures) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.textures))
            old_texture = self.textures.pop(oldest_key)
            if old_texture.texture and hasattr(old_texture.texture, 'destroy'):
                old_texture.texture.destroy()
        
        self.textures[key] = rendered
    
    def clear(self):
        """Clear all cached textures."""
        for rendered in self.textures.values():
            if rendered.texture and hasattr(rendered.texture, 'destroy'):
                rendered.texture.destroy()
        self.textures.clear()
    
    def get_cache_key(self, text: str, style: SubtitleStyle, viewport_size: Tuple[int, int]) -> str:
        """Generate cache key for subtitle texture."""
        return f"{text}_{style.name}_{style.font_size}_{viewport_size[0]}x{viewport_size[1]}"
    
    def get(self, key: str) -> Optional[RenderedSubtitle]:
        """Get cached texture."""
        return self.textures.get(key)
    
    def put(self, key: str, rendered: RenderedSubtitle):
        """Store texture in cache."""
        if len(self.textures) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.textures))
            old_texture = self.textures.pop(oldest_key)
            if old_texture.texture and hasattr(old_texture.texture, 'destroy'):
                old_texture.texture.destroy()
        
        self.textures[key] = rendered
    
    def clear(self):
        """Clear all cached textures."""
        for rendered in self.textures.values():
            if rendered.texture and hasattr(rendered.texture, 'destroy'):
                rendered.texture.destroy()
        self.textures.clear()


class OpenGLSubtitleRenderer:
    """
    GPU-accelerated subtitle renderer using OpenGL shaders.
    
    Provides high-performance text rendering with support for .ass format styling,
    text effects, and texture caching for optimal performance.
    """
    
    def __init__(self):
        self.texture_cache = TextureCache()
        self.shader_program = None
        self.vertex_buffer = None
        self.index_buffer = None
        self.initialized = False
        self.effects_manager = EffectsManager()
        self.current_time = 0.0
        
        # Shader source code (will be generated dynamically based on effects)
        self.vertex_shader_source = None
        self.fragment_shader_source = None
    
    def _get_vertex_shader(self) -> str:
        """Get vertex shader source code."""
        return """
        #version 330 core
        
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 texCoord;
        
        out vec2 TexCoord;
        
        uniform mat4 projection;
        uniform mat4 model;
        
        void main()
        {
            gl_Position = projection * model * vec4(position, 1.0);
            TexCoord = texCoord;
        }
        """
    
    def _get_fragment_shader(self) -> str:
        """Get fragment shader source code."""
        return """
        #version 330 core
        
        in vec2 TexCoord;
        out vec4 FragColor;
        
        uniform sampler2D textTexture;
        uniform vec3 textColor;
        uniform float alpha;
        
        // Effect parameters
        uniform bool enableGlow;
        uniform vec3 glowColor;
        uniform float glowRadius;
        
        uniform bool enableOutline;
        uniform vec3 outlineColor;
        uniform float outlineWidth;
        
        uniform bool enableShadow;
        uniform vec3 shadowColor;
        uniform vec2 shadowOffset;
        
        void main()
        {
            vec4 sampled = texture(textTexture, TexCoord);
            vec3 finalColor = textColor;
            float finalAlpha = sampled.r * alpha;
            
            // Apply glow effect
            if (enableGlow && glowRadius > 0.0) {
                float glow = 0.0;
                int samples = int(glowRadius * 2.0);
                for (int x = -samples; x <= samples; x++) {
                    for (int y = -samples; y <= samples; y++) {
                        vec2 offset = vec2(float(x), float(y)) / textureSize(textTexture, 0);
                        float dist = length(offset);
                        if (dist <= glowRadius) {
                            float weight = 1.0 - (dist / glowRadius);
                            glow += texture(textTexture, TexCoord + offset).r * weight;
                        }
                    }
                }
                glow /= float((samples * 2 + 1) * (samples * 2 + 1));
                finalColor = mix(finalColor, glowColor, glow * 0.5);
            }
            
            // Apply outline effect
            if (enableOutline && outlineWidth > 0.0) {
                float outline = 0.0;
                int samples = int(outlineWidth);
                for (int x = -samples; x <= samples; x++) {
                    for (int y = -samples; y <= samples; y++) {
                        if (x == 0 && y == 0) continue;
                        vec2 offset = vec2(float(x), float(y)) / textureSize(textTexture, 0);
                        outline = max(outline, texture(textTexture, TexCoord + offset).r);
                    }
                }
                if (outline > 0.1 && sampled.r < 0.1) {
                    finalColor = outlineColor;
                    finalAlpha = outline * alpha;
                }
            }
            
            // Apply shadow effect
            if (enableShadow) {
                vec2 shadowTexCoord = TexCoord - shadowOffset / textureSize(textTexture, 0);
                float shadowSample = texture(textTexture, shadowTexCoord).r;
                if (shadowSample > 0.1 && sampled.r < 0.1) {
                    finalColor = shadowColor;
                    finalAlpha = shadowSample * alpha * 0.7;
                }
            }
            
            FragColor = vec4(finalColor, finalAlpha);
        }
        """
        
    def initialize_opengl(self) -> bool:
        """Initialize OpenGL resources."""
        if self.initialized:
            return True
            
        try:
            # Generate shaders based on current effects
            self._update_shaders()
            
            # Import PyQt6 components only when needed to avoid context issues
            from PyQt6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
            import OpenGL.GL as gl
            
            # Create and compile shaders
            self.shader_program = QOpenGLShaderProgram()
            
            if not self.shader_program.addShaderFromSourceCode(
                QOpenGLShader.ShaderTypeBit.Vertex, self.vertex_shader_source
            ):
                print(f"Vertex shader compilation failed: {self.shader_program.log()}")
                return False
            
            if not self.shader_program.addShaderFromSourceCode(
                QOpenGLShader.ShaderTypeBit.Fragment, self.fragment_shader_source
            ):
                print(f"Fragment shader compilation failed: {self.shader_program.log()}")
                return False
            
            if not self.shader_program.link():
                print(f"Shader program linking failed: {self.shader_program.log()}")
                return False
            
            # Create vertex buffer for quad rendering
            self.create_quad_buffers()
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"OpenGL initialization failed: {e}")
            return False
    
    def create_quad_buffers(self):
        """Create vertex and index buffers for quad rendering."""
        try:
            import OpenGL.GL as gl
            
            # Quad vertices (position + texture coordinates)
            vertices = np.array([
                # positions    # texture coords
                -1.0, -1.0, 0.0,  0.0, 0.0,  # bottom left
                 1.0, -1.0, 0.0,  1.0, 0.0,  # bottom right
                 1.0,  1.0, 0.0,  1.0, 1.0,  # top right
                -1.0,  1.0, 0.0,  0.0, 1.0   # top left
            ], dtype=np.float32)
            
            indices = np.array([
                0, 1, 2,  # first triangle
                2, 3, 0   # second triangle
            ], dtype=np.uint32)
            
            # Generate and bind vertex buffer
            self.vertex_buffer = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vertex_buffer)
            gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices.nbytes, vertices, gl.GL_STATIC_DRAW)
            
            # Generate and bind index buffer
            self.index_buffer = gl.glGenBuffers(1)
            gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
            gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, gl.GL_STATIC_DRAW)
            
        except ImportError:
            # OpenGL not available, use mock implementation
            self.vertex_buffer = 1
            self.index_buffer = 2    

    def create_text_texture(self, text: str, style: SubtitleStyle, viewport_size: Tuple[int, int]):
        """Create OpenGL texture from text using Qt's text rendering."""
        try:
            from PyQt6.QtGui import QFont, QFontMetrics, QColor, QPainter, QImage, QPen
            from PyQt6.QtCore import QRect
            from PyQt6.QtOpenGL import QOpenGLTexture
            
            # Calculate font size based on viewport
            font_size = int(style.font_size * viewport_size[1] / 720)  # Scale for 720p reference
            font = QFont(style.font_name, font_size)
            font.setBold(style.bold)
            font.setItalic(style.italic)
            
            # Calculate text metrics
            metrics = QFontMetrics(font)
            text_rect = metrics.boundingRect(text)
            
            # Add padding for effects
            padding = max(20, font_size // 4)
            image_width = text_rect.width() + padding * 2
            image_height = text_rect.height() + padding * 2
            
            # Create image for text rendering
            image = QImage(image_width, image_height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(QColor(0, 0, 0, 0))  # Transparent background
            
            # Render text to image
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            painter.setFont(font)
            
            # Set text color
            color = QColor()
            color.setNamedColor(style.primary_color)
            painter.setPen(QPen(color))
            
            # Draw text
            painter.drawText(
                QRect(padding, padding, text_rect.width(), text_rect.height()),
                0,  # No alignment flags
                text
            )
            painter.end()
            
            # Create OpenGL texture
            texture = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
            texture.setData(image)
            texture.setMinificationFilter(QOpenGLTexture.Filter.Linear)
            texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
            texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
            
            return texture
            
        except ImportError:
            # PyQt6 not available, return mock texture
            class MockTexture:
                def width(self): return 300
                def height(self): return 50
                def destroy(self): pass
            return MockTexture()
            
    def render_subtitle(self, subtitle: SubtitleLine, style: SubtitleStyle, 
                       viewport_size: Tuple[int, int], current_time: float) -> Optional[RenderedSubtitle]:
        """
        Render a subtitle line with the specified style.
        
        Args:
            subtitle: The subtitle line to render
            style: The style to apply
            viewport_size: Current viewport dimensions (width, height)
            current_time: Current playback time
            
        Returns:
            RenderedSubtitle object or None if not visible
        """
        # Check if subtitle should be visible
        if current_time < subtitle.start_time or current_time > subtitle.end_time:
            return None
        
        # Check cache first
        cache_key = self.texture_cache.get_cache_key(subtitle.text, style, viewport_size)
        cached = self.texture_cache.get(cache_key)
        if cached:
            return cached
        
        # Create new texture
        texture = self.create_text_texture(subtitle.text, style, viewport_size)
        
        # Calculate position based on .ass alignment
        position = self.calculate_subtitle_position(subtitle, style, viewport_size, texture)
        
        # Create rendered subtitle
        rendered = RenderedSubtitle(
            texture=texture,
            position=position,
            size=(texture.width(), texture.height()),
            start_time=subtitle.start_time,
            end_time=subtitle.end_time,
            text=subtitle.text,
            style_name=style.name
        )
        
        # Cache the result
        self.texture_cache.put(cache_key, rendered)
        
        return rendered
    
    def calculate_subtitle_position(self, subtitle: SubtitleLine, style: SubtitleStyle, 
                                  viewport_size: Tuple[int, int], texture) -> Tuple[float, float]:
        """Calculate subtitle position based on .ass alignment and margins."""
        viewport_width, viewport_height = viewport_size
        
        # Default to bottom center if no alignment specified
        alignment = getattr(style, 'alignment', 2)  # 2 = bottom center in .ass format
        
        # Calculate base position
        if alignment in [1, 2, 3]:  # Bottom alignment
            y = viewport_height - style.margin_v - texture.height()
        elif alignment in [4, 5, 6]:  # Middle alignment
            y = (viewport_height - texture.height()) / 2
        else:  # Top alignment (7, 8, 9)
            y = style.margin_v
        
        if alignment in [1, 4, 7]:  # Left alignment
            x = style.margin_l
        elif alignment in [2, 5, 8]:  # Center alignment
            x = (viewport_width - texture.width()) / 2
        else:  # Right alignment (3, 6, 9)
            x = viewport_width - style.margin_r - texture.width()
        
        return (x, y)
        
    def create_model_matrix(self, rendered_subtitle: RenderedSubtitle, viewport_size: Tuple[int, int]) -> np.ndarray:
        """Create model matrix for subtitle positioning and scaling."""
        viewport_width, viewport_height = viewport_size
        
        # Convert screen coordinates to normalized device coordinates
        x = (rendered_subtitle.position[0] / viewport_width) * 2.0 - 1.0
        y = 1.0 - (rendered_subtitle.position[1] / viewport_height) * 2.0
        
        # Scale based on texture size
        scale_x = rendered_subtitle.size[0] / viewport_width
        scale_y = rendered_subtitle.size[1] / viewport_height
        
        # Create transformation matrix
        model_matrix = np.array([
            [scale_x, 0.0, 0.0, x],
            [0.0, scale_y, 0.0, y],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32)
        
        return model_matrix
    
    def _update_shaders(self):
        """Update shader source code based on current effects."""
        active_effects = self.effects_manager.get_active_effects()
        self.vertex_shader_source, self.fragment_shader_source = \
            self.effects_manager.generate_shader_code(active_effects)
    
    def set_current_time(self, time: float):
        """Set current playback time for time-based effects."""
        self.current_time = time
    
    def add_effect(self, effect_type: str, parameters: Dict[str, Any]) -> str:
        """Add a new effect and return its ID."""
        from .effects_manager import EffectType
        
        # Convert string to EffectType enum
        try:
            effect_enum = EffectType(effect_type)
        except ValueError:
            print(f"Unknown effect type: {effect_type}")
            return ""
        
        effect = self.effects_manager.create_effect(effect_enum, parameters)
        layer = self.effects_manager.add_effect_layer(effect)
        
        # Regenerate shaders if initialized
        if self.initialized:
            self._update_shaders()
            self._recompile_shaders()
        
        return effect.id
    
    def remove_effect(self, effect_id: str) -> bool:
        """Remove an effect by ID."""
        success = self.effects_manager.remove_effect_layer(effect_id)
        
        if success and self.initialized:
            self._update_shaders()
            self._recompile_shaders()
        
        return success
    
    def update_effect_parameters(self, effect_id: str, parameters: Dict[str, Any]) -> bool:
        """Update parameters for an existing effect."""
        return self.effects_manager.update_effect_parameters(effect_id, parameters)
    
    def reorder_effects(self, effect_id: str, new_order: int) -> bool:
        """Change the rendering order of an effect."""
        success = self.effects_manager.reorder_effect_layer(effect_id, new_order)
        
        if success and self.initialized:
            self._update_shaders()
            self._recompile_shaders()
        
        return success
    
    def toggle_effect(self, effect_id: str, enabled: Optional[bool] = None) -> bool:
        """Toggle or set the enabled state of an effect."""
        return self.effects_manager.toggle_effect_layer(effect_id, enabled)
    
    def apply_effect_preset(self, preset_name: str) -> bool:
        """Apply a predefined effect preset."""
        success = self.effects_manager.apply_preset(preset_name)
        
        if success and self.initialized:
            self._update_shaders()
            self._recompile_shaders()
        
        return success
    
    def get_available_presets(self) -> List[str]:
        """Get list of available effect presets."""
        return self.effects_manager.get_available_presets()
    
    def get_active_effects(self) -> List[Dict[str, Any]]:
        """Get information about currently active effects."""
        active_layers = self.effects_manager.get_active_effects()
        return [
            {
                'id': layer.effect.id,
                'name': layer.effect.name,
                'type': layer.effect.type,
                'parameters': layer.effect.parameters,
                'order': layer.order,
                'enabled': layer.enabled
            }
            for layer in active_layers
        ]
    
    def _recompile_shaders(self):
        """Recompile shaders with new effect code."""
        if not self.shader_program:
            return
        
        try:
            from PyQt6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
            
            # Create new shader program
            new_program = QOpenGLShaderProgram()
            
            if not new_program.addShaderFromSourceCode(
                QOpenGLShader.ShaderTypeBit.Vertex, self.vertex_shader_source
            ):
                print(f"Vertex shader recompilation failed: {new_program.log()}")
                return
            
            if not new_program.addShaderFromSourceCode(
                QOpenGLShader.ShaderTypeBit.Fragment, self.fragment_shader_source
            ):
                print(f"Fragment shader recompilation failed: {new_program.log()}")
                return
            
            if not new_program.link():
                print(f"Shader program relinking failed: {new_program.log()}")
                return
            
            # Replace old program
            self.shader_program = new_program
            
        except Exception as e:
            print(f"Shader recompilation failed: {e}")
    
    def apply_effects(self, effects: Optional[Dict[str, Any]] = None):
        """Apply visual effects to the shader using the effects manager."""
        if not self.shader_program:
            return
        
        # Get uniforms from effects manager
        uniforms = self.effects_manager.get_effect_uniforms()
        
        # Add time uniform for animations
        uniforms['time'] = self.current_time
        
        # Apply uniforms to shader
        for uniform_name, value in uniforms.items():
            try:
                if isinstance(value, bool):
                    self.shader_program.setUniformValue(uniform_name, value)
                elif isinstance(value, (int, float)):
                    self.shader_program.setUniformValue(uniform_name, float(value))
                elif isinstance(value, (list, tuple)) and len(value) == 2:
                    self.shader_program.setUniformValue(uniform_name, float(value[0]), float(value[1]))
                elif isinstance(value, (list, tuple)) and len(value) == 3:
                    self.shader_program.setUniformValue(uniform_name, float(value[0]), float(value[1]), float(value[2]))
                elif isinstance(value, (list, tuple)) and len(value) == 4:
                    self.shader_program.setUniformValue(uniform_name, float(value[0]), float(value[1]), float(value[2]), float(value[3]))
            except Exception as e:
                print(f"Failed to set uniform {uniform_name}: {e}")
            
    def render_subtitles_batch(self, subtitles: List[SubtitleLine], styles: Dict[str, SubtitleStyle],
                              viewport_size: Tuple[int, int], current_time: float,
                              projection_matrix: np.ndarray, effects: Optional[Dict[str, Any]] = None) -> List[RenderedSubtitle]:
        """
        Render multiple subtitles efficiently in a batch.
        
        Args:
            subtitles: List of subtitle lines to render
            styles: Dictionary of available styles
            viewport_size: Current viewport dimensions
            current_time: Current playback time
            projection_matrix: 4x4 projection matrix
            effects: Optional effects parameters
            
        Returns:
            List of rendered subtitles that are currently visible
        """
        rendered_subtitles = []
        
        for subtitle in subtitles:
            # Get style for this subtitle
            style = styles.get(subtitle.style, styles.get('Default'))
            if not style:
                continue
            
            # Render subtitle
            rendered = self.render_subtitle(subtitle, style, viewport_size, current_time)
            if rendered:
                rendered_subtitles.append(rendered)
        
        return rendered_subtitles
    
    def cleanup(self):
        """Clean up OpenGL resources."""
        if self.texture_cache:
            self.texture_cache.clear()
        
        if self.shader_program:
            self.shader_program = None
        
        if self.vertex_buffer:
            try:
                import OpenGL.GL as gl
                gl.glDeleteBuffers(1, [self.vertex_buffer])
            except:
                pass
            self.vertex_buffer = None
        
        if self.index_buffer:
            try:
                import OpenGL.GL as gl
                gl.glDeleteBuffers(1, [self.index_buffer])
            except:
                pass
            self.index_buffer = None
        
        self.initialized = False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        return {
            'cache_size': len(self.texture_cache.textures),
            'cache_max_size': self.texture_cache.max_size,
            'initialized': self.initialized,
            'shader_program_valid': self.shader_program is not None
        }


if __name__ == "__main__":
    print("Testing OpenGL Subtitle Renderer...")
    renderer = OpenGLSubtitleRenderer()
    print("Renderer created successfully")
    print("Performance stats:", renderer.get_performance_stats())