"""
Unit Tests for Enhanced FFmpeg Integration

Tests enhanced FFmpeg process management, optimized streaming pipeline,
progress tracking, and advanced export settings.
"""

import unittest
import time
import subprocess
import threading
import queue
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Import the enhanced FFmpeg integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.enhanced_ffmpeg_integration import (
    EnhancedFFmpegProcessor, EnhancedExportSettings, FFmpegCapabilities,
    FFmpegProgress, FFmpegPreset, VideoCodec, AudioCodec, ContainerFormat,
    BatchExportJob, BatchFFmpegProcessor,
    create_enhanced_ffmpeg_processor, get_ffmpeg_capabilities,
    create_optimized_export_settings, create_batch_processor
)
from core.frame_capture_system import CapturedFrame, PixelFormat
import numpy as np


class TestFFmpegCapabilities(unittest.TestCase):
    """Test FFmpeg capabilities detection"""
    
    def test_capabilities_creation(self):
        """Test creating FFmpeg capabilities"""
        capabilities = FFmpegCapabilities(
            version="4.4.0",
            available=True,
            supported_codecs=["libx264", "aac"],
            supported_formats=["mp4", "mkv"],
            supported_filters=["scale", "overlay"],
            hardware_acceleration=["nvenc"]
        )
        
        self.assertEqual(capabilities.version, "4.4.0")
        self.assertTrue(capabilities.available)
        self.assertIn("libx264", capabilities.supported_codecs)
        self.assertIn("mp4", capabilities.supported_formats)
        self.assertIn("scale", capabilities.supported_filters)
        self.assertIn("nvenc", capabilities.hardware_acceleration)
        self.assertIsNone(capabilities.error_message)
    
    def test_capabilities_with_error(self):
        """Test FFmpeg capabilities with error"""
        capabilities = FFmpegCapabilities(
            available=False,
            error_message="FFmpeg not found"
        )
        
        self.assertFalse(capabilities.available)
        self.assertEqual(capabilities.error_message, "FFmpeg not found")
        self.assertEqual(len(capabilities.supported_codecs), 0)


class TestEnhancedExportSettings(unittest.TestCase):
    """Test enhanced export settings"""
    
    def test_default_settings(self):
        """Test default export settings"""
        settings = EnhancedExportSettings()
        
        self.assertEqual(settings.output_path, "output.mp4")
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.video_codec, VideoCodec.H264)
        self.assertEqual(settings.preset, FFmpegPreset.MEDIUM)
        self.assertEqual(settings.crf, 23)
        self.assertIsNone(settings.bitrate)
        self.assertEqual(settings.audio_codec, AudioCodec.AAC)
        self.assertEqual(settings.audio_bitrate, 128)
        self.assertEqual(settings.container_format, ContainerFormat.MP4)
        self.assertEqual(settings.pixel_format, "yuv420p")
        self.assertFalse(settings.two_pass_encoding)
        self.assertIsNone(settings.hardware_acceleration)
        self.assertEqual(len(settings.custom_filters), 0)
        self.assertEqual(len(settings.metadata), 0)
    
    def test_custom_settings(self):
        """Test custom export settings"""
        settings = EnhancedExportSettings(
            output_path="custom_output.mkv",
            width=1280,
            height=720,
            fps=24.0,
            video_codec=VideoCodec.H265,
            preset=FFmpegPreset.SLOW,
            crf=18,
            audio_codec=AudioCodec.OPUS,
            audio_bitrate=192,
            container_format=ContainerFormat.MKV,
            two_pass_encoding=True,
            hardware_acceleration="nvenc",
            custom_filters=["scale=1280:720", "fps=24"],
            metadata={"title": "Test Video", "author": "Test Author"}
        )
        
        self.assertEqual(settings.output_path, "custom_output.mkv")
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.fps, 24.0)
        self.assertEqual(settings.video_codec, VideoCodec.H265)
        self.assertEqual(settings.preset, FFmpegPreset.SLOW)
        self.assertEqual(settings.crf, 18)
        self.assertEqual(settings.audio_codec, AudioCodec.OPUS)
        self.assertEqual(settings.audio_bitrate, 192)
        self.assertEqual(settings.container_format, ContainerFormat.MKV)
        self.assertTrue(settings.two_pass_encoding)
        self.assertEqual(settings.hardware_acceleration, "nvenc")
        self.assertIn("scale=1280:720", settings.custom_filters)
        self.assertEqual(settings.metadata["title"], "Test Video")


class TestFFmpegProgress(unittest.TestCase):
    """Test FFmpeg progress tracking"""
    
    def test_progress_creation(self):
        """Test creating FFmpeg progress"""
        progress = FFmpegProgress(
            frame=100,
            fps=30.0,
            bitrate="2000kbits/s",
            total_size="10MB",
            out_time="00:03:20.00",
            speed="1.5x"
        )
        
        self.assertEqual(progress.frame, 100)
        self.assertEqual(progress.fps, 30.0)
        self.assertEqual(progress.bitrate, "2000kbits/s")
        self.assertEqual(progress.total_size, "10MB")
        self.assertEqual(progress.out_time, "00:03:20.00")
        self.assertEqual(progress.speed, "1.5x")
        self.assertEqual(progress.progress_percent, 0.0)
        self.assertEqual(progress.estimated_remaining, 0.0)
        self.assertEqual(progress.elapsed_time, 0.0)


class TestEnhancedFFmpegProcessor(unittest.TestCase):
    """Test enhanced FFmpeg processor"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = EnhancedFFmpegProcessor()
        
        # Mock FFmpeg capabilities for testing
        self.mock_capabilities = FFmpegCapabilities(
            version="4.4.0",
            available=True,
            supported_codecs=["libx264", "libx265", "aac", "libmp3lame"],
            supported_formats=["mp4", "mkv", "webm"],
            supported_filters=["scale", "overlay", "fps"],
            hardware_acceleration=["nvenc", "qsv"]
        )
        self.processor.capabilities = self.mock_capabilities
    
    @patch('subprocess.run')
    def test_detect_capabilities_success(self, mock_run):
        """Test successful FFmpeg capabilities detection"""
        # Mock successful FFmpeg version check
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.0-0ubuntu1"
        mock_run.return_value = mock_result
        
        # Mock codec and format detection
        with patch.object(self.processor, '_get_supported_codecs', return_value=["libx264", "aac"]), \
             patch.object(self.processor, '_get_supported_formats', return_value=["mp4", "mkv"]), \
             patch.object(self.processor, '_get_supported_filters', return_value=["scale"]), \
             patch.object(self.processor, '_detect_hardware_acceleration', return_value=["nvenc"]):
            
            capabilities = self.processor._detect_capabilities()
            
            self.assertTrue(capabilities.available)
            self.assertEqual(capabilities.version, "4.4.0-0ubuntu1")
            self.assertIn("libx264", capabilities.supported_codecs)
            self.assertIn("mp4", capabilities.supported_formats)
            self.assertIn("scale", capabilities.supported_filters)
            self.assertIn("nvenc", capabilities.hardware_acceleration)
    
    @patch('subprocess.run')
    def test_detect_capabilities_failure(self, mock_run):
        """Test FFmpeg capabilities detection failure"""
        # Mock FFmpeg not found
        mock_run.side_effect = FileNotFoundError("FFmpeg not found")
        
        capabilities = self.processor._detect_capabilities()
        
        self.assertFalse(capabilities.available)
        self.assertEqual(capabilities.error_message, "FFmpeg not found in system PATH")
    
    def test_validate_settings_success(self):
        """Test successful settings validation"""
        settings = EnhancedExportSettings(
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container_format=ContainerFormat.MP4
        )
        
        errors = self.processor.validate_settings(settings)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_settings_failure(self):
        """Test settings validation with errors"""
        settings = EnhancedExportSettings(
            width=-100,  # Invalid width
            height=0,    # Invalid height
            fps=-30.0,   # Invalid fps
            crf=100,     # Invalid CRF
            bitrate=-1000,  # Invalid bitrate
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container_format=ContainerFormat.MP4
        )
        
        errors = self.processor.validate_settings(settings)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Invalid resolution" in error for error in errors))
        self.assertTrue(any("Invalid frame rate" in error for error in errors))
        self.assertTrue(any("Invalid CRF" in error for error in errors))
        self.assertTrue(any("Invalid bitrate" in error for error in errors))
    
    def test_validate_settings_warnings(self):
        """Test settings validation with warnings"""
        settings = EnhancedExportSettings(
            width=1921,  # Odd width (warning)
            height=1079,  # Odd height (warning)
            fps=200.0,   # Very high fps (warning)
            crf=5,       # Very low CRF (warning)
            audio_bitrate=32,  # Low audio bitrate (warning)
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            container_format=ContainerFormat.MP4
        )
        
        errors = self.processor.validate_settings(settings)
        
        # Should have warnings but no hard errors
        warnings = [error for error in errors if error.startswith("Warning:")]
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("even numbers" in warning for warning in warnings))
        self.assertTrue(any("high frame rate" in warning for warning in warnings))
        self.assertTrue(any("low CRF" in warning for warning in warnings))
    
    def test_build_ffmpeg_command_basic(self):
        """Test building basic FFmpeg command"""
        settings = EnhancedExportSettings(
            output_path="test_output.mp4",
            width=1280,
            height=720,
            fps=30.0,
            video_codec=VideoCodec.H264,
            preset=FFmpegPreset.MEDIUM,
            crf=23,
            audio_codec=AudioCodec.AAC,
            container_format=ContainerFormat.MP4
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-hide_banner", cmd)
        self.assertIn("-y", cmd)
        self.assertIn("-f", cmd)
        self.assertIn("rawvideo", cmd)
        self.assertIn("-s", cmd)
        self.assertIn("1280x720", cmd)
        self.assertIn("-r", cmd)
        self.assertIn("30.0", cmd)
        self.assertIn("-c:v", cmd)
        self.assertIn("libx264", cmd)
        self.assertIn("-crf", cmd)
        self.assertIn("23", cmd)
        self.assertIn("-preset", cmd)
        self.assertIn("medium", cmd)
        self.assertIn("test_output.mp4", cmd)
    
    def test_build_ffmpeg_command_with_audio(self):
        """Test building FFmpeg command with audio input"""
        settings = EnhancedExportSettings(
            output_path="test_output.mp4",
            audio_codec=AudioCodec.AAC,
            audio_bitrate=128
        )
        
        audio_file = "test_audio.mp3"
        
        with patch('os.path.exists', return_value=True):
            cmd = self.processor.build_ffmpeg_command(settings, audio_file)
            
            self.assertIn("-i", cmd)
            self.assertIn(audio_file, cmd)
            self.assertIn("-c:a", cmd)
            self.assertIn("aac", cmd)
            self.assertIn("-b:a", cmd)
            self.assertIn("128k", cmd)
    
    def test_build_ffmpeg_command_with_hardware_acceleration(self):
        """Test building FFmpeg command with hardware acceleration"""
        settings = EnhancedExportSettings(
            hardware_acceleration="nvenc"
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("-hwaccel", cmd)
        self.assertIn("cuda", cmd)
    
    def test_build_ffmpeg_command_with_custom_filters(self):
        """Test building FFmpeg command with custom filters"""
        settings = EnhancedExportSettings(
            custom_filters=["scale=1920:1080", "fps=30"]
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("-vf", cmd)
        filter_index = cmd.index("-vf") + 1
        self.assertIn("scale=1920:1080,fps=30", cmd[filter_index])
    
    def test_build_ffmpeg_command_with_metadata(self):
        """Test building FFmpeg command with metadata"""
        settings = EnhancedExportSettings(
            metadata={"title": "Test Video", "author": "Test Author"}
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("-metadata", cmd)
        # Check that metadata entries are present
        metadata_count = cmd.count("-metadata")
        self.assertEqual(metadata_count, 2)  # Two metadata entries
    
    def test_prepare_frame_for_ffmpeg(self):
        """Test preparing frame data for FFmpeg"""
        # Create test frame
        test_data = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
        frame = CapturedFrame(
            frame_number=1,
            timestamp=0.033,
            width=100,
            height=100,
            pixel_format=PixelFormat.RGBA8,
            data=test_data,
            capture_time=time.time(),
            render_time=0.016
        )
        
        frame_bytes = self.processor._prepare_frame_for_ffmpeg(frame)
        
        self.assertIsNotNone(frame_bytes)
        self.assertIsInstance(frame_bytes, bytes)
        self.assertEqual(len(frame_bytes), test_data.nbytes)
    
    def test_parse_progress_line(self):
        """Test parsing FFmpeg progress lines"""
        # Test various progress line formats
        test_lines = [
            "frame=100",
            "fps=30.5",
            "bitrate=2000.0kbits/s",
            "total_size=1048576",
            "out_time=00:03:20.00",
            "speed=1.5x",
            "progress=continue"
        ]
        
        for line in test_lines:
            self.processor._parse_progress_line(line)
        
        # Check that progress info was updated
        self.assertEqual(self.processor.progress_info.frame, 100)
        self.assertEqual(self.processor.progress_info.fps, 30.5)
        self.assertEqual(self.processor.progress_info.bitrate, "2000.0kbits/s")
        self.assertEqual(self.processor.progress_info.speed, "1.5x")
        self.assertEqual(self.processor.progress_info.progress, "continue")
    
    def test_get_progress_info(self):
        """Test getting progress information"""
        # Set some progress data
        self.processor.progress_info.frame = 50
        self.processor.progress_info.fps = 25.0
        self.processor.progress_info.bitrate = "1500kbits/s"
        
        progress = self.processor.get_progress_info()
        
        self.assertEqual(progress.frame, 50)
        self.assertEqual(progress.fps, 25.0)
        self.assertEqual(progress.bitrate, "1500kbits/s")
    
    def test_cleanup(self):
        """Test processor cleanup"""
        # Set up some state
        self.processor.is_encoding = False
        self.processor.frame_queue = queue.Queue()
        self.processor.frame_queue.put("test_frame")
        
        # Cleanup
        self.processor.cleanup()
        
        # Verify cleanup
        self.assertIsNone(self.processor.ffmpeg_process)
        self.assertIsNone(self.processor.frame_queue)
        self.assertIsNone(self.processor.frame_writer_thread)
        self.assertIsNone(self.processor.progress_monitor_thread)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_enhanced_ffmpeg_processor(self):
        """Test creating enhanced FFmpeg processor"""
        processor = create_enhanced_ffmpeg_processor()
        
        self.assertIsInstance(processor, EnhancedFFmpegProcessor)
        self.assertIsNotNone(processor.capabilities)
    
    @patch('core.enhanced_ffmpeg_integration.EnhancedFFmpegProcessor')
    def test_get_ffmpeg_capabilities(self, mock_processor_class):
        """Test getting FFmpeg capabilities"""
        mock_processor = Mock()
        mock_capabilities = FFmpegCapabilities(available=True, version="4.4.0")
        mock_processor.get_capabilities.return_value = mock_capabilities
        mock_processor_class.return_value = mock_processor
        
        capabilities = get_ffmpeg_capabilities()
        
        self.assertEqual(capabilities, mock_capabilities)
        mock_processor.get_capabilities.assert_called_once()
    
    def test_create_optimized_export_settings_high_quality(self):
        """Test creating optimized export settings for high quality"""
        settings = create_optimized_export_settings(
            "output.mp4",
            width=1920,
            height=1080,
            fps=30.0,
            quality="high"
        )
        
        self.assertEqual(settings.output_path, "output.mp4")
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.crf, 18)  # High quality CRF
        self.assertEqual(settings.preset, FFmpegPreset.SLOW)
        self.assertEqual(settings.audio_bitrate, 192)
    
    def test_create_optimized_export_settings_medium_quality(self):
        """Test creating optimized export settings for medium quality"""
        settings = create_optimized_export_settings(
            "output.mp4",
            quality="medium"
        )
        
        self.assertEqual(settings.crf, 23)  # Medium quality CRF
        self.assertEqual(settings.preset, FFmpegPreset.MEDIUM)
        self.assertEqual(settings.audio_bitrate, 128)
    
    def test_create_optimized_export_settings_low_quality(self):
        """Test creating optimized export settings for low quality"""
        settings = create_optimized_export_settings(
            "output.mp4",
            quality="low"
        )
        
        self.assertEqual(settings.crf, 28)  # Low quality CRF
        self.assertEqual(settings.preset, FFmpegPreset.FAST)
        self.assertEqual(settings.audio_bitrate, 96)
    
    def test_create_optimized_export_settings_ultrafast(self):
        """Test creating optimized export settings for ultrafast encoding"""
        settings = create_optimized_export_settings(
            "output.mp4",
            quality="ultrafast"
        )
        
        self.assertEqual(settings.bitrate, 2000)  # Use bitrate instead of CRF
        self.assertIsNone(settings.crf)
        self.assertEqual(settings.preset, FFmpegPreset.ULTRAFAST)
        self.assertEqual(settings.audio_bitrate, 128)
    
    def test_create_optimized_export_settings_lossless(self):
        """Test creating optimized export settings for lossless encoding"""
        settings = create_optimized_export_settings(
            "output.mp4",
            quality="lossless"
        )
        
        self.assertEqual(settings.crf, 0)  # Lossless CRF
        self.assertEqual(settings.preset, FFmpegPreset.MEDIUM)
        self.assertEqual(settings.audio_bitrate, 320)
        self.assertEqual(settings.pixel_format, "yuv444p")
    
    def test_create_web_optimized_settings(self):
        """Test creating web-optimized export settings"""
        from core.enhanced_ffmpeg_integration import create_web_optimized_settings
        
        settings = create_web_optimized_settings("web_output.mp4")
        
        self.assertEqual(settings.width, 1280)
        self.assertEqual(settings.height, 720)
        self.assertEqual(settings.video_codec, VideoCodec.H264)
        self.assertEqual(settings.container_format, ContainerFormat.MP4)
        self.assertEqual(settings.profile, "main")
        self.assertEqual(settings.level, "3.1")
        self.assertIn("title", settings.metadata)
    
    def test_create_mobile_optimized_settings(self):
        """Test creating mobile-optimized export settings"""
        from core.enhanced_ffmpeg_integration import create_mobile_optimized_settings
        
        settings = create_mobile_optimized_settings("mobile_output.mp4")
        
        self.assertEqual(settings.width, 854)
        self.assertEqual(settings.height, 480)
        self.assertEqual(settings.crf, 26)
        self.assertEqual(settings.preset, FFmpegPreset.FAST)
        self.assertEqual(settings.profile, "baseline")
        self.assertEqual(settings.level, "3.0")
        self.assertEqual(settings.audio_bitrate, 96)


class TestFFmpegCommandBuilding(unittest.TestCase):
    """Test FFmpeg command building with various configurations"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = EnhancedFFmpegProcessor()
        self.processor.capabilities = FFmpegCapabilities(
            available=True,
            supported_codecs=["libx264", "libx265", "aac", "libmp3lame"],
            supported_formats=["mp4", "mkv"],
            hardware_acceleration=["nvenc"]
        )
    
    def test_command_with_two_pass_encoding(self):
        """Test FFmpeg command with two-pass encoding"""
        settings = EnhancedExportSettings(
            two_pass_encoding=True,
            bitrate=5000
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        # Two-pass encoding would require special handling
        # For now, just verify basic command structure
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-b:v", cmd)
        self.assertIn("5000k", cmd)
    
    def test_command_with_threading_options(self):
        """Test FFmpeg command with threading options"""
        settings = EnhancedExportSettings(
            threads=8,
            thread_type="slice"
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("-threads", cmd)
        self.assertIn("8", cmd)
    
    def test_command_with_profile_and_level(self):
        """Test FFmpeg command with H.264 profile and level"""
        settings = EnhancedExportSettings(
            profile="high",
            level="4.1",
            tune="film"
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        self.assertIn("-profile:v", cmd)
        self.assertIn("high", cmd)
        self.assertIn("-level", cmd)
        self.assertIn("4.1", cmd)
        self.assertIn("-tune", cmd)
        self.assertIn("film", cmd)
    
    def test_command_with_different_codecs(self):
        """Test FFmpeg command with different video/audio codecs"""
        settings = EnhancedExportSettings(
            video_codec=VideoCodec.H265,
            audio_codec=AudioCodec.OPUS,
            container_format=ContainerFormat.MKV
        )
        
        # Test with audio input
        with patch('os.path.exists', return_value=True):
            cmd = self.processor.build_ffmpeg_command(settings, "test_audio.mp3")
            
            self.assertIn("libx265", cmd)
            self.assertIn("libopus", cmd)
            self.assertIn("-f", cmd)
            self.assertIn("mkv", cmd)
        
        # Test without audio input (should use -an)
        cmd_no_audio = self.processor.build_ffmpeg_command(settings)
        self.assertIn("libx265", cmd_no_audio)
        self.assertIn("-an", cmd_no_audio)  # No audio
        self.assertIn("-f", cmd_no_audio)
        self.assertIn("mkv", cmd_no_audio)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in FFmpeg integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = EnhancedFFmpegProcessor()
    
    def test_invalid_frame_data_handling(self):
        """Test handling of invalid frame data"""
        # Test with None frame
        result = self.processor._prepare_frame_for_ffmpeg(None)
        self.assertIsNone(result)
        
        # Test with invalid frame data
        invalid_frame = Mock()
        invalid_frame.pixel_format = PixelFormat.RGBA8
        invalid_frame.data = None
        
        result = self.processor._prepare_frame_for_ffmpeg(invalid_frame)
        self.assertIsNone(result)
    
    def test_progress_parsing_error_handling(self):
        """Test error handling in progress parsing"""
        # Test with invalid progress lines
        invalid_lines = [
            "invalid_line_without_equals",
            "key=",  # Empty value
            "=value",  # Empty key
            "frame=not_a_number",
            "fps=invalid_float"
        ]
        
        for line in invalid_lines:
            # Should not raise exceptions
            try:
                self.processor._parse_progress_line(line)
            except Exception as e:
                self.fail(f"Progress parsing should handle invalid line '{line}' gracefully, but raised: {e}")
    
    def test_capabilities_detection_timeout(self):
        """Test capabilities detection with timeout"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
            
            capabilities = self.processor._detect_capabilities()
            
            self.assertFalse(capabilities.available)
            self.assertIn("timed out", capabilities.error_message)


class TestPerformanceOptimizations(unittest.TestCase):
    """Test performance optimizations in FFmpeg integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = EnhancedFFmpegProcessor()
    
    def test_frame_buffer_size_configuration(self):
        """Test frame buffer size configuration"""
        # Test default buffer size
        self.assertEqual(self.processor.frame_buffer_size, 10)
        
        # Test custom buffer size
        self.processor.frame_buffer_size = 20
        self.assertEqual(self.processor.frame_buffer_size, 20)
    
    def test_streaming_chunk_size_configuration(self):
        """Test streaming chunk size configuration"""
        # Test default chunk size
        self.assertEqual(self.processor.streaming_chunk_size, 1024 * 1024)  # 1MB
        
        # Test custom chunk size
        self.processor.streaming_chunk_size = 2 * 1024 * 1024  # 2MB
        self.assertEqual(self.processor.streaming_chunk_size, 2 * 1024 * 1024)
    
    def test_hardware_acceleration_detection(self):
        """Test hardware acceleration detection"""
        with patch.object(self.processor, '_check_codec_support') as mock_check:
            # Mock different hardware acceleration support
            mock_check.side_effect = lambda codec: codec in ["h264_nvenc", "h264_qsv"]
            
            hw_accel = self.processor._detect_hardware_acceleration()
            
            self.assertIn("nvenc", hw_accel)
            self.assertIn("qsv", hw_accel)
            self.assertNotIn("vaapi", hw_accel)
            self.assertNotIn("videotoolbox", hw_accel)


class TestBatchExportJob(unittest.TestCase):
    """Test batch export job functionality"""
    
    def test_batch_job_creation(self):
        """Test creating a batch export job"""
        settings = EnhancedExportSettings(output_path="test.mp4")
        frame_source = Mock()
        
        job = BatchExportJob(
            job_id="test_job_1",
            settings=settings,
            frame_source=frame_source,
            total_frames=100,
            input_audio="test.mp3"
        )
        
        self.assertEqual(job.job_id, "test_job_1")
        self.assertEqual(job.settings, settings)
        self.assertEqual(job.frame_source, frame_source)
        self.assertEqual(job.total_frames, 100)
        self.assertEqual(job.input_audio, "test.mp3")
        self.assertEqual(job.status, "pending")
        self.assertIsNone(job.error_message)
        self.assertIsNone(job.start_time)
        self.assertIsNone(job.end_time)
        self.assertEqual(job.progress_percent, 0.0)


class TestBatchFFmpegProcessor(unittest.TestCase):
    """Test batch FFmpeg processor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.batch_processor = BatchFFmpegProcessor(max_concurrent_jobs=2)
    
    def test_batch_processor_creation(self):
        """Test creating a batch processor"""
        processor = BatchFFmpegProcessor(max_concurrent_jobs=3)
        
        self.assertEqual(processor.max_concurrent_jobs, 3)
        self.assertEqual(len(processor.jobs), 0)
        self.assertEqual(len(processor.active_processors), 0)
        self.assertFalse(processor.is_processing)
        self.assertFalse(processor.should_cancel)
        self.assertEqual(processor.total_jobs, 0)
        self.assertEqual(processor.completed_jobs, 0)
        self.assertEqual(processor.failed_jobs, 0)
        self.assertEqual(processor.cancelled_jobs, 0)
    
    def test_add_job(self):
        """Test adding jobs to batch queue"""
        settings = EnhancedExportSettings(output_path="test1.mp4")
        frame_source = Mock()
        
        job = BatchExportJob(
            job_id="test_job_1",
            settings=settings,
            frame_source=frame_source,
            total_frames=100
        )
        
        self.batch_processor.add_job(job)
        
        self.assertEqual(len(self.batch_processor.jobs), 1)
        self.assertEqual(self.batch_processor.jobs[0], job)
    
    def test_add_export_job_convenience(self):
        """Test convenience method for adding export jobs"""
        settings = EnhancedExportSettings(output_path="test2.mp4")
        frame_source = Mock()
        
        job = self.batch_processor.add_export_job(
            job_id="test_job_2",
            settings=settings,
            frame_source=frame_source,
            total_frames=200,
            input_audio="test.mp3"
        )
        
        self.assertEqual(len(self.batch_processor.jobs), 1)
        self.assertEqual(job.job_id, "test_job_2")
        self.assertEqual(job.settings, settings)
        self.assertEqual(job.total_frames, 200)
        self.assertEqual(job.input_audio, "test.mp3")
    
    def test_add_job_while_processing_raises_error(self):
        """Test that adding jobs while processing raises an error"""
        self.batch_processor.is_processing = True
        
        settings = EnhancedExportSettings(output_path="test.mp4")
        frame_source = Mock()
        job = BatchExportJob("test", settings, frame_source, 100)
        
        with self.assertRaises(RuntimeError):
            self.batch_processor.add_job(job)
    
    def test_get_batch_status(self):
        """Test getting batch status"""
        # Add some jobs
        for i in range(3):
            settings = EnhancedExportSettings(output_path=f"test{i}.mp4")
            self.batch_processor.add_export_job(
                job_id=f"job_{i}",
                settings=settings,
                frame_source=Mock(),
                total_frames=100
            )
        
        status = self.batch_processor.get_batch_status()
        
        self.assertFalse(status['is_processing'])
        self.assertEqual(status['total_jobs'], 0)  # Not started yet
        self.assertEqual(status['completed_jobs'], 0)
        self.assertEqual(status['failed_jobs'], 0)
        self.assertEqual(status['cancelled_jobs'], 0)
        self.assertEqual(status['active_jobs'], 0)
        self.assertEqual(status['pending_jobs'], 3)
    
    def test_get_job_status(self):
        """Test getting individual job status"""
        settings = EnhancedExportSettings(output_path="test.mp4")
        job = self.batch_processor.add_export_job(
            job_id="test_job",
            settings=settings,
            frame_source=Mock(),
            total_frames=100
        )
        
        status = self.batch_processor.get_job_status("test_job")
        
        self.assertIsNotNone(status)
        self.assertEqual(status['job_id'], "test_job")
        self.assertEqual(status['status'], "pending")
        self.assertEqual(status['progress_percent'], 0.0)
        self.assertIsNone(status['error_message'])
        self.assertIsNone(status['start_time'])
        self.assertIsNone(status['end_time'])
        self.assertIsNone(status['duration'])
    
    def test_get_job_status_nonexistent(self):
        """Test getting status of non-existent job"""
        status = self.batch_processor.get_job_status("nonexistent")
        self.assertIsNone(status)
    
    def test_clear_completed_jobs(self):
        """Test clearing completed jobs"""
        # Add jobs with different statuses
        for i, status in enumerate(["pending", "completed", "failed", "running"]):
            settings = EnhancedExportSettings(output_path=f"test{i}.mp4")
            job = self.batch_processor.add_export_job(
                job_id=f"job_{i}",
                settings=settings,
                frame_source=Mock(),
                total_frames=100
            )
            job.status = status
        
        self.assertEqual(len(self.batch_processor.jobs), 4)
        
        self.batch_processor.clear_completed_jobs()
        
        # Should only have pending and running jobs left
        self.assertEqual(len(self.batch_processor.jobs), 2)
        remaining_statuses = [job.status for job in self.batch_processor.jobs]
        self.assertIn("pending", remaining_statuses)
        self.assertIn("running", remaining_statuses)
    
    def test_clear_jobs_while_processing_raises_error(self):
        """Test that clearing jobs while processing raises an error"""
        self.batch_processor.is_processing = True
        
        with self.assertRaises(RuntimeError):
            self.batch_processor.clear_completed_jobs()
    
    @patch('core.enhanced_ffmpeg_integration.EnhancedFFmpegProcessor')
    def test_start_batch_processing_empty_queue(self, mock_processor_class):
        """Test starting batch processing with empty queue"""
        result = self.batch_processor.start_batch_processing()
        
        self.assertFalse(result)
        self.assertFalse(self.batch_processor.is_processing)
    
    @patch('core.enhanced_ffmpeg_integration.EnhancedFFmpegProcessor')
    def test_start_batch_processing_already_running(self, mock_processor_class):
        """Test starting batch processing when already running"""
        self.batch_processor.is_processing = True
        
        result = self.batch_processor.start_batch_processing()
        
        self.assertFalse(result)


class TestBatchProcessingConvenience(unittest.TestCase):
    """Test batch processing convenience functions"""
    
    def test_create_batch_processor(self):
        """Test creating batch processor with convenience function"""
        processor = create_batch_processor(max_concurrent_jobs=3)
        
        self.assertIsInstance(processor, BatchFFmpegProcessor)
        self.assertEqual(processor.max_concurrent_jobs, 3)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True, exit=False)