#!/usr/bin/env python3
"""
Demo script for libass integration system.

This script demonstrates the libass integration functionality including:
- ASS file loading and parsing
- Karaoke timing extraction
- Bitmap texture generation
- Font loading and text styling
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.libass_integration import (
    LibassIntegration, LibassContext, LibassError,
    create_libass_context, load_ass_file_with_libass
)
from core.models import SubtitleFile, KaraokeTimingInfo


def create_sample_ass_file() -> str:
    """Create a sample ASS file with karaoke timing for testing."""
    ass_content = """[Script Info]
Title: Libass Integration Demo
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10
Style: Karaoke,Arial,28,&H00FFFF00,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:03.00,Karaoke,,0,0,0,,{\\k30}Ka{\\k25}ra{\\k20}o{\\k25}ke{\\k30}time!
Dialogue: 0,0:00:03.50,0:00:06.00,Default,,0,0,0,,Regular subtitle without karaoke timing
Dialogue: 0,0:00:06.50,0:00:09.00,Karaoke,,0,0,0,,{\\k40}Sing{\\k35}a{\\k30}long{\\k25}now
Dialogue: 0,0:00:09.50,0:00:12.00,Karaoke,,0,0,0,,{\\kf50}Fade{\\kf40}effect{\\kf35}here
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
        f.write(ass_content)
        return f.name


def demo_libass_context():
    """Demonstrate LibassContext functionality."""
    print("=== LibassContext Demo ===")
    
    # Create context
    context = create_libass_context(1920, 1080)
    print(f"Libass available: {context.is_available()}")
    
    if context.is_available():
        print("✓ Libass library loaded successfully")
    else:
        print("⚠ Libass library not available, using fallback parsing")
    
    # Test font information
    print(f"Context dimensions: {context.width}x{context.height}")
    
    context.cleanup()
    print("Context cleaned up")
    print()


def demo_libass_integration():
    """Demonstrate LibassIntegration functionality."""
    print("=== LibassIntegration Demo ===")
    
    # Create sample ASS file
    ass_file = create_sample_ass_file()
    print(f"Created sample ASS file: {ass_file}")
    
    try:
        # Create integration instance
        integration = LibassIntegration(1920, 1080)
        
        # Load and parse subtitle file
        print("Loading and parsing ASS file...")
        subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(ass_file)
        
        print(f"✓ Loaded {len(subtitle_file.lines)} subtitle lines")
        print(f"✓ Extracted {len(karaoke_data)} karaoke timing entries")
        
        # Display subtitle information
        print("\nSubtitle Lines:")
        for i, line in enumerate(subtitle_file.lines):
            print(f"  {i+1}. [{line.start_time:.2f}s - {line.end_time:.2f}s] {line.text}")
            if line.has_karaoke_tags and line.word_timings:
                print(f"     Karaoke words: {[wt.word for wt in line.word_timings]}")
                print(f"     Word durations: {[f'{wt.end_time - wt.start_time:.2f}s' for wt in line.word_timings]}")
        
        # Display karaoke timing information
        print("\nKaraoke Timing Data:")
        for i, karaoke_info in enumerate(karaoke_data):
            print(f"  {i+1}. [{karaoke_info.start_time:.2f}s - {karaoke_info.end_time:.2f}s] {karaoke_info.text}")
            print(f"     Syllables: {karaoke_info.syllable_count}")
            print(f"     Timings: {[f'{t:.2f}s' for t in karaoke_info.syllable_timings]}")
        
        # Test validation
        print("\nValidating ASS format...")
        is_valid, errors = integration.validate_ass_format(ass_file)
        print(f"Valid: {is_valid}")
        if errors:
            print("Validation issues:")
            for error in errors:
                print(f"  - {error}")
        
        # Test font information
        print("\nFont Information:")
        font_info = integration.get_font_info()
        for key, value in font_info.items():
            print(f"  {key}: {value}")
        
        # Test bitmap texture generation (mock timestamps)
        print("\nGenerating bitmap textures...")
        timestamps = [0.5, 1.0, 1.5, 2.0]
        textures = integration.generate_bitmap_textures(timestamps)
        print(f"Generated textures for {len(textures)} timestamps")
        
        # Cleanup
        integration.cleanup()
        print("Integration cleaned up")
        
    except LibassError as e:
        print(f"✗ LibassError: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    finally:
        # Clean up temporary file
        try:
            os.unlink(ass_file)
            print(f"Cleaned up temporary file: {ass_file}")
        except OSError:
            pass
    
    print()


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("=== Convenience Functions Demo ===")
    
    # Create sample ASS file
    ass_file = create_sample_ass_file()
    print(f"Created sample ASS file: {ass_file}")
    
    try:
        # Test convenience function
        print("Using convenience function to load ASS file...")
        subtitle_file, karaoke_data = load_ass_file_with_libass(ass_file, 1280, 720)
        
        print(f"✓ Loaded subtitle file: {subtitle_file.path}")
        print(f"✓ Found {len(subtitle_file.lines)} lines")
        print(f"✓ Extracted {len(karaoke_data)} karaoke entries")
        
        # Show karaoke detection
        karaoke_lines = [line for line in subtitle_file.lines if line.has_karaoke_tags]
        print(f"✓ Detected {len(karaoke_lines)} lines with karaoke timing")
        
    except LibassError as e:
        print(f"✗ LibassError: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    finally:
        # Clean up temporary file
        try:
            os.unlink(ass_file)
            print(f"Cleaned up temporary file: {ass_file}")
        except OSError:
            pass
    
    print()


def demo_error_handling():
    """Demonstrate error handling."""
    print("=== Error Handling Demo ===")
    
    integration = LibassIntegration()
    
    # Test with non-existent file
    try:
        integration.load_and_parse_subtitle_file("nonexistent.ass")
    except LibassError as e:
        print(f"✓ Caught expected error for non-existent file: {e}")
    
    # Test with invalid ASS content
    invalid_ass_content = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,invalid_time,0:00:02.00,Default,,0,0,0,,Test text
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
        f.write(invalid_ass_content)
        invalid_file = f.name
    
    try:
        integration.load_and_parse_subtitle_file(invalid_file)
    except LibassError as e:
        print(f"✓ Caught expected error for invalid ASS file: {e}")
    finally:
        try:
            os.unlink(invalid_file)
        except OSError:
            pass
    
    integration.cleanup()
    print()


def main():
    """Run all demos."""
    print("Libass Integration System Demo")
    print("=" * 50)
    print()
    
    demo_libass_context()
    demo_libass_integration()
    demo_convenience_functions()
    demo_error_handling()
    
    print("Demo completed!")


if __name__ == "__main__":
    main()