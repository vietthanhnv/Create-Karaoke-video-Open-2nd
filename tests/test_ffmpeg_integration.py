"""
Unit tests for FFmpeg integration in the export system
"""

import unittest
import tempfile
import os
import shutil
import subprocess
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path

# Import the modules to test
try:
    from src.core.opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, ExportProgress,
        FFmpegQualityPresets, create_export_renderer
    )
    from src.core.models import Project, AudioFile, VideoFile, SubtitleFile
except ImportError:
    import sys
    sys.path.append('src/core')
    from opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, ExportProgress,
        FFmpegQualityPresets, create_export_renderer
    )
    from models import Project, AudioFile, VideoFile, SubtitleFile


class TestExportSettings(unittest.TestCase):
    """Test enhanced ExportSettings."""
    
    def test_default_settings(self):
        """Test default export settings."""
        settings = ExportSettings(output_path="test.mp4")
        
        self.assertEqual(settings.width, 1920)
        self.assertEqual(settings.height, 1080)
        self.assertEqual(settings.fps, 30.0)
        self.assertEqual(settings.codec, "libx264")
        self.assertEqual(settings.preset, "medium")
        self.assertEqual(settings.profile, "high")
        self.assertEqual(settings.audio_codec, "aac")
        self.assertEqual(settings.container_format, "mp4")
    
    def test_advanced_settings(self):
        """Test advanced encoding settings."""
        settings = ExportSettings(
            output_path="test.mp4",
            crf=18,
            preset="slow",
            max_bitrate=10000,
            buffer_size=20000
        )
        
        self.assertEqual(settings.crf, 18)
        self.assertEqual(settings.preset, "slow")
        self.assertEqual(settings.max_bitrate, 10000)
        self.assertEqual(settings.buffer_size, 20000)


class TestFFmpegCapabilities(unittest.TestCase):
    """Test FFmpeg capability detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
    
    @patch('subprocess.run')
    def test_check_ffmpeg_capabilities_success(self, mock_run):
        """Test successful FFmpeg capability detection."""
        # Mock FFmpeg version output
        version_result = Mock()
        version_result.returncode = 0
        version_result.stdout = "ffmpeg version 4.4.0"
        
        # Mock codec output
        codec_result = Mock()
        codec_result.returncode = 0
        codec_result.stdout = """
        DEV.LS h264                 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
        D.V.L. libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (encoder)
        DEA.L. aac                  AAC (Advanced Audio Coding) (encoder)
        """
        
        # Mock format output
        format_result = Mock()
        format_result.returncode = 0
        format_result.stdout = """
        E mp4             MP4 (MPEG-4 Part 14) (muxer)
        E mkv             Matroska (muxer)
        """
        
        mock_run.side_effect = [version_result, codec_result, format_result]
        
        capabilities = self.renderer.check_ffmpeg_capabilities()
        
        self.assertTrue(capabilities['available'])
        self.assertEqual(capabilities['version'], '4.4.0')
        self.assertIn('libx264', capabilities['codecs'])
        self.assertIn('aac', capabilities['codecs'])
        self.assertIn('mp4', capabilities['formats'])
    
    @patch('subprocess.run')
    def test_check_ffmpeg_capabilities_not_found(self, mock_run):
        """Test FFmpeg not found."""
        mock_run.side_effect = FileNotFoundError()
        
        capabilities = self.renderer.check_ffmpeg_capabilities()
        
        self.assertFalse(capabilities['available'])
        self.assertIn('not found', capabilities['error'])
    
    @patch('subprocess.run')
    def test_check_ffmpeg_capabilities_timeout(self, mock_run):
        """Test FFmpeg command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired('ffmpeg', 10)
        
        capabilities = self.renderer.check_ffmpeg_capabilities()
        
        self.assertFalse(capabilities['available'])
        self.assertIn('timed out', capabilities['error'])
    
    def test_validate_export_settings_valid(self):
        """Test validation of valid export settings."""
        settings = ExportSettings(
            output_path="test.mp4",
            width=1920,
            height=1080,
            fps=30.0,
            bitrate=5000
        )
        
        # Mock FFmpeg capabilities
        with patch.object(self.renderer, 'check_ffmpeg_capabilities') as mock_check:
            mock_check.return_value = {
                'available': True,
                'codecs': ['libx264', 'aac'],
                'formats': ['mp4']
            }
            
            errors = self.renderer.validate_export_settings(settings)
            self.assertEqual(len(errors), 0)
    
    def test_validate_export_settings_invalid_resolution(self):
        """Test validation with invalid resolution."""
        settings = ExportSettings(
            output_path="test.mp4",
            width=1921,  # Odd width
            height=1081  # Odd height
        )
        
        with patch.object(self.renderer, 'check_ffmpeg_capabilities') as mock_check:
            mock_check.return_value = {
                'available': True,
                'codecs': ['libx264'],
                'formats': ['mp4']
            }
            
            errors = self.renderer.validate_export_settings(settings)
            self.assertGreater(len(errors), 0)
            self.assertTrue(any('even width and height' in error for error in errors))
    
    def test_validate_export_settings_invalid_crf(self):
        """Test validation with invalid CRF value."""
        settings = ExportSettings(
            output_path="test.mp4",
            crf=60  # Invalid CRF
        )
        
        with patch.object(self.renderer, 'check_ffmpeg_capabilities') as mock_check:
            mock_check.return_value = {
                'available': True,
                'codecs': ['libx264'],
                'formats': ['mp4']
            }
            
            errors = self.renderer.validate_export_settings(settings)
            self.assertTrue(any('CRF must be between 0 and 51' in error for error in errors))


class TestFFmpegCommandGeneration(unittest.TestCase):
    """Test FFmpeg command generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
        self.renderer.export_settings = ExportSettings(
            output_path="test.mp4",
            width=1920,
            height=1080,
            fps=30.0,
            bitrate=5000
        )
        
        # Create test project
        self.test_project = Project(
            id="test",
            name="Test",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=30.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            )
        )
        self.renderer.current_project = self.test_project
    
    def test_build_ffmpeg_command_basic(self):
        """Test basic FFmpeg command generation."""
        cmd = self.renderer.build_ffmpeg_command()
        
        # Check basic structure
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-y", cmd)  # Overwrite
        self.assertIn("-f", cmd)
        self.assertIn("rawvideo", cmd)
        self.assertIn("-i", cmd)
        self.assertIn("-", cmd)  # stdin
        self.assertIn("test.mp4", cmd)
    
    def test_build_ffmpeg_command_with_audio(self):
        """Test FFmpeg command with audio input."""
        cmd = self.renderer.build_ffmpeg_command()
        
        # Should include audio input (check for filename in path)
        audio_found = any("test_audio.mp3" in arg for arg in cmd)
        self.assertTrue(audio_found, f"Audio file not found in command: {cmd}")
        self.assertIn("-c:a", cmd)
        self.assertIn("aac", cmd)
        self.assertIn("-ar", cmd)  # Audio sample rate
        self.assertIn("-ac", cmd)  # Audio channels
    
    def test_build_ffmpeg_command_no_audio(self):
        """Test FFmpeg command without audio."""
        self.renderer.current_project.audio_file = None
        
        cmd = self.renderer.build_ffmpeg_command()
        
        # Should not include audio settings
        self.assertNotIn("-c:a", cmd)
    
    def test_build_ffmpeg_command_crf_mode(self):
        """Test FFmpeg command with CRF encoding."""
        self.renderer.export_settings.crf = 20
        
        cmd = self.renderer.build_ffmpeg_command()
        
        self.assertIn("-crf", cmd)
        self.assertIn("20", cmd)
    
    def test_build_ffmpeg_command_bitrate_mode(self):
        """Test FFmpeg command with bitrate encoding."""
        self.renderer.export_settings.crf = None
        self.renderer.export_settings.bitrate = 8000
        
        cmd = self.renderer.build_ffmpeg_command()
        
        self.assertIn("-b:v", cmd)
        self.assertIn("8000k", cmd)
    
    def test_build_ffmpeg_command_advanced_options(self):
        """Test FFmpeg command with advanced options."""
        self.renderer.export_settings.max_bitrate = 10000
        self.renderer.export_settings.buffer_size = 20000
        self.renderer.export_settings.preset = "slow"
        self.renderer.export_settings.profile = "main"
        
        cmd = self.renderer.build_ffmpeg_command()
        
        self.assertIn("-maxrate", cmd)
        self.assertIn("10000k", cmd)
        self.assertIn("-bufsize", cmd)
        self.assertIn("20000k", cmd)
        self.assertIn("-preset", cmd)
        self.assertIn("slow", cmd)
        self.assertIn("-profile:v", cmd)
        self.assertIn("main", cmd)
    
    def test_build_ffmpeg_command_different_formats(self):
        """Test FFmpeg command for different container formats."""
        # Test MKV
        self.renderer.export_settings.container_format = "mkv"
        cmd = self.renderer.build_ffmpeg_command()
        self.assertIn("-f", cmd)
        self.assertIn("matroska", cmd)
        
        # Test AVI
        self.renderer.export_settings.container_format = "avi"
        cmd = self.renderer.build_ffmpeg_command()
        self.assertIn("-f", cmd)
        self.assertIn("avi", cmd)


class TestFFmpegProcessManagement(unittest.TestCase):
    """Test FFmpeg process management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
        self.renderer.export_settings = ExportSettings(output_path="test.mp4")
        self.renderer.current_project = Project(id="test", name="Test")
    
    @patch('subprocess.Popen')
    @patch('pathlib.Path.mkdir')
    def test_start_ffmpeg_process_success(self, mock_mkdir, mock_popen):
        """Test successful FFmpeg process startup."""
        # Mock validation
        with patch.object(self.renderer, 'validate_export_settings') as mock_validate:
            mock_validate.return_value = []  # No errors
            
            # Mock subprocess
            mock_process = Mock()
            mock_popen.return_value = mock_process
            
            # Mock monitor thread start
            with patch.object(self.renderer, '_start_ffmpeg_monitor'):
                success = self.renderer.start_ffmpeg_process()
            
            self.assertTrue(success)
            self.assertEqual(self.renderer.ffmpeg_process, mock_process)
            mock_popen.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_start_ffmpeg_process_validation_failure(self, mock_popen):
        """Test FFmpeg process startup with validation failure."""
        with patch.object(self.renderer, 'validate_export_settings') as mock_validate:
            mock_validate.return_value = ["Test error"]
            
            success = self.renderer.start_ffmpeg_process()
            
            self.assertFalse(success)
            mock_popen.assert_not_called()
    
    @patch('subprocess.Popen')
    def test_start_ffmpeg_process_exception(self, mock_popen):
        """Test FFmpeg process startup with exception."""
        mock_popen.side_effect = Exception("Test error")
        
        with patch.object(self.renderer, 'validate_export_settings') as mock_validate:
            mock_validate.return_value = []
            
            success = self.renderer.start_ffmpeg_process()
            
            self.assertFalse(success)
    
    def test_parse_ffmpeg_progress(self):
        """Test FFmpeg progress parsing."""
        # Test FPS parsing
        self.renderer._parse_ffmpeg_progress("fps=25.5")
        self.assertEqual(self.renderer.progress.ffmpeg_fps, 25.5)
        
        # Test bitrate parsing
        self.renderer._parse_ffmpeg_progress("bitrate=1500.2kbits/s")
        self.assertEqual(self.renderer.progress.ffmpeg_bitrate, "1500.2kbits/s")
        
        # Test speed parsing
        self.renderer._parse_ffmpeg_progress("speed=1.2x")
        self.assertEqual(self.renderer.progress.ffmpeg_speed, "1.2x")
        self.assertEqual(self.renderer.progress.encoding_speed, 1.2)
    
    def test_parse_ffmpeg_error(self):
        """Test FFmpeg error parsing."""
        # Test file not found
        error = self.renderer._parse_ffmpeg_error(b"No such file or directory")
        self.assertEqual(error, "Input file not found")
        
        # Test permission denied
        error = self.renderer._parse_ffmpeg_error(b"Permission denied")
        self.assertEqual(error, "Permission denied - check file permissions")
        
        # Test unknown error
        error = self.renderer._parse_ffmpeg_error(b"Some unknown error message")
        self.assertIn("unknown error", error.lower())


class TestFrameExportPipeline(unittest.TestCase):
    """Test frame export pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
        self.renderer.export_settings = ExportSettings(
            output_path="test.mp4",
            width=640,
            height=480,
            fps=30.0
        )
        self.renderer.progress = ExportProgress(total_frames=10)
    
    def test_convert_frame_to_raw_mock(self):
        """Test frame conversion to raw bytes (mock mode)."""
        # Test with None image (should return mock data)
        frame_data = self.renderer._convert_frame_to_raw(None)
        
        expected_size = 640 * 480 * 4  # RGBA
        self.assertEqual(len(frame_data), expected_size)
    
    @patch('queue.Queue')
    def test_frame_queue_initialization(self, mock_queue_class):
        """Test frame queue initialization."""
        mock_queue = Mock()
        mock_queue.put = Mock()
        mock_queue_class.return_value = mock_queue
        
        with patch.object(self.renderer, 'start_ffmpeg_process') as mock_start:
            mock_start.return_value = True
            
            # Mock other dependencies
            with patch.object(self.renderer, '_start_frame_writer'):
                with patch.object(self.renderer, '_get_project_duration') as mock_duration:
                    mock_duration.return_value = 1.0
                    
                    # Mock render method to avoid OpenGL calls
                    with patch.object(self.renderer, 'render_frame_at_time') as mock_render:
                        mock_render.return_value = None
                        
                        # Mock frame writer thread
                        self.renderer.frame_writer_thread = Mock()
                        self.renderer.frame_writer_thread.join = Mock()
                        
                        # Mock FFmpeg process
                        self.renderer.ffmpeg_process = Mock()
                        self.renderer.ffmpeg_process.communicate.return_value = (b"", b"")
                        self.renderer.ffmpeg_process.returncode = 0
                        
                        self.renderer.export_frames()
        
        # Verify queue was created
        mock_queue_class.assert_called()
    
    def test_cancel_export_cleanup(self):
        """Test export cancellation and cleanup."""
        # Set up mock resources
        self.renderer.ffmpeg_process = Mock()
        self.renderer.frame_writer_thread = Mock()
        self.renderer.frame_writer_thread.is_alive.return_value = True
        self.renderer.frame_writer_thread.join = Mock()
        self.renderer.frame_queue = Mock()
        
        self.renderer.cancel_export()
        
        # Verify cleanup
        self.assertTrue(self.renderer.should_cancel)
        self.renderer.ffmpeg_process.terminate.assert_called_once()
        self.renderer.frame_writer_thread.join.assert_called_once()


class TestFFmpegQualityPresets(unittest.TestCase):
    """Test FFmpeg quality presets."""
    
    def test_get_presets(self):
        """Test quality preset retrieval."""
        presets = FFmpegQualityPresets.get_presets()
        
        self.assertIsInstance(presets, dict)
        self.assertIn("Web Low (480p)", presets)
        self.assertIn("HD (1080p)", presets)
        self.assertIn("4K (2160p)", presets)
        
        # Check preset structure
        hd_preset = presets["HD (1080p)"]
        self.assertEqual(hd_preset.width, 1920)
        self.assertEqual(hd_preset.height, 1080)
        self.assertIsInstance(hd_preset.bitrate, int)
    
    def test_get_format_options(self):
        """Test format options retrieval."""
        formats = FFmpegQualityPresets.get_format_options()
        
        self.assertIsInstance(formats, dict)
        self.assertIn("MP4 (H.264)", formats)
        self.assertIn("MP4 (H.265)", formats)
        self.assertIn("MKV (H.264)", formats)
        
        # Check format structure
        mp4_format = formats["MP4 (H.264)"]
        self.assertEqual(mp4_format["container_format"], "mp4")
        self.assertEqual(mp4_format["codec"], "libx264")
        self.assertIn("description", mp4_format)


class TestExportIntegration(unittest.TestCase):
    """Integration tests for export system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.renderer = create_export_renderer()
        
        # Create test project
        self.project = Project(
            id="integration_test",
            name="Integration Test",
            audio_file=AudioFile(
                path="test_audio.mp3",
                duration=2.0,  # Short duration for testing
                format="mp3",
                sample_rate=44100,
                channels=2
            )
        )
        
        self.settings = ExportSettings(
            output_path=os.path.join(self.temp_dir, "test_output.mp4"),
            width=640,
            height=480,
            fps=10.0  # Low FPS for faster testing
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_export_setup(self):
        """Test complete export setup process."""
        # Mock OpenGL initialization to avoid access violations in test environment
        with patch.object(self.renderer, 'initialize_opengl_context') as mock_gl:
            mock_gl.return_value = True
            with patch.object(self.renderer, 'create_framebuffer') as mock_fb:
                mock_fb.return_value = True
                with patch.object(self.renderer, 'initialize_subtitle_renderer') as mock_sub:
                    mock_sub.return_value = True
                    
                    success = self.renderer.setup_export(self.project, self.settings)
        
        # Should succeed with mocked implementation
        self.assertTrue(success)
        self.assertEqual(self.renderer.current_project, self.project)
        self.assertEqual(self.renderer.export_settings, self.settings)
    
    @patch('subprocess.Popen')
    def test_export_with_mocked_ffmpeg(self, mock_popen):
        """Test export process with mocked FFmpeg."""
        # Mock FFmpeg process
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdin = Mock()
        mock_process.communicate.return_value = (b"", b"")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Set up renderer
        self.renderer.setup_export(self.project, self.settings)
        
        # Mock validation and other dependencies
        with patch.object(self.renderer, 'validate_export_settings') as mock_validate:
            mock_validate.return_value = []
            
            with patch.object(self.renderer, 'render_frame_at_time') as mock_render:
                mock_render.return_value = None  # Mock frame
                
                # Start export
                success = self.renderer.start_export_async()
                self.assertTrue(success)
    
    def test_quality_preset_application(self):
        """Test applying quality presets."""
        presets = FFmpegQualityPresets.get_presets()
        
        for preset_name, preset_settings in presets.items():
            # Apply preset to our settings
            test_settings = ExportSettings(
                output_path=self.settings.output_path,
                width=preset_settings.width,
                height=preset_settings.height,
                fps=preset_settings.fps,
                bitrate=preset_settings.bitrate,
                preset=preset_settings.preset,
                crf=preset_settings.crf
            )
            
            # Validate settings
            with patch.object(self.renderer, 'check_ffmpeg_capabilities') as mock_check:
                mock_check.return_value = {
                    'available': True,
                    'codecs': ['libx264', 'aac'],
                    'formats': ['mp4']
                }
                
                errors = self.renderer.validate_export_settings(test_settings)
                self.assertEqual(len(errors), 0, f"Preset {preset_name} validation failed: {errors}")


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of export system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = OpenGLExportRenderer()
    
    def test_concurrent_progress_updates(self):
        """Test concurrent progress updates."""
        # Simulate multiple threads updating progress
        def update_progress(thread_id):
            for i in range(10):
                self.renderer.progress.current_frame = thread_id * 10 + i
                self.renderer.progress.status = f"Thread {thread_id} frame {i}"
                time.sleep(0.001)  # Small delay
        
        threads = []
        for i in range(3):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        self.assertGreaterEqual(self.renderer.progress.current_frame, 0)
    
    def test_cancel_during_export(self):
        """Test cancellation during export."""
        self.renderer.is_exporting = True
        self.renderer.should_cancel = False
        
        # Mock FFmpeg process
        self.renderer.ffmpeg_process = Mock()
        
        # Cancel in separate thread
        def cancel_export():
            time.sleep(0.1)
            self.renderer.cancel_export()
        
        cancel_thread = threading.Thread(target=cancel_export)
        cancel_thread.start()
        
        # Wait for cancellation
        cancel_thread.join()
        
        self.assertTrue(self.renderer.should_cancel)
        self.renderer.ffmpeg_process.terminate.assert_called_once()


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)