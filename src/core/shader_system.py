"""
OpenGL Shader System for Visual Effects

This module provides a comprehensive shader compilation, caching, and management system
for advanced visual effects including glow/bloom, particle systems, text animations,
color transitions, and background blur effects.
"""

import os
import hashlib
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenGL libraries
try:
    import OpenGL.GL as gl
    import OpenGL.GL.shaders as shaders
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    logger.warning("OpenGL not available, using mock implementation")


class ShaderType(Enum):
    """Shader types"""
    VERTEX = gl.GL_VERTEX_SHADER if OPENGL_AVAILABLE else 0x8B31
    FRAGMENT = gl.GL_FRAGMENT_SHADER if OPENGL_AVAILABLE else 0x8B30
    GEOMETRY = gl.GL_GEOMETRY_SHADER if OPENGL_AVAILABLE else 0x8DD9


class EffectType(Enum):
    """Visual effect types"""
    GLOW_BLOOM = "glow_bloom"
    PARTICLE_SYSTEM = "particle_system"
    TEXT_ANIMATION = "text_animation"
    COLOR_TRANSITION = "color_transition"
    BACKGROUND_BLUR = "background_blur"
    BASIC_TEXTURE = "basic_texture"


@dataclass
class ShaderSource:
    """Shader source code container"""
    vertex_source: str
    fragment_source: str
    geometry_source: Optional[str] = None
    defines: Dict[str, str] = None
    
    def __post_init__(self):
        if self.defines is None:
            self.defines = {}


@dataclass
class UniformInfo:
    """Uniform variable information"""
    name: str
    location: int
    type: int
    size: int


@dataclass
class EffectParameters:
    """Base class for effect parameters"""
    pass


@dataclass
class GlowBloomParameters(EffectParameters):
    """Glow/bloom effect parameters"""
    intensity: float = 1.0
    radius: float = 5.0
    threshold: float = 0.8
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    blur_passes: int = 3


@dataclass
class ParticleSystemParameters(EffectParameters):
    """Particle system parameters"""
    count: int = 100
    size: float = 2.0
    lifetime: float = 2.0
    velocity: Tuple[float, float] = (0.0, 50.0)
    gravity: Tuple[float, float] = (0.0, -9.8)
    color_start: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    color_end: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.0)
    spawn_rate: float = 50.0


@dataclass
class TextAnimationParameters(EffectParameters):
    """Text animation parameters"""
    scale_factor: float = 1.0
    rotation_angle: float = 0.0
    fade_alpha: float = 1.0
    translation: Tuple[float, float] = (0.0, 0.0)
    animation_time: float = 0.0
    scale_animation: bool = True
    rotation_animation: bool = True
    fade_animation: bool = True


@dataclass
class ColorTransitionParameters(EffectParameters):
    """Color transition parameters"""
    start_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    end_color: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0)
    progress: float = 0.0
    transition_type: str = "linear"  # linear, ease_in, ease_out, ease_in_out


@dataclass
class BackgroundBlurParameters(EffectParameters):
    """Background blur parameters"""
    blur_radius: float = 5.0
    blur_intensity: float = 1.0
    blur_passes: int = 2
    focus_point: Tuple[float, float] = (0.5, 0.5)
    focus_radius: float = 0.3


class ShaderProgram:
    """OpenGL shader program wrapper"""
    
    def __init__(self, name: str, sources: ShaderSource, mock_mode: bool = False):
        self.name = name
        self.sources = sources
        self.program_id = 0
        self.uniforms: Dict[str, UniformInfo] = {}
        self.is_valid = False
        self.mock_mode = mock_mode
        
        if OPENGL_AVAILABLE and not mock_mode:
            self._compile_and_link()
        elif mock_mode:
            self._create_mock_program()
    
    def _compile_and_link(self):
        """Compile shaders and link program"""
        try:
            # Compile vertex shader
            vertex_shader = self._compile_shader(
                self.sources.vertex_source, ShaderType.VERTEX
            )
            
            # Compile fragment shader
            fragment_shader = self._compile_shader(
                self.sources.fragment_source, ShaderType.FRAGMENT
            )
            
            # Compile geometry shader if present
            geometry_shader = None
            if self.sources.geometry_source:
                geometry_shader = self._compile_shader(
                    self.sources.geometry_source, ShaderType.GEOMETRY
                )
            
            # Create and link program
            self.program_id = gl.glCreateProgram()
            gl.glAttachShader(self.program_id, vertex_shader)
            gl.glAttachShader(self.program_id, fragment_shader)
            
            if geometry_shader:
                gl.glAttachShader(self.program_id, geometry_shader)
            
            gl.glLinkProgram(self.program_id)
            
            # Check link status
            link_status = gl.glGetProgramiv(self.program_id, gl.GL_LINK_STATUS)
            if not link_status:
                error_log = gl.glGetProgramInfoLog(self.program_id).decode('utf-8')
                raise RuntimeError(f"Shader program linking failed: {error_log}")
            
            # Clean up individual shaders
            gl.glDeleteShader(vertex_shader)
            gl.glDeleteShader(fragment_shader)
            if geometry_shader:
                gl.glDeleteShader(geometry_shader)
            
            # Query uniforms
            self._query_uniforms()
            
            self.is_valid = True
            logger.info(f"Shader program '{self.name}' compiled successfully")
            
        except Exception as e:
            logger.error(f"Failed to compile shader program '{self.name}': {e}")
            if self.program_id:
                gl.glDeleteProgram(self.program_id)
                self.program_id = 0
    
    def _compile_shader(self, source: str, shader_type: ShaderType) -> int:
        """Compile individual shader"""
        # Add defines to source
        processed_source = self._process_source(source)
        
        # Create and compile shader
        shader_id = gl.glCreateShader(shader_type.value)
        gl.glShaderSource(shader_id, processed_source)
        gl.glCompileShader(shader_id)
        
        # Check compilation status
        compile_status = gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS)
        if not compile_status:
            error_log = gl.glGetShaderInfoLog(shader_id).decode('utf-8')
            gl.glDeleteShader(shader_id)
            raise RuntimeError(f"Shader compilation failed: {error_log}")
        
        return shader_id
    
    def _process_source(self, source: str) -> str:
        """Process shader source with defines"""
        lines = source.split('\n')
        processed_lines = []
        
        # Find version directive
        version_line = None
        for i, line in enumerate(lines):
            if line.strip().startswith('#version'):
                version_line = i
                break
        
        # Add version if not present
        if version_line is None:
            processed_lines.append('#version 330 core')
            version_line = 0
        else:
            processed_lines.append(lines[version_line])
        
        # Add defines after version
        for define_name, define_value in self.sources.defines.items():
            processed_lines.append(f'#define {define_name} {define_value}')
        
        # Add remaining source lines
        start_line = version_line + 1 if version_line is not None else 0
        processed_lines.extend(lines[start_line:])
        
        return '\n'.join(processed_lines)
    
    def _query_uniforms(self):
        """Query uniform variables"""
        if not OPENGL_AVAILABLE:
            return
        
        uniform_count = gl.glGetProgramiv(self.program_id, gl.GL_ACTIVE_UNIFORMS)
        
        for i in range(uniform_count):
            name, size, type = gl.glGetActiveUniform(self.program_id, i)
            name = name.decode('utf-8')
            location = gl.glGetUniformLocation(self.program_id, name)
            
            self.uniforms[name] = UniformInfo(
                name=name,
                location=location,
                type=type,
                size=size
            )
    
    def _create_mock_program(self):
        """Create mock program for testing"""
        self.program_id = hash(self.name) % 10000
        self.is_valid = True
        
        # Create mock uniforms based on effect type
        mock_uniforms = {
            'u_mvp_matrix': UniformInfo('u_mvp_matrix', 0, gl.GL_FLOAT_MAT4 if OPENGL_AVAILABLE else 0x8B5C, 1),
            'u_texture': UniformInfo('u_texture', 1, gl.GL_SAMPLER_2D if OPENGL_AVAILABLE else 0x8B5E, 1),
            'u_time': UniformInfo('u_time', 2, gl.GL_FLOAT if OPENGL_AVAILABLE else 0x1406, 1),
            'u_resolution': UniformInfo('u_resolution', 3, gl.GL_FLOAT_VEC2 if OPENGL_AVAILABLE else 0x8B50, 1),
        }
        
        self.uniforms = mock_uniforms
        logger.info(f"Mock shader program '{self.name}' created")
    
    def use(self):
        """Use this shader program"""
        if OPENGL_AVAILABLE and not self.mock_mode and self.is_valid:
            gl.glUseProgram(self.program_id)
        elif self.mock_mode and self.is_valid:
            logger.debug(f"Mock use shader program '{self.name}'")
    
    def set_uniform_float(self, name: str, value: float):
        """Set float uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniform1f(location, value)
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = {value}")
    
    def set_uniform_vec2(self, name: str, value: Tuple[float, float]):
        """Set vec2 uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniform2f(location, value[0], value[1])
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = {value}")
    
    def set_uniform_vec3(self, name: str, value: Tuple[float, float, float]):
        """Set vec3 uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniform3f(location, value[0], value[1], value[2])
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = {value}")
    
    def set_uniform_vec4(self, name: str, value: Tuple[float, float, float, float]):
        """Set vec4 uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniform4f(location, value[0], value[1], value[2], value[3])
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = {value}")
    
    def set_uniform_matrix4(self, name: str, matrix: np.ndarray):
        """Set mat4 uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniformMatrix4fv(location, 1, gl.GL_FALSE, matrix.astype(np.float32))
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = matrix")
    
    def set_uniform_int(self, name: str, value: int):
        """Set int uniform"""
        if name not in self.uniforms:
            return
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            location = self.uniforms[name].location
            gl.glUniform1i(location, value)
        elif self.mock_mode:
            logger.debug(f"Mock set uniform {name} = {value}")
    
    def has_uniform(self, name: str) -> bool:
        """Check if uniform exists"""
        return name in self.uniforms
    
    def get_uniform_location(self, name: str) -> int:
        """Get uniform location"""
        if name in self.uniforms:
            return self.uniforms[name].location
        return -1
    
    def destroy(self):
        """Destroy shader program"""
        if OPENGL_AVAILABLE and not self.mock_mode and self.program_id:
            gl.glDeleteProgram(self.program_id)
        
        self.program_id = 0
        self.is_valid = False
        self.uniforms.clear()


class ShaderCache:
    """Shader compilation cache system"""
    
    def __init__(self, cache_dir: str = "temp/shader_cache"):
        self.cache_dir = cache_dir
        self.cache_index_file = os.path.join(cache_dir, "cache_index.json")
        self.cache_index: Dict[str, Dict[str, Any]] = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load cache index
        self._load_cache_index()
    
    def _load_cache_index(self):
        """Load cache index from disk"""
        try:
            if os.path.exists(self.cache_index_file):
                with open(self.cache_index_file, 'r') as f:
                    self.cache_index = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load shader cache index: {e}")
            self.cache_index = {}
    
    def _save_cache_index(self):
        """Save cache index to disk"""
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save shader cache index: {e}")
    
    def _compute_hash(self, sources: ShaderSource) -> str:
        """Compute hash for shader sources"""
        content = f"{sources.vertex_source}{sources.fragment_source}"
        if sources.geometry_source:
            content += sources.geometry_source
        content += str(sorted(sources.defines.items()))
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cached_program(self, name: str, sources: ShaderSource) -> Optional[str]:
        """Get cached shader program hash"""
        shader_hash = self._compute_hash(sources)
        
        if name in self.cache_index:
            cache_entry = self.cache_index[name]
            if cache_entry.get('hash') == shader_hash:
                return shader_hash
        
        return None
    
    def cache_program(self, name: str, sources: ShaderSource, program: ShaderProgram):
        """Cache compiled shader program"""
        shader_hash = self._compute_hash(sources)
        
        # Store cache entry
        self.cache_index[name] = {
            'hash': shader_hash,
            'uniforms': {name: asdict(info) for name, info in program.uniforms.items()},
            'timestamp': os.path.getmtime(__file__)  # Use current time
        }
        
        # Save cache index
        self._save_cache_index()
        
        logger.debug(f"Cached shader program '{name}' with hash {shader_hash[:8]}")
    
    def clear_cache(self):
        """Clear shader cache"""
        try:
            if os.path.exists(self.cache_dir):
                import shutil
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
            
            self.cache_index = {}
            logger.info("Shader cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear shader cache: {e}")


class VisualEffectsShaderSystem:
    """Complete visual effects shader system"""
    
    def __init__(self, cache_dir: str = "temp/shader_cache", mock_mode: bool = False):
        self.programs: Dict[str, ShaderProgram] = {}
        self.cache = ShaderCache(cache_dir)
        self.mock_mode = mock_mode
        
        # Initialize built-in shaders
        self._initialize_builtin_shaders()
    
    def _initialize_builtin_shaders(self):
        """Initialize built-in effect shaders"""
        # Create all built-in effect shaders
        self._create_glow_bloom_shader()
        self._create_particle_system_shader()
        self._create_text_animation_shader()
        self._create_color_transition_shader()
        self._create_background_blur_shader()
        self._create_basic_texture_shader()
    
    def _create_glow_bloom_shader(self):
        """Create glow/bloom effect shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        
        uniform mat4 u_mvp_matrix;
        
        out vec2 v_texcoord;
        
        void main() {
            gl_Position = u_mvp_matrix * vec4(a_position, 1.0);
            v_texcoord = a_texcoord;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        out vec4 frag_color;
        
        uniform sampler2D u_texture;
        uniform float u_intensity;
        uniform float u_radius;
        uniform float u_threshold;
        uniform vec3 u_glow_color;
        uniform vec2 u_resolution;
        uniform int u_blur_passes;
        
        vec4 gaussian_blur(sampler2D tex, vec2 uv, vec2 resolution, float radius) {
            vec4 color = vec4(0.0);
            float total_weight = 0.0;
            
            float blur_size = radius / resolution.x;
            
            for (int x = -int(radius); x <= int(radius); x++) {
                for (int y = -int(radius); y <= int(radius); y++) {
                    vec2 offset = vec2(float(x), float(y)) * blur_size;
                    float weight = exp(-(float(x*x + y*y)) / (2.0 * radius * radius / 4.0));
                    
                    color += texture(tex, uv + offset) * weight;
                    total_weight += weight;
                }
            }
            
            return color / total_weight;
        }
        
        void main() {
            vec4 original = texture(u_texture, v_texcoord);
            
            // Extract bright areas for bloom
            float brightness = dot(original.rgb, vec3(0.299, 0.587, 0.114));
            vec4 bright = brightness > u_threshold ? original : vec4(0.0);
            
            // Apply Gaussian blur for glow effect
            vec4 blurred = gaussian_blur(u_texture, v_texcoord, u_resolution, u_radius);
            
            // Combine original with glow
            vec3 glow = blurred.rgb * u_glow_color * u_intensity;
            vec3 final_color = original.rgb + glow;
            
            frag_color = vec4(final_color, original.a);
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.GLOW_BLOOM.value, sources)
    
    def _create_particle_system_shader(self):
        """Create particle system shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        layout (location = 2) in vec3 a_particle_pos;
        layout (location = 3) in float a_particle_life;
        layout (location = 4) in vec2 a_particle_velocity;
        
        uniform mat4 u_mvp_matrix;
        uniform float u_time;
        uniform float u_particle_size;
        uniform vec2 u_gravity;
        
        out vec2 v_texcoord;
        out float v_life;
        out vec4 v_color;
        
        void main() {
            // Calculate particle position based on physics
            vec3 pos = a_particle_pos;
            float life_progress = 1.0 - a_particle_life;
            
            // Apply velocity and gravity
            pos.xy += a_particle_velocity * u_time * life_progress;
            pos.xy += u_gravity * u_time * u_time * life_progress * 0.5;
            
            // Scale particle based on size
            pos += a_position * u_particle_size;
            
            gl_Position = u_mvp_matrix * vec4(pos, 1.0);
            v_texcoord = a_texcoord;
            v_life = a_particle_life;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        in float v_life;
        out vec4 frag_color;
        
        uniform vec4 u_color_start;
        uniform vec4 u_color_end;
        
        void main() {
            // Create circular particle shape
            float dist = length(v_texcoord - vec2(0.5));
            if (dist > 0.5) discard;
            
            // Interpolate color based on life
            vec4 color = mix(u_color_start, u_color_end, 1.0 - v_life);
            
            // Apply soft edges
            float alpha = 1.0 - smoothstep(0.3, 0.5, dist);
            color.a *= alpha * v_life;
            
            frag_color = color;
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.PARTICLE_SYSTEM.value, sources)
    
    def _create_text_animation_shader(self):
        """Create text animation shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        
        uniform mat4 u_mvp_matrix;
        uniform float u_scale_factor;
        uniform float u_rotation_angle;
        uniform vec2 u_translation;
        uniform float u_animation_time;
        
        out vec2 v_texcoord;
        out float v_animation_progress;
        
        mat4 scale_matrix(float scale) {
            return mat4(
                scale, 0.0, 0.0, 0.0,
                0.0, scale, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0
            );
        }
        
        mat4 rotation_matrix(float angle) {
            float c = cos(angle);
            float s = sin(angle);
            return mat4(
                c, -s, 0.0, 0.0,
                s, c, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                0.0, 0.0, 0.0, 1.0
            );
        }
        
        mat4 translation_matrix(vec2 translation) {
            return mat4(
                1.0, 0.0, 0.0, 0.0,
                0.0, 1.0, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                translation.x, translation.y, 0.0, 1.0
            );
        }
        
        void main() {
            // Apply transformations
            mat4 transform = translation_matrix(u_translation) * 
                           rotation_matrix(u_rotation_angle) * 
                           scale_matrix(u_scale_factor);
            
            gl_Position = u_mvp_matrix * transform * vec4(a_position, 1.0);
            v_texcoord = a_texcoord;
            v_animation_progress = u_animation_time;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        in float v_animation_progress;
        out vec4 frag_color;
        
        uniform sampler2D u_texture;
        uniform float u_fade_alpha;
        
        void main() {
            vec4 color = texture(u_texture, v_texcoord);
            
            // Apply fade animation
            color.a *= u_fade_alpha;
            
            // Apply animation effects based on progress
            float pulse = sin(v_animation_progress * 6.28318) * 0.1 + 0.9;
            color.rgb *= pulse;
            
            frag_color = color;
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.TEXT_ANIMATION.value, sources)
    
    def _create_color_transition_shader(self):
        """Create color transition shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        
        uniform mat4 u_mvp_matrix;
        
        out vec2 v_texcoord;
        
        void main() {
            gl_Position = u_mvp_matrix * vec4(a_position, 1.0);
            v_texcoord = a_texcoord;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        out vec4 frag_color;
        
        uniform sampler2D u_texture;
        uniform vec4 u_start_color;
        uniform vec4 u_end_color;
        uniform float u_progress;
        uniform int u_transition_type; // 0=linear, 1=ease_in, 2=ease_out, 3=ease_in_out
        
        float ease_in(float t) {
            return t * t;
        }
        
        float ease_out(float t) {
            return 1.0 - (1.0 - t) * (1.0 - t);
        }
        
        float ease_in_out(float t) {
            return t < 0.5 ? 2.0 * t * t : 1.0 - pow(-2.0 * t + 2.0, 2.0) / 2.0;
        }
        
        void main() {
            vec4 original = texture(u_texture, v_texcoord);
            
            // Apply transition function
            float t = u_progress;
            if (u_transition_type == 1) {
                t = ease_in(t);
            } else if (u_transition_type == 2) {
                t = ease_out(t);
            } else if (u_transition_type == 3) {
                t = ease_in_out(t);
            }
            
            // Interpolate colors
            vec4 transition_color = mix(u_start_color, u_end_color, t);
            
            // Blend with original texture
            vec4 final_color = original * transition_color;
            
            frag_color = final_color;
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.COLOR_TRANSITION.value, sources)
    
    def _create_background_blur_shader(self):
        """Create background blur shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        
        uniform mat4 u_mvp_matrix;
        
        out vec2 v_texcoord;
        
        void main() {
            gl_Position = u_mvp_matrix * vec4(a_position, 1.0);
            v_texcoord = a_texcoord;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        out vec4 frag_color;
        
        uniform sampler2D u_texture;
        uniform float u_blur_radius;
        uniform float u_blur_intensity;
        uniform vec2 u_focus_point;
        uniform float u_focus_radius;
        uniform vec2 u_resolution;
        
        vec4 gaussian_blur(sampler2D tex, vec2 uv, float radius) {
            vec4 color = vec4(0.0);
            float total_weight = 0.0;
            
            float blur_size = radius / u_resolution.x;
            int samples = int(radius);
            
            for (int x = -samples; x <= samples; x++) {
                for (int y = -samples; y <= samples; y++) {
                    vec2 offset = vec2(float(x), float(y)) * blur_size;
                    float weight = exp(-(float(x*x + y*y)) / (2.0 * radius * radius / 4.0));
                    
                    color += texture(tex, uv + offset) * weight;
                    total_weight += weight;
                }
            }
            
            return color / total_weight;
        }
        
        void main() {
            vec4 original = texture(u_texture, v_texcoord);
            
            // Calculate distance from focus point
            float dist = distance(v_texcoord, u_focus_point);
            
            // Determine blur amount based on distance from focus
            float blur_amount = smoothstep(u_focus_radius, u_focus_radius + 0.2, dist);
            blur_amount *= u_blur_intensity;
            
            if (blur_amount > 0.01) {
                // Apply blur
                vec4 blurred = gaussian_blur(u_texture, v_texcoord, u_blur_radius * blur_amount);
                frag_color = mix(original, blurred, blur_amount);
            } else {
                frag_color = original;
            }
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.BACKGROUND_BLUR.value, sources)
    
    def _create_basic_texture_shader(self):
        """Create basic texture rendering shader"""
        vertex_source = """
        #version 330 core
        
        layout (location = 0) in vec3 a_position;
        layout (location = 1) in vec2 a_texcoord;
        
        uniform mat4 u_mvp_matrix;
        
        out vec2 v_texcoord;
        
        void main() {
            gl_Position = u_mvp_matrix * vec4(a_position, 1.0);
            v_texcoord = a_texcoord;
        }
        """
        
        fragment_source = """
        #version 330 core
        
        in vec2 v_texcoord;
        out vec4 frag_color;
        
        uniform sampler2D u_texture;
        uniform vec4 u_color_multiplier;
        
        void main() {
            vec4 color = texture(u_texture, v_texcoord);
            frag_color = color * u_color_multiplier;
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        self.create_program(EffectType.BASIC_TEXTURE.value, sources)
    
    def create_program(self, name: str, sources: ShaderSource) -> Optional[ShaderProgram]:
        """Create shader program with caching"""
        # Check cache first
        cached_hash = self.cache.get_cached_program(name, sources)
        if cached_hash:
            logger.debug(f"Using cached shader program '{name}'")
        
        # Create program
        program = ShaderProgram(name, sources, self.mock_mode)
        
        if program.is_valid:
            self.programs[name] = program
            
            # Cache the program
            if not cached_hash:
                self.cache.cache_program(name, sources, program)
            
            logger.info(f"Created shader program '{name}'")
            return program
        else:
            logger.error(f"Failed to create shader program '{name}'")
            return None
    
    def get_program(self, name: str) -> Optional[ShaderProgram]:
        """Get shader program by name"""
        return self.programs.get(name)
    
    def use_program(self, name: str) -> bool:
        """Use shader program by name"""
        program = self.get_program(name)
        if program and program.is_valid:
            program.use()
            return True
        return False
    
    def apply_glow_bloom_effect(self, program_name: str, params: GlowBloomParameters):
        """Apply glow/bloom effect parameters"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        program.set_uniform_float('u_intensity', params.intensity)
        program.set_uniform_float('u_radius', params.radius)
        program.set_uniform_float('u_threshold', params.threshold)
        program.set_uniform_vec3('u_glow_color', params.color)
        program.set_uniform_int('u_blur_passes', params.blur_passes)
    
    def apply_particle_system_effect(self, program_name: str, params: ParticleSystemParameters):
        """Apply particle system parameters"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        program.set_uniform_float('u_particle_size', params.size)
        program.set_uniform_vec2('u_gravity', params.gravity)
        program.set_uniform_vec4('u_color_start', params.color_start)
        program.set_uniform_vec4('u_color_end', params.color_end)
    
    def apply_text_animation_effect(self, program_name: str, params: TextAnimationParameters):
        """Apply text animation parameters"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        program.set_uniform_float('u_scale_factor', params.scale_factor)
        program.set_uniform_float('u_rotation_angle', params.rotation_angle)
        program.set_uniform_float('u_fade_alpha', params.fade_alpha)
        program.set_uniform_vec2('u_translation', params.translation)
        program.set_uniform_float('u_animation_time', params.animation_time)
    
    def apply_color_transition_effect(self, program_name: str, params: ColorTransitionParameters):
        """Apply color transition parameters"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        program.set_uniform_vec4('u_start_color', params.start_color)
        program.set_uniform_vec4('u_end_color', params.end_color)
        program.set_uniform_float('u_progress', params.progress)
        
        # Map transition type to integer
        transition_map = {
            'linear': 0,
            'ease_in': 1,
            'ease_out': 2,
            'ease_in_out': 3
        }
        program.set_uniform_int('u_transition_type', transition_map.get(params.transition_type, 0))
    
    def apply_background_blur_effect(self, program_name: str, params: BackgroundBlurParameters):
        """Apply background blur parameters"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        program.set_uniform_float('u_blur_radius', params.blur_radius)
        program.set_uniform_float('u_blur_intensity', params.blur_intensity)
        program.set_uniform_vec2('u_focus_point', params.focus_point)
        program.set_uniform_float('u_focus_radius', params.focus_radius)
    
    def set_common_uniforms(self, program_name: str, mvp_matrix: np.ndarray, 
                          resolution: Tuple[float, float], time: float = 0.0):
        """Set common uniforms used by most shaders"""
        program = self.get_program(program_name)
        if not program:
            return
        
        program.use()
        if program.has_uniform('u_mvp_matrix'):
            program.set_uniform_matrix4('u_mvp_matrix', mvp_matrix)
        if program.has_uniform('u_resolution'):
            program.set_uniform_vec2('u_resolution', resolution)
        if program.has_uniform('u_time'):
            program.set_uniform_float('u_time', time)
    
    def reload_program(self, name: str) -> bool:
        """Reload shader program (useful for development)"""
        if name not in self.programs:
            return False
        
        old_program = self.programs[name]
        sources = old_program.sources
        
        # Destroy old program
        old_program.destroy()
        del self.programs[name]
        
        # Create new program
        new_program = self.create_program(name, sources)
        return new_program is not None
    
    def get_program_names(self) -> List[str]:
        """Get list of available program names"""
        return list(self.programs.keys())
    
    def validate_programs(self) -> Dict[str, bool]:
        """Validate all shader programs"""
        results = {}
        for name, program in self.programs.items():
            results[name] = program.is_valid
        return results
    
    def cleanup(self):
        """Clean up all shader programs"""
        for program in self.programs.values():
            program.destroy()
        
        self.programs.clear()
        logger.info("Shader system cleaned up")


# Convenience functions
def create_shader_system(cache_dir: str = "temp/shader_cache", 
                        mock_mode: bool = False) -> VisualEffectsShaderSystem:
    """Create visual effects shader system"""
    return VisualEffectsShaderSystem(cache_dir, mock_mode)


def create_identity_matrix() -> np.ndarray:
    """Create 4x4 identity matrix"""
    return np.eye(4, dtype=np.float32)


def create_orthographic_matrix(left: float, right: float, bottom: float, top: float,
                             near: float = -1.0, far: float = 1.0) -> np.ndarray:
    """Create orthographic projection matrix"""
    matrix = np.zeros((4, 4), dtype=np.float32)
    
    matrix[0, 0] = 2.0 / (right - left)
    matrix[1, 1] = 2.0 / (top - bottom)
    matrix[2, 2] = -2.0 / (far - near)
    matrix[3, 3] = 1.0
    
    matrix[3, 0] = -(right + left) / (right - left)
    matrix[3, 1] = -(top + bottom) / (top - bottom)
    matrix[3, 2] = -(far + near) / (far - near)
    
    return matrix


if __name__ == "__main__":
    # Test the shader system
    print("Testing Visual Effects Shader System...")
    
    # Create shader system
    shader_system = create_shader_system(mock_mode=True)
    
    # Test program creation
    programs = shader_system.get_program_names()
    print(f"Available programs: {programs}")
    
    # Test effect parameters
    glow_params = GlowBloomParameters(intensity=1.5, radius=8.0, color=(1.0, 0.8, 0.6))
    shader_system.apply_glow_bloom_effect(EffectType.GLOW_BLOOM.value, glow_params)
    
    particle_params = ParticleSystemParameters(count=200, size=3.0, lifetime=1.5)
    shader_system.apply_particle_system_effect(EffectType.PARTICLE_SYSTEM.value, particle_params)
    
    # Test validation
    validation_results = shader_system.validate_programs()
    print(f"Program validation: {validation_results}")
    
    # Cleanup
    shader_system.cleanup()
    print("Shader system test completed")