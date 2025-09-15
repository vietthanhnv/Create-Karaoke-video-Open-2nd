"""
Unit tests for the Visual Effects Shader System

Tests shader compilation, caching, effect parameter application,
and all visual effects including glow/bloom, particle systems,
text animations, color transitions, and background blur.
"""

import unittest
import tempfile
import shutil
import os
import numpy as np
from unittest.mock import patch, MagicMock

# Import the shader system
from src.core.shader_system import (
    VisualEffectsShaderSystem,
    ShaderProgram,
    ShaderSource,
    ShaderCache,
    EffectType,
    GlowBloomParameters,
    ParticleSystemParameters,
    TextAnimationParameters,
    ColorTransitionParameters,
    BackgroundBlurParameters,
    create_shader_system,
    create_identity_matrix,
    create_orthographic_matrix
)


class TestShaderSource(unittest.TestCase):
    """Test shader source container"""
    
    def test_shader_source_creation(self):
        """Test shader source creation"""
        vertex = "vertex shader code"
        fragment = "fragment shader code"
        geometry = "geometry shader code"
        defines = {"TEST": "1"}
        
        source = ShaderSource(vertex, fragment, geometry, defines)
        
        self.assertEqual(source.vertex_source, vertex)
        self.assertEqual(source.fragment_source, fragment)
        self.assertEqual(source.geometry_source, geometry)
        self.assertEqual(source.defines, defines)
    
    def test_shader_source_defaults(self):
        """Test shader source with defaults"""
        vertex = "vertex shader code"
        fragment = "fragment shader code"
        
        source = ShaderSource(vertex, fragment)
        
        self.assertEqual(source.vertex_source, vertex)
        self.assertEqual(source.fragment_source, fragment)
        self.assertIsNone(source.geometry_source)
        self.assertEqual(source.defines, {})


class TestEffectParameters(unittest.TestCase):
    """Test effect parameter classes"""
    
    def test_glow_bloom_parameters(self):
        """Test glow/bloom parameters"""
        params = GlowBloomParameters(
            intensity=2.0,
            radius=10.0,
            threshold=0.9,
            color=(1.0, 0.5, 0.0),
            blur_passes=5
        )
        
        self.assertEqual(params.intensity, 2.0)
        self.assertEqual(params.radius, 10.0)
        self.assertEqual(params.threshold, 0.9)
        self.assertEqual(params.color, (1.0, 0.5, 0.0))
        self.assertEqual(params.blur_passes, 5)
    
    def test_particle_system_parameters(self):
        """Test particle system parameters"""
        params = ParticleSystemParameters(
            count=200,
            size=3.0,
            lifetime=1.5,
            velocity=(10.0, 20.0),
            gravity=(0.0, -10.0),
            color_start=(1.0, 1.0, 1.0, 1.0),
            color_end=(1.0, 0.0, 0.0, 0.0),
            spawn_rate=100.0
        )
        
        self.assertEqual(params.count, 200)
        self.assertEqual(params.size, 3.0)
        self.assertEqual(params.lifetime, 1.5)
        self.assertEqual(params.velocity, (10.0, 20.0))
        self.assertEqual(params.gravity, (0.0, -10.0))
        self.assertEqual(params.color_start, (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(params.color_end, (1.0, 0.0, 0.0, 0.0))
        self.assertEqual(params.spawn_rate, 100.0)
    
    def test_text_animation_parameters(self):
        """Test text animation parameters"""
        params = TextAnimationParameters(
            scale_factor=1.5,
            rotation_angle=45.0,
            fade_alpha=0.8,
            translation=(10.0, 20.0),
            animation_time=2.0,
            scale_animation=True,
            rotation_animation=False,
            fade_animation=True
        )
        
        self.assertEqual(params.scale_factor, 1.5)
        self.assertEqual(params.rotation_angle, 45.0)
        self.assertEqual(params.fade_alpha, 0.8)
        self.assertEqual(params.translation, (10.0, 20.0))
        self.assertEqual(params.animation_time, 2.0)
        self.assertTrue(params.scale_animation)
        self.assertFalse(params.rotation_animation)
        self.assertTrue(params.fade_animation)
    
    def test_color_transition_parameters(self):
        """Test color transition parameters"""
        params = ColorTransitionParameters(
            start_color=(1.0, 0.0, 0.0, 1.0),
            end_color=(0.0, 1.0, 0.0, 1.0),
            progress=0.5,
            transition_type="ease_in_out"
        )
        
        self.assertEqual(params.start_color, (1.0, 0.0, 0.0, 1.0))
        self.assertEqual(params.end_color, (0.0, 1.0, 0.0, 1.0))
        self.assertEqual(params.progress, 0.5)
        self.assertEqual(params.transition_type, "ease_in_out")
    
    def test_background_blur_parameters(self):
        """Test background blur parameters"""
        params = BackgroundBlurParameters(
            blur_radius=8.0,
            blur_intensity=0.7,
            blur_passes=3,
            focus_point=(0.3, 0.7),
            focus_radius=0.2
        )
        
        self.assertEqual(params.blur_radius, 8.0)
        self.assertEqual(params.blur_intensity, 0.7)
        self.assertEqual(params.blur_passes, 3)
        self.assertEqual(params.focus_point, (0.3, 0.7))
        self.assertEqual(params.focus_radius, 0.2)


class TestShaderProgram(unittest.TestCase):
    """Test shader program functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.vertex_source = """
        #version 330 core
        layout (location = 0) in vec3 a_position;
        uniform mat4 u_mvp_matrix;
        void main() {
            gl_Position = u_mvp_matrix * vec4(a_position, 1.0);
        }
        """
        
        self.fragment_source = """
        #version 330 core
        out vec4 frag_color;
        uniform vec4 u_color;
        void main() {
            frag_color = u_color;
        }
        """
    
    def test_mock_shader_program_creation(self):
        """Test mock shader program creation"""
        sources = ShaderSource(self.vertex_source, self.fragment_source)
        program = ShaderProgram("test_program", sources, mock_mode=True)
        
        self.assertTrue(program.is_valid)
        self.assertGreater(program.program_id, 0)
        self.assertIn('u_mvp_matrix', program.uniforms)
        self.assertIn('u_texture', program.uniforms)
    
    def test_shader_program_uniform_operations(self):
        """Test shader program uniform operations"""
        sources = ShaderSource(self.vertex_source, self.fragment_source)
        program = ShaderProgram("test_program", sources, mock_mode=True)
        
        # Test uniform existence
        self.assertTrue(program.has_uniform('u_mvp_matrix'))
        self.assertFalse(program.has_uniform('nonexistent_uniform'))
        
        # Test uniform location
        location = program.get_uniform_location('u_mvp_matrix')
        self.assertGreaterEqual(location, 0)
        
        # Test setting uniforms (should not raise exceptions in mock mode)
        program.use()
        program.set_uniform_float('u_time', 1.0)
        program.set_uniform_vec2('u_resolution', (1920.0, 1080.0))
        program.set_uniform_vec3('u_color', (1.0, 0.5, 0.0))
        program.set_uniform_vec4('u_color4', (1.0, 0.5, 0.0, 1.0))
        program.set_uniform_int('u_texture', 0)
        
        matrix = create_identity_matrix()
        program.set_uniform_matrix4('u_mvp_matrix', matrix)
    
    def test_shader_program_destruction(self):
        """Test shader program destruction"""
        sources = ShaderSource(self.vertex_source, self.fragment_source)
        program = ShaderProgram("test_program", sources, mock_mode=True)
        
        self.assertTrue(program.is_valid)
        
        program.destroy()
        
        self.assertFalse(program.is_valid)
        self.assertEqual(program.program_id, 0)
        self.assertEqual(len(program.uniforms), 0)


class TestShaderCache(unittest.TestCase):
    """Test shader caching system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache = ShaderCache(self.temp_dir)
        
        self.vertex_source = "vertex shader code"
        self.fragment_source = "fragment shader code"
        self.sources = ShaderSource(self.vertex_source, self.fragment_source)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cache_directory_creation(self):
        """Test cache directory creation"""
        self.assertTrue(os.path.exists(self.temp_dir))
        self.assertTrue(os.path.isdir(self.temp_dir))
    
    def test_shader_hash_computation(self):
        """Test shader hash computation"""
        hash1 = self.cache._compute_hash(self.sources)
        hash2 = self.cache._compute_hash(self.sources)
        
        # Same sources should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different sources should produce different hash
        different_sources = ShaderSource("different vertex", "different fragment")
        hash3 = self.cache._compute_hash(different_sources)
        self.assertNotEqual(hash1, hash3)
    
    def test_cache_operations(self):
        """Test cache operations"""
        program_name = "test_program"
        
        # Initially no cached program
        cached_hash = self.cache.get_cached_program(program_name, self.sources)
        self.assertIsNone(cached_hash)
        
        # Create mock program and cache it
        program = ShaderProgram(program_name, self.sources, mock_mode=True)
        self.cache.cache_program(program_name, self.sources, program)
        
        # Now should find cached program
        cached_hash = self.cache.get_cached_program(program_name, self.sources)
        self.assertIsNotNone(cached_hash)
    
    def test_cache_persistence(self):
        """Test cache persistence across instances"""
        program_name = "test_program"
        
        # Cache a program
        program = ShaderProgram(program_name, self.sources, mock_mode=True)
        self.cache.cache_program(program_name, self.sources, program)
        
        # Create new cache instance
        new_cache = ShaderCache(self.temp_dir)
        
        # Should find cached program
        cached_hash = new_cache.get_cached_program(program_name, self.sources)
        self.assertIsNotNone(cached_hash)
    
    def test_cache_clearing(self):
        """Test cache clearing"""
        program_name = "test_program"
        
        # Cache a program
        program = ShaderProgram(program_name, self.sources, mock_mode=True)
        self.cache.cache_program(program_name, self.sources, program)
        
        # Verify cached
        cached_hash = self.cache.get_cached_program(program_name, self.sources)
        self.assertIsNotNone(cached_hash)
        
        # Clear cache
        self.cache.clear_cache()
        
        # Should no longer be cached
        cached_hash = self.cache.get_cached_program(program_name, self.sources)
        self.assertIsNone(cached_hash)


class TestVisualEffectsShaderSystem(unittest.TestCase):
    """Test complete visual effects shader system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.shader_system = VisualEffectsShaderSystem(self.temp_dir, mock_mode=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.shader_system.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_builtin_shaders_creation(self):
        """Test built-in shaders are created"""
        expected_shaders = [
            EffectType.GLOW_BLOOM.value,
            EffectType.PARTICLE_SYSTEM.value,
            EffectType.TEXT_ANIMATION.value,
            EffectType.COLOR_TRANSITION.value,
            EffectType.BACKGROUND_BLUR.value,
            EffectType.BASIC_TEXTURE.value
        ]
        
        program_names = self.shader_system.get_program_names()
        
        for shader_name in expected_shaders:
            self.assertIn(shader_name, program_names)
    
    def test_program_retrieval(self):
        """Test program retrieval"""
        # Test existing program
        program = self.shader_system.get_program(EffectType.GLOW_BLOOM.value)
        self.assertIsNotNone(program)
        self.assertTrue(program.is_valid)
        
        # Test non-existing program
        program = self.shader_system.get_program("nonexistent_program")
        self.assertIsNone(program)
    
    def test_program_usage(self):
        """Test program usage"""
        # Test using existing program
        success = self.shader_system.use_program(EffectType.GLOW_BLOOM.value)
        self.assertTrue(success)
        
        # Test using non-existing program
        success = self.shader_system.use_program("nonexistent_program")
        self.assertFalse(success)
    
    def test_glow_bloom_effect_application(self):
        """Test glow/bloom effect parameter application"""
        params = GlowBloomParameters(
            intensity=2.0,
            radius=10.0,
            threshold=0.9,
            color=(1.0, 0.8, 0.6),
            blur_passes=4
        )
        
        # Should not raise exception
        self.shader_system.apply_glow_bloom_effect(EffectType.GLOW_BLOOM.value, params)
    
    def test_particle_system_effect_application(self):
        """Test particle system effect parameter application"""
        params = ParticleSystemParameters(
            count=150,
            size=2.5,
            lifetime=2.0,
            velocity=(5.0, 15.0),
            gravity=(0.0, -9.8),
            color_start=(1.0, 1.0, 1.0, 1.0),
            color_end=(1.0, 0.0, 0.0, 0.0),
            spawn_rate=75.0
        )
        
        # Should not raise exception
        self.shader_system.apply_particle_system_effect(EffectType.PARTICLE_SYSTEM.value, params)
    
    def test_text_animation_effect_application(self):
        """Test text animation effect parameter application"""
        params = TextAnimationParameters(
            scale_factor=1.2,
            rotation_angle=30.0,
            fade_alpha=0.9,
            translation=(5.0, 10.0),
            animation_time=1.5
        )
        
        # Should not raise exception
        self.shader_system.apply_text_animation_effect(EffectType.TEXT_ANIMATION.value, params)
    
    def test_color_transition_effect_application(self):
        """Test color transition effect parameter application"""
        params = ColorTransitionParameters(
            start_color=(1.0, 0.0, 0.0, 1.0),
            end_color=(0.0, 1.0, 0.0, 1.0),
            progress=0.7,
            transition_type="ease_out"
        )
        
        # Should not raise exception
        self.shader_system.apply_color_transition_effect(EffectType.COLOR_TRANSITION.value, params)
    
    def test_background_blur_effect_application(self):
        """Test background blur effect parameter application"""
        params = BackgroundBlurParameters(
            blur_radius=6.0,
            blur_intensity=0.8,
            blur_passes=2,
            focus_point=(0.4, 0.6),
            focus_radius=0.25
        )
        
        # Should not raise exception
        self.shader_system.apply_background_blur_effect(EffectType.BACKGROUND_BLUR.value, params)
    
    def test_common_uniforms_setting(self):
        """Test setting common uniforms"""
        mvp_matrix = create_identity_matrix()
        resolution = (1920.0, 1080.0)
        time = 5.0
        
        # Should not raise exception
        self.shader_system.set_common_uniforms(
            EffectType.GLOW_BLOOM.value, mvp_matrix, resolution, time
        )
    
    def test_custom_program_creation(self):
        """Test custom program creation"""
        vertex_source = """
        #version 330 core
        layout (location = 0) in vec3 a_position;
        void main() {
            gl_Position = vec4(a_position, 1.0);
        }
        """
        
        fragment_source = """
        #version 330 core
        out vec4 frag_color;
        void main() {
            frag_color = vec4(1.0, 0.0, 0.0, 1.0);
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        program = self.shader_system.create_program("custom_program", sources)
        
        self.assertIsNotNone(program)
        self.assertTrue(program.is_valid)
        self.assertIn("custom_program", self.shader_system.get_program_names())
    
    def test_program_validation(self):
        """Test program validation"""
        validation_results = self.shader_system.validate_programs()
        
        # All built-in programs should be valid
        for program_name, is_valid in validation_results.items():
            self.assertTrue(is_valid, f"Program {program_name} should be valid")
    
    def test_program_reloading(self):
        """Test program reloading"""
        program_name = EffectType.GLOW_BLOOM.value
        
        # Program should exist
        self.assertIsNotNone(self.shader_system.get_program(program_name))
        
        # Reload should succeed
        success = self.shader_system.reload_program(program_name)
        self.assertTrue(success)
        
        # Program should still exist and be valid
        program = self.shader_system.get_program(program_name)
        self.assertIsNotNone(program)
        self.assertTrue(program.is_valid)
        
        # Reloading non-existent program should fail
        success = self.shader_system.reload_program("nonexistent_program")
        self.assertFalse(success)
    
    def test_effect_parameter_edge_cases(self):
        """Test effect parameters with edge case values"""
        # Test with extreme values
        extreme_glow_params = GlowBloomParameters(
            intensity=0.0,
            radius=0.1,
            threshold=1.0,
            color=(0.0, 0.0, 0.0),
            blur_passes=1
        )
        
        # Should handle extreme values without crashing
        self.shader_system.apply_glow_bloom_effect(EffectType.GLOW_BLOOM.value, extreme_glow_params)
        
        # Test with maximum values
        max_particle_params = ParticleSystemParameters(
            count=10000,
            size=100.0,
            lifetime=1000.0,
            velocity=(1000.0, 1000.0),
            gravity=(100.0, -100.0),
            spawn_rate=10000.0
        )
        
        # Should handle maximum values without crashing
        self.shader_system.apply_particle_system_effect(EffectType.PARTICLE_SYSTEM.value, max_particle_params)
    
    def test_shader_system_cleanup(self):
        """Test shader system cleanup"""
        # Verify programs exist before cleanup
        self.assertGreater(len(self.shader_system.get_program_names()), 0)
        
        # Cleanup
        self.shader_system.cleanup()
        
        # Verify programs are cleaned up
        self.assertEqual(len(self.shader_system.get_program_names()), 0)


class TestMatrixUtilities(unittest.TestCase):
    """Test matrix utility functions"""
    
    def test_identity_matrix_creation(self):
        """Test identity matrix creation"""
        matrix = create_identity_matrix()
        
        self.assertEqual(matrix.shape, (4, 4))
        self.assertEqual(matrix.dtype, np.float32)
        
        # Check identity matrix properties
        expected = np.eye(4, dtype=np.float32)
        np.testing.assert_array_equal(matrix, expected)
    
    def test_orthographic_matrix_creation(self):
        """Test orthographic projection matrix creation"""
        left, right = -10.0, 10.0
        bottom, top = -5.0, 5.0
        near, far = -1.0, 1.0
        
        matrix = create_orthographic_matrix(left, right, bottom, top, near, far)
        
        self.assertEqual(matrix.shape, (4, 4))
        self.assertEqual(matrix.dtype, np.float32)
        
        # Check specific matrix elements
        self.assertAlmostEqual(matrix[0, 0], 2.0 / (right - left))
        self.assertAlmostEqual(matrix[1, 1], 2.0 / (top - bottom))
        self.assertAlmostEqual(matrix[2, 2], -2.0 / (far - near))
        self.assertAlmostEqual(matrix[3, 3], 1.0)
    
    def test_orthographic_matrix_with_defaults(self):
        """Test orthographic matrix with default near/far values"""
        matrix = create_orthographic_matrix(-1.0, 1.0, -1.0, 1.0)
        
        self.assertEqual(matrix.shape, (4, 4))
        self.assertEqual(matrix.dtype, np.float32)
        
        # Should create valid orthographic matrix
        self.assertAlmostEqual(matrix[0, 0], 1.0)
        self.assertAlmostEqual(matrix[1, 1], 1.0)
        self.assertAlmostEqual(matrix[3, 3], 1.0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_shader_system(self):
        """Test shader system creation convenience function"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Test with mock mode
            shader_system = create_shader_system(temp_dir, mock_mode=True)
            
            self.assertIsInstance(shader_system, VisualEffectsShaderSystem)
            self.assertGreater(len(shader_system.get_program_names()), 0)
            
            shader_system.cleanup()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestShaderSystemIntegration(unittest.TestCase):
    """Integration tests for shader system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.shader_system = create_shader_system(self.temp_dir, mock_mode=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.shader_system.cleanup()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_complete_effect_workflow(self):
        """Test complete effect application workflow"""
        # Set up common uniforms
        mvp_matrix = create_orthographic_matrix(-1.0, 1.0, -1.0, 1.0)
        resolution = (1920.0, 1080.0)
        time = 2.5
        
        # Apply glow effect
        glow_params = GlowBloomParameters(intensity=1.5, radius=8.0, color=(1.0, 0.8, 0.6))
        self.shader_system.use_program(EffectType.GLOW_BLOOM.value)
        self.shader_system.set_common_uniforms(EffectType.GLOW_BLOOM.value, mvp_matrix, resolution, time)
        self.shader_system.apply_glow_bloom_effect(EffectType.GLOW_BLOOM.value, glow_params)
        
        # Apply particle effect
        particle_params = ParticleSystemParameters(count=100, size=2.0, lifetime=1.5)
        self.shader_system.use_program(EffectType.PARTICLE_SYSTEM.value)
        self.shader_system.set_common_uniforms(EffectType.PARTICLE_SYSTEM.value, mvp_matrix, resolution, time)
        self.shader_system.apply_particle_system_effect(EffectType.PARTICLE_SYSTEM.value, particle_params)
        
        # Apply text animation
        text_params = TextAnimationParameters(scale_factor=1.2, rotation_angle=15.0, fade_alpha=0.9)
        self.shader_system.use_program(EffectType.TEXT_ANIMATION.value)
        self.shader_system.set_common_uniforms(EffectType.TEXT_ANIMATION.value, mvp_matrix, resolution, time)
        self.shader_system.apply_text_animation_effect(EffectType.TEXT_ANIMATION.value, text_params)
        
        # Apply color transition
        color_params = ColorTransitionParameters(
            start_color=(1.0, 0.0, 0.0, 1.0),
            end_color=(0.0, 1.0, 0.0, 1.0),
            progress=0.6,
            transition_type="ease_in_out"
        )
        self.shader_system.use_program(EffectType.COLOR_TRANSITION.value)
        self.shader_system.set_common_uniforms(EffectType.COLOR_TRANSITION.value, mvp_matrix, resolution, time)
        self.shader_system.apply_color_transition_effect(EffectType.COLOR_TRANSITION.value, color_params)
        
        # Apply background blur
        blur_params = BackgroundBlurParameters(blur_radius=5.0, blur_intensity=0.7, focus_point=(0.5, 0.5))
        self.shader_system.use_program(EffectType.BACKGROUND_BLUR.value)
        self.shader_system.set_common_uniforms(EffectType.BACKGROUND_BLUR.value, mvp_matrix, resolution, time)
        self.shader_system.apply_background_blur_effect(EffectType.BACKGROUND_BLUR.value, blur_params)
        
        # Verify all programs are still valid
        validation_results = self.shader_system.validate_programs()
        for program_name, is_valid in validation_results.items():
            self.assertTrue(is_valid, f"Program {program_name} should remain valid after use")
    
    def test_shader_caching_integration(self):
        """Test shader caching integration"""
        # Create custom shader
        vertex_source = """
        #version 330 core
        layout (location = 0) in vec3 a_position;
        uniform mat4 u_transform;
        void main() {
            gl_Position = u_transform * vec4(a_position, 1.0);
        }
        """
        
        fragment_source = """
        #version 330 core
        out vec4 frag_color;
        uniform vec3 u_color;
        void main() {
            frag_color = vec4(u_color, 1.0);
        }
        """
        
        sources = ShaderSource(vertex_source, fragment_source)
        program_name = "cached_test_program"
        
        # Create program (should cache it)
        program1 = self.shader_system.create_program(program_name, sources)
        self.assertIsNotNone(program1)
        
        # Create new shader system instance
        shader_system2 = create_shader_system(self.temp_dir, mock_mode=True)
        
        # Create same program again (should use cache)
        program2 = shader_system2.create_program(program_name, sources)
        self.assertIsNotNone(program2)
        
        shader_system2.cleanup()
    
    def test_error_handling(self):
        """Test error handling in shader system"""
        # Test applying effects to non-existent programs
        glow_params = GlowBloomParameters()
        
        # Should not raise exception when program doesn't exist
        self.shader_system.apply_glow_bloom_effect("nonexistent_program", glow_params)
        
        # Test setting uniforms on non-existent programs
        matrix = create_identity_matrix()
        self.shader_system.set_common_uniforms("nonexistent_program", matrix, (1920.0, 1080.0))


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)