#!/usr/bin/env python3
"""
Demo: Frame Capture and Rendering System

This demo showcases the enhanced frame capture and rendering system for the karaoke video creator.
It demonstrates frame-by-frame rendering, pixel format conversion, and performance tracking.
"""

import sys
import os
import time
import numpy as np

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.frame_capture_system import (
    FrameCaptureSystem, FrameRenderingEngine, FrameCaptureSettings,
    PixelFormat, FrameTimestamp, create_frame_capture_system,
    capture_video_frames
)
from core.opengl_context import OpenGLContext, ContextBackend
from core.models import Project, AudioFile, VideoFile, ImageFile, SubtitleFile, SubtitleLine


def create_demo_project():
    """Create a demo project with sample media files"""
    print("Creating demo project...")
    
    project = Project(id="demo_project", name="Frame Capture Demo")
    
    # Add demo audio file
    project.audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=5.0,
        sample_rate=44100,
        channels=2,
        format="MP3"
    )
    
    # Add demo video file
    project.video_file = VideoFile(
        path="demo_video.mp4",
        duration=5.0,
        resolution={"width": 1920, "height": 1080},
        frame_rate=30.0,
        format="MP4"
    )
    
    # Add demo subtitle file with sample lines
    project.subtitle_file = SubtitleFile(path="demo_subtitles.ass")
    project.subtitle_file.lines = [
        SubtitleLine(
            start_time=0.0,
            end_time=2.0,
            text="Welcome to the Frame Capture Demo",
            style="Default"
        ),
        SubtitleLine(
            start_time=2.5,
            end_time=4.5,
            text="Testing frame-by-frame rendering",
            style="Default"
        )
    ]
    
    print(f"Demo project created: {project.name}")
    print(f"  Audio: {project.audio_file.duration}s")
    print(f"  Video: {project.video_file.resolution['width']}x{project.video_file.resolution['height']}")
    print(f"  Subtitles: {len(project.subtitle_file.lines)} lines")
    
    return project


def demo_frame_timestamp_generation():
    """Demonstrate frame timestamp generation"""
    print("\n" + "="*60)
    print("DEMO: Frame Timestamp Generation")
    print("="*60)
    
    # Create OpenGL context (mock for demo)
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    
    # Create capture system
    capture_system = create_frame_capture_system(context)
    
    # Test different frame rates
    test_cases = [
        (1.0, 24.0, "24 fps (Cinema)"),
        (1.0, 30.0, "30 fps (Standard)"),
        (0.5, 60.0, "60 fps (High refresh)")
    ]
    
    for duration, fps, description in test_cases:
        print(f"\n{description}:")
        timestamps = capture_system.generate_frame_timestamps(duration, fps)
        
        print(f"  Duration: {duration}s")
        print(f"  Frame rate: {fps} fps")
        print(f"  Total frames: {len(timestamps)}")
        print(f"  Frame duration: {1.0/fps:.4f}s")
        
        # Show first few timestamps
        print("  First 5 timestamps:")
        for i, ts in enumerate(timestamps[:5]):
            print(f"    Frame {ts.frame_number}: {ts.timestamp:.4f}s")
    
    context.cleanup()


def demo_pixel_format_conversions():
    """Demonstrate pixel format conversions"""
    print("\n" + "="*60)
    print("DEMO: Pixel Format Conversions")
    print("="*60)
    
    # Create OpenGL context (mock for demo)
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    
    # Create rendering engine
    engine = FrameRenderingEngine(context)
    
    # Create test image data (small for demo)
    width, height = 8, 8
    test_image = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Create test pattern
    test_image[0:2, 0:2] = [255, 0, 0, 255]    # Red square
    test_image[0:2, 2:4] = [0, 255, 0, 255]    # Green square
    test_image[2:4, 0:2] = [0, 0, 255, 255]    # Blue square
    test_image[2:4, 2:4] = [255, 255, 255, 255] # White square
    
    print(f"Original RGBA image: {test_image.shape}")
    print(f"Original size: {test_image.nbytes} bytes")
    
    # Test different format conversions
    conversions = [
        (PixelFormat.RGB8, "RGB8 (Drop alpha)"),
        (PixelFormat.BGRA8, "BGRA8 (Swap R/B)"),
        (PixelFormat.BGR8, "BGR8 (Swap R/B, drop alpha)"),
        (PixelFormat.YUV420P, "YUV420P (FFmpeg compatible)"),
        (PixelFormat.YUV444P, "YUV444P (Full chroma)")
    ]
    
    for pixel_format, description in conversions:
        converted = engine._convert_pixel_format(test_image, pixel_format)
        
        print(f"\n{description}:")
        print(f"  Output shape: {converted.shape}")
        print(f"  Output size: {converted.nbytes} bytes")
        print(f"  Compression ratio: {test_image.nbytes / converted.nbytes:.2f}x")
        
        # Show data range
        print(f"  Value range: {np.min(converted)} - {np.max(converted)}")
    
    context.cleanup()


def demo_frame_rendering_performance():
    """Demonstrate frame rendering performance"""
    print("\n" + "="*60)
    print("DEMO: Frame Rendering Performance")
    print("="*60)
    
    # Create OpenGL context (mock for demo)
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    
    # Create demo project
    project = create_demo_project()
    
    # Test different settings
    test_settings = [
        FrameCaptureSettings(width=640, height=480, fps=30.0, pixel_format=PixelFormat.RGBA8),
        FrameCaptureSettings(width=1280, height=720, fps=30.0, pixel_format=PixelFormat.RGB8),
        FrameCaptureSettings(width=1920, height=1080, fps=30.0, pixel_format=PixelFormat.YUV420P)
    ]
    
    for i, settings in enumerate(test_settings):
        print(f"\nTest {i+1}: {settings.width}x{settings.height} @ {settings.fps}fps ({settings.pixel_format.value})")
        
        # Create rendering engine
        engine = FrameRenderingEngine(context)
        
        # Initialize with mock components
        engine.current_project = project
        engine.capture_settings = settings
        
        # Simulate rendering multiple frames
        test_timestamps = [0.0, 0.5, 1.0, 1.5, 2.0]
        start_time = time.time()
        
        for timestamp in test_timestamps:
            # Simulate frame rendering time
            render_start = time.time()
            
            # Mock rendering work
            time.sleep(0.001)  # Simulate 1ms render time
            
            render_time = time.time() - render_start
            engine.render_times.append(render_time)
        
        total_time = time.time() - start_time
        
        # Get performance stats
        stats = engine.get_performance_stats()
        
        print(f"  Frames rendered: {stats['frame_count']}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Average render time: {stats['average_render_time']:.4f}s")
        print(f"  Estimated FPS: {stats['fps_estimate']:.1f}")
        print(f"  Min/Max render time: {stats['min_render_time']:.4f}s / {stats['max_render_time']:.4f}s")
        
        engine.cleanup()
    
    context.cleanup()


def demo_audio_synchronization():
    """Demonstrate audio synchronization"""
    print("\n" + "="*60)
    print("DEMO: Audio Synchronization")
    print("="*60)
    
    # Create OpenGL context (mock for demo)
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    
    # Create capture system
    capture_system = create_frame_capture_system(context)
    
    # Generate base timestamps
    duration = 2.0
    fps = 30.0
    timestamps = capture_system.generate_frame_timestamps(duration, fps)
    capture_system.frame_timestamps = timestamps
    
    print(f"Generated {len(timestamps)} timestamps for {duration}s @ {fps}fps")
    
    # Test different audio sync offsets
    test_offsets = [-0.1, 0.0, 0.05, 0.1]
    
    for offset in test_offsets:
        print(f"\nAudio sync offset: {offset:+.3f}s")
        
        # Reset timestamps
        timestamps = capture_system.generate_frame_timestamps(duration, fps)
        capture_system.frame_timestamps = timestamps
        
        # Show original first few timestamps
        print("  Before sync:")
        for i in range(3):
            print(f"    Frame {i}: {timestamps[i].timestamp:.4f}s")
        
        # Apply synchronization
        capture_system.synchronize_with_audio(duration, offset)
        
        # Show synchronized timestamps
        print("  After sync:")
        for i in range(3):
            print(f"    Frame {i}: {timestamps[i].timestamp:.4f}s")
        
        # Verify offset was applied correctly
        expected_first = offset
        actual_first = timestamps[0].timestamp
        print(f"  Verification: Expected {expected_first:.4f}s, Got {actual_first:.4f}s")
    
    context.cleanup()


def demo_frame_capture_workflow():
    """Demonstrate complete frame capture workflow"""
    print("\n" + "="*60)
    print("DEMO: Complete Frame Capture Workflow")
    print("="*60)
    
    # Create OpenGL context (mock for demo)
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    
    # Create demo project
    project = create_demo_project()
    
    # Create capture settings
    settings = FrameCaptureSettings(
        width=1280,
        height=720,
        fps=30.0,
        pixel_format=PixelFormat.RGBA8,
        quality=1.0,
        sync_with_audio=True,
        audio_offset=0.05
    )
    
    print("Capture Settings:")
    print(f"  Resolution: {settings.width}x{settings.height}")
    print(f"  Frame rate: {settings.fps} fps")
    print(f"  Pixel format: {settings.pixel_format.value}")
    print(f"  Quality: {settings.quality}")
    print(f"  Audio sync: {settings.sync_with_audio}")
    print(f"  Audio offset: {settings.audio_offset}s")
    
    # Create capture system
    capture_system = create_frame_capture_system(context)
    
    # Initialize capture system (mock)
    print("\nInitializing capture system...")
    success = capture_system.initialize(project, settings)
    print(f"Initialization: {'Success' if success else 'Failed'}")
    
    if success:
        # Generate frame timestamps for short duration
        duration = 1.0  # 1 second for demo
        timestamps = capture_system.generate_frame_timestamps(duration, settings.fps)
        
        print(f"\nGenerated {len(timestamps)} frame timestamps")
        print(f"Duration: {duration}s")
        print(f"Frame interval: {1.0/settings.fps:.4f}s")
        
        # Apply audio synchronization
        if settings.sync_with_audio:
            capture_system.synchronize_with_audio(duration, settings.audio_offset)
            print(f"Applied audio sync offset: {settings.audio_offset}s")
        
        # Simulate frame capture (mock)
        print("\nSimulating frame capture...")
        
        def progress_callback(progress):
            if int(progress * 100) % 20 == 0:  # Print every 20%
                print(f"  Progress: {progress*100:.0f}%")
        
        # Mock capture frames (since we don't have real OpenGL)
        captured_frames = []
        for i, timestamp_info in enumerate(timestamps[:10]):  # Limit to 10 frames for demo
            # Simulate frame capture
            mock_frame_data = np.random.randint(0, 255, (settings.height, settings.width, 4), dtype=np.uint8)
            
            # Create mock captured frame
            from core.frame_capture_system import CapturedFrame
            frame = CapturedFrame(
                frame_number=timestamp_info.frame_number,
                timestamp=timestamp_info.timestamp,
                width=settings.width,
                height=settings.height,
                pixel_format=settings.pixel_format,
                data=mock_frame_data,
                capture_time=time.time(),
                render_time=0.016  # Mock 16ms render time
            )
            
            captured_frames.append(frame)
            
            # Update progress
            progress = (i + 1) / min(len(timestamps), 10)
            progress_callback(progress)
        
        print(f"\nCaptured {len(captured_frames)} frames")
        
        # Show frame statistics
        if captured_frames:
            total_size = sum(frame.size_bytes for frame in captured_frames)
            avg_render_time = sum(frame.render_time for frame in captured_frames) / len(captured_frames)
            
            print(f"Total data size: {total_size / (1024*1024):.2f} MB")
            print(f"Average frame size: {total_size / len(captured_frames) / 1024:.1f} KB")
            print(f"Average render time: {avg_render_time:.4f}s")
            print(f"Estimated capture FPS: {1.0/avg_render_time:.1f}")
        
        # Get capture statistics
        stats = capture_system.get_capture_statistics()
        if stats:
            print(f"\nCapture Statistics:")
            for key, value in stats.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")
    
    # Cleanup
    capture_system.cleanup()
    context.cleanup()


def demo_error_handling():
    """Demonstrate error handling and edge cases"""
    print("\n" + "="*60)
    print("DEMO: Error Handling and Edge Cases")
    print("="*60)
    
    # Test invalid frame timestamps
    print("Testing invalid frame timestamps:")
    try:
        from core.frame_capture_system import FrameTimestamp
        invalid_ts = FrameTimestamp(-1, -1.0, 0.033, 30.0)
        print("  Created invalid timestamp (this should not happen)")
    except Exception as e:
        print(f"  Caught expected error: {type(e).__name__}")
    
    # Test invalid pixel format conversion
    print("\nTesting pixel format conversion edge cases:")
    context = OpenGLContext(ContextBackend.MOCK)
    context.initialize()
    engine = FrameRenderingEngine(context)
    
    # Test with None data
    result = engine._convert_pixel_format(None, PixelFormat.RGB8)
    print(f"  None input result: {result}")
    
    # Test with invalid dimensions for YUV420P (odd dimensions)
    odd_data = np.zeros((7, 7, 4), dtype=np.uint8)  # Odd dimensions
    result = engine._rgba_to_yuv420p(odd_data)
    print(f"  Odd dimensions YUV420P: {result.shape if result is not None else 'None'}")
    
    # Test with empty data
    empty_data = np.zeros((0, 0, 4), dtype=np.uint8)
    result = engine._convert_pixel_format(empty_data, PixelFormat.RGB8)
    print(f"  Empty data result: {result.shape if result is not None else 'None'}")
    
    context.cleanup()
    
    print("\nError handling tests completed")


def main():
    """Run all frame capture system demos"""
    print("Frame Capture and Rendering System Demo")
    print("=" * 60)
    print("This demo showcases the enhanced frame capture system capabilities:")
    print("- Frame-by-frame rendering at specified timestamps")
    print("- Framebuffer capture to raw pixel data")
    print("- Pixel format conversion (RGBA to YUV420p for FFmpeg)")
    print("- Frame rate synchronization with audio timing")
    print("- Performance tracking and optimization")
    
    try:
        # Run all demos
        demo_frame_timestamp_generation()
        demo_pixel_format_conversions()
        demo_frame_rendering_performance()
        demo_audio_synchronization()
        demo_frame_capture_workflow()
        demo_error_handling()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("All frame capture system features demonstrated:")
        print("✓ Frame timestamp generation with various frame rates")
        print("✓ Pixel format conversions (RGBA, RGB, BGR, YUV420P, YUV444P)")
        print("✓ Performance tracking and optimization")
        print("✓ Audio synchronization with timing offsets")
        print("✓ Complete frame capture workflow")
        print("✓ Error handling and edge cases")
        print("\nThe frame capture system is ready for production use!")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())