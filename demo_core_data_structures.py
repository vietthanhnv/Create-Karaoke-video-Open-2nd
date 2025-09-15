#!/usr/bin/env python3
"""
Demonstration of core data structures and file validation implementation.

This script demonstrates the functionality implemented for task 2:
- Core data structures (ProjectConfig, AudioFile, SubtitleFile, EffectsConfig, ExportSettings)
- File format validation for supported media types
- Karaoke timing extraction from ASS files
"""

import tempfile
import os
from src.core.models import (
    ProjectConfig, AudioFile, SubtitleFile, EffectsConfig, ExportSettings,
    KaraokeTimingInfo, AudioFormat
)
from src.core.validation import FileValidator, ValidationLevel


def demo_data_structures():
    """Demonstrate core data structure creation and validation."""
    print("=== Core Data Structures Demo ===\n")
    
    # 1. ProjectConfig
    print("1. ProjectConfig:")
    config = ProjectConfig(
        audio_file="demo.mp3",
        subtitle_file="demo.ass",
        background_image="background.jpg",
        width=1920,
        height=1080,
        fps=30.0,
        duration=180.0
    )
    print(f"   Audio: {config.audio_file}")
    print(f"   Subtitle: {config.subtitle_file}")
    print(f"   Background: {config.background_image}")
    print(f"   Resolution: {config.width}x{config.height} @ {config.fps}fps")
    print(f"   Duration: {config.duration}s\n")
    
    # 2. AudioFile
    print("2. AudioFile:")
    audio = AudioFile(
        path="demo.mp3",
        duration=180.5,
        sample_rate=44100,
        channels=2,
        format="mp3",
        bitrate=320,
        file_size=7200000
    )
    print(f"   Path: {audio.path}")
    print(f"   Duration: {audio.duration}s")
    print(f"   Format: {audio.format} ({audio.sample_rate}Hz, {audio.channels}ch)")
    print(f"   Bitrate: {audio.bitrate}kbps")
    print(f"   Size: {audio.file_size / 1024 / 1024:.1f}MB\n")
    
    # 3. KaraokeTimingInfo
    print("3. KaraokeTimingInfo:")
    karaoke = KaraokeTimingInfo(
        start_time=10.0,
        end_time=15.0,
        text="{\\k50}Hello {\\k75}world {\\k100}karaoke",
        syllable_count=3,
        syllable_timings=[0.5, 0.75, 1.0],
        style_overrides="\\c&H00FF00&"
    )
    print(f"   Time: {karaoke.start_time}s - {karaoke.end_time}s")
    print(f"   Text: {karaoke.text}")
    print(f"   Syllables: {karaoke.syllable_count}")
    print(f"   Timings: {karaoke.syllable_timings}\n")
    
    # 4. SubtitleFile
    print("4. SubtitleFile:")
    subtitle = SubtitleFile(
        path="demo.ass",
        format="ass",
        line_count=25,
        karaoke_data=[karaoke],
        file_size=5120
    )
    print(f"   Path: {subtitle.path}")
    print(f"   Format: {subtitle.format}")
    print(f"   Lines: {subtitle.line_count}")
    print(f"   Has karaoke: {subtitle.has_karaoke_timing()}")
    print(f"   Size: {subtitle.file_size} bytes\n")
    
    # 5. EffectsConfig
    print("5. EffectsConfig:")
    effects = EffectsConfig(
        glow_enabled=True,
        glow_intensity=1.5,
        glow_radius=8.0,
        glow_color=[1.0, 0.8, 0.2],
        particles_enabled=True,
        particle_count=100,
        text_animation_enabled=True,
        scale_factor=1.2,
        color_transition_enabled=True,
        start_color=[1.0, 1.0, 1.0],
        end_color=[1.0, 0.0, 0.0]
    )
    print(f"   Glow: {'Enabled' if effects.glow_enabled else 'Disabled'}")
    print(f"   Glow intensity: {effects.glow_intensity}")
    print(f"   Particles: {effects.particle_count if effects.particles_enabled else 'Disabled'}")
    print(f"   Text animation: {'Enabled' if effects.text_animation_enabled else 'Disabled'}")
    print(f"   Color transition: {'Enabled' if effects.color_transition_enabled else 'Disabled'}\n")
    
    # 6. ExportSettings
    print("6. ExportSettings:")
    export = ExportSettings(
        resolution={"width": 1920, "height": 1080},
        bitrate=5000,
        format="mp4",
        frame_rate=30.0,
        audio_bitrate=192,
        codec="h264"
    )
    print(f"   Resolution: {export.resolution['width']}x{export.resolution['height']}")
    print(f"   Format: {export.format} ({export.codec})")
    print(f"   Video bitrate: {export.bitrate}kbps")
    print(f"   Audio bitrate: {export.audio_bitrate}kbps")
    print(f"   Frame rate: {export.frame_rate}fps\n")


def demo_file_validation():
    """Demonstrate file format validation."""
    print("=== File Validation Demo ===\n")
    
    # Test supported formats
    print("1. Supported Audio Formats:")
    audio_formats = FileValidator.get_supported_extensions(AudioFormat.MP3.__class__)
    print(f"   {', '.join(audio_formats)}\n")
    
    # Test format checking
    print("2. Format Validation:")
    test_files = [
        ("test.mp3", "MP3 audio"),
        ("test.wav", "WAV audio"),
        ("test.flac", "FLAC audio"),
        ("test.aac", "AAC audio"),
        ("test.ass", "ASS subtitle"),
        ("test.jpg", "JPEG image"),
        ("test.png", "PNG image"),
        ("test.bmp", "BMP image"),
        ("test.mp4", "MP4 video"),
        ("test.mov", "MOV video"),
        ("test.avi", "AVI video"),
        ("test.ogg", "Unsupported format")
    ]
    
    for filename, description in test_files:
        extension = FileValidator.get_file_extension(filename)
        if extension in FileValidator.AUDIO_EXTENSIONS:
            status = "✓ Supported audio"
        elif extension in FileValidator.VIDEO_EXTENSIONS:
            status = "✓ Supported video"
        elif extension in FileValidator.IMAGE_EXTENSIONS:
            status = "✓ Supported image"
        elif extension in FileValidator.SUBTITLE_EXTENSIONS:
            status = "✓ Supported subtitle"
        else:
            status = "✗ Unsupported"
        
        print(f"   {filename:<12} ({description:<18}) - {status}")
    print()


def demo_karaoke_timing():
    """Demonstrate karaoke timing extraction."""
    print("=== Karaoke Timing Demo ===\n")
    
    # Create a sample ASS file with karaoke timing
    ass_content = """[Script Info]
Title: Demo Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:05.00,Default,,0,0,0,,{\\k50}Hello {\\k75}beautiful {\\k100}world
Dialogue: 0,0:00:05.50,0:00:09.00,Default,,0,0,0,,{\\k60}This {\\k40}is {\\k80}karaoke {\\k120}timing
Dialogue: 0,0:00:10.00,0:00:13.50,Default,,0,0,0,,{\\K100}Sing {\\K150}along {\\K200}now
"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
        f.write(ass_content)
        temp_file = f.name
    
    try:
        print("1. ASS Time Format Parsing:")
        test_times = ["0:00:01.00", "0:01:30.50", "1:00:00.00"]
        for time_str in test_times:
            seconds = FileValidator._parse_ass_time(time_str)
            print(f"   {time_str} = {seconds}s")
        print()
        
        print("2. Karaoke Timing Extraction:")
        karaoke_data = FileValidator.extract_karaoke_timing(temp_file)
        
        for i, timing in enumerate(karaoke_data, 1):
            print(f"   Line {i}:")
            print(f"     Time: {timing.start_time}s - {timing.end_time}s")
            print(f"     Text: {timing.text}")
            print(f"     Syllables: {timing.syllable_count}")
            print(f"     Timings: {timing.syllable_timings}")
            print()
        
    finally:
        # Clean up
        os.unlink(temp_file)


def demo_project_validation():
    """Demonstrate project configuration validation."""
    print("=== Project Validation Demo ===\n")
    
    # Test valid configuration
    print("1. Valid Configuration:")
    valid_config = ProjectConfig(
        audio_file="demo.mp3",
        subtitle_file="demo.ass",
        background_image="background.jpg",
        width=1920,
        height=1080,
        fps=30.0
    )
    
    # Mock the file validation since we don't have actual files
    print("   (Note: File validation would check actual file existence)\n")
    
    # Test invalid configuration
    print("2. Invalid Configuration:")
    try:
        invalid_config = ProjectConfig(
            width=0,  # Invalid
            height=-100,  # Invalid
            fps=-1,  # Invalid
            duration=-5.0  # Invalid
        )
        # This should not be reached
        print("   ERROR: Validation should have failed!")
    except ValueError as e:
        print(f"   ✓ Validation error correctly caught: {e}")
    print()
    
    # Test format requirements
    print("3. Format Requirements for Task:")
    print("   Required audio formats: MP3, WAV, FLAC")
    print("   Required subtitle format: ASS with karaoke timing (\\k, \\K, \\kf tags)")
    print("   Optional background image formats: JPG, PNG, BMP")
    print("   Optional background video formats: MP4, MOV, AVI")
    print()


def main():
    """Run all demonstrations."""
    print("Core Data Structures and File Validation Demo")
    print("=" * 50)
    print()
    
    demo_data_structures()
    demo_file_validation()
    demo_karaoke_timing()
    demo_project_validation()
    
    print("Demo completed successfully!")
    print("\nTask 2 Implementation Summary:")
    print("✓ Created ProjectConfig data structure")
    print("✓ Enhanced AudioFile with task-specific fields")
    print("✓ Enhanced SubtitleFile with karaoke timing support")
    print("✓ Created EffectsConfig for visual effects")
    print("✓ Enhanced ExportSettings with task-specific fields")
    print("✓ Added KaraokeTimingInfo for karaoke timing data")
    print("✓ Implemented file format validation for MP3/WAV/FLAC")
    print("✓ Implemented ASS file validation with karaoke timing")
    print("✓ Added optional background media validation (JPG/PNG/BMP, MP4/MOV/AVI)")
    print("✓ Created comprehensive unit tests")
    print("✓ Maintained backward compatibility with existing code")


if __name__ == "__main__":
    main()