"""
Demo test for FFmpeg integration functionality
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch

# Import the modules to test
try:
    from src.core.opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, FFmpegQualityPresets
    )
    from src.core.export_manager import ExportManager, ExportConfiguration
    from src.core.models import Project, AudioFile, VideoFile
except ImportError:
    import sys
    sys.path.append('src/core')
    from opengl_export_renderer import (
        OpenGLExportRenderer, ExportSettings, FFmpegQualityPresets
    )
    from export_manager import ExportManager, ExportConfiguration
    from models import Project, AudioFile, VideoFile


class TestFFmpegIntegrationDemo(unittest.TestCase):
    """Demo test showing FFmpeg integration capabilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test project
        self.project = Project(
            id="demo_project",
            name="Demo Project",
            audio_file=AudioFile(
                path="demo_audio.mp3",
                duration=10.0,
                format="mp3",
                sample_rate=44100,
                channels=2
            ),
            video_file=VideoFile(
                path="demo_video.mp4",
                duration=10.0,
                resolution={"width": 1920, "height": 1080},
                format="mp4",
                frame_rate=30.0
            )
        )
    
    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_ffmpeg_capability_detection(self):
        """Test FFmpeg capability detection."""
        renderer = OpenGLExportRenderer()
        
        # Mock FFmpeg being available
        with patch('subprocess.run') as mock_run:
            # Mock version check
            version_result = Mock()
            version_result.returncode = 0
            version_result.stdout = "ffmpeg version 4.4.0-0ubuntu1"
            
            # Mock codec check
            codec_result = Mock()
            codec_result.returncode = 0
            codec_result.stdout = """
            DEV.LS h264                 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
            D.V.L. libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (encoder)
            DEA.L. aac                  AAC (Advanced Audio Coding) (encoder)
            """
            
            # Mock format check
            format_result = Mock()
            format_result.returncode = 0
            format_result.stdout = """
            E mp4             MP4 (MPEG-4 Part 14) (muxer)
            E mkv             Matroska (muxer)
            """
            
            mock_run.side_effect = [version_result, codec_result, format_result]
            
            capabilities = renderer.check_ffmpeg_capabilities()
            
            print(f"FFmpeg Available: {capabilities['available']}")
            print(f"FFmpeg Version: {capabilities['version']}")
            print(f"Supported Codecs: {capabilities['codecs']}")
            print(f"Supported Formats: {capabilities['formats']}")
            
            self.assertTrue(capabilities['available'])
            self.assertEqual(capabilities['version'], '4.4.0-0ubuntu1')
            self.assertIn('libx264', capabilities['codecs'])
            self.assertIn('mp4', capabilities['formats'])
    
    def test_quality_presets_demo(self):
        """Demonstrate quality presets functionality."""
        presets = FFmpegQualityPresets.get_presets()
        
        print("\nAvailable Quality Presets:")
        for name, settings in presets.items():
            print(f"  {name}:")
            print(f"    Resolution: {settings.width}x{settings.height}")
            print(f"    Bitrate: {settings.bitrate} kbps")
            print(f"    Preset: {settings.preset}")
            if settings.crf:
                print(f"    CRF: {settings.crf}")
        
        # Test that all presets are valid
        renderer = OpenGLExportRenderer()
        
        with patch.object(renderer, 'check_ffmpeg_capabilities') as mock_check:
            mock_check.return_value = {
                'available': True,
                'codecs': ['libx264', 'libx265', 'aac'],
                'formats': ['mp4', 'mkv', 'avi']
            }
            
            for preset_name, preset_settings in presets.items():
                test_settings = ExportSettings(
                    output_path=os.path.join(self.temp_dir, f"{preset_name}.mp4"),
                    width=preset_settings.width,
                    height=preset_settings.height,
                    fps=preset_settings.fps,
                    bitrate=preset_settings.bitrate,
                    preset=preset_settings.preset,
                    crf=preset_settings.crf
                )
                
                errors = renderer.validate_export_settings(test_settings)
                self.assertEqual(len(errors), 0, f"Preset {preset_name} validation failed: {errors}")
    
    def test_ffmpeg_command_generation_demo(self):
        """Demonstrate FFmpeg command generation."""
        renderer = OpenGLExportRenderer()
        renderer.current_project = self.project
        
        # Test different export scenarios
        scenarios = [
            ("Basic HD Export", ExportSettings(
                output_path=os.path.join(self.temp_dir, "basic_hd.mp4"),
                width=1920,
                height=1080,
                fps=30.0,
                bitrate=8000
            )),
            ("High Quality CRF", ExportSettings(
                output_path=os.path.join(self.temp_dir, "high_quality.mp4"),
                width=1920,
                height=1080,
                fps=30.0,
                crf=18,
                preset="slow"
            )),
            ("4K Export", ExportSettings(
                output_path=os.path.join(self.temp_dir, "4k_export.mp4"),
                width=3840,
                height=2160,
                fps=30.0,
                bitrate=25000,
                preset="medium"
            ))
        ]
        
        print("\nFFmpeg Command Generation Demo:")
        for scenario_name, settings in scenarios:
            renderer.export_settings = settings
            
            try:
                cmd = renderer.build_ffmpeg_command()
                print(f"\n{scenario_name}:")
                print(f"  Command: {' '.join(cmd[:10])}... (truncated)")
                print(f"  Resolution: {settings.width}x{settings.height}")
                print(f"  Bitrate: {settings.bitrate if not settings.crf else f'CRF {settings.crf}'}")
                print(f"  Preset: {settings.preset}")
                
                # Verify command structure
                self.assertIn("ffmpeg", cmd)
                self.assertIn("-y", cmd)
                self.assertIn(str(settings.width), ' '.join(cmd))
                self.assertIn(str(settings.height), ' '.join(cmd))
                
            except Exception as e:
                self.fail(f"Command generation failed for {scenario_name}: {e}")
    
    def test_export_manager_integration_demo(self):
        """Demonstrate export manager integration with FFmpeg."""
        manager = ExportManager()
        manager.set_project(self.project)
        
        # Create export configuration
        config = ExportConfiguration(
            width=1280,
            height=720,
            fps=30.0,
            bitrate=5000,
            output_dir=self.temp_dir,
            filename="demo_export.mp4"
        )
        
        print("\nExport Manager Integration Demo:")
        
        # Test validation
        with patch.object(manager, '_check_ffmpeg_available') as mock_ffmpeg:
            mock_ffmpeg.return_value = True
            
            validation_results = manager.validate_export_requirements(config)
            
            print(f"Validation Results: {len(validation_results)} items")
            for result in validation_results:
                print(f"  {result.level.name}: {result.message}")
            
            # Should have minimal validation issues with complete project
            error_count = sum(1 for r in validation_results if r.level.name == 'ERROR')
            self.assertLessEqual(error_count, 1)  # Allow for missing subtitle warning
        
        # Test export settings conversion
        export_settings = config.to_export_settings()
        print(f"\nExport Settings:")
        print(f"  Output: {export_settings.output_path}")
        print(f"  Resolution: {export_settings.width}x{export_settings.height}")
        print(f"  Codec: {export_settings.codec}")
        print(f"  Bitrate: {export_settings.bitrate} kbps")
        
        self.assertEqual(export_settings.width, 1280)
        self.assertEqual(export_settings.height, 720)
        self.assertEqual(export_settings.codec, "libx264")
    
    def test_format_options_demo(self):
        """Demonstrate format options."""
        formats = FFmpegQualityPresets.get_format_options()
        
        print("\nSupported Export Formats:")
        for format_name, format_info in formats.items():
            print(f"  {format_name}:")
            print(f"    Container: {format_info['container_format']}")
            print(f"    Video Codec: {format_info['codec']}")
            print(f"    Audio Codec: {format_info['audio_codec']}")
            print(f"    Description: {format_info['description']}")
        
        # Verify format structure
        self.assertIn("MP4 (H.264)", formats)
        self.assertIn("MP4 (H.265)", formats)
        
        mp4_format = formats["MP4 (H.264)"]
        self.assertEqual(mp4_format["container_format"], "mp4")
        self.assertEqual(mp4_format["codec"], "libx264")


if __name__ == '__main__':
    # Run demo tests with output
    unittest.main(verbosity=2, buffer=False)