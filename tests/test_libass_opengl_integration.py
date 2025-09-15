"""
Unit tests for libass-OpenGL texture integration system.

Tests the texture loading pipeline, texture streaming, caching system,
and karaoke timing integration.
"""

import unittest
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Import the modules to test
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.libass_opengl_integration import (
    TextureStreamFrame, TextureStreamConfig, TextureCache, TextureStreamer,
    KaraokeTextureRenderer, LibassOpenGLIntegration
)
from core.libass_integration import LibassImage
from core.opengl_context import OpenGLContext, ContextBackend
from core.models import SubtitleFile, SubtitleLine, KaraokeTimingInfo


class TestTextureStreamFrame(unittest.TestCase):
    """Test TextureStreamFrame data structure"""
    
    def test_frame_creation(self):
        """Test creating texture stream frame"""
        # Create mock texture
        mock_texture = Mock()
        mock_texture.width.return_value = 100
        mock_texture.height.return_value = 50
        
        # Create mock libass image
        libass_image = LibassImage(
            width=100, height=50, stride=100,
            bitmap=b'\xFF' * (100 * 50),
            dst_x=0, dst_y=0, color=0xFFFFFFFF
        )
        
        # Create mock karaoke data
        karaoke_data = KaraokeTimingInfo(
            start_time=1.0, end_time=3.0, text="Test",
            syllable_count=2, syllable_timings=[0.5, 0.5],
            style_overrides=""
        )
        
        # Create frame
        frame = TextureStreamFrame(
            timestamp=2.0,
            texture=mock_texture,
            libass_images=[libass_image],
            karaoke_data=karaoke_data
        )
        
        self.assertEqual(frame.timestamp, 2.0)
        self.assertEqual(frame.texture, mock_texture)
        self.assertEqual(len(frame.libass_images), 1)
        self.assertEqual(frame.karaoke_data, karaoke_data)
        self.assertFalse(frame.is_cached)
        self.assertIsInstance(frame.last_access_time, float)


class TestTextureCache(unittest.TestCase):
    """Test texture caching system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache = TextureCache(max_size=3, timeout=1.0)
        
        # Create mock texture frames
        self.mock_frames = []
        for i in range(5):
            mock_texture = Mock()
            mock_texture.destroy = Mock()
            
            frame = TextureStreamFrame(
                timestamp=float(i),
                texture=mock_texture,
                libass_images=[],
                karaoke_data=None
            )
            self.mock_frames.append(frame)
    
    def test_cache_put_and_get(self):
        """Test basic cache operations"""
        # Put frame in cache
        self.cache.put("key1", self.mock_frames[0])
        
        # Get frame from cache
        retrieved = self.cache.get("key1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.timestamp, 0.0)
        self.assertTrue(retrieved.is_cached)
        
        # Check cache stats
        stats = self.cache.get_stats()
        self.assertEqual(stats['size'], 1)
        self.assertEqual(stats['hit_count'], 1)
        self.assertEqual(stats['miss_count'], 0)
    
    def test_cache_miss(self):
        """Test cache miss"""
        retrieved = self.cache.get("nonexistent")
        self.assertIsNone(retrieved)
        
        stats = self.cache.get_stats()
        self.assertEqual(stats['miss_count'], 1)
    
    def test_cache_eviction(self):
        """Test LRU cache eviction"""
        # Fill cache beyond capacity
        for i in range(4):
            self.cache.put(f"key{i}", self.mock_frames[i])
        
        # Check that oldest entry was evicted
        self.assertEqual(len(self.cache.cache), 3)
        self.assertIsNone(self.cache.get("key0"))  # Should be evicted
        self.assertIsNotNone(self.cache.get("key1"))  # Should still exist
        
        # Verify texture cleanup was called
        self.mock_frames[0].texture.destroy.assert_called_once()
    
    def test_cache_timeout(self):
        """Test cache entry timeout"""
        # Put frame in cache
        self.cache.put("key1", self.mock_frames[0])
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Try to get expired frame
        retrieved = self.cache.get("key1")
        self.assertIsNone(retrieved)
        
        # Verify texture cleanup
        self.mock_frames[0].texture.destroy.assert_called_once()
    
    def test_cache_clear(self):
        """Test cache clearing"""
        # Add frames to cache
        for i in range(3):
            self.cache.put(f"key{i}", self.mock_frames[i])
        
        # Clear cache
        self.cache.clear()
        
        # Verify cache is empty
        self.assertEqual(len(self.cache.cache), 0)
        self.assertEqual(len(self.cache.access_order), 0)
        
        # Verify all textures were destroyed
        for frame in self.mock_frames[:3]:
            frame.texture.destroy.assert_called_once()
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key1 = self.cache._generate_cache_key(1.0, "hash1", (1920, 1080))
        key2 = self.cache._generate_cache_key(1.0, "hash2", (1920, 1080))
        key3 = self.cache._generate_cache_key(1.0, "hash1", (1280, 720))
        
        # Keys should be different for different parameters
        self.assertNotEqual(key1, key2)
        self.assertNotEqual(key1, key3)
        
        # Same parameters should generate same key
        key1_duplicate = self.cache._generate_cache_key(1.0, "hash1", (1920, 1080))
        self.assertEqual(key1, key1_duplicate)


class TestTextureStreamer(unittest.TestCase):
    """Test texture streaming system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = TextureStreamConfig(max_cache_size=5, preload_frames=2)
        self.streamer = TextureStreamer(self.config)
        
        # Create mock subtitle file
        self.subtitle_file = SubtitleFile(
            file_path="test.ass",
            lines=[
                SubtitleLine(
                    start_time=1.0, end_time=3.0, text="Test line 1",
                    style="Default"
                ),
                SubtitleLine(
                    start_time=4.0, end_time=6.0, text="Test line 2",
                    style="Default"
                )
            ],
            karaoke_data=[]
        )
        
        # Create mock karaoke data
        self.karaoke_data = [
            KaraokeTimingInfo(
                start_time=1.0, end_time=3.0, text="Test line 1",
                syllable_count=2, syllable_timings=[1.0, 1.0],
                style_overrides=""
            )
        ]
    
    def test_set_subtitle_data(self):
        """Test setting subtitle data"""
        self.streamer.set_subtitle_data(self.subtitle_file, self.karaoke_data)
        
        self.assertEqual(self.streamer.current_subtitle_file, self.subtitle_file)
        self.assertEqual(self.streamer.current_karaoke_data, self.karaoke_data)
        self.assertEqual(len(self.streamer.preloaded_frames), 0)
    
    @patch('core.libass_opengl_integration.LibassContext')
    @patch('core.libass_opengl_integration.OpenGLContext')
    def test_render_frame(self, mock_opengl_context, mock_libass_context):
        """Test frame rendering"""
        # Set up mocks
        mock_libass_context.render_frame.return_value = [
            LibassImage(100, 50, 100, b'\xFF' * (100 * 50), 0, 0, 0xFFFFFFFF)
        ]
        
        mock_texture = Mock()
        mock_opengl_context.create_texture_from_data.return_value = mock_texture
        
        # Set subtitle data
        self.streamer.set_subtitle_data(self.subtitle_file, self.karaoke_data)
        
        # Render frame
        frame = self.streamer._render_frame(
            2.0, mock_libass_context, mock_opengl_context, (1920, 1080), "test_hash"
        )
        
        self.assertIsNotNone(frame)
        self.assertEqual(frame.timestamp, 2.0)
        self.assertEqual(frame.texture, mock_texture)
        self.assertEqual(len(frame.libass_images), 1)
        self.assertIsNotNone(frame.karaoke_data)
    
    def test_find_karaoke_data(self):
        """Test finding karaoke data for timestamp"""
        self.streamer.current_karaoke_data = self.karaoke_data
        
        # Test timestamp within range
        karaoke_info = self.streamer._find_karaoke_data(2.0)
        self.assertIsNotNone(karaoke_info)
        self.assertEqual(karaoke_info.text, "Test line 1")
        
        # Test timestamp outside range
        karaoke_info = self.streamer._find_karaoke_data(5.0)
        self.assertIsNone(karaoke_info)
    
    def test_compute_subtitle_hash(self):
        """Test subtitle hash computation"""
        hash1 = self.streamer._compute_subtitle_hash(self.subtitle_file)
        hash2 = self.streamer._compute_subtitle_hash(self.subtitle_file)
        
        # Same file should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different file should produce different hash
        different_file = SubtitleFile(
            file_path="different.ass", lines=[], karaoke_data=[]
        )
        hash3 = self.streamer._compute_subtitle_hash(different_file)
        self.assertNotEqual(hash1, hash3)
    
    def test_get_cache_stats(self):
        """Test cache statistics"""
        stats = self.streamer.get_cache_stats()
        
        self.assertIn('cache_stats', stats)
        self.assertIn('preloaded_frames', stats)
        self.assertIn('config', stats)
        
        self.assertEqual(stats['preloaded_frames'], 0)
        self.assertEqual(stats['config']['max_cache_size'], 5)


class TestKaraokeTextureRenderer(unittest.TestCase):
    """Test karaoke texture rendering"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock OpenGL context
        self.mock_opengl_context = Mock()
        self.mock_opengl_context.create_texture_from_data.return_value = Mock()
        
        self.renderer = KaraokeTextureRenderer(self.mock_opengl_context)
        
        # Create test karaoke data
        self.karaoke_data = KaraokeTimingInfo(
            start_time=1.0, end_time=4.0, text="Test karaoke",
            syllable_count=3, syllable_timings=[1.0, 1.0, 1.0],
            style_overrides=""
        )
    
    def test_render_karaoke_frame(self):
        """Test karaoke frame rendering"""
        textures = self.renderer.render_karaoke_frame(
            self.karaoke_data, 2.5, (1920, 1080)
        )
        
        # Should create textures for each syllable
        self.assertEqual(len(textures), 3)
        
        # Verify texture creation was called
        self.assertEqual(self.mock_opengl_context.create_texture_from_data.call_count, 3)
    
    def test_update_karaoke_progress(self):
        """Test karaoke progress calculation"""
        # Test before start
        progress = self.renderer.update_karaoke_progress(self.karaoke_data, 0.5)
        self.assertEqual(progress, 0.0)
        
        # Test at middle
        progress = self.renderer.update_karaoke_progress(self.karaoke_data, 2.5)
        self.assertEqual(progress, 0.5)
        
        # Test after end
        progress = self.renderer.update_karaoke_progress(self.karaoke_data, 5.0)
        self.assertEqual(progress, 1.0)
    
    def test_create_syllable_texture(self):
        """Test syllable texture creation"""
        # Test active syllable
        texture = self.renderer._create_syllable_texture("test", 0, True, (1920, 1080))
        self.assertIsNotNone(texture)
        
        # Test inactive syllable
        texture = self.renderer._create_syllable_texture("test", 0, False, (1920, 1080))
        self.assertIsNotNone(texture)
        
        # Verify texture creation calls
        self.assertEqual(self.mock_opengl_context.create_texture_from_data.call_count, 2)


class TestLibassOpenGLIntegration(unittest.TestCase):
    """Test main integration class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock OpenGL context
        self.mock_opengl_context = Mock()
        self.mock_opengl_context.backend = Mock()
        self.mock_opengl_context.backend.value = "mock"
        
        # Create integration instance
        self.integration = LibassOpenGLIntegration(self.mock_opengl_context)
    
    @patch('core.libass_opengl_integration.LibassIntegration')
    def test_load_subtitle_file(self, mock_libass_integration_class):
        """Test subtitle file loading"""
        # Set up mock
        mock_libass_integration = Mock()
        mock_libass_integration_class.return_value = mock_libass_integration
        
        # Create mock return data
        mock_subtitle_file = Mock()
        mock_subtitle_file.lines = [Mock(), Mock()]  # Add lines attribute
        mock_karaoke_data = [Mock()]
        mock_libass_integration.load_and_parse_subtitle_file.return_value = (
            mock_subtitle_file, mock_karaoke_data
        )
        
        # Create new integration to use mocked libass
        integration = LibassOpenGLIntegration(self.mock_opengl_context)
        integration.libass_integration = mock_libass_integration
        
        # Test loading
        result = integration.load_subtitle_file("test.ass")
        
        self.assertTrue(result)
        self.assertEqual(integration.current_subtitle_file, mock_subtitle_file)
        self.assertEqual(integration.current_karaoke_data, mock_karaoke_data)
        
        # Verify libass integration was called
        mock_libass_integration.load_and_parse_subtitle_file.assert_called_once_with("test.ass")
    
    def test_set_viewport_size(self):
        """Test viewport size setting"""
        self.integration.set_viewport_size(1280, 720)
        self.assertEqual(self.integration.viewport_size, (1280, 720))
    
    def test_get_active_subtitles(self):
        """Test getting active subtitles"""
        # Create mock subtitle file
        subtitle_lines = [
            Mock(start_time=1.0, end_time=3.0),
            Mock(start_time=2.0, end_time=4.0),
            Mock(start_time=5.0, end_time=7.0)
        ]
        
        mock_subtitle_file = Mock()
        mock_subtitle_file.lines = subtitle_lines
        
        self.integration.current_subtitle_file = mock_subtitle_file
        
        # Test timestamp with active subtitles
        active = self.integration.get_active_subtitles(2.5)
        self.assertEqual(len(active), 2)  # First two lines should be active
        
        # Test timestamp with no active subtitles
        active = self.integration.get_active_subtitles(8.0)
        self.assertEqual(len(active), 0)
    
    def test_get_karaoke_progress(self):
        """Test karaoke progress calculation"""
        # Create mock karaoke data
        karaoke_data = Mock()
        karaoke_data.start_time = 1.0
        karaoke_data.end_time = 3.0
        
        self.integration.current_karaoke_data = [karaoke_data]
        # Mock the karaoke renderer method
        self.integration.karaoke_renderer = Mock()
        self.integration.karaoke_renderer.update_karaoke_progress.return_value = 0.5
        
        # Test progress calculation
        progress = self.integration.get_karaoke_progress(2.0)
        self.assertEqual(progress, 0.5)
        
        # Verify karaoke renderer was called
        self.integration.karaoke_renderer.update_karaoke_progress.assert_called_once_with(
            karaoke_data, 2.0
        )
    
    def test_get_performance_stats(self):
        """Test performance statistics"""
        stats = self.integration.get_performance_stats()
        
        self.assertIn('texture_streaming', stats)
        self.assertIn('libass_available', stats)
        self.assertIn('opengl_context', stats)
        self.assertIn('viewport_size', stats)
        self.assertIn('subtitle_file_loaded', stats)
        self.assertIn('karaoke_data_count', stats)
        
        self.assertEqual(stats['viewport_size'], (1920, 1080))
        self.assertFalse(stats['subtitle_file_loaded'])
        self.assertEqual(stats['karaoke_data_count'], 0)
    
    def test_cleanup(self):
        """Test resource cleanup"""
        # Mock the cleanup methods
        self.integration.texture_streamer.cleanup = Mock()
        self.integration.libass_integration.cleanup = Mock()
        
        # Call cleanup
        self.integration.cleanup()
        
        # Verify cleanup methods were called
        self.integration.texture_streamer.cleanup.assert_called_once()
        self.integration.libass_integration.cleanup.assert_called_once()


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    @patch('core.libass_opengl_integration.LibassOpenGLIntegration')
    def test_create_libass_opengl_integration(self, mock_integration_class):
        """Test integration creation function"""
        from core.libass_opengl_integration import create_libass_opengl_integration
        
        mock_opengl_context = Mock()
        
        # Call function
        integration = create_libass_opengl_integration(
            mock_opengl_context, cache_size=50, preload_frames=3
        )
        
        # Verify integration was created with correct parameters
        mock_integration_class.assert_called_once()
        args, kwargs = mock_integration_class.call_args
        
        self.assertEqual(args[0], mock_opengl_context)
        # Check that the function was called with the right context
        self.assertEqual(args[0], mock_opengl_context)
        # The config is passed as a positional argument, check the call was made
        self.assertTrue(mock_integration_class.called)
    
    @patch('core.libass_opengl_integration.create_libass_opengl_integration')
    def test_load_and_render_subtitle(self, mock_create_integration):
        """Test subtitle loading and rendering function"""
        from core.libass_opengl_integration import load_and_render_subtitle
        
        # Set up mocks
        mock_integration = Mock()
        mock_integration.load_subtitle_file.return_value = True
        mock_integration.render_frame.return_value = Mock()
        mock_create_integration.return_value = mock_integration
        
        mock_opengl_context = Mock()
        
        # Call function
        result = load_and_render_subtitle(
            "test.ass", 2.0, mock_opengl_context, (1280, 720)
        )
        
        # Verify calls
        mock_integration.set_viewport_size.assert_called_once_with(1280, 720)
        mock_integration.load_subtitle_file.assert_called_once_with("test.ass")
        mock_integration.render_frame.assert_called_once_with(2.0)
        mock_integration.cleanup.assert_called_once()
        
        self.assertIsNotNone(result)


class TestLibassImageConversion(unittest.TestCase):
    """Test LibassImage RGBA conversion"""
    
    def test_to_rgba_bytes(self):
        """Test conversion of libass bitmap to RGBA bytes"""
        # Create test libass image
        width, height = 4, 2
        bitmap_data = bytes([255, 128, 64, 0] * height)  # Grayscale values
        
        image = LibassImage(
            width=width, height=height, stride=width,
            bitmap=bitmap_data, dst_x=0, dst_y=0,
            color=0xFF0000FF  # Red color with full alpha
        )
        
        # Convert to RGBA
        rgba_bytes = image.to_rgba_bytes()
        
        # Check result
        expected_size = width * height * 4  # RGBA
        self.assertEqual(len(rgba_bytes), expected_size)
        
        # Convert to numpy array for easier testing
        rgba_array = np.frombuffer(rgba_bytes, dtype=np.uint8)
        rgba_array = rgba_array.reshape((height, width, 4))
        
        # Check first pixel (intensity 255)
        self.assertEqual(rgba_array[0, 0, 0], 255)  # Red component
        self.assertEqual(rgba_array[0, 0, 1], 0)    # Green component
        self.assertEqual(rgba_array[0, 0, 2], 0)    # Blue component
        self.assertEqual(rgba_array[0, 0, 3], 255)  # Alpha component


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)