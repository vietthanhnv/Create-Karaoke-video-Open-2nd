"""
Unit Tests for Frame Capture System

Tests frame-by-frame rendering, framebuffer capture, pixel format conversion,
and frame rate synchronization functionality.
"""

import unittest
import time
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Import the frame capture system
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.frame_capture_system import (
    FrameCaptureSystem, FrameRenderingEngine, FrameCaptureSettings,
    PixelFormat, FrameTimestamp, CapturedFrame, create_frame_capture_system,
    capture_video_frames
)
from core.opengl_context import OpenGLContext, ContextBackend
from core.models import Project, AudioFile, VideoFile, ImageFile, SubtitleFile


class TestFrameTimestamp(unittest.TestCase):
    """Test FrameTimestamp functionality"""
    
    def test_frame_timestamp_creation(self):
        """Test creating frame timestamps"""
        timestamp = FrameTimestamp(
            frame_number=10,
            timestamp=0.333,
            duration=0.033,
            fps=30.0
        )
        
        self.assertEqual(timestamp.frame_number, 10)
        self.assertAlmostEqual(timestamp.timestamp, 0.333, places=3)
        self.assertAlmostEqual(timestamp.duration, 0.033, places=3)
        self.assertEqual(timestamp.fps, 30.0)
    
    def test_next_timestamp(self):
        """Test calculating next frame timestamp"""
        timestamp = FrameTimestamp(
            frame_number=0,
            timestamp=0.0,
            duration=0.033,
            fps=30.0
        )
        
        next_ts = timestamp.next_timestamp
        self.assertAlmostEqual(next_ts, 0.033, places=3)
    
    def test_previous_timestamp(self):
        """Test calculating previous frame timestamp"""
        timestamp = FrameTimestamp(
            frame_number=1,
            timestamp=0.033,
            duration=0.033,
            fps=30.0
        )
        
        prev_ts = timestamp.previous_timestamp
        self.assertAlmostEqual(prev_ts, 0.0, places=3)
        
        # Test boundary condition
        timestamp_zero = FrameTimestamp(
            frame_number=0,
            timestamp=0.0,
            duration=0.033,
            fps=30.0
        )
        
        prev_ts_zero = timestamp_zero.previous_timestamp
        self.assertEqual(prev_ts_zero, 0.0)


class TestCapturedFrame(unittest.TestCase):
    """Test CapturedFrame functionality"""
    
    def test_captured_frame_creation(self):
        """Test creating captured frames"""
        test_data = np.zeros((100, 100, 4), dtype=np.uint8)
        
        frame = CapturedFrame(
            frame_number=5,
            timestamp=0.167,
            width=100,
            height=100,
            pixel_format=PixelFormat.RGBA8,
            data=test_data,
            capture_time=time.time(),
            render_time=0.016
        )
        
        self.assertEqual(frame.frame_number, 5)
        self.assertAlmostEqual(frame.timestamp, 0.167, places=3)
        self.assertEqual(frame.width, 100)
        self.assertEqual(frame.height, 100)
        self.assertEqual(frame.pixel_format, PixelFormat.RGBA8)
        self.assertEqual(frame.size_bytes, test_data.nbytes)
    
    def test_frame_to_dict(self):
        """Test converting frame to dictionary"""
        test_data = np.zeros((50, 50, 3), dtype=np.uint8)
        
        frame = CapturedFrame(
            frame_number=1,
            timestamp=0.033,
            width=50,
            height=50,
            pixel_format=PixelFormat.RGB8,
            data=test_data,
            capture_time=time.time(),
            render_time=0.020
        )
        
        frame_dict = frame.to_dict()
        
        self.assertEqual(frame_dict['frame_number'], 1)
        self.assertAlmostEqual(frame_dict['timestamp'], 0.033, places=3)
        self.assertEqual(frame_dict['width'], 50)
        self.assertEqual(frame_dict['height'], 50)
        self.assertEqual(frame_dict['pixel_format'], 'rgb8')
        self.assertEqual(frame_dict['size_bytes'], test_data.nbytes)


class TestFrameCaptureSettings(unittest.TestCase):
    """Test FrameCaptureSettings functionality"""
    
    def test_default_settings(self):
        """Test default capture settings"""
        settings = FrameCaptureSettings()
        
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.pixel_format, PixelFormat.RGBA8)
        self.assertEqual(settings.quality, 1.0)
        self.assertTrue(settings.use_threading)
        self.assertEqual(settings.buffer_size, 10)
        self.assertTrue(settings.sync_with_audio)
        self.assertEqual(settings.audio_offset, 0.0)
        self.assertTrue(settings.flip_vertically)
        self.assertFalse(settings.premultiply_alpha)
    
    def test_custom_settings(self):
        """Test custom capture settings"""
        settings = FrameCaptureSettings(
            width=1280,
            height=720,
            fps=24.0,
            pixel_format=PixelFormat.YUV420P,
            quality=0.8,
            use_threading=False,
            buffer_size=5,
            sync_with_audio=False,
            audio_offset=0.1,
            flip_vertically=False,
            premultiply_alpha=True
        )
        
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.fps, 24.0)
        self.assertEqual(settings.pixel_format, PixelFormat.YUV420P)
        self.assertEqual(settings.quality, 0.8)
        self.assertFalse(settings.use_threading)
        self.assertEqual(settings.buffer_size, 5)
        self.assertFalse(settings.sync_with_audio)
        self.assertEqual(settings.audio_offset, 0.1)
        self.assertFalse(settings.flip_vertically)
        self.assertTrue(settings.premultiply_alpha)


class TestFrameRenderingEngine(unittest.TestCase):
    """Test FrameRenderingEngine functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock OpenGL context
        self.mock_context = Mock(spec=OpenGLContext)
        self.mock_context.backend = ContextBackend.MOCK
        self.mock_context.make_current.return_value = True
        
        # Create mock framebuffer
        self.mock_framebuffer = Mock()
        self.mock_framebuffer.bind.return_value = None
        self.mock_framebuffer.unbind.return_value = None
        self.mock_framebuffer.clear.return_value = None
        
        # Mock framebuffer read_pixels to return test data
        test_pixels = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
        self.mock_framebuffer.read_pixels.return_value = test_pixels
        
        self.mock_context.create_framebuffer.return_value = self.mock_framebuffer
        
        # Create rendering engine
        self.engine = FrameRenderingEngine(self.mock_context)
        
        # Create test project
        self.test_project = self._create_test_project()
        
        # Create test settings
        self.test_settings = FrameCaptureSettings(width=100, height=100, fps=30.0)
    
    def _create_test_project(self):
        """Create a test project with mock media files"""
        project = Project(id="test_project_1", name="Test Project")
        
        # Add mock audio file
        project.audio_file = AudioFile(
            path="test_audio.mp3",
            duration=10.0,
            sample_rate=44100,
            channels=2,
            format="MP3"
        )
        
        # Add mock video file
        project.video_file = VideoFile(
            path="test_video.mp4",
            duration=10.0,
            resolution={"width": 1920, "height": 1080},
            frame_rate=30.0,
            format="MP4"
        )
        
        # Add mock subtitle file
        project.subtitle_file = SubtitleFile(path="test_subtitles.ass")
        
        return project
    
    def test_engine_initialization(self):
        """Test rendering engine initialization"""
        with patch('core.frame_capture_system.OpenGLSubtitleRenderer') as mock_subtitle_renderer, \
             patch('core.frame_capture_system.EffectsRenderingPipeline') as mock_effects_pipeline:
            
            # Mock successful initialization
            mock_subtitle_instance = Mock()
            mock_subtitle_instance.initialize_opengl.return_value = True
            mock_subtitle_renderer.return_value = mock_subtitle_instance
            
            mock_effects_instance = Mock()
            mock_effects_instance.initialize.return_value = True
            mock_effects_pipeline.return_value = mock_effects_instance
            
            # Test initialization
            success = self.engine.initialize(self.test_project, self.test_settings)
            
            self.assertTrue(success)
            self.assertEqual(self.engine.current_project, self.test_project)
            self.assertEqual(self.engine.capture_settings, self.test_settings)
            self.assertIsNotNone(self.engine.framebuffer)
            self.assertIsNotNone(self.engine.subtitle_renderer)
            self.assertIsNotNone(self.engine.effects_pipeline)
    
    def test_engine_initialization_failure(self):
        """Test rendering engine initialization failure"""
        # Mock framebuffer creation failure
        self.mock_context.create_framebuffer.return_value = None
        
        success = self.engine.initialize(self.test_project, self.test_settings)
        
        self.assertFalse(success)
    
    def test_frame_rendering_at_timestamp(self):
        """Test rendering frame at specific timestamp"""
        with patch('core.frame_capture_system.OpenGLSubtitleRenderer') as mock_subtitle_renderer, \
             patch('core.frame_capture_system.EffectsRenderingPipeline') as mock_effects_pipeline:
            
            # Mock successful initialization
            mock_subtitle_instance = Mock()
            mock_subtitle_instance.initialize_opengl.return_value = True
            mock_subtitle_renderer.return_value = mock_subtitle_instance
            
            mock_effects_instance = Mock()
            mock_effects_instance.initialize.return_value = True
            mock_effects_pipeline.return_value = mock_effects_instance
            
            # Initialize engine
            self.engine.initialize(self.test_project, self.test_settings)
            
            # Test frame rendering
            timestamp = 1.5
            frame = self.engine.render_frame_at_timestamp(timestamp)
            
            self.assertIsNotNone(frame)
            self.assertIsInstance(frame, CapturedFrame)
            self.assertEqual(frame.timestamp, timestamp)
            self.assertEqual(frame.width, self.test_settings.width)
            self.assertEqual(frame.height, self.test_settings.height)
            self.assertEqual(frame.pixel_format, self.test_settings.pixel_format)
            
            # Verify OpenGL calls were made
            self.mock_context.make_current.assert_called()
            self.mock_framebuffer.bind.assert_called()
            self.mock_framebuffer.clear.assert_called()
            self.mock_framebuffer.read_pixels.assert_called()
            self.mock_framebuffer.unbind.assert_called()
    
    def test_pixel_format_conversion_rgba_to_rgb(self):
        """Test RGBA to RGB pixel format conversion"""
        # Create test RGBA data
        rgba_data = np.random.randint(0, 255, (10, 10, 4), dtype=np.uint8)
        
        # Convert to RGB
        rgb_data = self.engine._rgba_to_rgb(rgba_data)
        
        self.assertEqual(rgb_data.shape, (10, 10, 3))
        np.testing.assert_array_equal(rgb_data, rgba_data[:, :, :3])
    
    def test_pixel_format_conversion_rgba_to_bgra(self):
        """Test RGBA to BGRA pixel format conversion"""
        # Create test RGBA data
        rgba_data = np.random.randint(0, 255, (10, 10, 4), dtype=np.uint8)
        
        # Convert to BGRA
        bgra_data = self.engine._rgba_to_bgra(rgba_data)
        
        self.assertEqual(bgra_data.shape, (10, 10, 4))
        # Check that red and blue channels are swapped
        np.testing.assert_array_equal(bgra_data[:, :, 0], rgba_data[:, :, 2])  # B = R
        np.testing.assert_array_equal(bgra_data[:, :, 1], rgba_data[:, :, 1])  # G = G
        np.testing.assert_array_equal(bgra_data[:, :, 2], rgba_data[:, :, 0])  # R = B
        np.testing.assert_array_equal(bgra_data[:, :, 3], rgba_data[:, :, 3])  # A = A
    
    def test_pixel_format_conversion_rgba_to_yuv420p(self):
        """Test RGBA to YUV420P pixel format conversion"""
        # Create test RGBA data (must be even dimensions for YUV420P)
        rgba_data = np.random.randint(0, 255, (20, 20, 4), dtype=np.uint8)
        
        # Convert to YUV420P
        yuv_data = self.engine._rgba_to_yuv420p(rgba_data)
        
        # YUV420P should have Y plane (full res) + U plane (1/4 res) + V plane (1/4 res)
        expected_size = 20 * 20 + 2 * (10 * 10)  # Y + U + V
        self.assertEqual(yuv_data.shape[0], expected_size)
    
    def test_pixel_format_conversion_rgba_to_yuv444p(self):
        """Test RGBA to YUV444P pixel format conversion"""
        # Create test RGBA data
        rgba_data = np.random.randint(0, 255, (10, 10, 4), dtype=np.uint8)
        
        # Convert to YUV444P
        yuv_data = self.engine._rgba_to_yuv444p(rgba_data)
        
        # YUV444P should have 3 full-resolution planes
        expected_size = 3 * 10 * 10  # Y + U + V (all full resolution)
        self.assertEqual(yuv_data.shape[0], expected_size)
    
    def test_performance_stats(self):
        """Test performance statistics tracking"""
        # Initially no stats
        stats = self.engine.get_performance_stats()
        self.assertEqual(stats['frame_count'], 0)
        self.assertEqual(stats['fps_estimate'], 0.0)
        
        # Add some render times
        self.engine.render_times = [0.016, 0.020, 0.018, 0.015, 0.022]
        
        stats = self.engine.get_performance_stats()
        self.assertEqual(stats['frame_count'], 5)
        self.assertAlmostEqual(stats['average_render_time'], 0.0182, places=3)
        self.assertEqual(stats['min_render_time'], 0.015)
        self.assertEqual(stats['max_render_time'], 0.022)
        self.assertGreater(stats['fps_estimate'], 0)
    
    def test_background_cache(self):
        """Test background rendering cache"""
        # Test cache functionality
        test_data = np.array([0.5, 0.6, 0.7, 1.0], dtype=np.float32)
        self.engine.background_cache[1.5] = test_data
        
        # Verify cache entry
        self.assertIn(1.5, self.engine.background_cache)
        np.testing.assert_array_equal(self.engine.background_cache[1.5], test_data)
        
        # Test cache size limit
        for i in range(60):  # Exceed cache_max_size (50)
            self.engine.background_cache[float(i)] = test_data
        
        # Cache should not exceed max size significantly
        self.assertLessEqual(len(self.engine.background_cache), 60)
    
    def test_cleanup(self):
        """Test engine cleanup"""
        with patch('core.frame_capture_system.OpenGLSubtitleRenderer') as mock_subtitle_renderer, \
             patch('core.frame_capture_system.EffectsRenderingPipeline') as mock_effects_pipeline:
            
            # Mock successful initialization
            mock_subtitle_instance = Mock()
            mock_subtitle_instance.initialize_opengl.return_value = True
            mock_subtitle_instance.cleanup.return_value = None
            mock_subtitle_renderer.return_value = mock_subtitle_instance
            
            mock_effects_instance = Mock()
            mock_effects_instance.initialize.return_value = True
            mock_effects_instance.cleanup.return_value = None
            mock_effects_pipeline.return_value = mock_effects_instance
            
            # Initialize and then cleanup
            self.engine.initialize(self.test_project, self.test_settings)
            self.engine.cleanup()
            
            # Verify cleanup was called
            mock_subtitle_instance.cleanup.assert_called_once()
            mock_effects_instance.cleanup.assert_called_once()
            
            # Verify resources are cleared
            self.assertIsNone(self.engine.framebuffer)
            self.assertIsNone(self.engine.subtitle_renderer)
            self.assertIsNone(self.engine.effects_pipeline)
            self.assertEqual(len(self.engine.background_cache), 0)
            self.assertEqual(len(self.engine.render_times), 0)


class TestFrameCaptureSystem(unittest.TestCase):
    """Test FrameCaptureSystem functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create mock OpenGL context
        self.mock_context = Mock(spec=OpenGLContext)
        self.mock_context.backend = ContextBackend.MOCK
        
        # Create capture system
        self.capture_system = FrameCaptureSystem(self.mock_context)
        
        # Create test project
        self.test_project = self._create_test_project()
        
        # Create test settings
        self.test_settings = FrameCaptureSettings(width=100, height=100, fps=30.0)
    
    def _create_test_project(self):
        """Create a test project with mock media files"""
        project = Project(id="test_project_2", name="Test Project")
        
        project.audio_file = AudioFile(
            path="test_audio.mp3",
            duration=5.0,
            sample_rate=44100,
            channels=2,
            format="MP3"
        )
        
        return project
    
    def test_frame_timestamp_generation(self):
        """Test generating frame timestamps"""
        duration = 2.0  # 2 seconds
        fps = 30.0
        
        timestamps = self.capture_system.generate_frame_timestamps(duration, fps)
        
        expected_frames = int(duration * fps)  # 60 frames
        self.assertEqual(len(timestamps), expected_frames)
        
        # Check first and last timestamps
        self.assertEqual(timestamps[0].frame_number, 0)
        self.assertAlmostEqual(timestamps[0].timestamp, 0.0, places=3)
        
        self.assertEqual(timestamps[-1].frame_number, expected_frames - 1)
        self.assertLess(timestamps[-1].timestamp, duration)
        
        # Check frame duration consistency
        for timestamp in timestamps:
            self.assertAlmostEqual(timestamp.duration, 1.0 / fps, places=3)
            self.assertEqual(timestamp.fps, fps)
    
    def test_frame_timestamp_generation_with_start_time(self):
        """Test generating frame timestamps with start time offset"""
        duration = 1.0
        fps = 24.0
        start_time = 0.5
        
        timestamps = self.capture_system.generate_frame_timestamps(duration, fps, start_time)
        
        # First timestamp should start at start_time
        self.assertAlmostEqual(timestamps[0].timestamp, start_time, places=3)
        
        # All timestamps should be >= start_time
        for timestamp in timestamps:
            self.assertGreaterEqual(timestamp.timestamp, start_time)
    
    def test_audio_synchronization(self):
        """Test audio synchronization functionality"""
        # Generate some test timestamps
        timestamps = self.capture_system.generate_frame_timestamps(1.0, 30.0)
        self.capture_system.frame_timestamps = timestamps
        
        # Apply audio synchronization
        audio_duration = 1.0
        audio_offset = 0.1
        
        original_timestamps = [ts.timestamp for ts in timestamps]
        self.capture_system.synchronize_with_audio(audio_duration, audio_offset)
        
        # Check that timestamps were adjusted
        for i, timestamp in enumerate(timestamps):
            expected_timestamp = original_timestamps[i] + audio_offset
            self.assertAlmostEqual(timestamp.timestamp, expected_timestamp, places=3)
        
        self.assertEqual(self.capture_system.audio_sync_offset, audio_offset)
    
    def test_capture_statistics(self):
        """Test capture statistics tracking"""
        # Initially no statistics
        stats = self.capture_system.get_capture_statistics()
        self.assertEqual(stats, {})
        
        # Set up capture state
        self.capture_system.is_capturing = True
        self.capture_system.frames_captured = 15
        self.capture_system.total_frames = 30
        self.capture_system.capture_start_time = time.time() - 1.0  # 1 second ago
        self.capture_system.audio_sync_offset = 0.05
        
        # Mock rendering engine stats
        mock_render_stats = {
            'average_render_time': 0.020,
            'fps_estimate': 50.0,
            'frame_count': 15
        }
        self.capture_system.rendering_engine.get_performance_stats = Mock(return_value=mock_render_stats)
        
        stats = self.capture_system.get_capture_statistics()
        
        self.assertEqual(stats['frames_captured'], 15)
        self.assertEqual(stats['total_frames'], 30)
        self.assertGreater(stats['elapsed_time'], 0.9)
        self.assertGreater(stats['capture_fps'], 0)
        self.assertEqual(stats['progress_percent'], 50.0)
        self.assertEqual(stats['render_stats'], mock_render_stats)
        self.assertEqual(stats['audio_sync_offset'], 0.05)
    
    @patch('core.frame_capture_system.FrameRenderingEngine')
    def test_capture_frame_sequence(self, mock_engine_class):
        """Test capturing a sequence of frames"""
        # Mock rendering engine
        mock_engine = Mock()
        mock_engine.initialize.return_value = True
        mock_engine_class.return_value = mock_engine
        
        # Create mock captured frames
        def create_mock_frame(timestamp):
            return CapturedFrame(
                frame_number=int(timestamp * 30),
                timestamp=timestamp,
                width=100,
                height=100,
                pixel_format=PixelFormat.RGBA8,
                data=np.zeros((100, 100, 4), dtype=np.uint8),
                capture_time=time.time(),
                render_time=0.016
            )
        
        mock_engine.render_frame_at_timestamp.side_effect = create_mock_frame
        
        # Replace the rendering engine
        self.capture_system.rendering_engine = mock_engine
        
        # Generate test timestamps
        timestamps = self.capture_system.generate_frame_timestamps(0.5, 30.0)  # 15 frames
        
        # Capture frames
        captured_frames = self.capture_system.capture_frame_sequence(timestamps)
        
        self.assertEqual(len(captured_frames), len(timestamps))
        
        # Verify each frame
        for i, frame in enumerate(captured_frames):
            self.assertIsInstance(frame, CapturedFrame)
            self.assertEqual(frame.frame_number, timestamps[i].frame_number)
            self.assertAlmostEqual(frame.timestamp, timestamps[i].timestamp, places=3)
    
    def test_capture_cancellation(self):
        """Test cancelling frame capture"""
        # Start a mock capture
        self.capture_system.is_capturing = True
        self.capture_system.should_cancel = False
        
        # Cancel capture
        self.capture_system.cancel_capture()
        
        self.assertTrue(self.capture_system.should_cancel)
    
    def test_cleanup(self):
        """Test capture system cleanup"""
        # Mock rendering engine
        mock_engine = Mock()
        self.capture_system.rendering_engine = mock_engine
        
        # Cleanup
        self.capture_system.cleanup()
        
        # Verify rendering engine cleanup was called
        mock_engine.cleanup.assert_called_once()


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_frame_capture_system(self):
        """Test creating frame capture system"""
        mock_context = Mock(spec=OpenGLContext)
        
        capture_system = create_frame_capture_system(mock_context)
        
        self.assertIsInstance(capture_system, FrameCaptureSystem)
        self.assertEqual(capture_system.opengl_context, mock_context)
    
    @patch('core.frame_capture_system.FrameCaptureSystem')
    def test_capture_video_frames(self, mock_capture_system_class):
        """Test capturing video frames convenience function"""
        # Mock capture system
        mock_capture_system = Mock()
        mock_capture_system.initialize.return_value = True
        mock_capture_system.generate_frame_timestamps.return_value = [
            FrameTimestamp(0, 0.0, 0.033, 30.0),
            FrameTimestamp(1, 0.033, 0.033, 30.0)
        ]
        mock_capture_system.capture_frame_sequence.return_value = [
            Mock(spec=CapturedFrame),
            Mock(spec=CapturedFrame)
        ]
        mock_capture_system_class.return_value = mock_capture_system
        
        # Create test project
        project = Project(id="test_project_3", name="Test")
        project.audio_file = AudioFile(
            path="test.mp3",
            duration=2.0,
            sample_rate=44100,
            channels=2,
            format="MP3"
        )
        
        settings = FrameCaptureSettings(fps=30.0)
        mock_context = Mock(spec=OpenGLContext)
        
        # Capture frames
        frames = capture_video_frames(project, settings, mock_context)
        
        self.assertEqual(len(frames), 2)
        mock_capture_system.initialize.assert_called_once_with(project, settings)
        mock_capture_system.cleanup.assert_called_once()


class TestPixelFormatConversions(unittest.TestCase):
    """Test pixel format conversion accuracy"""
    
    def setUp(self):
        """Set up test data"""
        # Create mock OpenGL context
        self.mock_context = Mock(spec=OpenGLContext)
        self.engine = FrameRenderingEngine(self.mock_context)
    
    def test_rgba_to_rgb_conversion_accuracy(self):
        """Test RGBA to RGB conversion preserves color data"""
        # Create test pattern with known values
        rgba_data = np.zeros((4, 4, 4), dtype=np.uint8)
        rgba_data[0, 0] = [255, 0, 0, 255]    # Red
        rgba_data[0, 1] = [0, 255, 0, 255]    # Green
        rgba_data[0, 2] = [0, 0, 255, 255]    # Blue
        rgba_data[0, 3] = [255, 255, 255, 128] # White with alpha
        
        rgb_data = self.engine._rgba_to_rgb(rgba_data)
        
        # Check that RGB values are preserved
        np.testing.assert_array_equal(rgb_data[0, 0], [255, 0, 0])
        np.testing.assert_array_equal(rgb_data[0, 1], [0, 255, 0])
        np.testing.assert_array_equal(rgb_data[0, 2], [0, 0, 255])
        np.testing.assert_array_equal(rgb_data[0, 3], [255, 255, 255])
    
    def test_yuv420p_conversion_accuracy(self):
        """Test YUV420P conversion produces valid YUV data"""
        # Create test pattern
        rgba_data = np.zeros((8, 8, 4), dtype=np.uint8)
        
        # Set some test pixels
        rgba_data[0, 0] = [255, 0, 0, 255]    # Red
        rgba_data[0, 2] = [0, 255, 0, 255]    # Green
        rgba_data[2, 0] = [0, 0, 255, 255]    # Blue
        rgba_data[2, 2] = [255, 255, 255, 255] # White
        
        yuv_data = self.engine._rgba_to_yuv420p(rgba_data)
        
        # YUV420P should have correct size
        expected_size = 8 * 8 + 2 * (4 * 4)  # Y + U + V
        self.assertEqual(len(yuv_data), expected_size)
        
        # YUV values should be in valid range [0, 255]
        self.assertTrue(np.all(yuv_data >= 0))
        self.assertTrue(np.all(yuv_data <= 255))
    
    def test_yuv444p_conversion_accuracy(self):
        """Test YUV444P conversion produces valid YUV data"""
        # Create test pattern
        rgba_data = np.zeros((4, 4, 4), dtype=np.uint8)
        rgba_data[0, 0] = [255, 0, 0, 255]    # Red
        rgba_data[1, 1] = [0, 255, 0, 255]    # Green
        rgba_data[2, 2] = [0, 0, 255, 255]    # Blue
        rgba_data[3, 3] = [255, 255, 255, 255] # White
        
        yuv_data = self.engine._rgba_to_yuv444p(rgba_data)
        
        # YUV444P should have correct size (3 full-resolution planes)
        expected_size = 3 * 4 * 4
        self.assertEqual(len(yuv_data), expected_size)
        
        # YUV values should be in valid range [0, 255]
        self.assertTrue(np.all(yuv_data >= 0))
        self.assertTrue(np.all(yuv_data <= 255))


class TestFrameRateSynchronization(unittest.TestCase):
    """Test frame rate synchronization with audio timing"""
    
    def test_frame_rate_calculation(self):
        """Test frame rate calculations are accurate"""
        test_cases = [
            (24.0, 1.0 / 24.0),
            (25.0, 1.0 / 25.0),
            (30.0, 1.0 / 30.0),
            (60.0, 1.0 / 60.0),
            (23.976, 1.0 / 23.976)
        ]
        
        for fps, expected_duration in test_cases:
            timestamp = FrameTimestamp(0, 0.0, expected_duration, fps)
            
            self.assertAlmostEqual(timestamp.duration, expected_duration, places=6)
            self.assertAlmostEqual(timestamp.next_timestamp, expected_duration, places=6)
    
    def test_audio_sync_timing_accuracy(self):
        """Test audio synchronization timing accuracy"""
        capture_system = FrameCaptureSystem(Mock())
        
        # Generate timestamps for 1 second at 30fps
        timestamps = capture_system.generate_frame_timestamps(1.0, 30.0)
        capture_system.frame_timestamps = timestamps
        
        # Test various audio offsets
        test_offsets = [-0.1, -0.05, 0.0, 0.05, 0.1, 0.25]
        
        for offset in test_offsets:
            # Reset timestamps
            timestamps = capture_system.generate_frame_timestamps(1.0, 30.0)
            capture_system.frame_timestamps = timestamps
            
            original_times = [ts.timestamp for ts in timestamps]
            
            # Apply synchronization
            capture_system.synchronize_with_audio(1.0, offset)
            
            # Check all timestamps were adjusted correctly
            for i, timestamp in enumerate(timestamps):
                expected_time = original_times[i] + offset
                self.assertAlmostEqual(timestamp.timestamp, expected_time, places=6)


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance tracking and metrics"""
    
    def test_render_time_tracking(self):
        """Test render time tracking accuracy"""
        mock_context = Mock(spec=OpenGLContext)
        engine = FrameRenderingEngine(mock_context)
        
        # Add test render times
        test_times = [0.016, 0.020, 0.018, 0.015, 0.022, 0.019, 0.017]
        engine.render_times = test_times
        
        stats = engine.get_performance_stats()
        
        # Check statistics accuracy
        expected_avg = np.mean(test_times)
        expected_min = np.min(test_times)
        expected_max = np.max(test_times)
        expected_fps = 1.0 / expected_avg
        
        self.assertAlmostEqual(stats['average_render_time'], expected_avg, places=6)
        self.assertEqual(stats['min_render_time'], expected_min)
        self.assertEqual(stats['max_render_time'], expected_max)
        self.assertAlmostEqual(stats['fps_estimate'], expected_fps, places=2)
        self.assertEqual(stats['frame_count'], len(test_times))
    
    def test_capture_performance_tracking(self):
        """Test capture performance tracking"""
        mock_context = Mock(spec=OpenGLContext)
        capture_system = FrameCaptureSystem(mock_context)
        
        # Set up capture state
        start_time = time.time() - 2.0  # 2 seconds ago
        capture_system.capture_start_time = start_time
        capture_system.frames_captured = 60
        capture_system.total_frames = 120
        capture_system.is_capturing = True
        
        # Mock rendering engine stats
        mock_render_stats = {
            'average_render_time': 0.016,
            'fps_estimate': 62.5,
            'frame_count': 60
        }
        capture_system.rendering_engine.get_performance_stats = Mock(return_value=mock_render_stats)
        
        stats = capture_system.get_capture_statistics()
        
        # Check performance calculations
        self.assertEqual(stats['frames_captured'], 60)
        self.assertEqual(stats['total_frames'], 120)
        self.assertAlmostEqual(stats['progress_percent'], 50.0, places=1)
        self.assertGreater(stats['elapsed_time'], 1.9)
        self.assertGreater(stats['capture_fps'], 25.0)  # Should be around 30 fps
        self.assertEqual(stats['render_stats'], mock_render_stats)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True, exit=False)