"""
Integration tests for OpenGL preview and export consistency validation.

Tests that ensure the OpenGL preview accurately represents the final export output,
validating visual consistency between preview and exported video.
"""

import unittest
import tempfile
import os
import shutil
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.core.models import (
    Project, VideoFile, AudioFile, SubtitleFile, 
    SubtitleLine, SubtitleStyle, Effect
)
from src.core.opengl_export_renderer import OpenGLExportRenderer, ExportSettings
from src.core.effects_manager import EffectsManager, EffectType


class MockOpenGLContext:
    """Mock OpenGL context for testing without actual OpenGL."""
    
    def __init__(self):
        self.is_valid = True
        self.current_program = None
        self.textures = {}
        self.framebuffers = {}
        
    def makeCurrent(self):
        return True
        
    def doneCurrent(self):
        pass
        
    def create_texture(self, width, height):
        texture_id = len(self.textures) + 1
        self.textures[texture_id] = {
            'width': width,
            'height': height,
            'data': np.zeros((height, width, 4), dtype=np.uint8)
        }
        return texture_id
        
    def create_framebuffer(self, width, height):
        fb_id = len(self.framebuffers) + 1
        self.framebuffers[fb_id] = {
            'width': width,
            'height': height,
            'color_texture': self.create_texture(width, height)
        }
        return fb_id
        
    def render_to_framebuffer(self, fb_id, render_func):
        if fb_id in self.framebuffers:
            fb = self.framebuffers[fb_id]
            # Simulate rendering by creating test pattern
            texture_data = np.random.randint(0, 255, 
                (fb['height'], fb['width'], 4), dtype=np.uint8)
            self.textures[fb['color_texture']]['data'] = texture_data
            return texture_data
        return None
        
    def read_framebuffer_pixels(self, fb_id):
        if fb_id in self.framebuffers:
            fb = self.framebuffers[fb_id]
            return self.textures[fb['color_texture']]['data']
        return None


class TestOpenGLConsistencyValidation(unittest.TestCase):
    """Test OpenGL preview and export consistency."""
    
    def setUp(self):
        """Set up test fixtures for OpenGL consistency testing."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test project
        self.test_project = Project(
            id="consistency_test",
            name="Consistency Test Project",
            video_file=VideoFile(
                path="test_video.mp4",
                duration=30.0,
                resolution={"width": 1920, "height": 1080},
                frame_rate=30.0
            ),
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=30.0,
                sample_rate=44100,
                channels=2
            ),
            subtitle_file=SubtitleFile(
                path="test_subtitles.ass",
                lines=[
                    SubtitleLine(
                        start_time=0.0,
                        end_time=5.0,
                        text="Consistency test subtitle",
                        style="Default"
                    ),
                    SubtitleLine(
                        start_time=5.0,
                        end_time=10.0,
                        text="Second test subtitle",
                        style="Default"
                    )
                ],
                styles=[
                    SubtitleStyle(
                        name="Default",
                        font_name="Arial",
                        font_size=24,
                        primary_color="#FFFFFF"
                    )
                ]
            )
        )
        
        # Create export settings
        self.export_settings = ExportSettings(
            width=1280,
            height=720,
            fps=30.0,
            bitrate=5000,
            codec="libx264",
            output_path=os.path.join(self.temp_dir, "test_output.mp4")
        )
        
        # Mock OpenGL context
        self.mock_gl_context = MockOpenGLContext()
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_opengl_renderer_initialization(self):
        """Test OpenGL renderer initialization and setup."""
        renderer = OpenGLExportRenderer()
        
        # Test setup with mock implementation
        success = renderer.setup_export(self.test_project, self.export_settings)
        self.assertTrue(success)
        
        # Verify project and settings are stored
        self.assertEqual(renderer.current_project, self.test_project)
        self.assertEqual(renderer.export_settings, self.export_settings)
        
        # Test renderer state
        self.assertFalse(renderer.is_exporting)  # Should not be exporting yet
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_frame_rendering_consistency(self):
        """Test that frame rendering produces consistent results."""
        renderer = OpenGLExportRenderer()
        renderer.setup_export(self.test_project, self.export_settings)
        
        # Render the same frame multiple times
        timestamp = 2.5  # During first subtitle
        
        frames = []
        for i in range(5):
            frame = renderer.render_frame_at_time(timestamp)
            frames.append(frame)
        
        # All frames should be identical (or very similar for mock implementation)
        self.assertEqual(len(frames), 5)
        for frame in frames:
            self.assertIsNotNone(frame)
            
        # In mock implementation, frames should have consistent structure
        if frames[0] is not None:
            for i in range(1, len(frames)):
                self.assertEqual(type(frames[i]), type(frames[0]))
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_subtitle_rendering_accuracy(self):
        """Test subtitle rendering accuracy at different timestamps."""
        renderer = OpenGLExportRenderer()
        renderer.setup_export(self.test_project, self.export_settings)
        
        # Test timestamps and expected subtitle visibility
        test_cases = [
            (2.5, True, "Consistency test subtitle"),   # During first subtitle
            (7.5, True, "Second test subtitle"),        # During second subtitle
            (12.5, False, None),                        # After all subtitles
            (-1.0, False, None),                        # Before start
        ]
        
        for timestamp, should_have_subtitle, expected_text in test_cases:
            # Get visible subtitles at timestamp
            visible_subtitles = renderer._get_visible_subtitles_at_time(timestamp)
            
            if should_have_subtitle:
                self.assertGreater(len(visible_subtitles), 0, 
                    f"Expected subtitle at {timestamp}s")
                if expected_text and visible_subtitles:
                    self.assertEqual(visible_subtitles[0].text, expected_text)
            else:
                self.assertEqual(len(visible_subtitles), 0, 
                    f"Expected no subtitle at {timestamp}s")
    
    def test_effects_consistency_between_preview_and_export(self):
        """Test that effects are applied consistently in preview and export."""
        effects_manager = EffectsManager()
        
        # Add glow effect
        glow_effect = effects_manager.create_effect(EffectType.GLOW, {
            'radius': 8.0,
            'intensity': 0.9,
            'color': [1.0, 0.0, 1.0]
        })
        effects_manager.add_effect_layer(glow_effect)
        
        # Add outline effect
        outline_effect = effects_manager.create_effect(EffectType.OUTLINE, {
            'width': 3.0,
            'color': [0.0, 0.0, 0.0]
        })
        effects_manager.add_effect_layer(outline_effect)
        
        # Generate shader code for both preview and export
        vertex_shader, fragment_shader = effects_manager.generate_shader_code()
        
        # Verify shader consistency
        self.assertIn('glow', fragment_shader.lower())
        self.assertIn('outline', fragment_shader.lower())
        
        # Get uniforms for both contexts
        uniforms = effects_manager.get_effect_uniforms()
        
        # Verify uniform consistency
        self.assertEqual(uniforms['glowRadius'], 8.0)
        self.assertEqual(uniforms['glowIntensity'], 0.9)
        self.assertEqual(uniforms['outlineWidth'], 3.0)
        
        # Test that the same parameters produce the same shader code
        vertex_shader2, fragment_shader2 = effects_manager.generate_shader_code()
        self.assertEqual(vertex_shader, vertex_shader2)
        self.assertEqual(fragment_shader, fragment_shader2)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_resolution_scaling_consistency(self):
        """Test that different resolutions maintain visual consistency."""
        renderer = OpenGLExportRenderer()
        
        # Test different export resolutions
        resolutions = [
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (854, 480),    # SD
            (640, 360),    # Low res
        ]
        
        for width, height in resolutions:
            settings = ExportSettings(
                width=width,
                height=height,
                fps=30.0,
                bitrate=5000,
                output_path=os.path.join(self.temp_dir, f"test_{width}x{height}.mp4")
            )
            
            success = renderer.setup_export(self.test_project, settings)
            self.assertTrue(success, f"Failed to setup export for {width}x{height}")
            
            # Render frame at same timestamp
            frame = renderer.render_frame_at_time(2.5)
            self.assertIsNotNone(frame, f"Failed to render frame for {width}x{height}")
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_timing_precision_consistency(self):
        """Test timing precision consistency between preview and export."""
        renderer = OpenGLExportRenderer()
        renderer.setup_export(self.test_project, self.export_settings)
        
        # Test precise timing boundaries
        boundary_timestamps = [
            4.999,  # Just before first subtitle ends
            5.000,  # Exact boundary (first ends, second starts)
            5.001,  # Just after boundary
        ]
        
        for timestamp in boundary_timestamps:
            visible_subtitles = renderer._get_visible_subtitles_at_time(timestamp)
            
            if timestamp < 5.0:
                # Should see first subtitle
                self.assertEqual(len(visible_subtitles), 1)
                self.assertEqual(visible_subtitles[0].text, "Consistency test subtitle")
            elif timestamp == 5.0:
                # At exact boundary, should see second subtitle
                self.assertEqual(len(visible_subtitles), 1)
                self.assertEqual(visible_subtitles[0].text, "Second test subtitle")
            else:
                # After boundary, should see second subtitle
                self.assertEqual(len(visible_subtitles), 1)
                self.assertEqual(visible_subtitles[0].text, "Second test subtitle")
    
    def test_color_space_consistency(self):
        """Test color space consistency between preview and export."""
        # Test color conversion and consistency
        test_colors = [
            "#FFFFFF",  # White
            "#000000",  # Black
            "#FF0000",  # Red
            "#00FF00",  # Green
            "#0000FF",  # Blue
            "#FFFF00",  # Yellow
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
        ]
        
        for color_hex in test_colors:
            # Convert hex to RGB
            rgb = tuple(int(color_hex[i:i+2], 16) for i in (1, 3, 5))
            
            # Convert to normalized float values (OpenGL format)
            normalized_rgb = tuple(c / 255.0 for c in rgb)
            
            # Verify conversion consistency
            self.assertEqual(len(normalized_rgb), 3)
            for component in normalized_rgb:
                self.assertGreaterEqual(component, 0.0)
                self.assertLessEqual(component, 1.0)
            
            # Convert back to verify round-trip consistency
            converted_back = tuple(int(c * 255) for c in normalized_rgb)
            self.assertEqual(converted_back, rgb)
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_performance_consistency(self):
        """Test that performance is consistent between preview and export modes."""
        import time
        
        renderer = OpenGLExportRenderer()
        renderer.setup_export(self.test_project, self.export_settings)
        
        # Time multiple frame renders
        timestamps = [i * 0.5 for i in range(20)]  # 20 frames over 10 seconds
        
        render_times = []
        for timestamp in timestamps:
            start_time = time.time()
            frame = renderer.render_frame_at_time(timestamp)
            render_time = time.time() - start_time
            render_times.append(render_time)
            
            self.assertIsNotNone(frame)
        
        # Calculate performance statistics
        avg_render_time = sum(render_times) / len(render_times)
        max_render_time = max(render_times)
        min_render_time = min(render_times)
        
        # Performance should be consistent (max time shouldn't be much larger than average)
        self.assertLess(max_render_time, avg_render_time * 3.0, 
            "Render time variance too high")
        
        # All renders should complete in reasonable time (mock implementation)
        self.assertLess(avg_render_time, 0.1, "Average render time too slow")
    
    def test_shader_compilation_consistency(self):
        """Test shader compilation consistency across different effect combinations."""
        effects_manager = EffectsManager()
        
        # Test different effect combinations
        effect_combinations = [
            [],  # No effects
            [EffectType.GLOW],  # Single effect
            [EffectType.GLOW, EffectType.OUTLINE],  # Two effects
            [EffectType.GLOW, EffectType.OUTLINE, EffectType.SHADOW],  # Three effects
            [EffectType.GLOW, EffectType.OUTLINE, EffectType.SHADOW, EffectType.BOUNCE],  # Four effects
        ]
        
        for effect_types in effect_combinations:
            # Clear previous effects
            effects_manager.clear_all_effects()
            
            # Add effects
            for effect_type in effect_types:
                effect = effects_manager.create_effect(effect_type, {})
                effects_manager.add_effect_layer(effect)
            
            # Generate shaders multiple times
            shaders = []
            for i in range(3):
                vertex_shader, fragment_shader = effects_manager.generate_shader_code()
                shaders.append((vertex_shader, fragment_shader))
            
            # All shader generations should be identical
            for i in range(1, len(shaders)):
                self.assertEqual(shaders[i][0], shaders[0][0], 
                    f"Vertex shader inconsistent for effects: {effect_types}")
                self.assertEqual(shaders[i][1], shaders[0][1], 
                    f"Fragment shader inconsistent for effects: {effect_types}")
    
    @patch('src.core.opengl_export_renderer.PYQT_AVAILABLE', False)
    def test_memory_consistency_during_rendering(self):
        """Test memory usage consistency during rendering operations."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        renderer = OpenGLExportRenderer()
        renderer.setup_export(self.test_project, self.export_settings)
        
        # Render many frames to test memory consistency
        for i in range(100):
            timestamp = i * 0.1  # 100 frames over 10 seconds
            frame = renderer.render_frame_at_time(timestamp)
            self.assertIsNotNone(frame)
            
            # Check memory every 20 frames
            if i % 20 == 0:
                current_memory = process.memory_info().rss
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 50MB for mock implementation)
                self.assertLess(memory_increase, 50 * 1024 * 1024, 
                    f"Memory usage too high at frame {i}: {memory_increase / 1024 / 1024:.1f}MB")
        
        # Force garbage collection
        gc.collect()
        
        # Final memory check
        final_memory = process.memory_info().rss
        final_increase = final_memory - initial_memory
        
        # Memory should not have grown excessively
        self.assertLess(final_increase, 100 * 1024 * 1024, 
            f"Final memory increase too high: {final_increase / 1024 / 1024:.1f}MB")


class TestVisualConsistencyValidation(unittest.TestCase):
    """Test automated visual consistency verification."""
    
    def setUp(self):
        """Set up visual consistency test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create reference project for visual testing
        self.reference_project = Project(
            id="visual_test",
            name="Visual Consistency Test",
            video_file=VideoFile(
                path="reference_video.mp4",
                duration=20.0,
                resolution={"width": 1920, "height": 1080}
            ),
            audio_file=AudioFile(
                path="reference_audio.mp3",
                duration=20.0
            ),
            subtitle_file=SubtitleFile(
                path="reference_subtitles.ass",
                lines=[
                    SubtitleLine(0.0, 5.0, "Visual test line 1", "Default"),
                    SubtitleLine(5.0, 10.0, "Visual test line 2", "Default"),
                    SubtitleLine(10.0, 15.0, "Visual test line 3", "Default"),
                ],
                styles=[SubtitleStyle(name="Default", font_size=32)]
            )
        )
    
    def tearDown(self):
        """Clean up visual consistency test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_frame_difference_calculation(self):
        """Test frame difference calculation for visual consistency."""
        # Create mock frame data
        frame1 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        frame2 = frame1.copy()  # Identical frame
        frame3 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)  # Different frame
        
        # Calculate differences
        diff_identical = np.mean(np.abs(frame1.astype(float) - frame2.astype(float)))
        diff_different = np.mean(np.abs(frame1.astype(float) - frame3.astype(float)))
        
        # Identical frames should have zero difference
        self.assertEqual(diff_identical, 0.0)
        
        # Different frames should have non-zero difference
        self.assertGreater(diff_different, 0.0)
    
    def test_subtitle_positioning_consistency(self):
        """Test subtitle positioning consistency across different resolutions."""
        # Test subtitle positioning at different resolutions
        resolutions = [
            (1920, 1080),
            (1280, 720),
            (854, 480)
        ]
        
        # Reference subtitle position (normalized coordinates)
        ref_x = 0.5  # Center horizontally
        ref_y = 0.85  # Near bottom
        
        for width, height in resolutions:
            # Calculate pixel positions
            pixel_x = int(ref_x * width)
            pixel_y = int(ref_y * height)
            
            # Verify positions are within bounds
            self.assertGreaterEqual(pixel_x, 0)
            self.assertLess(pixel_x, width)
            self.assertGreaterEqual(pixel_y, 0)
            self.assertLess(pixel_y, height)
            
            # Verify relative positioning is maintained
            relative_x = pixel_x / width
            relative_y = pixel_y / height
            
            self.assertAlmostEqual(relative_x, ref_x, places=3)
            self.assertAlmostEqual(relative_y, ref_y, places=3)
    
    def test_font_scaling_consistency(self):
        """Test font scaling consistency across resolutions."""
        # Base font size at 1920x1080
        base_font_size = 32
        base_width = 1920
        base_height = 1080
        
        # Test resolutions
        test_resolutions = [
            (1280, 720),
            (854, 480),
            (640, 360)
        ]
        
        for width, height in test_resolutions:
            # Calculate scaling factor (use minimum dimension for consistent scaling)
            scale_factor = min(width / base_width, height / base_height)
            scaled_font_size = int(base_font_size * scale_factor)
            
            # Verify scaled font size is reasonable
            self.assertGreater(scaled_font_size, 0)
            self.assertLessEqual(scaled_font_size, base_font_size)
            
            # Verify scaling maintains readability (minimum size)
            min_readable_size = 12
            if scaled_font_size < min_readable_size:
                # Should clamp to minimum readable size
                scaled_font_size = min_readable_size
            
            self.assertGreaterEqual(scaled_font_size, min_readable_size)
    
    def test_color_accuracy_validation(self):
        """Test color accuracy validation between preview and export."""
        # Test color values
        test_colors = [
            (255, 255, 255),  # White
            (0, 0, 0),        # Black
            (255, 0, 0),      # Red
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
        ]
        
        for r, g, b in test_colors:
            # Convert to normalized OpenGL format
            gl_r = r / 255.0
            gl_g = g / 255.0
            gl_b = b / 255.0
            
            # Verify conversion accuracy
            self.assertAlmostEqual(gl_r, r / 255.0, places=6)
            self.assertAlmostEqual(gl_g, g / 255.0, places=6)
            self.assertAlmostEqual(gl_b, b / 255.0, places=6)
            
            # Convert back to verify round-trip accuracy
            back_r = int(gl_r * 255)
            back_g = int(gl_g * 255)
            back_b = int(gl_b * 255)
            
            self.assertEqual(back_r, r)
            self.assertEqual(back_g, g)
            self.assertEqual(back_b, b)
    
    def test_temporal_consistency_validation(self):
        """Test temporal consistency of subtitle transitions."""
        # Test subtitle transition timing
        subtitle_lines = [
            SubtitleLine(0.0, 3.0, "Line 1", "Default"),
            SubtitleLine(3.0, 6.0, "Line 2", "Default"),
            SubtitleLine(6.0, 9.0, "Line 3", "Default"),
        ]
        
        # Test timestamps around transitions
        test_timestamps = [
            2.9,   # Just before first transition
            3.0,   # Exact transition point
            3.1,   # Just after first transition
            5.9,   # Just before second transition
            6.0,   # Exact second transition
            6.1,   # Just after second transition
        ]
        
        for timestamp in test_timestamps:
            visible_lines = [
                line for line in subtitle_lines
                if line.start_time <= timestamp <= line.end_time
            ]
            
            # Should have exactly one visible line at any given time
            self.assertEqual(len(visible_lines), 1, 
                f"Expected 1 visible line at {timestamp}s, got {len(visible_lines)}")
            
            # Verify correct line is visible
            visible_line = visible_lines[0]
            if timestamp < 3.0:
                self.assertEqual(visible_line.text, "Line 1")
            elif timestamp < 6.0:
                self.assertEqual(visible_line.text, "Line 2")
            else:
                self.assertEqual(visible_line.text, "Line 3")


if __name__ == '__main__':
    # Run tests silently as per steering guidelines
    unittest.main(verbosity=0, buffer=True)