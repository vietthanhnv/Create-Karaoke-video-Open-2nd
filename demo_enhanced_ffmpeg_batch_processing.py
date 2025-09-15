#!/usr/bin/env python3
"""
Enhanced FFmpeg Integration and Batch Processing Demo

This demo showcases the enhanced FFmpeg integration with:
- Better error handling and progress tracking
- Optimized raw frame data streaming pipeline
- Advanced export settings configuration
- Batch processing capabilities
- Comprehensive validation and optimization
"""

import os
import sys
import time
import numpy as np
from typing import Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.enhanced_ffmpeg_integration import (
    EnhancedFFmpegProcessor, EnhancedExportSettings, BatchFFmpegProcessor,
    FFmpegPreset, VideoCodec, AudioCodec, ContainerFormat,
    create_enhanced_ffmpeg_processor, get_ffmpeg_capabilities,
    create_optimized_export_settings, create_web_optimized_settings,
    create_mobile_optimized_settings, create_batch_processor
)
from core.frame_capture_system import CapturedFrame, PixelFormat


def create_test_frame(frame_number: int, width: int = 640, height: int = 480) -> CapturedFrame:
    """Create a test frame with animated content"""
    # Create a simple animated pattern
    data = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Create animated gradient
    for y in range(height):
        for x in range(width):
            # Animated color based on frame number and position
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = int(((frame_number % 60) / 60) * 255)
            a = 255
            
            data[y, x] = [r, g, b, a]
    
    return CapturedFrame(
        frame_number=frame_number,
        timestamp=frame_number / 30.0,  # 30 FPS
        width=width,
        height=height,
        pixel_format=PixelFormat.RGBA8,
        data=data,
        capture_time=time.time(),
        render_time=0.033
    )


def demo_ffmpeg_capabilities():
    """Demo FFmpeg capabilities detection"""
    print("=== FFmpeg Capabilities Detection ===")
    
    capabilities = get_ffmpeg_capabilities()
    
    print(f"FFmpeg Available: {capabilities.available}")
    if capabilities.available:
        print(f"Version: {capabilities.version}")
        print(f"Supported Codecs: {len(capabilities.supported_codecs)}")
        print(f"  Video: {[c for c in capabilities.supported_codecs if 'x264' in c or 'x265' in c or 'vp9' in c]}")
        print(f"  Audio: {[c for c in capabilities.supported_codecs if c in ['aac', 'libmp3lame', 'libopus']]}")
        print(f"Supported Formats: {capabilities.supported_formats[:10]}...")  # Show first 10
        print(f"Hardware Acceleration: {capabilities.hardware_acceleration}")
    else:
        print(f"Error: {capabilities.error_message}")
    
    print()


def demo_export_settings_optimization():
    """Demo different export settings optimizations"""
    print("=== Export Settings Optimization ===")
    
    # Test different quality presets
    quality_levels = ["high", "medium", "low", "ultrafast", "lossless"]
    
    for quality in quality_levels:
        settings = create_optimized_export_settings(
            f"output_{quality}.mp4",
            width=1280,
            height=720,
            quality=quality
        )
        
        print(f"{quality.upper()} Quality Settings:")
        print(f"  CRF: {settings.crf}, Bitrate: {settings.bitrate}")
        print(f"  Preset: {settings.preset.value}")
        print(f"  Audio Bitrate: {settings.audio_bitrate}kbps")
        if settings.profile:
            print(f"  Profile: {settings.profile}")
        print()
    
    # Test specialized settings
    print("Web Optimized Settings:")
    web_settings = create_web_optimized_settings("web_output.mp4")
    print(f"  Resolution: {web_settings.width}x{web_settings.height}")
    print(f"  Profile: {web_settings.profile}, Level: {web_settings.level}")
    print(f"  Metadata: {web_settings.metadata}")
    print()
    
    print("Mobile Optimized Settings:")
    mobile_settings = create_mobile_optimized_settings("mobile_output.mp4")
    print(f"  Resolution: {mobile_settings.width}x{mobile_settings.height}")
    print(f"  Profile: {mobile_settings.profile}, Level: {mobile_settings.level}")
    print(f"  Audio Bitrate: {mobile_settings.audio_bitrate}kbps")
    print()


def demo_settings_validation():
    """Demo enhanced settings validation"""
    print("=== Settings Validation Demo ===")
    
    processor = create_enhanced_ffmpeg_processor()
    
    # Test valid settings
    print("Valid Settings:")
    valid_settings = EnhancedExportSettings(
        output_path="valid_output.mp4",
        width=1920,
        height=1080,
        fps=30.0,
        crf=23
    )
    
    errors = processor.validate_settings(valid_settings)
    if not errors:
        print("  ✓ All settings are valid")
    else:
        print(f"  Validation issues: {len(errors)}")
        for error in errors[:3]:  # Show first 3
            print(f"    - {error}")
    print()
    
    # Test settings with warnings
    print("Settings with Warnings:")
    warning_settings = EnhancedExportSettings(
        output_path="warning_output.mp4",
        width=1921,  # Odd width
        height=1079,  # Odd height
        fps=200.0,   # Very high fps
        crf=5,       # Very low CRF
        audio_bitrate=32  # Low audio bitrate
    )
    
    errors = processor.validate_settings(warning_settings)
    warnings = [e for e in errors if e.startswith("Warning:")]
    print(f"  Warnings: {len(warnings)}")
    for warning in warnings[:3]:  # Show first 3
        print(f"    - {warning}")
    print()
    
    # Test invalid settings
    print("Invalid Settings:")
    invalid_settings = EnhancedExportSettings(
        output_path="invalid_output.mp4",
        width=-100,   # Invalid width
        height=0,     # Invalid height
        fps=-30.0,    # Invalid fps
        crf=100,      # Invalid CRF
        bitrate=-1000 # Invalid bitrate
    )
    
    errors = processor.validate_settings(invalid_settings)
    hard_errors = [e for e in errors if not e.startswith("Warning:")]
    print(f"  Errors: {len(hard_errors)}")
    for error in hard_errors[:3]:  # Show first 3
        print(f"    - {error}")
    print()


def demo_batch_processing():
    """Demo batch processing capabilities"""
    print("=== Batch Processing Demo ===")
    
    # Create batch processor
    batch_processor = create_batch_processor(max_concurrent_jobs=2)
    
    print(f"Created batch processor with max {batch_processor.max_concurrent_jobs} concurrent jobs")
    
    # Add multiple jobs
    jobs_data = [
        ("job_1", "batch_output_1.mp4", "high", 1920, 1080),
        ("job_2", "batch_output_2.mp4", "medium", 1280, 720),
        ("job_3", "batch_output_3.mp4", "low", 854, 480),
    ]
    
    for job_id, output_path, quality, width, height in jobs_data:
        settings = create_optimized_export_settings(
            output_path,
            width=width,
            height=height,
            quality=quality
        )
        
        # Create a simple frame source for demo
        def create_frame_source(total_frames=60):
            frame_count = 0
            def frame_source():
                nonlocal frame_count
                if frame_count < total_frames:
                    frame = create_test_frame(frame_count, width, height)
                    frame_count += 1
                    return frame
                return None
            return frame_source
        
        job = batch_processor.add_export_job(
            job_id=job_id,
            settings=settings,
            frame_source=create_frame_source(),
            total_frames=60
        )
        
        print(f"Added job: {job_id} ({quality} quality, {width}x{height})")
    
    # Show batch status
    status = batch_processor.get_batch_status()
    print(f"\nBatch Status:")
    print(f"  Total Jobs: {len(batch_processor.jobs)}")
    print(f"  Pending Jobs: {status['pending_jobs']}")
    print(f"  Is Processing: {status['is_processing']}")
    
    # Show individual job statuses
    print(f"\nJob Statuses:")
    for job in batch_processor.jobs:
        job_status = batch_processor.get_job_status(job.job_id)
        if job_status:
            print(f"  {job_status['job_id']}: {job_status['status']}")
    
    print("\nNote: Actual batch processing would require starting the batch with start_batch_processing()")
    print()


def demo_command_building():
    """Demo FFmpeg command building"""
    print("=== FFmpeg Command Building Demo ===")
    
    processor = create_enhanced_ffmpeg_processor()
    
    # Test different command configurations
    configs = [
        ("Basic H.264", EnhancedExportSettings(
            output_path="basic.mp4",
            video_codec=VideoCodec.H264,
            crf=23
        )),
        ("High Quality H.265", EnhancedExportSettings(
            output_path="high_quality.mp4",
            video_codec=VideoCodec.H265,
            crf=18,
            preset=FFmpegPreset.SLOW,
            profile="main",
            tune="film"
        )),
        ("Web Optimized", EnhancedExportSettings(
            output_path="web.mp4",
            width=1280,
            height=720,
            video_codec=VideoCodec.H264,
            crf=23,
            preset=FFmpegPreset.MEDIUM,
            profile="main",
            level="3.1",
            custom_filters=["scale=1280:720"],
            metadata={"title": "Web Video"}
        )),
    ]
    
    for name, settings in configs:
        print(f"{name}:")
        cmd = processor.build_ffmpeg_command(settings)
        
        # Show key parts of the command
        key_parts = []
        for i, arg in enumerate(cmd):
            if arg in ["-c:v", "-crf", "-preset", "-profile:v", "-s", "-r"]:
                if i + 1 < len(cmd):
                    key_parts.append(f"{arg} {cmd[i + 1]}")
        
        print(f"  Key parameters: {', '.join(key_parts)}")
        print(f"  Output: {settings.output_path}")
        print()


def main():
    """Main demo function"""
    print("Enhanced FFmpeg Integration and Batch Processing Demo")
    print("=" * 60)
    print()
    
    try:
        # Run all demos
        demo_ffmpeg_capabilities()
        demo_export_settings_optimization()
        demo_settings_validation()
        demo_batch_processing()
        demo_command_building()
        
        print("Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Enhanced FFmpeg capabilities detection")
        print("✓ Optimized export settings for different use cases")
        print("✓ Comprehensive settings validation with warnings")
        print("✓ Batch processing system for multiple jobs")
        print("✓ Advanced FFmpeg command building")
        print("✓ Better error handling and progress tracking")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())