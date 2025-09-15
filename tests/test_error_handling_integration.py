"""
Integration tests for comprehensive error handling system.

Tests error handling integration with existing components including
OpenGL, libass, FFmpeg, and validation systems.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.error_handling import (
    ErrorSeverity, ErrorCategory, ErrorInfo, KaraokeError,
    OpenGLValidator, LibassValidator, FFmpegValidator, DependencyValidator,
    global_error_handler, create_user_friendly_error_message
)


class TestErrorHandlingIntegration(unittest.TestCase):
    """Test error handling integration with existing components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_opengl_error_integration(self):
        """Test OpenGL error handling integration."""
        # Test OpenGL error checking
        errors = OpenGLValidator.check_opengl_errors("test_context")
        
        # Should return a list (may be empty if no OpenGL errors)
        self.assertIsInstance(errors, list)
        
        # If there are errors, they should be properly formatted
        for error in errors:
            self.assertIsInstance(error, ErrorInfo)
            self.assertEqual(error.category, ErrorCategory.OPENGL)
            self.assertIn("GL_", error.code)
    
    def test_libass_validation_integration(self):
        """Test libass validation integration."""
        # Create a test ASS file
        ass_content = """[Script Info]
Title: Test Karaoke

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\k50}Test {\\k50}karaoke {\\k100}timing
"""
        
        test_file = os.path.join(self.temp_dir, "test.ass")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        # Test validation
        errors = LibassValidator.validate_ass_file(test_file)
        
        # Should have no critical errors for valid file
        critical_errors = [e for e in errors if e.severity == ErrorSeverity.ERROR]
        self.assertEqual(len(critical_errors), 0)
        
        # Test with invalid file
        invalid_file = os.path.join(self.temp_dir, "invalid.ass")
        with open(invalid_file, 'w', encoding='utf-8') as f:
            f.write("Invalid ASS content")
        
        errors = LibassValidator.validate_ass_file(invalid_file)
        
        # Should have errors for invalid file
        self.assertGreater(len(errors), 0)
        
        # All errors should be properly categorized
        for error in errors:
            self.assertIsInstance(error, ErrorInfo)
            self.assertEqual(error.category, ErrorCategory.LIBASS)
    
    @patch('subprocess.run')
    def test_ffmpeg_validation_integration(self, mock_run):
        """Test FFmpeg validation integration."""
        # Test successful FFmpeg validation
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.0"
        mock_run.return_value = mock_result
        
        with patch.object(FFmpegValidator, '_validate_ffmpeg_codecs', return_value=[]):
            result = FFmpegValidator.validate_ffmpeg_installation()
            self.assertIsNone(result)
        
        # Test FFmpeg not found
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        
        result = FFmpegValidator.validate_ffmpeg_installation()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.category, ErrorCategory.FFMPEG)
        self.assertEqual(result.code, "FFMPEG_NOT_FOUND")
        self.assertIn("Install FFmpeg", result.recovery_suggestions[0])
    
    def test_dependency_validation_integration(self):
        """Test dependency validation integration."""
        # Test dependency validation
        errors = DependencyValidator.validate_all_dependencies()
        
        # Should return a list of errors
        self.assertIsInstance(errors, list)
        
        # All errors should be properly categorized
        for error in errors:
            self.assertIsInstance(error, ErrorInfo)
            self.assertIn(error.category, [
                ErrorCategory.DEPENDENCY,
                ErrorCategory.FFMPEG,
                ErrorCategory.SYSTEM
            ])
    
    def test_global_error_handler_integration(self):
        """Test global error handler integration."""
        # Test handling different types of errors
        test_errors = [
            ValueError("Invalid value"),
            FileNotFoundError("File not found"),
            PermissionError("Permission denied"),
            Exception("Generic error")
        ]
        
        for error in test_errors:
            result = global_error_handler.handle_error(error, "test_context")
            
            self.assertIsInstance(result, ErrorInfo)
            self.assertIn(result.category, [
                ErrorCategory.SYSTEM,
                ErrorCategory.FILE_IO
            ])
            self.assertGreater(len(result.recovery_suggestions), 0)
    
    def test_user_friendly_error_messages(self):
        """Test user-friendly error message generation."""
        # Create various error types
        error_infos = [
            ErrorInfo(
                category=ErrorCategory.OPENGL,
                severity=ErrorSeverity.ERROR,
                code="GL_ERROR",
                message="OpenGL error occurred",
                recovery_suggestions=["Update drivers", "Check OpenGL support"]
            ),
            ErrorInfo(
                category=ErrorCategory.LIBASS,
                severity=ErrorSeverity.WARNING,
                code="ASS_NO_KARAOKE",
                message="No karaoke timing found",
                details="File may not have karaoke effects",
                recovery_suggestions=["Add karaoke timing tags"]
            ),
            ErrorInfo(
                category=ErrorCategory.FFMPEG,
                severity=ErrorSeverity.CRITICAL,
                code="FFMPEG_NOT_FOUND",
                message="FFmpeg not installed",
                recovery_suggestions=["Install FFmpeg", "Add to PATH"]
            )
        ]
        
        for error_info in error_infos:
            message = create_user_friendly_error_message(error_info)
            
            # Should contain error message
            self.assertIn(error_info.message, message)
            
            # Should contain recovery suggestions
            for suggestion in error_info.recovery_suggestions:
                self.assertIn(suggestion, message)
            
            # Should have user-friendly formatting
            self.assertIn("❌", message)
            if error_info.recovery_suggestions:
                self.assertIn("💡", message)
    
    def test_error_recovery_suggestions(self):
        """Test error recovery suggestions are appropriate."""
        # Test OpenGL errors
        opengl_errors = OpenGLValidator.check_opengl_errors("test")
        for error in opengl_errors:
            self.assertGreater(len(error.recovery_suggestions), 0)
            # Should have graphics-related suggestions
            suggestions_text = " ".join(error.recovery_suggestions).lower()
            self.assertTrue(
                any(keyword in suggestions_text for keyword in [
                    "driver", "opengl", "graphics", "update"
                ])
            )
        
        # Test FFmpeg error analysis
        ffmpeg_error = FFmpegValidator.analyze_ffmpeg_error(
            "No such file or directory", ["ffmpeg", "-i", "missing.mp4"]
        )
        
        self.assertGreater(len(ffmpeg_error.recovery_suggestions), 0)
        suggestions_text = " ".join(ffmpeg_error.recovery_suggestions).lower()
        self.assertTrue(
            any(keyword in suggestions_text for keyword in [
                "file", "path", "check", "exists"
            ])
        )
    
    def test_error_categorization_accuracy(self):
        """Test that errors are categorized correctly."""
        test_cases = [
            ("opengl context failed", "opengl_init", ErrorCategory.OPENGL),
            ("libass parsing error", "subtitle_load", ErrorCategory.LIBASS),
            ("ffmpeg encoding failed", "video_export", ErrorCategory.FFMPEG),
            ("unknown error", "general", ErrorCategory.SYSTEM)
        ]
        
        for error_msg, context, expected_category in test_cases:
            error = Exception(error_msg)
            result = global_error_handler.handle_error(error, context)
            
            self.assertEqual(result.category, expected_category)
        
        # Test file-specific errors
        file_error = FileNotFoundError("File not found")
        result = global_error_handler.handle_error(file_error, "file_operation")
        self.assertEqual(result.category, ErrorCategory.FILE_IO)
    
    def test_error_severity_assignment(self):
        """Test that error severity is assigned appropriately."""
        # Critical errors
        critical_errors = [
            FileNotFoundError("Required file missing"),
            PermissionError("Access denied")
        ]
        
        for error in critical_errors:
            result = global_error_handler.handle_error(error, "test")
            self.assertIn(result.severity, [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL])
        
        # Regular errors
        regular_errors = [
            ValueError("Invalid parameter"),
            RuntimeError("Operation failed")
        ]
        
        for error in regular_errors:
            result = global_error_handler.handle_error(error, "test")
            self.assertEqual(result.severity, ErrorSeverity.ERROR)
    
    def test_technical_info_collection(self):
        """Test that technical information is collected properly."""
        error = ValueError("Test error")
        result = global_error_handler.handle_error(error, "test_context")
        
        # Should have technical info
        self.assertIsInstance(result.technical_info, dict)
        self.assertIn("error_type", result.technical_info)
        self.assertIn("context", result.technical_info)
        self.assertEqual(result.technical_info["error_type"], "ValueError")
        self.assertEqual(result.technical_info["context"], "test_context")
    
    def test_error_history_tracking(self):
        """Test that error history is tracked properly."""
        initial_count = len(global_error_handler.error_history)
        
        # Generate some errors
        test_errors = [
            ValueError("Error 1"),
            RuntimeError("Error 2"),
            FileNotFoundError("Error 3")
        ]
        
        for error in test_errors:
            global_error_handler.handle_error(error, "test")
        
        # Should have added to history
        final_count = len(global_error_handler.error_history)
        self.assertEqual(final_count - initial_count, len(test_errors))
        
        # Recent errors should be in history
        recent_errors = global_error_handler.error_history[-len(test_errors):]
        for i, error_info in enumerate(recent_errors):
            self.assertIn(f"Error {i+1}", error_info.message)


class TestErrorHandlingPerformance(unittest.TestCase):
    """Test error handling system performance."""
    
    def test_error_handling_performance(self):
        """Test that error handling doesn't significantly impact performance."""
        import time
        
        # Test handling many errors quickly
        start_time = time.time()
        
        for i in range(100):
            error = ValueError(f"Test error {i}")
            global_error_handler.handle_error(error, f"context_{i}")
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Should handle 100 errors in less than 1 second
        self.assertLess(elapsed, 1.0)
    
    def test_validation_performance(self):
        """Test that validation functions perform adequately."""
        import time
        
        # Create test ASS file
        ass_content = """[Script Info]
Title: Performance Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join([
    f"Dialogue: 0,0:00:{i:02d}.00,0:00:{i+1:02d}.00,Default,,0,0,0,,{{\\k50}}Line {i}"
    for i in range(100)
])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_path = f.name
        
        try:
            start_time = time.time()
            
            # Validate the file multiple times
            for _ in range(10):
                LibassValidator.validate_ass_file(temp_path)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Should validate 10 times in less than 2 seconds
            self.assertLess(elapsed, 2.0)
            
        finally:
            os.unlink(temp_path)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)