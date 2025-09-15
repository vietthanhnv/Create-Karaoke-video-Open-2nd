"""
Comprehensive Tests for Enhanced FFmpeg Integration

Tests the complete enhanced FFmpeg integration including:
- Enhanced error handling and progress tracking
- Optimized raw frame data streaming pipeline
- Advanced export settings configuration
- Batch processing capabilities
"""

import unittest
import time
import tempfile
import os
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Import the enhanced FFmpeg integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.enhanced_ffmpeg_integration import (
    EnhancedFFmpegProcessor, EnhancedExportSettings, BatchFFmpegProcessor,
    FFmpegCapabilities, FFmpegProgress, FFmpegPreset, VideoCodec, AudioCodec,
    ContainerFormat, create_enhanced_ffmpeg_processor, create_optimized_export_settings,
    create_web_optimized_settings, create_mobile_optimized_settings,
    create_batch_processor
)
from core.frame_capture_system import CapturedFrame, PixelFormat


class TestEnhancedFFmpegIntegrationComprehensive(unittest.TestCase):
    """Comprehensive tests for enhanced FFmpeg integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = create_enhanced_ffmpeg_processor()
        
        # Mock FFmpeg capabilities for testing
        self.mock_capabilities = FFmpegCapabilities(
            version="4.4.0",
            available=True,
            supported_codecs=["libx264", "libx265", "aac", "libmp3lame", "libopus"],
            supported_formats=["mp4", "mkv", "webm"],
            supported_filters=["scale", "overlay", "fps"],
            hardware_acceleration=["nvenc", "qsv"]
        )
        self.processor.capabilities = self.mock_capabilities
    
    def create_test_frame(self, frame_number: int, width: int = 640, height: int = 480) -> CapturedFrame:
        """Create a test frame for testing"""
        data = np.random.randint(0, 255, (height, width, 4), dtype=np.uint8)
        return CapturedFrame(
            frame_number=frame_number,
            timestamp=frame_number / 30.0,
            width=width,
            height=height,
            pixel_format=PixelFormat.RGBA8,
            data=data,
            capture_time=time.time(),
            render_time=0.033
        )
    
    def test_enhanced_error_handling(self):
        """Test enhanced error handling capabilities"""
        # Test error analysis
        error_lines = [
            "No such file or directory",
            "Permission denied",
            "Invalid data found"
        ]
        
        error_msg = self.processor._analyze_ffmpeg_errors(1, error_lines, "stderr output")
        
        self.assertIn("Input file not found", error_msg)
        self.assertIn("code 1", error_msg)
    
    def test_optimized_frame_streaming(self):
        """Test optimized frame data streaming"""
        # Test frame preparation
        test_frame = self.create_test_frame(1)
        frame_bytes = self.processor._prepare_frame_for_ffmpeg(test_frame)
        
        self.assertIsNotNone(frame_bytes)
        self.assertIsInstance(frame_bytes, bytes)
        self.assertEqual(len(frame_bytes), test_frame.data.nbytes)
    
    def test_enhanced_progress_tracking(self):
        """Test enhanced progress tracking with stderr parsing"""
        # Test progress line parsing
        progress_lines = [
            "frame=100",
            "fps=30.5",
            "bitrate=2000.0kbits/s",
            "total_size=1048576",
            "out_time=00:03:20.00",
            "speed=1.5x"
        ]
        
        for line in progress_lines:
            self.processor._parse_progress_line(line)
        
        # Verify progress info was updated
        self.assertEqual(self.processor.progress_info.frame, 100)
        self.assertEqual(self.processor.progress_info.fps, 30.5)
        self.assertEqual(self.processor.progress_info.bitrate, "2000.0kbits/s")
        self.assertEqual(self.processor.progress_info.speed, "1.5x")
    
    def test_advanced_export_settings_validation(self):
        """Test advanced export settings validation"""
        # Test comprehensive validation
        settings = EnhancedExportSettings(
            width=1921,  # Odd width (should generate warning)
            height=1080,
            fps=200.0,   # Very high fps (should generate warning)
            crf=5,       # Very low CRF (should generate warning)
            audio_bitrate=32,  # Low audio bitrate (should generate warning)
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC
        )
        
        errors = self.processor.validate_settings(settings)
        warnings = [e for e in errors if e.startswith("Warning:")]
        
        self.assertGreater(len(warnings), 0)
        self.assertTrue(any("even numbers" in w for w in warnings))
        self.assertTrue(any("high frame rate" in w for w in warnings))
        self.assertTrue(any("low CRF" in w for w in warnings))
    
    def test_optimized_export_settings_creation(self):
        """Test creation of optimized export settings"""
        # Test different quality levels
        quality_tests = [
            ("high", 18, FFmpegPreset.SLOW, 192, "high"),
            ("medium", 23, FFmpegPreset.MEDIUM, 128, "main"),
            ("low", 28, FFmpegPreset.FAST, 96, "baseline"),
            ("lossless", 0, FFmpegPreset.MEDIUM, 320, None)
        ]
        
        for quality, expected_crf, expected_preset, expected_audio, expected_profile in quality_tests:
            settings = create_optimized_export_settings(
                f"test_{quality}.mp4",
                quality=quality
            )
            
            if quality != "ultrafast":  # ultrafast uses bitrate instead of CRF
                self.assertEqual(settings.crf, expected_crf)
            self.assertEqual(settings.preset, expected_preset)
            self.assertEqual(settings.audio_bitrate, expected_audio)
            if expected_profile:
                self.assertEqual(settings.profile, expected_profile)
    
    def test_specialized_export_settings(self):
        """Test specialized export settings (web, mobile)"""
        # Test web optimized settings
        web_settings = create_web_optimized_settings("web_test.mp4")
        self.assertEqual(web_settings.width, 1280)
        self.assertEqual(web_settings.height, 720)
        self.assertEqual(web_settings.profile, "main")
        self.assertEqual(web_settings.level, "3.1")
        self.assertIn("title", web_settings.metadata)
        
        # Test mobile optimized settings
        mobile_settings = create_mobile_optimized_settings("mobile_test.mp4")
        self.assertEqual(mobile_settings.width, 854)
        self.assertEqual(mobile_settings.height, 480)
        self.assertEqual(mobile_settings.profile, "baseline")
        self.assertEqual(mobile_settings.level, "3.0")
        self.assertEqual(mobile_settings.audio_bitrate, 96)
    
    def test_batch_processing_system(self):
        """Test batch processing capabilities"""
        batch_processor = create_batch_processor(max_concurrent_jobs=2)
        
        # Add multiple jobs
        for i in range(3):
            settings = create_optimized_export_settings(f"batch_test_{i}.mp4")
            frame_source = Mock(return_value=self.create_test_frame(i))
            
            job = batch_processor.add_export_job(
                job_id=f"test_job_{i}",
                settings=settings,
                frame_source=frame_source,
                total_frames=30
            )
            
            self.assertEqual(job.job_id, f"test_job_{i}")
            self.assertEqual(job.total_frames, 30)
            self.assertEqual(job.status, "pending")
        
        # Test batch status
        status = batch_processor.get_batch_status()
        self.assertEqual(status['total_jobs'], 0)  # Not started yet
        self.assertEqual(status['pending_jobs'], 3)
        self.assertFalse(status['is_processing'])
        
        # Test individual job status
        job_status = batch_processor.get_job_status("test_job_0")
        self.assertIsNotNone(job_status)
        self.assertEqual(job_status['job_id'], "test_job_0")
        self.assertEqual(job_status['status'], "pending")
    
    def test_ffmpeg_command_building_comprehensive(self):
        """Test comprehensive FFmpeg command building"""
        # Test complex settings
        settings = EnhancedExportSettings(
            output_path="complex_test.mp4",
            width=1920,
            height=1080,
            fps=30.0,
            video_codec=VideoCodec.H265,
            preset=FFmpegPreset.SLOW,
            crf=18,
            profile="main",
            level="4.1",
            tune="film",
            audio_codec=AudioCodec.AAC,
            audio_bitrate=192,
            custom_filters=["scale=1920:1080", "fps=30"],
            metadata={"title": "Test Video", "author": "Test"},
            hardware_acceleration="nvenc",
            threads=8
        )
        
        cmd = self.processor.build_ffmpeg_command(settings, "test_audio.mp3")
        
        # Verify key components are present
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-hwaccel", cmd)
        self.assertIn("cuda", cmd)
        self.assertIn("-threads", cmd)
        self.assertIn("8", cmd)
        self.assertIn("-c:v", cmd)
        self.assertIn("libx265", cmd)
        self.assertIn("-crf", cmd)
        self.assertIn("18", cmd)
        self.assertIn("-preset", cmd)
        self.assertIn("slow", cmd)
        self.assertIn("-profile:v", cmd)
        self.assertIn("main", cmd)
        self.assertIn("-level", cmd)
        self.assertIn("4.1", cmd)
        self.assertIn("-tune", cmd)
        self.assertIn("film", cmd)
        self.assertIn("-vf", cmd)
        self.assertIn("-metadata", cmd)
        self.assertIn("complex_test.mp4", cmd)
    
    def test_performance_optimizations(self):
        """Test performance optimization features"""
        # Test buffer size configuration
        self.processor.frame_buffer_size = 20
        self.assertEqual(self.processor.frame_buffer_size, 20)
        
        # Test streaming chunk size configuration
        self.processor.streaming_chunk_size = 2 * 1024 * 1024  # 2MB
        self.assertEqual(self.processor.streaming_chunk_size, 2 * 1024 * 1024)
        
        # Test hardware acceleration detection
        hw_accel = self.processor.capabilities.hardware_acceleration
        self.assertIn("nvenc", hw_accel)
        self.assertIn("qsv", hw_accel)
    
    def test_error_recovery_mechanisms(self):
        """Test error recovery and handling mechanisms"""
        # Test invalid frame handling
        invalid_frame = Mock()
        invalid_frame.pixel_format = PixelFormat.RGBA8
        invalid_frame.data = None
        
        result = self.processor._prepare_frame_for_ffmpeg(invalid_frame)
        self.assertIsNone(result)
        
        # Test progress parsing error handling
        invalid_lines = [
            "invalid_line_without_equals",
            "frame=not_a_number",
            "fps=invalid_float"
        ]
        
        # Should not raise exceptions
        for line in invalid_lines:
            try:
                self.processor._parse_progress_line(line)
            except Exception as e:
                self.fail(f"Progress parsing should handle invalid line gracefully: {e}")
    
    def test_codec_container_compatibility(self):
        """Test codec and container compatibility validation"""
        # Test H.265 with MP4 (should be compatible)
        settings = EnhancedExportSettings(
            video_codec=VideoCodec.H265,
            container_format=ContainerFormat.MP4
        )
        
        errors = self.processor.validate_settings(settings)
        compatibility_warnings = [e for e in errors if "may not be optimal" in e]
        
        # H.265 with MP4 should be compatible (no warnings)
        h265_mp4_warnings = [w for w in compatibility_warnings if "libx265" in w and "mp4" in w]
        self.assertEqual(len(h265_mp4_warnings), 0)
    
    def test_two_pass_encoding_support(self):
        """Test two-pass encoding configuration"""
        settings = EnhancedExportSettings(
            two_pass_encoding=True,
            bitrate=5000
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        # Should include bitrate settings for two-pass
        self.assertIn("-b:v", cmd)
        self.assertIn("5000k", cmd)
    
    def test_metadata_handling(self):
        """Test metadata handling in export settings"""
        settings = EnhancedExportSettings(
            metadata={
                "title": "Test Video",
                "author": "Test Author",
                "description": "Test Description"
            }
        )
        
        cmd = self.processor.build_ffmpeg_command(settings)
        
        # Should include metadata entries
        metadata_count = cmd.count("-metadata")
        self.assertEqual(metadata_count, 3)  # Three metadata entries
    
    def test_cleanup_and_resource_management(self):
        """Test cleanup and resource management"""
        import queue
        
        # Set up some state
        self.processor.is_encoding = False
        self.processor.frame_queue = queue.Queue()
        self.processor.frame_queue.put("test_frame")
        
        # Test cleanup
        self.processor.cleanup()
        
        # Verify cleanup
        self.assertIsNone(self.processor.ffmpeg_process)
        self.assertIsNone(self.processor.frame_queue)
        self.assertIsNone(self.processor.frame_writer_thread)
        self.assertIsNone(self.processor.progress_monitor_thread)


class TestIntegrationWithExistingSystems(unittest.TestCase):
    """Test integration with existing karaoke video creator systems"""
    
    def test_frame_capture_integration(self):
        """Test integration with frame capture system"""
        processor = create_enhanced_ffmpeg_processor()
        
        # Create test frame from frame capture system
        test_data = np.random.randint(0, 255, (480, 640, 4), dtype=np.uint8)
        frame = CapturedFrame(
            frame_number=1,
            timestamp=0.033,
            width=640,
            height=480,
            pixel_format=PixelFormat.RGBA8,
            data=test_data,
            capture_time=time.time(),
            render_time=0.016
        )
        
        # Test frame preparation
        frame_bytes = processor._prepare_frame_for_ffmpeg(frame)
        
        self.assertIsNotNone(frame_bytes)
        self.assertEqual(len(frame_bytes), test_data.nbytes)
    
    def test_export_settings_compatibility(self):
        """Test export settings compatibility with existing export system"""
        # Test that enhanced settings work with existing patterns
        settings = create_optimized_export_settings(
            "karaoke_output.mp4",
            width=1920,
            height=1080,
            fps=30.0,
            quality="high"
        )
        
        # Verify settings are compatible with karaoke video requirements
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.video_codec, VideoCodec.H264)  # Standard for karaoke
        self.assertEqual(settings.container_format, ContainerFormat.MP4)  # Standard format
        self.assertIsNotNone(settings.crf)  # Quality-based encoding
        self.assertGreater(settings.audio_bitrate, 128)  # Good audio quality for karaoke


if __name__ == "__main__":
    unittest.main()