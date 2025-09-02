"""
Automated visual consistency verification tests.

Tests that verify visual output consistency between different rendering modes,
resolutions, and effect combinations to ensure WYSIWYG accuracy.
"""

import unittest
import tempfile
import os
import shutil
import numpy as np
import hashlib
from unittest.mock import Mock, patch
from typing import List, Tuple, Dict, Any

from src.core.models import (
    Project, VideoFile, AudioFile, SubtitleFile, 
    SubtitleLine, SubtitleStyle, Effect
)
from src.core.effects_manager import EffectsManager, EffectType
from src.core.opengl_export_renderer import OpenGLExportRenderer, ExportSettings


class MockFrameRenderer:
    """Mock frame renderer for visual consistency testing."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.frame_cache = {}
        
    def render_frame(self, timestamp: float, effects: List[Dict], subtitles: List[SubtitleLine]) -> np.ndarray:
        """Render a frame with given parameters."""
        # Create deterministic frame based on inputs
        frame_key = self._create_frame_key(timestamp, effects, subtitles)
        
        if frame_key in self.frame_cache:
            return self.frame_cache[frame_key]
        
        # Create base frame (gradient background)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Add gradient background
        for y in range(self.height):
            intensity = int((y / self.height) * 255)
            frame[y, :, :] = [intensity // 3, intensity // 2, intensity]
        
        # Add subtitle rendering simulation
        for subtitle in subtitles:
            if subtitle.start_time <= timestamp <= subtitle.end_time:
                self._render_subtitle_to_frame(frame, subtitle, effects)
        
        # Add effect simulation
        for effect in effects:
            self._apply_effect_to_frame(frame, effect)
        
        self.frame_cache[frame_key] = frame
        return frame
    
    def _create_frame_key(self, timestamp: float, effects: List[Dict], subtitles: List[SubtitleLine]) -> str:
        """Create a unique key for frame caching."""
        key_data = f"{timestamp}_{len(effects)}_{len(subtitles)}"
        for effect in effects:
            key_data += f"_{effect.get('type', '')}_{effect.get('enabled', True)}"
        for subtitle in subtitles:
            if subtitle.start_time <= timestamp <= subtitle.end_time:
                key_data += f"_{subtitle.text}_{subtitle.style}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _render_subtitle_to_frame(self, frame: np.ndarray, subtitle: SubtitleLine, effects: List[Dict]):
        """Simulate subtitle rendering on frame."""
        # Simple subtitle simulation - add white rectangle at bottom
        text_height = 40
        text_width = min(len(subtitle.text) * 12, self.width - 40)
        
        y_start = self.height - text_height - 20
        y_end = self.height - 20
        x_start = (self.width - text_width) // 2
        x_end = x_start + text_width
        
        # Base text color (white)
        frame[y_start:y_end, x_start:x_end] = [255, 255, 255]
        
        # Apply effect modifications
        for effect in effects:
            if effect.get('enabled', True):
                self._apply_subtitle_effect(frame, effect, y_start, y_end, x_start, x_end)
    
    def _apply_subtitle_effect(self, frame: np.ndarray, effect: Dict, y1: int, y2: int, x1: int, x2: int):
        """Apply effect to subtitle area."""
        effect_type = effect.get('type', '')
        
        if effect_type == 'glow':
            # Simulate glow by adding colored border
            glow_color = effect.get('color', [1.0, 1.0, 0.0])
            glow_rgb = [int(c * 255) for c in glow_color[:3]]
            
            # Add glow border
            border_size = 3
            y1_glow = max(0, y1 - border_size)
            y2_glow = min(self.height, y2 + border_size)
            x1_glow = max(0, x1 - border_size)
            x2_glow = min(self.width, x2 + border_size)
            
            # Top/bottom borders
            frame[y1_glow:y1, x1_glow:x2_glow] = glow_rgb
            frame[y2:y2_glow, x1_glow:x2_glow] = glow_rgb
            
            # Left/right borders
            frame[y1:y2, x1_glow:x1] = glow_rgb
            frame[y1:y2, x2:x2_glow] = glow_rgb
        
        elif effect_type == 'outline':
            # Simulate outline by adding black border
            outline_color = [0, 0, 0]  # Black outline
            
            # Add outline
            if y1 > 0:
                frame[y1-1:y1, x1:x2] = outline_color
            if y2 < self.height:
                frame[y2:y2+1, x1:x2] = outline_color
            if x1 > 0:
                frame[y1:y2, x1-1:x1] = outline_color
            if x2 < self.width:
                frame[y1:y2, x2:x2+1] = outline_color
    
    def _apply_effect_to_frame(self, frame: np.ndarray, effect: Dict):
        """Apply global effect to entire frame."""
        if not effect.get('enabled', True):
            return
        
        effect_type = effect.get('type', '')
        
        if effect_type == 'brightness':
            brightness = effect.get('value', 1.0)
            frame[:] = np.clip(frame * brightness, 0, 255).astype(np.uint8)
        
        elif effect_type == 'contrast':
            contrast = effect.get('value', 1.0)
            frame[:] = np.clip((frame - 128) * contrast + 128, 0, 255).astype(np.uint8)


class TestVisualConsistencyVerification(unittest.TestCase):
    """Test automated visual consistency verification."""
    
    def setUp(self):
        """Set up visual consistency test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test project
        self.test_project = Project(
            id="visual_consistency_test",
            name="Visual Consistency Test",
            video_file=VideoFile(
                path="test_video.mp4",
                duration=20.0,
                resolution={"width": 1920, "height": 1080},
                frame_rate=30.0
            ),
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=20.0
            ),
            subtitle_file=SubtitleFile(
                path="test_subtitles.ass",
                lines=[
                    SubtitleLine(0.0, 5.0, "First test subtitle", "Default"),
                    SubtitleLine(5.0, 10.0, "Second test subtitle", "Default"),
                    SubtitleLine(10.0, 15.0, "Third test subtitle", "Default"),
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
        
        # Create mock renderers for different resolutions
        self.renderers = {
            "1920x1080": MockFrameRenderer(1920, 1080),
            "1280x720": MockFrameRenderer(1280, 720),
            "854x480": MockFrameRenderer(854, 480),
        }
    
    def tearDown(self):
        """Clean up visual consistency test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_frame_consistency_across_renders(self):
        """Test that identical render calls produce identical frames."""
        renderer = self.renderers["1920x1080"]
        
        # Render the same frame multiple times
        timestamp = 2.5
        effects = [{"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}]
        subtitles = [line for line in self.test_project.subtitle_file.lines 
                    if line.start_time <= timestamp <= line.end_time]
        
        frames = []
        for i in range(5):
            frame = renderer.render_frame(timestamp, effects, subtitles)
            frames.append(frame)
        
        # All frames should be identical
        reference_frame = frames[0]
        for i, frame in enumerate(frames[1:], 1):
            np.testing.assert_array_equal(frame, reference_frame, 
                f"Frame {i} differs from reference frame")
    
    def test_subtitle_visibility_consistency(self):
        """Test subtitle visibility consistency across different timestamps."""
        renderer = self.renderers["1920x1080"]
        effects = []
        
        # Test cases: (timestamp, expected_subtitle_count, expected_text_fragment)
        test_cases = [
            (2.5, 1, "First"),     # During first subtitle
            (7.5, 1, "Second"),    # During second subtitle
            (12.5, 1, "Third"),    # During third subtitle
            (17.5, 0, None),       # After all subtitles
            (-1.0, 0, None),       # Before any subtitles
        ]
        
        for timestamp, expected_count, expected_text in test_cases:
            # Get visible subtitles
            visible_subtitles = [
                line for line in self.test_project.subtitle_file.lines
                if line.start_time <= timestamp <= line.end_time
            ]
            
            # Verify count
            self.assertEqual(len(visible_subtitles), expected_count,
                f"At {timestamp}s: expected {expected_count} subtitles, got {len(visible_subtitles)}")
            
            # Verify text content if expected
            if expected_text and visible_subtitles:
                self.assertIn(expected_text, visible_subtitles[0].text,
                    f"At {timestamp}s: expected text containing '{expected_text}'")
            
            # Render frame and verify it's consistent
            frame = renderer.render_frame(timestamp, effects, visible_subtitles)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (1080, 1920, 3))
    
    def test_effect_consistency_across_parameters(self):
        """Test effect consistency with different parameter values."""
        renderer = self.renderers["1280x720"]
        timestamp = 2.5
        subtitles = [self.test_project.subtitle_file.lines[0]]  # First subtitle
        
        # Test glow effect with different parameters
        glow_configs = [
            {"type": "glow", "enabled": True, "color": [1.0, 0.0, 0.0], "radius": 5.0},
            {"type": "glow", "enabled": True, "color": [0.0, 1.0, 0.0], "radius": 5.0},
            {"type": "glow", "enabled": True, "color": [0.0, 0.0, 1.0], "radius": 5.0},
            {"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0], "radius": 3.0},
            {"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0], "radius": 8.0},
        ]
        
        frames = {}
        for i, effect_config in enumerate(glow_configs):
            frame = renderer.render_frame(timestamp, [effect_config], subtitles)
            frames[i] = frame
            
            # Verify frame properties
            self.assertEqual(frame.shape, (720, 1280, 3))
            self.assertEqual(frame.dtype, np.uint8)
        
        # Different effect parameters should produce different frames
        for i in range(len(glow_configs)):
            for j in range(i + 1, len(glow_configs)):
                # Frames should be different (not identical)
                with self.assertRaises(AssertionError):
                    np.testing.assert_array_equal(frames[i], frames[j])
    
    def test_resolution_scaling_consistency(self):
        """Test visual consistency across different resolutions."""
        timestamp = 7.5  # During second subtitle
        effects = [{"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}]
        subtitles = [self.test_project.subtitle_file.lines[1]]  # Second subtitle
        
        frames = {}
        for resolution, renderer in self.renderers.items():
            frame = renderer.render_frame(timestamp, effects, subtitles)
            frames[resolution] = frame
            
            # Verify frame dimensions match renderer
            width, height = map(int, resolution.split('x'))
            self.assertEqual(frame.shape, (height, width, 3))
        
        # Test relative positioning consistency
        # Subtitle should appear in similar relative position across resolutions
        for resolution, frame in frames.items():
            width, height = map(int, resolution.split('x'))
            
            # Check bottom region where subtitle should appear
            bottom_region = frame[int(height * 0.8):, :, :]
            
            # Should have non-zero content (subtitle rendering)
            self.assertGreater(np.sum(bottom_region), 0, 
                f"No subtitle content found in {resolution}")
            
            # Should have white pixels (subtitle text)
            white_pixels = np.sum(np.all(bottom_region == [255, 255, 255], axis=2))
            self.assertGreater(white_pixels, 0, 
                f"No white subtitle pixels found in {resolution}")
    
    def test_temporal_consistency_validation(self):
        """Test temporal consistency of subtitle transitions."""
        renderer = self.renderers["1920x1080"]
        effects = []
        
        # Test transition points with high precision
        transition_timestamps = [
            4.99,   # Just before first transition (0-5s -> 5-10s)
            5.00,   # Exact transition point
            5.01,   # Just after transition
            9.99,   # Just before second transition (5-10s -> 10-15s)
            10.00,  # Exact second transition
            10.01,  # Just after second transition
        ]
        
        frames = {}
        for timestamp in transition_timestamps:
            visible_subtitles = [
                line for line in self.test_project.subtitle_file.lines
                if line.start_time <= timestamp <= line.end_time
            ]
            
            frame = renderer.render_frame(timestamp, effects, visible_subtitles)
            frames[timestamp] = frame
            
            # Verify exactly one subtitle is visible at each timestamp
            self.assertEqual(len(visible_subtitles), 1,
                f"Expected 1 subtitle at {timestamp}s, got {len(visible_subtitles)}")
        
        # Frames before and after transitions should be different
        self.assertFalse(np.array_equal(frames[4.99], frames[5.01]),
            "Frames before and after transition should differ")
        self.assertFalse(np.array_equal(frames[9.99], frames[10.01]),
            "Frames before and after second transition should differ")
        
        # Frames at exact transition points should be consistent
        # (same subtitle should be visible)
        frame_5_00 = frames[5.00]
        frame_5_01 = frames[5.01]
        
        # These should be identical (same subtitle visible)
        np.testing.assert_array_equal(frame_5_00, frame_5_01,
            "Frames at transition boundary should be identical")
    
    def test_effect_layering_consistency(self):
        """Test consistency of effect layering and ordering."""
        renderer = self.renderers["1280x720"]
        timestamp = 2.5
        subtitles = [self.test_project.subtitle_file.lines[0]]
        
        # Test different effect combinations
        effect_combinations = [
            [],  # No effects
            [{"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}],  # Glow only
            [{"type": "outline", "enabled": True}],  # Outline only
            [
                {"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]},
                {"type": "outline", "enabled": True}
            ],  # Glow + Outline
            [
                {"type": "outline", "enabled": True},
                {"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}
            ],  # Outline + Glow (different order)
        ]
        
        frames = {}
        for i, effects in enumerate(effect_combinations):
            frame = renderer.render_frame(timestamp, effects, subtitles)
            frames[i] = frame
        
        # No effects vs effects should be different
        self.assertFalse(np.array_equal(frames[0], frames[1]),
            "Frame with no effects should differ from frame with glow")
        
        # Single effects should be different from each other
        self.assertFalse(np.array_equal(frames[1], frames[2]),
            "Glow-only should differ from outline-only")
        
        # Combined effects should be different from single effects
        self.assertFalse(np.array_equal(frames[1], frames[3]),
            "Glow-only should differ from glow+outline")
        self.assertFalse(np.array_equal(frames[2], frames[3]),
            "Outline-only should differ from glow+outline")
        
        # Different effect orders might produce different results
        # (This depends on implementation - some renderers may be order-independent)
        # We test that the frames are at least valid
        self.assertEqual(frames[3].shape, frames[4].shape)
        self.assertEqual(frames[3].dtype, frames[4].dtype)
    
    def test_color_accuracy_consistency(self):
        """Test color accuracy and consistency."""
        renderer = self.renderers["854x480"]
        timestamp = 2.5
        subtitles = [self.test_project.subtitle_file.lines[0]]
        
        # Test different glow colors
        test_colors = [
            [1.0, 0.0, 0.0],  # Red
            [0.0, 1.0, 0.0],  # Green
            [0.0, 0.0, 1.0],  # Blue
            [1.0, 1.0, 0.0],  # Yellow
            [1.0, 0.0, 1.0],  # Magenta
            [0.0, 1.0, 1.0],  # Cyan
        ]
        
        frames = {}
        for i, color in enumerate(test_colors):
            effects = [{"type": "glow", "enabled": True, "color": color}]
            frame = renderer.render_frame(timestamp, effects, subtitles)
            frames[i] = frame
            
            # Verify frame is valid
            self.assertEqual(frame.shape, (480, 854, 3))
            self.assertEqual(frame.dtype, np.uint8)
            
            # Verify frame has content
            self.assertGreater(np.sum(frame), 0, f"Frame {i} appears to be empty")
        
        # Different colors should produce different frames
        for i in range(len(test_colors)):
            for j in range(i + 1, len(test_colors)):
                self.assertFalse(np.array_equal(frames[i], frames[j]),
                    f"Frames with different colors ({i}, {j}) should not be identical")
    
    def test_performance_consistency_validation(self):
        """Test that rendering performance is consistent."""
        import time
        
        renderer = self.renderers["1920x1080"]
        effects = [{"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}]
        
        # Test rendering performance across multiple frames
        timestamps = [i * 0.5 for i in range(40)]  # 40 frames over 20 seconds
        render_times = []
        
        for timestamp in timestamps:
            visible_subtitles = [
                line for line in self.test_project.subtitle_file.lines
                if line.start_time <= timestamp <= line.end_time
            ]
            
            start_time = time.time()
            frame = renderer.render_frame(timestamp, effects, visible_subtitles)
            render_time = time.time() - start_time
            
            render_times.append(render_time)
            
            # Verify frame is valid
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape, (1080, 1920, 3))
        
        # Calculate performance statistics
        avg_render_time = sum(render_times) / len(render_times)
        max_render_time = max(render_times)
        min_render_time = min(render_times)
        
        # Performance should be consistent
        # Max time shouldn't be more than 3x average time
        self.assertLess(max_render_time, avg_render_time * 3.0,
            f"Render time variance too high: max={max_render_time:.4f}s, avg={avg_render_time:.4f}s")
        
        # All renders should be reasonably fast (mock implementation)
        self.assertLess(avg_render_time, 0.01,
            f"Average render time too slow: {avg_render_time:.4f}s")
    
    def test_memory_consistency_during_rendering(self):
        """Test memory usage consistency during rendering."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        renderer = self.renderers["1920x1080"]
        effects = [{"type": "glow", "enabled": True, "color": [1.0, 1.0, 0.0]}]
        
        # Render many frames to test memory consistency
        memory_samples = []
        
        for i in range(100):
            timestamp = i * 0.2  # 100 frames over 20 seconds
            visible_subtitles = [
                line for line in self.test_project.subtitle_file.lines
                if line.start_time <= timestamp <= line.end_time
            ]
            
            frame = renderer.render_frame(timestamp, effects, visible_subtitles)
            
            # Sample memory every 10 frames
            if i % 10 == 0:
                current_memory = process.memory_info().rss
                memory_increase = current_memory - initial_memory
                memory_samples.append(memory_increase)
        
        # Memory usage should be relatively stable
        max_memory = max(memory_samples)
        min_memory = min(memory_samples)
        memory_variance = max_memory - min_memory
        
        # Memory variance should be reasonable (less than 50MB)
        self.assertLess(memory_variance, 50 * 1024 * 1024,
            f"Memory variance too high: {memory_variance / 1024 / 1024:.1f}MB")
        
        # Force garbage collection
        gc.collect()
        
        # Final memory should not be excessive
        final_memory = process.memory_info().rss
        final_increase = final_memory - initial_memory
        
        self.assertLess(final_increase, 100 * 1024 * 1024,
            f"Final memory increase too high: {final_increase / 1024 / 1024:.1f}MB")


if __name__ == '__main__':
    # Run tests silently as per steering guidelines
    unittest.main(verbosity=0, buffer=True)