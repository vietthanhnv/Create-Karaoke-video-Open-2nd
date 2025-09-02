#!/usr/bin/env python3
"""
Test script for karaoke ASS file parsing.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core.subtitle_parser import parse_ass_file


def main():
    """Test karaoke ASS file parsing."""
    
    print("Testing karaoke ASS file parsing...")
    
    try:
        # Parse the test karaoke file
        subtitle_file, errors, warnings = parse_ass_file("test_karaoke.ass")
        
        print(f"\nParsing completed:")
        print(f"- Errors: {len(errors)}")
        print(f"- Warnings: {len(warnings)}")
        print(f"- Subtitle lines: {len(subtitle_file.lines)}")
        print(f"- Styles: {len(subtitle_file.styles)}")
        
        # Print any errors or warnings
        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"  Line {error.line_number}: {error.message}")
        
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  Line {warning.line_number}: {warning.message}")
        
        # Print parsed subtitle lines with karaoke timing
        print("\nParsed subtitle lines:")
        for i, line in enumerate(subtitle_file.lines):
            print(f"\nLine {i+1}:")
            print(f"  Time: {line.start_time:.2f}s - {line.end_time:.2f}s")
            print(f"  Text: '{line.text}'")
            print(f"  Style: {line.style}")
            
            if line.word_timings:
                print(f"  Word timings ({len(line.word_timings)} words):")
                for j, word_timing in enumerate(line.word_timings):
                    print(f"    {j+1}. '{word_timing.word}': {word_timing.start_time:.2f}s - {word_timing.end_time:.2f}s")
            else:
                print("  No word timings (will use automatic distribution)")
        
        # Test karaoke animation at different times
        print("\nTesting karaoke animation:")
        test_times = [1.5, 2.0, 2.5, 4.5, 5.0, 7.5, 8.0]
        
        for test_time in test_times:
            print(f"\nAt time {test_time}s:")
            for i, line in enumerate(subtitle_file.lines):
                if line.start_time <= test_time <= line.end_time:
                    active_words = line.get_active_words(test_time)
                    progress = line.get_progress_ratio(test_time)
                    print(f"  Line {i+1}: Active words: {active_words}, Progress: {progress:.2f}")
        
        print("\nKaraoke parsing test completed successfully!")
        
    except Exception as e:
        print(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()