#!/usr/bin/env python3
"""
Demonstration of the comprehensive error handling and validation system.

This script shows how the error handling system works with various types of
errors including OpenGL, libass, FFmpeg, and dependency validation.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.error_handling import (
    ErrorSeverity, ErrorCategory, ErrorInfo, KaraokeError,
    OpenGLError, LibassError, FFmpegError, DependencyError, ValidationError,
    ErrorHandler, OpenGLValidator, LibassValidator, FFmpegValidator,
    DependencyValidator, create_user_friendly_error_message,
    log_error_for_debugging, global_error_handler
)


def demonstrate_error_classification():
    """Demonstrate error classification and handling."""
    print("=" * 60)
    print("ERROR CLASSIFICATION DEMONSTRATION")
    print("=" * 60)
    
    # Test different types of errors
    test_errors = [
        (ValueError("Invalid parameter value"), "parameter_validation"),
        (FileNotFoundError("Required file missing"), "file_loading"),
        (PermissionError("Access denied"), "file_access"),
        (Exception("OpenGL context creation failed"), "opengl_initialization"),
        (Exception("libass parsing error"), "subtitle_processing"),
        (Exception("ffmpeg encoding failed"), "video_export"),
    ]
    
    for error, context in test_errors:
        print(f"\nHandling: {type(error).__name__}: {error}")
        print(f"Context: {context}")
        
        error_info = global_error_handler.handle_error(error, context)
        
        print(f"Category: {error_info.category.value}")
        print(f"Severity: {error_info.severity.value}")
        print(f"Code: {error_info.code}")
        print(f"Recovery suggestions: {len(error_info.recovery_suggestions)}")
        
        if error_info.recovery_suggestions:
            for i, suggestion in enumerate(error_info.recovery_suggestions[:2], 1):
                print(f"  {i}. {suggestion}")


def demonstrate_opengl_validation():
    """Demonstrate OpenGL error checking and validation."""
    print("\n" + "=" * 60)
    print("OPENGL VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    # Check for OpenGL errors
    print("\nChecking for OpenGL errors...")
    errors = OpenGLValidator.check_opengl_errors("demo_context")
    
    if errors:
        print(f"Found {len(errors)} OpenGL errors:")
        for error in errors:
            print(f"  - {error.code}: {error.message}")
            print(f"    Suggestions: {', '.join(error.recovery_suggestions[:2])}")
    else:
        print("No OpenGL errors detected.")
    
    # Test shader validation (mock)
    print("\nTesting shader compilation validation...")
    try:
        # This would normally be called with real OpenGL shader IDs
        result = OpenGLValidator.validate_shader_compilation(123, "vertex")
        if result:
            print(f"Shader validation failed: {result.message}")
        else:
            print("Shader validation would succeed (mocked)")
    except Exception as e:
        print(f"Shader validation error: {e}")


def demonstrate_libass_validation():
    """Demonstrate libass ASS file validation."""
    print("\n" + "=" * 60)
    print("LIBASS VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    # Create test ASS files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Valid ASS file
        valid_ass = os.path.join(temp_dir, "valid.ass")
        valid_content = """[Script Info]
Title: Test Karaoke
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\k50}Test {\\k50}karaoke {\\k100}timing
Dialogue: 0,0:00:05.00,0:00:10.00,Default,,0,0,0,,{\\k75}More {\\k25}text
"""
        
        with open(valid_ass, 'w', encoding='utf-8') as f:
            f.write(valid_content)
        
        print(f"\nValidating valid ASS file: {os.path.basename(valid_ass)}")
        errors = LibassValidator.validate_ass_file(valid_ass)
        
        if errors:
            print(f"Found {len(errors)} validation issues:")
            for error in errors:
                print(f"  - {error.severity.value.upper()}: {error.message}")
        else:
            print("ASS file validation passed!")
        
        # Invalid ASS file
        invalid_ass = os.path.join(temp_dir, "invalid.ass")
        invalid_content = """[Script Info]
Title: Invalid ASS

[Events]
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\k-50}Invalid {\\k50}timing
"""
        
        with open(invalid_ass, 'w', encoding='utf-8') as f:
            f.write(invalid_content)
        
        print(f"\nValidating invalid ASS file: {os.path.basename(invalid_ass)}")
        errors = LibassValidator.validate_ass_file(invalid_ass)
        
        print(f"Found {len(errors)} validation issues:")
        for error in errors:
            print(f"  - {error.severity.value.upper()}: {error.message}")
            if error.recovery_suggestions:
                print(f"    Suggestion: {error.recovery_suggestions[0]}")


def demonstrate_ffmpeg_validation():
    """Demonstrate FFmpeg validation and error analysis."""
    print("\n" + "=" * 60)
    print("FFMPEG VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    # Test FFmpeg installation
    print("\nChecking FFmpeg installation...")
    result = FFmpegValidator.validate_ffmpeg_installation()
    
    if result:
        print(f"FFmpeg validation failed: {result.message}")
        print("Recovery suggestions:")
        for i, suggestion in enumerate(result.recovery_suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("FFmpeg installation validated successfully!")
    
    # Test error analysis
    print("\nTesting FFmpeg error analysis...")
    test_errors = [
        ("No such file or directory", ["ffmpeg", "-i", "missing.mp4"]),
        ("Permission denied", ["ffmpeg", "-i", "input.mp4", "output.mp4"]),
        ("Invalid data found", ["ffmpeg", "-i", "corrupted.mp4"]),
        ("Unknown error occurred", ["ffmpeg", "-i", "input.mp4"])
    ]
    
    for stderr, command in test_errors:
        print(f"\nAnalyzing error: {stderr}")
        error_info = FFmpegValidator.analyze_ffmpeg_error(stderr, command)
        print(f"  Code: {error_info.code}")
        print(f"  Category: {error_info.category.value}")
        print(f"  Primary suggestion: {error_info.recovery_suggestions[0]}")


def demonstrate_dependency_validation():
    """Demonstrate dependency validation."""
    print("\n" + "=" * 60)
    print("DEPENDENCY VALIDATION DEMONSTRATION")
    print("=" * 60)
    
    print("\nValidating all dependencies...")
    errors = DependencyValidator.validate_all_dependencies()
    
    if errors:
        print(f"Found {len(errors)} dependency issues:")
        
        # Group by category
        by_category = {}
        for error in errors:
            category = error.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(error)
        
        for category, category_errors in by_category.items():
            print(f"\n{category.upper()} Issues:")
            for error in category_errors:
                print(f"  - {error.message}")
                if error.recovery_suggestions:
                    print(f"    → {error.recovery_suggestions[0]}")
    else:
        print("All dependencies validated successfully!")


def demonstrate_user_friendly_messages():
    """Demonstrate user-friendly error message generation."""
    print("\n" + "=" * 60)
    print("USER-FRIENDLY ERROR MESSAGES")
    print("=" * 60)
    
    # Create sample errors
    sample_errors = [
        ErrorInfo(
            category=ErrorCategory.OPENGL,
            severity=ErrorSeverity.ERROR,
            code="GL_CONTEXT_FAILED",
            message="Failed to create OpenGL context",
            details="Graphics driver may be outdated",
            recovery_suggestions=[
                "Update your graphics drivers",
                "Check OpenGL 3.3+ support",
                "Try software rendering mode"
            ]
        ),
        ErrorInfo(
            category=ErrorCategory.LIBASS,
            severity=ErrorSeverity.WARNING,
            code="ASS_NO_KARAOKE_TIMING",
            message="No karaoke timing found in subtitle file",
            details="File may not have karaoke effects",
            recovery_suggestions=[
                "Add \\k, \\K, or \\kf timing tags to your ASS file",
                "Use karaoke timing software to generate tags"
            ]
        ),
        ErrorInfo(
            category=ErrorCategory.FFMPEG,
            severity=ErrorSeverity.CRITICAL,
            code="FFMPEG_NOT_FOUND",
            message="FFmpeg is not installed or not found in PATH",
            recovery_suggestions=[
                "Install FFmpeg from https://ffmpeg.org/",
                "Add FFmpeg to your system PATH",
                "Restart the application after installation"
            ]
        )
    ]
    
    for error_info in sample_errors:
        print(f"\n{error_info.category.value.upper()} Error Example:")
        print("-" * 40)
        message = create_user_friendly_error_message(error_info)
        print(message)


def demonstrate_error_recovery():
    """Demonstrate error recovery mechanisms."""
    print("\n" + "=" * 60)
    print("ERROR RECOVERY DEMONSTRATION")
    print("=" * 60)
    
    # Show error history
    print(f"\nError history contains {len(global_error_handler.error_history)} entries")
    
    if global_error_handler.error_history:
        print("\nRecent errors:")
        for error_info in global_error_handler.error_history[-3:]:
            print(f"  - {error_info.category.value}: {error_info.message}")
    
    # Demonstrate recovery attempt tracking
    print(f"\nRecovery attempts tracked: {len(global_error_handler.recovery_attempts)}")
    
    # Show how to create custom errors
    print("\nCreating custom KaraokeError...")
    custom_error_info = ErrorInfo(
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        code="CUSTOM_VALIDATION_ERROR",
        message="Custom validation failed",
        details="This is a demonstration of custom error creation",
        recovery_suggestions=["Fix the validation issue", "Try again"],
        technical_info={"demo": True, "timestamp": "2024-01-01"}
    )
    
    custom_error = KaraokeError(custom_error_info)
    print(f"Custom error created: {custom_error}")
    print(f"User message: {custom_error.get_user_message()}")


def main():
    """Run all error handling demonstrations."""
    print("KARAOKE VIDEO CREATOR - ERROR HANDLING SYSTEM DEMO")
    print("=" * 60)
    print("This demo shows the comprehensive error handling and validation system.")
    print("The system provides detailed error information, recovery suggestions,")
    print("and user-friendly messages for all types of errors.")
    
    try:
        demonstrate_error_classification()
        demonstrate_opengl_validation()
        demonstrate_libass_validation()
        demonstrate_ffmpeg_validation()
        demonstrate_dependency_validation()
        demonstrate_user_friendly_messages()
        demonstrate_error_recovery()
        
        print("\n" + "=" * 60)
        print("ERROR HANDLING SYSTEM DEMO COMPLETED")
        print("=" * 60)
        print("The error handling system is ready for production use!")
        print("It provides comprehensive error detection, classification,")
        print("and recovery guidance for all system components.")
        
    except Exception as e:
        print(f"\nDemo error: {e}")
        error_info = global_error_handler.handle_error(e, "demo_execution")
        print(f"Handled as: {error_info.category.value} - {error_info.message}")


if __name__ == "__main__":
    main()