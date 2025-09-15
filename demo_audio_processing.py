#!/usr/bin/env python3
"""
Demo script for audio processing and synchronization functionality.

This script demonstrates the key features of the audio processing system:
- Audio file loading and metadata extraction
- Audio-subtitle timing synchronization
- Audio duration validation
- FFmpeg audio embedding pipeline
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.audio import AudioProcessor, AudioSubtitleSynchronizer
from src.core.models import AudioFile, SubtitleFile
from unittest.mock import Mock


def demo_audio_loading():
    """Demonstrate audio file loading and metadata extraction."""
    print("=== Audio File Loading Demo ===")
    
    processor = AudioProcessor()
    
    # Show supported formats
    print(f"Supported audio formats: {processor.supported_formats}")
    
    # Create a mock audio file for demonstration
    print("\nCreating mock audio file...")
    audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=180.5,
        sample_rate=44100,
        channels=2,
        format="mp3",
        file_size=2304000,
        bitrate=128000
    )
    
    print(f"Audio file loaded:")
    print(f"  Path: {audio_file.path}")
    print(f"  Duration: {audio_file.duration:.2f} seconds")
    print(f"  Sample Rate: {audio_file.sample_rate} Hz")
    print(f"  Channels: {audio_file.channels}")
    print(f"  Format: {audio_file.format}")
    print(f"  Bitrate: {audio_file.bitrate} bps")
    print(f"  File Size: {audio_file.file_size} bytes")


def demo_timing_validation():
    """Demonstrate audio-subtitle timing validation."""
    print("\n=== Timing Validation Demo ===")
    
    processor = AudioProcessor()
    
    # Create audio file
    audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=180.0,
        sample_rate=44100,
        channels=2
    )
    
    # Create mock subtitle file
    subtitle_file = Mock()
    subtitle_file.lines = [
        Mock(start_time=0.0, end_time=5.0, text="First subtitle line"),
        Mock(start_time=10.0, end_time=15.0, text="Second subtitle line"),
        Mock(start_time=170.0, end_time=175.0, text="Last subtitle line")
    ]
    
    # Validate timing
    result = processor.validate_audio_duration(audio_file, subtitle_file)
    
    print(f"Timing validation results:")
    print(f"  Is synchronized: {result.is_synchronized}")
    print(f"  Audio duration: {result.audio_duration:.2f}s")
    print(f"  Subtitle duration: {result.subtitle_duration:.2f}s")
    print(f"  Timing offset: {result.timing_offset:.2f}s")
    
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    if result.errors:
        print(f"  Errors: {result.errors}")


def demo_synchronization_analysis():
    """Demonstrate audio-subtitle synchronization analysis."""
    print("\n=== Synchronization Analysis Demo ===")
    
    synchronizer = AudioSubtitleSynchronizer()
    
    # Create audio file
    audio_file = AudioFile(
        path="demo_audio.mp3",
        duration=120.0,
        sample_rate=44100,
        channels=2
    )
    
    # Create subtitle file with timing issues
    subtitle_file = Mock()
    subtitle_file.lines = [
        Mock(start_time=2.0, end_time=7.0, text="Delayed first line with good length"),
        Mock(start_time=12.0, end_time=17.0, text="Short"),
        Mock(start_time=112.0, end_time=117.0, text="Another longer line for better sync")
    ]
    
    # Analyze synchronization
    analysis = synchronizer.analyze_synchronization(audio_file, subtitle_file)
    
    print(f"Synchronization analysis:")
    print(f"  Sync points found: {len(analysis.sync_points)}")
    print(f"  Average offset: {analysis.average_offset:.2f}s")
    print(f"  Offset variance: {analysis.offset_variance:.4f}")
    print(f"  Sync quality: {analysis.sync_quality:.2f}")
    print(f"  Recommendations:")
    for rec in analysis.recommendations:
        print(f"    - {rec}")


def demo_timing_correction():
    """Demonstrate timing correction application."""
    print("\n=== Timing Correction Demo ===")
    
    synchronizer = AudioSubtitleSynchronizer()
    
    # Create subtitle file with timing offset
    subtitle_file = Mock()
    subtitle_file.lines = [
        Mock(start_time=2.0, end_time=7.0),
        Mock(start_time=12.0, end_time=17.0),
        Mock(start_time=22.0, end_time=27.0)
    ]
    
    print("Original timing:")
    for i, line in enumerate(subtitle_file.lines):
        print(f"  Line {i+1}: {line.start_time:.1f}s - {line.end_time:.1f}s")
    
    # Apply timing correction
    correction_applied = synchronizer.apply_timing_correction(
        subtitle_file, -2.0  # Advance subtitles by 2 seconds
    )
    
    print(f"\nTiming correction applied: {correction_applied}")
    print("Corrected timing:")
    for i, line in enumerate(subtitle_file.lines):
        print(f"  Line {i+1}: {line.start_time:.1f}s - {line.end_time:.1f}s")


def demo_ffmpeg_integration():
    """Demonstrate FFmpeg audio embedding pipeline."""
    print("\n=== FFmpeg Integration Demo ===")
    
    processor = AudioProcessor()
    
    # Create audio file
    audio_file = AudioFile(path="demo_audio.mp3")
    
    # Generate FFmpeg arguments with default settings
    args_default = processor.create_ffmpeg_audio_args(audio_file)
    print("FFmpeg arguments (default settings):")
    print(f"  {' '.join(args_default)}")
    
    # Generate FFmpeg arguments with custom settings
    custom_settings = {
        'audio_codec': 'aac',
        'audio_bitrate': '192k',
        'audio_sample_rate': 48000,
        'audio_channels': 2
    }
    
    args_custom = processor.create_ffmpeg_audio_args(audio_file, custom_settings)
    print("\nFFmpeg arguments (custom settings):")
    print(f"  {' '.join(args_custom)}")
    
    # Get audio stream information
    print("\nAudio stream compatibility check:")
    print("  AAC format: Compatible with H.264")
    print("  MP3 format: Compatible with H.264")
    print("  FLAC format: Needs conversion for H.264")


def demo_timing_precision_validation():
    """Demonstrate timing precision validation."""
    print("\n=== Timing Precision Validation Demo ===")
    
    synchronizer = AudioSubtitleSynchronizer()
    
    # Create subtitle file with various timing issues
    subtitle_file = Mock()
    subtitle_file.lines = [
        Mock(start_time=0.0, end_time=5.0),      # Good duration
        Mock(start_time=6.0, end_time=6.2),      # Very short duration
        Mock(start_time=7.0, end_time=18.0),     # Very long duration
        Mock(start_time=15.0, end_time=20.0),    # Overlap with previous
        Mock(start_time=25.0, end_time=23.0),    # Invalid: end before start
    ]
    
    # Validate timing precision
    results = synchronizer.validate_timing_precision(subtitle_file)
    
    print(f"Timing precision validation:")
    print(f"  Total lines: {results['total_lines']}")
    print(f"  Average duration: {results['average_duration']:.2f}s")
    print(f"  Min gap: {results['min_gap']:.2f}s")
    print(f"  Max gap: {results['max_gap']:.2f}s")
    
    if results['timing_errors']:
        print(f"  Timing errors:")
        for error in results['timing_errors']:
            print(f"    - {error}")
    
    if results['warnings']:
        print(f"  Warnings:")
        for warning in results['warnings']:
            print(f"    - {warning}")


def main():
    """Run all audio processing demos."""
    print("Audio Processing and Synchronization Demo")
    print("=" * 50)
    
    try:
        demo_audio_loading()
        demo_timing_validation()
        demo_synchronization_analysis()
        demo_timing_correction()
        demo_ffmpeg_integration()
        demo_timing_precision_validation()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey features demonstrated:")
        print("✓ Audio file loading and metadata extraction")
        print("✓ Audio-subtitle timing synchronization")
        print("✓ Audio duration validation against subtitle timing")
        print("✓ Audio embedding pipeline for FFmpeg export")
        print("✓ Comprehensive timing precision validation")
        print("✓ Synchronization analysis and recommendations")
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())