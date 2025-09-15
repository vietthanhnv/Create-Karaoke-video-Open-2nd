"""
Comprehensive error handling and validation system for the Karaoke Video Creator.

This module provides enhanced error classes, validation functions, and recovery
mechanisms for OpenGL, libass, FFmpeg, and dependency validation.
"""

import os
import sys
import logging
import traceback
import subprocess
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorizing issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better organization."""
    OPENGL = "opengl"
    LIBASS = "libass"
    FFMPEG = "ffmpeg"
    DEPENDENCY = "dependency"
    FILE_IO = "file_io"
    VALIDATION = "validation"
    SYSTEM = "system"
    NETWORK = "network"


@dataclass
class ErrorInfo:
    """Comprehensive error information with recovery suggestions."""
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    details: str = ""
    recovery_suggestions: List[str] = None
    technical_info: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []
        if self.technical_info is None:
            self.technical_info = {}


class KaraokeError(Exception):
    """Base exception class for all karaoke video creator errors."""
    
    def __init__(self, error_info: ErrorInfo, cause: Exception = None):
        self.error_info = error_info
        self.cause = cause
        super().__init__(error_info.message)
    
    def get_user_message(self) -> str:
        """Get user-friendly error message with recovery suggestions."""
        message = f"{self.error_info.message}"
        if self.error_info.recovery_suggestions:
            message += "\n\nSuggestions:"
            for suggestion in self.error_info.recovery_suggestions:
                message += f"\n• {suggestion}"
        return message
    
    def get_technical_details(self) -> str:
        """Get technical details for debugging."""
        details = f"Category: {self.error_info.category.value}\n"
        details += f"Severity: {self.error_info.severity.value}\n"
        details += f"Code: {self.error_info.code}\n"
        details += f"Message: {self.error_info.message}\n"
        
        if self.error_info.details:
            details += f"Details: {self.error_info.details}\n"
        
        if self.error_info.technical_info:
            details += "Technical Info:\n"
            for key, value in self.error_info.technical_info.items():
                details += f"  {key}: {value}\n"
        
        if self.cause:
            details += f"Caused by: {type(self.cause).__name__}: {self.cause}\n"
            details += f"Traceback: {traceback.format_exc()}\n"
        
        return details


class OpenGLError(KaraokeError):
    """OpenGL-specific error with detailed diagnostics."""
    pass


class LibassError(KaraokeError):
    """Libass-specific error with parsing details."""
    pass


class FFmpegError(KaraokeError):
    """FFmpeg-specific error with process information."""
    pass


class DependencyError(KaraokeError):
    """Dependency validation error with installation guidance."""
    pass


class ValidationError(KaraokeError):
    """File and configuration validation error."""
    pass


class ErrorHandler:
    """Central error handling and validation system."""
    
    def __init__(self):
        self.error_history: List[ErrorInfo] = []
        self.recovery_attempts: Dict[str, int] = {}
        self.max_recovery_attempts = 3
    
    def handle_error(self, error: Exception, context: str = "") -> ErrorInfo:
        """
        Handle an error and return structured error information.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            ErrorInfo object with details and recovery suggestions
        """
        if isinstance(error, KaraokeError):
            error_info = error.error_info
        else:
            error_info = self._classify_error(error, context)
        
        # Log the error
        logger.error(f"Error in {context}: {error_info.message}", exc_info=error)
        
        # Add to error history
        self.error_history.append(error_info)
        
        return error_info
    
    def _classify_error(self, error: Exception, context: str) -> ErrorInfo:
        """Classify an unknown error and create ErrorInfo."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Try to classify based on error message and context
        if "opengl" in error_message.lower() or "gl" in context.lower():
            return self._create_opengl_error_info(error, context)
        elif "libass" in error_message.lower() or "ass" in context.lower():
            return self._create_libass_error_info(error, context)
        elif "ffmpeg" in error_message.lower() or "ffmpeg" in context.lower():
            return self._create_ffmpeg_error_info(error, context)
        elif isinstance(error, (FileNotFoundError, PermissionError, OSError)):
            return self._create_file_error_info(error, context)
        else:
            return ErrorInfo(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.ERROR,
                code=f"UNKNOWN_{error_type}",
                message=f"Unexpected error: {error_message}",
                details=f"Context: {context}",
                recovery_suggestions=[
                    "Try restarting the application",
                    "Check system resources and permissions",
                    "Report this issue if it persists"
                ],
                technical_info={
                    "error_type": error_type,
                    "context": context,
                    "traceback": traceback.format_exc()
                }
            )
    
    def _create_opengl_error_info(self, error: Exception, context: str) -> ErrorInfo:
        """Create OpenGL-specific error information."""
        return ErrorInfo(
            category=ErrorCategory.OPENGL,
            severity=ErrorSeverity.ERROR,
            code="OPENGL_ERROR",
            message=f"OpenGL error: {str(error)}",
            details=f"Context: {context}",
            recovery_suggestions=[
                "Update your graphics drivers",
                "Check OpenGL 3.3+ support",
                "Try running with software rendering",
                "Restart the application"
            ],
            technical_info={
                "context": context,
                "error_type": type(error).__name__
            }
        )
    
    def _create_libass_error_info(self, error: Exception, context: str) -> ErrorInfo:
        """Create libass-specific error information."""
        return ErrorInfo(
            category=ErrorCategory.LIBASS,
            severity=ErrorSeverity.ERROR,
            code="LIBASS_ERROR",
            message=f"Subtitle processing error: {str(error)}",
            details=f"Context: {context}",
            recovery_suggestions=[
                "Check ASS file format and encoding",
                "Verify karaoke timing tags (\\k, \\K, \\kf)",
                "Ensure libass library is properly installed",
                "Try with a different ASS file"
            ],
            technical_info={
                "context": context,
                "error_type": type(error).__name__
            }
        )
    
    def _create_ffmpeg_error_info(self, error: Exception, context: str) -> ErrorInfo:
        """Create FFmpeg-specific error information."""
        return ErrorInfo(
            category=ErrorCategory.FFMPEG,
            severity=ErrorSeverity.ERROR,
            code="FFMPEG_ERROR",
            message=f"Video processing error: {str(error)}",
            details=f"Context: {context}",
            recovery_suggestions=[
                "Check FFmpeg installation and PATH",
                "Verify input file formats are supported",
                "Check available disk space",
                "Try with different encoding settings"
            ],
            technical_info={
                "context": context,
                "error_type": type(error).__name__
            }
        )
    
    def _create_file_error_info(self, error: Exception, context: str) -> ErrorInfo:
        """Create file I/O error information."""
        severity = ErrorSeverity.CRITICAL if isinstance(error, PermissionError) else ErrorSeverity.ERROR
        
        return ErrorInfo(
            category=ErrorCategory.FILE_IO,
            severity=severity,
            code=f"FILE_{type(error).__name__.upper()}",
            message=f"File operation failed: {str(error)}",
            details=f"Context: {context}",
            recovery_suggestions=[
                "Check file path and permissions",
                "Ensure file is not in use by another application",
                "Verify sufficient disk space",
                "Try running as administrator if needed"
            ],
            technical_info={
                "context": context,
                "error_type": type(error).__name__
            }
        )


class OpenGLValidator:
    """OpenGL error checking and shader validation."""
    
    @staticmethod
    def check_opengl_errors(context: str = "") -> List[ErrorInfo]:
        """
        Check for OpenGL errors and return detailed information.
        
        Args:
            context: Context where the check is performed
            
        Returns:
            List of ErrorInfo objects for any OpenGL errors found
        """
        errors = []
        
        try:
            from OpenGL import GL as gl
            
            error_code = gl.glGetError()
            while error_code != gl.GL_NO_ERROR:
                error_name = OpenGLValidator._get_opengl_error_name(error_code)
                
                error_info = ErrorInfo(
                    category=ErrorCategory.OPENGL,
                    severity=ErrorSeverity.ERROR,
                    code=f"GL_{error_name}",
                    message=f"OpenGL error: {error_name} (0x{error_code:04X})",
                    details=f"Context: {context}",
                    recovery_suggestions=OpenGLValidator._get_opengl_recovery_suggestions(error_code),
                    technical_info={
                        "error_code": error_code,
                        "error_name": error_name,
                        "context": context
                    }
                )
                errors.append(error_info)
                
                # Get next error
                error_code = gl.glGetError()
                
        except Exception as e:
            # If we can't check OpenGL errors, create a generic error
            error_info = ErrorInfo(
                category=ErrorCategory.OPENGL,
                severity=ErrorSeverity.WARNING,
                code="GL_CHECK_FAILED",
                message=f"Could not check OpenGL errors: {str(e)}",
                details=f"Context: {context}",
                recovery_suggestions=[
                    "OpenGL may not be properly initialized",
                    "Check graphics driver installation"
                ]
            )
            errors.append(error_info)
        
        return errors
    
    @staticmethod
    def _get_opengl_error_name(error_code: int) -> str:
        """Get human-readable name for OpenGL error code."""
        try:
            from OpenGL import GL as gl
            
            error_names = {
                gl.GL_INVALID_ENUM: "INVALID_ENUM",
                gl.GL_INVALID_VALUE: "INVALID_VALUE",
                gl.GL_INVALID_OPERATION: "INVALID_OPERATION",
                gl.GL_OUT_OF_MEMORY: "OUT_OF_MEMORY",
                gl.GL_INVALID_FRAMEBUFFER_OPERATION: "INVALID_FRAMEBUFFER_OPERATION"
            }
            
            return error_names.get(error_code, f"UNKNOWN_ERROR_{error_code}")
            
        except ImportError:
            return f"ERROR_{error_code}"
    
    @staticmethod
    def _get_opengl_recovery_suggestions(error_code: int) -> List[str]:
        """Get recovery suggestions for specific OpenGL errors."""
        try:
            from OpenGL import GL as gl
            
            suggestions = {
                gl.GL_INVALID_ENUM: [
                    "Check that all OpenGL enums are valid",
                    "Verify OpenGL version compatibility"
                ],
                gl.GL_INVALID_VALUE: [
                    "Check parameter values are within valid ranges",
                    "Verify buffer sizes and array indices"
                ],
                gl.GL_INVALID_OPERATION: [
                    "Check OpenGL state before operation",
                    "Ensure proper context is current"
                ],
                gl.GL_OUT_OF_MEMORY: [
                    "Reduce texture sizes or buffer allocations",
                    "Free unused OpenGL resources",
                    "Check available GPU memory"
                ],
                gl.GL_INVALID_FRAMEBUFFER_OPERATION: [
                    "Check framebuffer completeness",
                    "Verify framebuffer attachments"
                ]
            }
            
            return suggestions.get(error_code, [
                "Check OpenGL documentation for error details",
                "Verify graphics driver compatibility"
            ])
            
        except ImportError:
            return ["Update graphics drivers", "Check OpenGL support"]
    
    @staticmethod
    def validate_shader_compilation(shader_id: int, shader_type: str) -> Optional[ErrorInfo]:
        """
        Validate shader compilation and return error info if failed.
        
        Args:
            shader_id: OpenGL shader ID
            shader_type: Type of shader (vertex, fragment, etc.)
            
        Returns:
            ErrorInfo if compilation failed, None if successful
        """
        try:
            from OpenGL import GL as gl
            
            # Check compilation status
            compile_status = gl.glGetShaderiv(shader_id, gl.GL_COMPILE_STATUS)
            
            if not compile_status:
                # Get compilation log
                log_length = gl.glGetShaderiv(shader_id, gl.GL_INFO_LOG_LENGTH)
                if log_length > 0:
                    log = gl.glGetShaderInfoLog(shader_id).decode('utf-8')
                else:
                    log = "No compilation log available"
                
                return ErrorInfo(
                    category=ErrorCategory.OPENGL,
                    severity=ErrorSeverity.ERROR,
                    code="SHADER_COMPILATION_FAILED",
                    message=f"{shader_type} shader compilation failed",
                    details=f"Compilation log: {log}",
                    recovery_suggestions=[
                        "Check shader source code syntax",
                        "Verify GLSL version compatibility",
                        "Check for unsupported features"
                    ],
                    technical_info={
                        "shader_id": shader_id,
                        "shader_type": shader_type,
                        "compilation_log": log
                    }
                )
            
            return None
            
        except Exception as e:
            return ErrorInfo(
                category=ErrorCategory.OPENGL,
                severity=ErrorSeverity.ERROR,
                code="SHADER_VALIDATION_FAILED",
                message=f"Could not validate {shader_type} shader: {str(e)}",
                recovery_suggestions=[
                    "Check OpenGL context initialization",
                    "Verify shader ID is valid"
                ]
            )


class LibassValidator:
    """Libass parsing error handling with detailed feedback."""
    
    @staticmethod
    def validate_ass_file(file_path: str) -> List[ErrorInfo]:
        """
        Validate ASS file format and provide detailed error feedback.
        
        Args:
            file_path: Path to ASS file
            
        Returns:
            List of ErrorInfo objects for any validation issues
        """
        errors = []
        
        try:
            if not os.path.exists(file_path):
                errors.append(ErrorInfo(
                    category=ErrorCategory.LIBASS,
                    severity=ErrorSeverity.ERROR,
                    code="ASS_FILE_NOT_FOUND",
                    message=f"ASS file not found: {file_path}",
                    recovery_suggestions=[
                        "Check file path is correct",
                        "Ensure file exists and is accessible"
                    ]
                ))
                return errors
            
            # Read and validate file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError as e:
                errors.append(ErrorInfo(
                    category=ErrorCategory.LIBASS,
                    severity=ErrorSeverity.ERROR,
                    code="ASS_ENCODING_ERROR",
                    message=f"ASS file encoding error: {str(e)}",
                    recovery_suggestions=[
                        "Convert file to UTF-8 encoding",
                        "Check file is not corrupted"
                    ]
                ))
                return errors
            
            # Validate ASS structure
            structure_errors = LibassValidator._validate_ass_structure(content, file_path)
            errors.extend(structure_errors)
            
            # Validate karaoke timing
            timing_errors = LibassValidator._validate_karaoke_timing(content, file_path)
            errors.extend(timing_errors)
            
        except Exception as e:
            errors.append(ErrorInfo(
                category=ErrorCategory.LIBASS,
                severity=ErrorSeverity.ERROR,
                code="ASS_VALIDATION_FAILED",
                message=f"ASS file validation failed: {str(e)}",
                recovery_suggestions=[
                    "Check file format and permissions",
                    "Try with a different ASS file"
                ]
            ))
        
        return errors
    
    @staticmethod
    def _validate_ass_structure(content: str, file_path: str) -> List[ErrorInfo]:
        """Validate ASS file structure."""
        errors = []
        
        # Check for required sections
        required_sections = ['[Script Info]', '[V4+ Styles]', '[Events]']
        for section in required_sections:
            if section not in content:
                errors.append(ErrorInfo(
                    category=ErrorCategory.LIBASS,
                    severity=ErrorSeverity.ERROR,
                    code="ASS_MISSING_SECTION",
                    message=f"Missing required section: {section}",
                    details=f"File: {file_path}",
                    recovery_suggestions=[
                        f"Add {section} section to ASS file",
                        "Use a proper ASS editor or template"
                    ]
                ))
        
        # Check for dialogue lines
        if 'Dialogue:' not in content:
            errors.append(ErrorInfo(
                category=ErrorCategory.LIBASS,
                severity=ErrorSeverity.WARNING,
                code="ASS_NO_DIALOGUE",
                message="No dialogue lines found in ASS file",
                details=f"File: {file_path}",
                recovery_suggestions=[
                    "Add dialogue lines to Events section",
                    "Check file contains subtitle content"
                ]
            ))
        
        return errors
    
    @staticmethod
    def _validate_karaoke_timing(content: str, file_path: str) -> List[ErrorInfo]:
        """Validate karaoke timing tags."""
        errors = []
        
        import re
        
        lines = content.split('\n')
        events_section = False
        karaoke_found = False
        line_number = 0
        
        for line_num, line in enumerate(lines, 1):
            if line.strip() == '[Events]':
                events_section = True
                continue
            elif line.strip().startswith('[') and events_section:
                break
            
            if events_section and line.strip().startswith('Dialogue:'):
                line_number += 1
                
                # Check for karaoke timing tags
                karaoke_patterns = [r'\\k-?\d+', r'\\K-?\d+', r'\\kf-?\d+']
                
                for pattern in karaoke_patterns:
                    matches = re.findall(pattern, line)
                    if matches:
                        karaoke_found = True
                        
                        # Validate timing values
                        for match in matches:
                            timing_value = int(re.search(r'-?\d+', match).group())
                            if timing_value < 0:
                                errors.append(ErrorInfo(
                                    category=ErrorCategory.LIBASS,
                                    severity=ErrorSeverity.ERROR,
                                    code="ASS_INVALID_TIMING",
                                    message=f"Invalid karaoke timing: {match}",
                                    details=f"Line {line_num}: Negative timing values not allowed",
                                    recovery_suggestions=[
                                        "Use positive timing values",
                                        "Check karaoke timing calculation"
                                    ],
                                    technical_info={
                                        "line_number": line_num,
                                        "timing_tag": match,
                                        "timing_value": timing_value
                                    }
                                ))
        
        if not karaoke_found:
            errors.append(ErrorInfo(
                category=ErrorCategory.LIBASS,
                severity=ErrorSeverity.WARNING,
                code="ASS_NO_KARAOKE_TIMING",
                message="No karaoke timing found in ASS file",
                details=f"File: {file_path}",
                recovery_suggestions=[
                    "Add \\k, \\K, or \\kf timing tags",
                    "Use karaoke timing software to generate tags"
                ]
            ))
        
        return errors


class FFmpegValidator:
    """FFmpeg process failure detection and recovery."""
    
    @staticmethod
    def validate_ffmpeg_installation() -> Optional[ErrorInfo]:
        """
        Validate FFmpeg installation and capabilities.
        
        Returns:
            ErrorInfo if validation fails, None if successful
        """
        try:
            # Check if FFmpeg is available
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return ErrorInfo(
                    category=ErrorCategory.FFMPEG,
                    severity=ErrorSeverity.CRITICAL,
                    code="FFMPEG_NOT_WORKING",
                    message="FFmpeg is not working properly",
                    details=f"Exit code: {result.returncode}, Error: {result.stderr}",
                    recovery_suggestions=[
                        "Reinstall FFmpeg",
                        "Check FFmpeg is in system PATH",
                        "Verify FFmpeg executable permissions"
                    ]
                )
            
            # Check for required codecs
            codec_errors = FFmpegValidator._validate_ffmpeg_codecs()
            if codec_errors:
                return codec_errors[0]  # Return first critical codec error
            
            return None
            
        except FileNotFoundError:
            return ErrorInfo(
                category=ErrorCategory.FFMPEG,
                severity=ErrorSeverity.CRITICAL,
                code="FFMPEG_NOT_FOUND",
                message="FFmpeg not found in system PATH",
                recovery_suggestions=[
                    "Install FFmpeg from https://ffmpeg.org/",
                    "Add FFmpeg to system PATH",
                    "Restart application after installation"
                ]
            )
        except subprocess.TimeoutExpired:
            return ErrorInfo(
                category=ErrorCategory.FFMPEG,
                severity=ErrorSeverity.ERROR,
                code="FFMPEG_TIMEOUT",
                message="FFmpeg version check timed out",
                recovery_suggestions=[
                    "Check system performance",
                    "Try restarting the application",
                    "Check for FFmpeg conflicts"
                ]
            )
        except Exception as e:
            return ErrorInfo(
                category=ErrorCategory.FFMPEG,
                severity=ErrorSeverity.ERROR,
                code="FFMPEG_VALIDATION_FAILED",
                message=f"FFmpeg validation failed: {str(e)}",
                recovery_suggestions=[
                    "Check FFmpeg installation",
                    "Verify system permissions"
                ]
            )
    
    @staticmethod
    def _validate_ffmpeg_codecs() -> List[ErrorInfo]:
        """Validate required FFmpeg codecs are available."""
        errors = []
        
        required_codecs = {
            'libx264': 'H.264 video encoding',
            'aac': 'AAC audio encoding',
            'libass': 'ASS subtitle rendering'
        }
        
        try:
            # Get list of available codecs
            result = subprocess.run(
                ['ffmpeg', '-codecs'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                codec_output = result.stdout
                
                for codec, description in required_codecs.items():
                    if codec not in codec_output:
                        errors.append(ErrorInfo(
                            category=ErrorCategory.FFMPEG,
                            severity=ErrorSeverity.ERROR,
                            code=f"FFMPEG_MISSING_{codec.upper()}",
                            message=f"Required codec not available: {codec}",
                            details=f"Codec needed for: {description}",
                            recovery_suggestions=[
                                f"Install FFmpeg with {codec} support",
                                "Use a complete FFmpeg build",
                                "Check FFmpeg compilation options"
                            ]
                        ))
            
        except Exception as e:
            errors.append(ErrorInfo(
                category=ErrorCategory.FFMPEG,
                severity=ErrorSeverity.WARNING,
                code="FFMPEG_CODEC_CHECK_FAILED",
                message=f"Could not check FFmpeg codecs: {str(e)}",
                recovery_suggestions=[
                    "FFmpeg may still work for basic operations",
                    "Check FFmpeg installation if issues occur"
                ]
            ))
        
        return errors
    
    @staticmethod
    def analyze_ffmpeg_error(stderr_output: str, command: List[str]) -> ErrorInfo:
        """
        Analyze FFmpeg error output and provide specific guidance.
        
        Args:
            stderr_output: FFmpeg stderr output
            command: FFmpeg command that failed
            
        Returns:
            ErrorInfo with specific error analysis
        """
        error_patterns = {
            'No such file or directory': {
                'code': 'FFMPEG_FILE_NOT_FOUND',
                'message': 'Input file not found',
                'suggestions': [
                    'Check input file path is correct',
                    'Ensure file exists and is accessible'
                ]
            },
            'Permission denied': {
                'code': 'FFMPEG_PERMISSION_DENIED',
                'message': 'Permission denied accessing file',
                'suggestions': [
                    'Check file permissions',
                    'Run with administrator privileges if needed',
                    'Ensure file is not in use by another application'
                ]
            },
            'Invalid data found': {
                'code': 'FFMPEG_INVALID_DATA',
                'message': 'Invalid or corrupted media data',
                'suggestions': [
                    'Check input file is not corrupted',
                    'Try with a different input file',
                    'Verify file format is supported'
                ]
            },
            'Codec not found': {
                'code': 'FFMPEG_CODEC_NOT_FOUND',
                'message': 'Required codec not available',
                'suggestions': [
                    'Install FFmpeg with required codec support',
                    'Use a different output format',
                    'Check FFmpeg build configuration'
                ]
            },
            'No space left on device': {
                'code': 'FFMPEG_NO_SPACE',
                'message': 'Insufficient disk space',
                'suggestions': [
                    'Free up disk space',
                    'Choose a different output location',
                    'Use lower quality settings'
                ]
            }
        }
        
        # Find matching error pattern
        for pattern, info in error_patterns.items():
            if pattern in stderr_output:
                return ErrorInfo(
                    category=ErrorCategory.FFMPEG,
                    severity=ErrorSeverity.ERROR,
                    code=info['code'],
                    message=info['message'],
                    details=f"FFmpeg error: {stderr_output}",
                    recovery_suggestions=info['suggestions'],
                    technical_info={
                        'command': ' '.join(command),
                        'stderr': stderr_output
                    }
                )
        
        # Generic FFmpeg error
        return ErrorInfo(
            category=ErrorCategory.FFMPEG,
            severity=ErrorSeverity.ERROR,
            code='FFMPEG_UNKNOWN_ERROR',
            message='FFmpeg processing failed',
            details=f"FFmpeg error: {stderr_output}",
            recovery_suggestions=[
                'Check FFmpeg command syntax',
                'Verify input file format',
                'Try with different settings',
                'Check FFmpeg documentation'
            ],
            technical_info={
                'command': ' '.join(command),
                'stderr': stderr_output
            }
        )


class DependencyValidator:
    """Dependency validation with installation guidance."""
    
    @staticmethod
    def validate_all_dependencies() -> List[ErrorInfo]:
        """
        Validate all required dependencies.
        
        Returns:
            List of ErrorInfo objects for any missing or invalid dependencies
        """
        errors = []
        
        # Check Python dependencies
        python_deps = DependencyValidator._check_python_dependencies()
        errors.extend(python_deps)
        
        # Check system dependencies
        system_deps = DependencyValidator._check_system_dependencies()
        errors.extend(system_deps)
        
        # Check OpenGL support
        opengl_deps = DependencyValidator._check_opengl_support()
        errors.extend(opengl_deps)
        
        return errors
    
    @staticmethod
    def _check_python_dependencies() -> List[ErrorInfo]:
        """Check required Python packages."""
        errors = []
        
        required_packages = {
            'PyQt6': 'GUI framework',
            'OpenGL': 'OpenGL bindings',
            'numpy': 'Numerical computing',
            'Pillow': 'Image processing'
        }
        
        for package, description in required_packages.items():
            try:
                __import__(package)
            except ImportError:
                errors.append(ErrorInfo(
                    category=ErrorCategory.DEPENDENCY,
                    severity=ErrorSeverity.CRITICAL,
                    code=f"MISSING_{package.upper()}",
                    message=f"Required Python package not found: {package}",
                    details=f"Package needed for: {description}",
                    recovery_suggestions=[
                        f"Install {package}: pip install {package}",
                        "Install all requirements: pip install -r requirements.txt",
                        "Check virtual environment is activated"
                    ]
                ))
        
        return errors
    
    @staticmethod
    def _check_system_dependencies() -> List[ErrorInfo]:
        """Check system-level dependencies."""
        errors = []
        
        # Check FFmpeg
        ffmpeg_error = FFmpegValidator.validate_ffmpeg_installation()
        if ffmpeg_error:
            errors.append(ffmpeg_error)
        
        # Check libass (if available)
        try:
            import ctypes
            
            # Try to load libass
            if sys.platform == "win32":
                lib_names = ["libass.dll", "ass.dll"]
            elif sys.platform == "darwin":
                lib_names = ["libass.dylib", "libass.9.dylib"]
            else:
                lib_names = ["libass.so", "libass.so.9"]
            
            libass_found = False
            for lib_name in lib_names:
                try:
                    ctypes.CDLL(lib_name)
                    libass_found = True
                    break
                except OSError:
                    continue
            
            if not libass_found:
                errors.append(ErrorInfo(
                    category=ErrorCategory.DEPENDENCY,
                    severity=ErrorSeverity.ERROR,
                    code="LIBASS_NOT_FOUND",
                    message="libass library not found",
                    details="Required for ASS subtitle rendering",
                    recovery_suggestions=[
                        "Install libass development package",
                        "On Windows: Download libass DLL",
                        "On Linux: sudo apt-get install libass-dev",
                        "On macOS: brew install libass"
                    ]
                ))
                
        except Exception as e:
            errors.append(ErrorInfo(
                category=ErrorCategory.DEPENDENCY,
                severity=ErrorSeverity.WARNING,
                code="LIBASS_CHECK_FAILED",
                message=f"Could not check libass: {str(e)}",
                recovery_suggestions=[
                    "libass may still work if properly installed",
                    "Check system library paths"
                ]
            ))
        
        return errors
    
    @staticmethod
    def _check_opengl_support() -> List[ErrorInfo]:
        """Check OpenGL support and version."""
        errors = []
        
        try:
            from PyQt6.QtOpenGL import QOpenGLContext
            from PyQt6.QtGui import QSurfaceFormat
            
            # Create a context to check OpenGL support
            format = QSurfaceFormat()
            format.setVersion(3, 3)
            format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            
            context = QOpenGLContext()
            context.setFormat(format)
            
            if not context.create():
                errors.append(ErrorInfo(
                    category=ErrorCategory.DEPENDENCY,
                    severity=ErrorSeverity.CRITICAL,
                    code="OPENGL_CONTEXT_FAILED",
                    message="Could not create OpenGL 3.3 context",
                    recovery_suggestions=[
                        "Update graphics drivers",
                        "Check OpenGL 3.3+ support",
                        "Try software rendering mode"
                    ]
                ))
            
        except ImportError as e:
            errors.append(ErrorInfo(
                category=ErrorCategory.DEPENDENCY,
                severity=ErrorSeverity.CRITICAL,
                code="PYQT6_OPENGL_MISSING",
                message=f"PyQt6 OpenGL support not available: {str(e)}",
                recovery_suggestions=[
                    "Install PyQt6 with OpenGL support",
                    "pip install PyQt6[opengl]",
                    "Check PyQt6 installation"
                ]
            ))
        except Exception as e:
            errors.append(ErrorInfo(
                category=ErrorCategory.DEPENDENCY,
                severity=ErrorSeverity.WARNING,
                code="OPENGL_CHECK_FAILED",
                message=f"Could not check OpenGL support: {str(e)}",
                recovery_suggestions=[
                    "OpenGL may still work if drivers are installed",
                    "Try running the application to test"
                ]
            ))
        
        return errors


def create_user_friendly_error_message(error_info: ErrorInfo) -> str:
    """
    Create a user-friendly error message from ErrorInfo.
    
    Args:
        error_info: ErrorInfo object
        
    Returns:
        Formatted user-friendly error message
    """
    message = f"❌ {error_info.message}\n"
    
    if error_info.details:
        message += f"\nDetails: {error_info.details}\n"
    
    if error_info.recovery_suggestions:
        message += "\n💡 What you can do:\n"
        for i, suggestion in enumerate(error_info.recovery_suggestions, 1):
            message += f"{i}. {suggestion}\n"
    
    return message


def log_error_for_debugging(error_info: ErrorInfo) -> None:
    """
    Log error information for debugging purposes.
    
    Args:
        error_info: ErrorInfo object to log
    """
    logger.error(f"[{error_info.category.value.upper()}] {error_info.message}")
    
    if error_info.details:
        logger.error(f"Details: {error_info.details}")
    
    if error_info.technical_info:
        logger.debug(f"Technical info: {error_info.technical_info}")


# Global error handler instance
global_error_handler = ErrorHandler()