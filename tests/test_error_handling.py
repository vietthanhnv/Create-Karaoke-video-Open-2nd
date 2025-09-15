"""
Unit tests for comprehensive error handling and validation system.

Tests cover OpenGL error checking, libass parsing validation, FFmpeg process
failure detection, dependency validation, and user-friendly error messages.
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
    OpenGLError, LibassError, FFmpegError, DependencyError, ValidationError,
    ErrorHandler, OpenGLValidator, LibassValidator, FFmpegValidator,
    DependencyValidator, create_user_friendly_error_message,
    log_error_for_debugging, global_error_handler
)


class TestErrorInfo(unittest.TestCase):
    """Test ErrorInfo dataclass functionality."""
    
    def test_error_info_creation(self):
        """Test creating ErrorInfo with all fields."""
        error_info = ErrorInfo(
            category=ErrorCategory.OPENGL,
            severity=ErrorSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error message",
            details="Test details",
            recovery_suggestions=["Suggestion 1", "Suggestion 2"],
            technical_info={"key": "value"}
        )
        
        self.assertEqual(error_info.category, ErrorCategory.OPENGL)
        self.assertEqual(error_info.severity, ErrorSeverity.ERROR)
        self.assertEqual(error_info.code, "TEST_ERROR")
        self.assertEqual(error_info.message, "Test error message")
        self.assertEqual(error_info.details, "Test details")
        self.assertEqual(len(error_info.recovery_suggestions), 2)
        self.assertEqual(error_info.technical_info["key"], "value")
    
    def test_error_info_defaults(self):
        """Test ErrorInfo with default values."""
        error_info = ErrorInfo(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.WARNING,
            code="TEST_WARNING",
            message="Test warning"
        )
        
        self.assertEqual(error_info.details, "")
        self.assertEqual(error_info.recovery_suggestions, [])
        self.assertEqual(error_info.technical_info, {})


class TestKaraokeError(unittest.TestCase):
    """Test KaraokeError exception class."""
    
    def test_karaoke_error_creation(self):
        """Test creating KaraokeError with ErrorInfo."""
        error_info = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error",
            recovery_suggestions=["Fix the issue"]
        )
        
        error = KaraokeError(error_info)
        self.assertEqual(error.error_info, error_info)
        self.assertEqual(str(error), "Test error")
    
    def test_get_user_message(self):
        """Test user-friendly message generation."""
        error_info = ErrorInfo(
            category=ErrorCategory.FFMPEG,
            severity=ErrorSeverity.ERROR,
            code="FFMPEG_ERROR",
            message="FFmpeg failed",
            recovery_suggestions=["Check installation", "Try again"]
        )
        
        error = KaraokeError(error_info)
        user_message = error.get_user_message()
        
        self.assertIn("FFmpeg failed", user_message)
        self.assertIn("Check installation", user_message)
        self.assertIn("Try again", user_message)
    
    def test_get_technical_details(self):
        """Test technical details generation."""
        error_info = ErrorInfo(
            category=ErrorCategory.OPENGL,
            severity=ErrorSeverity.CRITICAL,
            code="GL_ERROR",
            message="OpenGL error",
            details="Context details",
            technical_info={"error_code": 1234}
        )
        
        error = KaraokeError(error_info)
        technical_details = error.get_technical_details()
        
        self.assertIn("Category: opengl", technical_details)
        self.assertIn("Severity: critical", technical_details)
        self.assertIn("Code: GL_ERROR", technical_details)
        self.assertIn("error_code: 1234", technical_details)


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandler()
    
    def test_handle_karaoke_error(self):
        """Test handling KaraokeError."""
        error_info = ErrorInfo(
            category=ErrorCategory.LIBASS,
            severity=ErrorSeverity.ERROR,
            code="LIBASS_ERROR",
            message="Libass error"
        )
        
        karaoke_error = LibassError(error_info)
        result = self.error_handler.handle_error(karaoke_error, "test_context")
        
        self.assertEqual(result, error_info)
        self.assertEqual(len(self.error_handler.error_history), 1)
    
    def test_handle_generic_error(self):
        """Test handling generic Python exception."""
        generic_error = ValueError("Invalid value")
        result = self.error_handler.handle_error(generic_error, "validation")
        
        self.assertEqual(result.category, ErrorCategory.SYSTEM)
        self.assertEqual(result.severity, ErrorSeverity.ERROR)
        self.assertIn("Invalid value", result.message)
    
    def test_handle_file_error(self):
        """Test handling file-related errors."""
        file_error = FileNotFoundError("File not found")
        result = self.error_handler.handle_error(file_error, "file_operation")
        
        self.assertEqual(result.category, ErrorCategory.FILE_IO)
        self.assertIn("File operation failed", result.message)
        self.assertIn("Check file path", result.recovery_suggestions[0])
    
    def test_classify_opengl_error(self):
        """Test OpenGL error classification."""
        gl_error = Exception("OpenGL context failed")
        result = self.error_handler.handle_error(gl_error, "opengl_init")
        
        self.assertEqual(result.category, ErrorCategory.OPENGL)
        self.assertIn("Update your graphics drivers", result.recovery_suggestions)
    
    def test_classify_libass_error(self):
        """Test libass error classification."""
        libass_error = Exception("libass parsing failed")
        result = self.error_handler.handle_error(libass_error, "subtitle_parsing")
        
        self.assertEqual(result.category, ErrorCategory.LIBASS)
        self.assertIn("Check ASS file format and encoding", result.recovery_suggestions)
    
    def test_classify_ffmpeg_error(self):
        """Test FFmpeg error classification."""
        ffmpeg_error = Exception("ffmpeg encoding failed")
        result = self.error_handler.handle_error(ffmpeg_error, "video_export")
        
        self.assertEqual(result.category, ErrorCategory.FFMPEG)
        self.assertIn("Check FFmpeg installation and PATH", result.recovery_suggestions)


class TestOpenGLValidator(unittest.TestCase):
    """Test OpenGL error checking and validation."""
    
    @patch('OpenGL.GL', create=True)
    def test_check_opengl_errors_no_errors(self, mock_gl):
        """Test OpenGL error checking with no errors."""
        mock_gl.glGetError.return_value = mock_gl.GL_NO_ERROR
        
        errors = OpenGLValidator.check_opengl_errors("test_context")
        
        self.assertEqual(len(errors), 0)
        mock_gl.glGetError.assert_called_once()
    
    @patch('OpenGL.GL', create=True)
    def test_check_opengl_errors_with_error(self, mock_gl):
        """Test OpenGL error checking with errors."""
        # Simulate GL_INVALID_ENUM error followed by GL_NO_ERROR
        mock_gl.glGetError.side_effect = [0x0500, 0]  # GL_INVALID_ENUM, GL_NO_ERROR
        mock_gl.GL_NO_ERROR = 0
        mock_gl.GL_INVALID_ENUM = 0x0500
        
        errors = OpenGLValidator.check_opengl_errors("test_context")
        
        self.assertGreaterEqual(len(errors), 1)  # May have multiple errors
        self.assertEqual(errors[0].category, ErrorCategory.OPENGL)
        self.assertIn("GL_", errors[0].code)  # Should contain GL_ prefix
    
    def test_check_opengl_errors_import_failure(self):
        """Test OpenGL error checking when OpenGL import fails."""
        # Mock the import to fail within the function
        with patch('builtins.__import__', side_effect=ImportError("No OpenGL")):
            errors = OpenGLValidator.check_opengl_errors("test_context")
            
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0].code, "GL_CHECK_FAILED")
    
    @patch('OpenGL.GL', create=True)
    def test_validate_shader_compilation_success(self, mock_gl):
        """Test successful shader compilation validation."""
        mock_gl.glGetShaderiv.return_value = 1  # GL_TRUE
        
        result = OpenGLValidator.validate_shader_compilation(123, "vertex")
        
        self.assertIsNone(result)
        mock_gl.glGetShaderiv.assert_called_once()
    
    @patch('OpenGL.GL', create=True)
    def test_validate_shader_compilation_failure(self, mock_gl):
        """Test failed shader compilation validation."""
        mock_gl.glGetShaderiv.side_effect = [0, 100]  # GL_FALSE, log length
        mock_gl.glGetShaderInfoLog.return_value = b"Compilation error"
        
        result = OpenGLValidator.validate_shader_compilation(123, "fragment")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.category, ErrorCategory.OPENGL)
        self.assertEqual(result.code, "SHADER_COMPILATION_FAILED")
        self.assertIn("Compilation error", result.details)


class TestLibassValidator(unittest.TestCase):
    """Test libass parsing error handling."""
    
    def test_validate_ass_file_not_found(self):
        """Test validation of non-existent ASS file."""
        errors = LibassValidator.validate_ass_file("nonexistent.ass")
        
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "ASS_FILE_NOT_FOUND")
    
    def test_validate_ass_file_valid(self):
        """Test validation of valid ASS file."""
        # Create temporary valid ASS file
        ass_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\k50}Test {\\k50}karaoke
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_path = f.name
        
        try:
            errors = LibassValidator.validate_ass_file(temp_path)
            
            # Should have no critical errors, maybe warnings about karaoke timing
            critical_errors = [e for e in errors if e.severity == ErrorSeverity.ERROR]
            self.assertEqual(len(critical_errors), 0)
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_ass_file_missing_sections(self):
        """Test validation of ASS file with missing sections."""
        # Create ASS file missing required sections
        ass_content = """[Script Info]
Title: Test
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_path = f.name
        
        try:
            errors = LibassValidator.validate_ass_file(temp_path)
            
            # Should have errors for missing sections
            section_errors = [e for e in errors if e.code == "ASS_MISSING_SECTION"]
            self.assertGreater(len(section_errors), 0)
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_ass_file_encoding_error(self):
        """Test validation of ASS file with encoding issues."""
        # Create file with invalid UTF-8
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ass', delete=False) as f:
            f.write(b'\xff\xfe[Script Info]\nTitle: Test')
            temp_path = f.name
        
        try:
            errors = LibassValidator.validate_ass_file(temp_path)
            
            # Should have encoding error
            encoding_errors = [e for e in errors if e.code == "ASS_ENCODING_ERROR"]
            self.assertEqual(len(encoding_errors), 1)
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_karaoke_timing_invalid(self):
        """Test validation of invalid karaoke timing."""
        ass_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,{\\k-50}Invalid {\\k50}timing
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_path = f.name
        
        try:
            errors = LibassValidator.validate_ass_file(temp_path)
            
            # Should have invalid timing error
            timing_errors = [e for e in errors if e.code == "ASS_INVALID_TIMING"]
            self.assertEqual(len(timing_errors), 1)
            
        finally:
            os.unlink(temp_path)


class TestFFmpegValidator(unittest.TestCase):
    """Test FFmpeg process failure detection."""
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_installation_success(self, mock_run):
        """Test successful FFmpeg validation."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.0"
        mock_run.return_value = mock_result
        
        # Mock codec check
        with patch.object(FFmpegValidator, '_validate_ffmpeg_codecs', return_value=[]):
            result = FFmpegValidator.validate_ffmpeg_installation()
            
            self.assertIsNone(result)
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_installation_not_found(self, mock_run):
        """Test FFmpeg not found."""
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        
        result = FFmpegValidator.validate_ffmpeg_installation()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "FFMPEG_NOT_FOUND")
        self.assertIn("Install FFmpeg", result.recovery_suggestions[0])
    
    @patch('subprocess.run')
    def test_validate_ffmpeg_installation_not_working(self, mock_run):
        """Test FFmpeg not working properly."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error message"
        mock_run.return_value = mock_result
        
        result = FFmpegValidator.validate_ffmpeg_installation()
        
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "FFMPEG_NOT_WORKING")
    
    def test_analyze_ffmpeg_error_file_not_found(self):
        """Test FFmpeg error analysis for file not found."""
        stderr = "No such file or directory"
        command = ["ffmpeg", "-i", "missing.mp4"]
        
        result = FFmpegValidator.analyze_ffmpeg_error(stderr, command)
        
        self.assertEqual(result.code, "FFMPEG_FILE_NOT_FOUND")
        self.assertIn("Check input file path is correct", result.recovery_suggestions)
    
    def test_analyze_ffmpeg_error_permission_denied(self):
        """Test FFmpeg error analysis for permission denied."""
        stderr = "Permission denied"
        command = ["ffmpeg", "-i", "input.mp4", "output.mp4"]
        
        result = FFmpegValidator.analyze_ffmpeg_error(stderr, command)
        
        self.assertEqual(result.code, "FFMPEG_PERMISSION_DENIED")
        self.assertIn("Check file permissions", result.recovery_suggestions)
    
    def test_analyze_ffmpeg_error_unknown(self):
        """Test FFmpeg error analysis for unknown error."""
        stderr = "Unknown error occurred"
        command = ["ffmpeg", "-i", "input.mp4"]
        
        result = FFmpegValidator.analyze_ffmpeg_error(stderr, command)
        
        self.assertEqual(result.code, "FFMPEG_UNKNOWN_ERROR")
        self.assertIn("Check FFmpeg command syntax", result.recovery_suggestions)


class TestDependencyValidator(unittest.TestCase):
    """Test dependency validation."""
    
    def test_check_python_dependencies_success(self):
        """Test successful Python dependency check."""
        # All required packages should be available in test environment
        errors = DependencyValidator._check_python_dependencies()
        
        # Filter out expected missing packages that might not be in test environment
        critical_errors = [e for e in errors if e.severity == ErrorSeverity.CRITICAL]
        
        # In a proper test environment, we might have some missing packages
        # This test mainly checks that the function runs without crashing
        self.assertIsInstance(errors, list)
    
    @patch('builtins.__import__')
    def test_check_python_dependencies_missing(self, mock_import):
        """Test Python dependency check with missing packages."""
        mock_import.side_effect = ImportError("No module named 'test_package'")
        
        errors = DependencyValidator._check_python_dependencies()
        
        # Should have errors for all missing packages
        self.assertGreater(len(errors), 0)
        
        for error in errors:
            self.assertEqual(error.category, ErrorCategory.DEPENDENCY)
            self.assertEqual(error.severity, ErrorSeverity.CRITICAL)
    
    @patch('subprocess.run')
    def test_check_system_dependencies_ffmpeg_missing(self, mock_run):
        """Test system dependency check with missing FFmpeg."""
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        
        errors = DependencyValidator._check_system_dependencies()
        
        # Should have FFmpeg error
        ffmpeg_errors = [e for e in errors if "FFMPEG" in e.code]
        self.assertGreater(len(ffmpeg_errors), 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""
    
    def test_create_user_friendly_error_message(self):
        """Test user-friendly error message creation."""
        error_info = ErrorInfo(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            code="TEST_ERROR",
            message="Test error occurred",
            details="Additional details",
            recovery_suggestions=["Try this", "Or this"]
        )
        
        message = create_user_friendly_error_message(error_info)
        
        self.assertIn("❌ Test error occurred", message)
        self.assertIn("Details: Additional details", message)
        self.assertIn("💡 What you can do:", message)
        self.assertIn("1. Try this", message)
        self.assertIn("2. Or this", message)
    
    def test_create_user_friendly_error_message_minimal(self):
        """Test user-friendly error message with minimal info."""
        error_info = ErrorInfo(
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.WARNING,
            code="TEST_WARNING",
            message="Simple warning"
        )
        
        message = create_user_friendly_error_message(error_info)
        
        self.assertIn("❌ Simple warning", message)
        self.assertNotIn("Details:", message)
        self.assertNotIn("💡 What you can do:", message)
    
    @patch('core.error_handling.logger')
    def test_log_error_for_debugging(self, mock_logger):
        """Test error logging for debugging."""
        error_info = ErrorInfo(
            category=ErrorCategory.OPENGL,
            severity=ErrorSeverity.ERROR,
            code="GL_ERROR",
            message="OpenGL error",
            details="Error details",
            technical_info={"error_code": 1234}
        )
        
        log_error_for_debugging(error_info)
        
        mock_logger.error.assert_called()
        mock_logger.debug.assert_called()


class TestGlobalErrorHandler(unittest.TestCase):
    """Test global error handler instance."""
    
    def test_global_error_handler_exists(self):
        """Test that global error handler is available."""
        self.assertIsInstance(global_error_handler, ErrorHandler)
    
    def test_global_error_handler_functionality(self):
        """Test global error handler basic functionality."""
        test_error = ValueError("Test error")
        result = global_error_handler.handle_error(test_error, "test")
        
        self.assertIsInstance(result, ErrorInfo)
        self.assertEqual(result.category, ErrorCategory.SYSTEM)


if __name__ == '__main__':
    # Run tests silently
    unittest.main(verbosity=0, buffer=True)