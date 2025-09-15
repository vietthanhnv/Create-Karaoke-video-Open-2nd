"""
OpenGL Context and Framebuffer Management System

This module provides offscreen OpenGL context creation and framebuffer management
for high-performance video rendering without requiring window display.
Supports both GLFW and PyQt6 backends for maximum compatibility.
"""

import sys
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenGL libraries
try:
    import OpenGL.GL as gl
    import OpenGL.GL.framebufferobjects as fbo
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    logger.warning("OpenGL not available, using mock implementation")

# Try to import PyQt6 for context creation
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QOpenGLContext, QSurfaceFormat, QOffscreenSurface
    from PyQt6.QtOpenGL import QOpenGLFramebufferObject
    from PyQt6.QtWidgets import QApplication
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logger.warning("PyQt6 not available for OpenGL context")

# Try to import GLFW as alternative
try:
    import glfw
    GLFW_AVAILABLE = True
except ImportError:
    glfw = None
    GLFW_AVAILABLE = False
    logger.warning("GLFW not available for OpenGL context")


class ContextBackend(Enum):
    """Available OpenGL context backends"""
    PYQT6 = "pyqt6"
    GLFW = "glfw"
    MOCK = "mock"


@dataclass
class OpenGLCapabilities:
    """OpenGL capabilities and limits"""
    version: str
    vendor: str
    renderer: str
    max_texture_size: int
    max_framebuffer_size: int
    max_color_attachments: int
    supports_core_profile: bool
    supports_framebuffer_objects: bool


@dataclass
class FramebufferConfig:
    """Configuration for framebuffer creation"""
    width: int
    height: int
    color_format: int = gl.GL_RGBA8 if OPENGL_AVAILABLE else 0
    depth_format: int = gl.GL_DEPTH_COMPONENT24 if OPENGL_AVAILABLE else 0
    stencil_format: int = gl.GL_STENCIL_INDEX8 if OPENGL_AVAILABLE else 0
    samples: int = 0  # 0 = no multisampling
    use_depth: bool = True
    use_stencil: bool = False


class OpenGLTexture:
    """Wrapper for OpenGL texture management"""
    
    def __init__(self, texture_id: int, width: int, height: int, format: int):
        self.texture_id = texture_id
        self.width = width
        self.height = height
        self.format = format
        self.is_valid = True
    
    def bind(self, unit: int = 0):
        """Bind texture to specified texture unit"""
        if OPENGL_AVAILABLE and self.is_valid:
            try:
                gl.glActiveTexture(gl.GL_TEXTURE0 + unit)
                gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
            except Exception as e:
                logger.debug(f"Mock texture bind (unit {unit}): {e}")
        elif self.is_valid:
            logger.debug(f"Mock texture bind to unit {unit}")
    
    def unbind(self):
        """Unbind texture"""
        if OPENGL_AVAILABLE:
            try:
                gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            except Exception as e:
                logger.debug(f"Mock texture unbind: {e}")
        else:
            logger.debug("Mock texture unbind")
    
    def destroy(self):
        """Destroy texture and free GPU memory"""
        if OPENGL_AVAILABLE and self.is_valid:
            gl.glDeleteTextures(1, [self.texture_id])
            self.is_valid = False


class OpenGLFramebuffer:
    """Wrapper for OpenGL framebuffer management"""
    
    def __init__(self, config: FramebufferConfig, mock_mode: bool = False):
        self.config = config
        self.framebuffer_id = 0
        self.color_texture: Optional[OpenGLTexture] = None
        self.depth_texture: Optional[OpenGLTexture] = None
        self.stencil_texture: Optional[OpenGLTexture] = None
        self.is_valid = False
        self.mock_mode = mock_mode
        
        if OPENGL_AVAILABLE and not mock_mode:
            self._create_framebuffer()
        elif mock_mode:
            self._create_mock_framebuffer()
    
    def _create_framebuffer(self):
        """Create framebuffer and attachments"""
        try:
            # Generate framebuffer
            self.framebuffer_id = gl.glGenFramebuffers(1)
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.framebuffer_id)
            
            # Create color attachment
            self._create_color_attachment()
            
            # Create depth attachment if requested
            if self.config.use_depth:
                self._create_depth_attachment()
            
            # Create stencil attachment if requested
            if self.config.use_stencil:
                self._create_stencil_attachment()
            
            # Check framebuffer completeness
            status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
            if status != gl.GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError(f"Framebuffer incomplete: {status}")
            
            # Unbind framebuffer
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
            
            self.is_valid = True
            logger.info(f"Framebuffer created: {self.config.width}x{self.config.height}")
            
        except Exception as e:
            logger.error(f"Failed to create framebuffer: {e}")
            self.destroy()
    
    def _create_color_attachment(self):
        """Create color texture attachment"""
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        
        # Allocate texture storage
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, self.config.color_format,
            self.config.width, self.config.height, 0,
            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, None
        )
        
        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        
        # Attach to framebuffer
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0,
            gl.GL_TEXTURE_2D, texture_id, 0
        )
        
        self.color_texture = OpenGLTexture(
            texture_id, self.config.width, self.config.height, self.config.color_format
        )
    
    def _create_depth_attachment(self):
        """Create depth texture attachment"""
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        
        # Allocate depth texture storage
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, self.config.depth_format,
            self.config.width, self.config.height, 0,
            gl.GL_DEPTH_COMPONENT, gl.GL_FLOAT, None
        )
        
        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        
        # Attach to framebuffer
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT,
            gl.GL_TEXTURE_2D, texture_id, 0
        )
        
        self.depth_texture = OpenGLTexture(
            texture_id, self.config.width, self.config.height, self.config.depth_format
        )
    
    def _create_stencil_attachment(self):
        """Create stencil texture attachment"""
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        
        # Allocate stencil texture storage
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, self.config.stencil_format,
            self.config.width, self.config.height, 0,
            gl.GL_STENCIL_INDEX, gl.GL_UNSIGNED_BYTE, None
        )
        
        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_NEAREST)
        
        # Attach to framebuffer
        gl.glFramebufferTexture2D(
            gl.GL_FRAMEBUFFER, gl.GL_STENCIL_ATTACHMENT,
            gl.GL_TEXTURE_2D, texture_id, 0
        )
        
        self.stencil_texture = OpenGLTexture(
            texture_id, self.config.width, self.config.height, self.config.stencil_format
        )
    
    def bind(self):
        """Bind framebuffer for rendering"""
        if (OPENGL_AVAILABLE and not self.mock_mode and self.is_valid):
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.framebuffer_id)
            gl.glViewport(0, 0, self.config.width, self.config.height)
        elif self.mock_mode and self.is_valid:
            # Mock bind - just log for testing
            logger.debug(f"Mock bind framebuffer {self.framebuffer_id}")
    
    def unbind(self):
        """Unbind framebuffer (bind default framebuffer)"""
        if OPENGL_AVAILABLE and not self.mock_mode:
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        elif self.mock_mode:
            logger.debug("Mock unbind framebuffer")
    
    def clear(self, color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)):
        """Clear framebuffer with specified color"""
        if OPENGL_AVAILABLE and not self.mock_mode and self.is_valid:
            self.bind()
            gl.glClearColor(*color)
            clear_flags = gl.GL_COLOR_BUFFER_BIT
            
            if self.config.use_depth:
                clear_flags |= gl.GL_DEPTH_BUFFER_BIT
                gl.glClearDepth(1.0)
            
            if self.config.use_stencil:
                clear_flags |= gl.GL_STENCIL_BUFFER_BIT
                gl.glClearStencil(0)
            
            gl.glClear(clear_flags)
        elif self.mock_mode and self.is_valid:
            logger.debug(f"Mock clear framebuffer with color {color}")
    
    def read_pixels(self, format: int = None, data_type: int = None) -> Optional[np.ndarray]:
        """Read framebuffer pixels to numpy array"""
        if not self.is_valid:
            return None
        
        if self.mock_mode:
            # Return mock pixel data for testing
            channels = 4  # RGBA
            pixel_array = np.zeros((self.config.height, self.config.width, channels), dtype=np.uint8)
            return pixel_array
        
        if not OPENGL_AVAILABLE:
            return None
        
        format = format or gl.GL_RGBA
        data_type = data_type or gl.GL_UNSIGNED_BYTE
        
        self.bind()
        
        # Read pixels
        pixels = gl.glReadPixels(
            0, 0, self.config.width, self.config.height,
            format, data_type
        )
        
        # Convert to numpy array
        if format == gl.GL_RGBA:
            channels = 4
        elif format == gl.GL_RGB:
            channels = 3
        else:
            channels = 1
        
        pixel_array = np.frombuffer(pixels, dtype=np.uint8)
        pixel_array = pixel_array.reshape((self.config.height, self.config.width, channels))
        
        # Flip vertically (OpenGL origin is bottom-left)
        pixel_array = np.flipud(pixel_array)
        
        return pixel_array
    
    def resize(self, width: int, height: int):
        """Resize framebuffer"""
        if width == self.config.width and height == self.config.height:
            return
        
        # Destroy current framebuffer
        self.destroy()
        
        # Create new framebuffer with new size
        self.config.width = width
        self.config.height = height
        
        if OPENGL_AVAILABLE and not self.mock_mode:
            self._create_framebuffer()
        elif self.mock_mode:
            self._create_mock_framebuffer()
    
    def _create_mock_framebuffer(self):
        """Create mock framebuffer for testing"""
        self.framebuffer_id = 1
        self.color_texture = OpenGLTexture(2, self.config.width, self.config.height, 0x1908)  # GL_RGBA
        
        if self.config.use_depth:
            self.depth_texture = OpenGLTexture(3, self.config.width, self.config.height, 0x1902)  # GL_DEPTH_COMPONENT
        
        if self.config.use_stencil:
            self.stencil_texture = OpenGLTexture(4, self.config.width, self.config.height, 0x1901)  # GL_STENCIL_INDEX
        
        self.is_valid = True
        logger.info(f"Mock framebuffer created: {self.config.width}x{self.config.height}")

    def destroy(self):
        """Destroy framebuffer and free GPU memory"""
        if (OPENGL_AVAILABLE and not self.mock_mode and self.is_valid) or (self.mock_mode and self.is_valid):
            # Destroy textures
            if self.color_texture:
                if not self.mock_mode:
                    self.color_texture.destroy()
                self.color_texture = None
            
            if self.depth_texture:
                if not self.mock_mode:
                    self.depth_texture.destroy()
                self.depth_texture = None
            
            if self.stencil_texture:
                if not self.mock_mode:
                    self.stencil_texture.destroy()
                self.stencil_texture = None
            
            # Destroy framebuffer
            if self.framebuffer_id and not self.mock_mode:
                gl.glDeleteFramebuffers(1, [self.framebuffer_id])
            
            self.framebuffer_id = 0
            self.is_valid = False


class OpenGLContext:
    """OpenGL context manager with multiple backend support"""
    
    def __init__(self, backend: Optional[ContextBackend] = None):
        self.backend = backend or self._detect_best_backend()
        self.context = None
        self.surface = None
        self.window = None  # For GLFW
        self.capabilities: Optional[OpenGLCapabilities] = None
        self.framebuffers: Dict[str, OpenGLFramebuffer] = {}
        self.is_current = False
        
        logger.info(f"Using OpenGL backend: {self.backend.value}")
    
    def _detect_best_backend(self) -> ContextBackend:
        """Detect the best available OpenGL backend"""
        if PYQT_AVAILABLE:
            return ContextBackend.PYQT6
        elif GLFW_AVAILABLE:
            return ContextBackend.GLFW
        else:
            return ContextBackend.MOCK
    
    def initialize(self, width: int = 1, height: int = 1) -> bool:
        """Initialize OpenGL context"""
        try:
            if self.backend == ContextBackend.PYQT6:
                return self._initialize_pyqt6(width, height)
            elif self.backend == ContextBackend.GLFW:
                return self._initialize_glfw(width, height)
            else:
                return self._initialize_mock()
        except Exception as e:
            logger.error(f"Failed to initialize OpenGL context: {e}")
            return False
    
    def _initialize_pyqt6(self, width: int, height: int) -> bool:
        """Initialize PyQt6 OpenGL context"""
        if not PYQT_AVAILABLE:
            return False
        
        # Ensure QApplication exists
        if not QApplication.instance():
            logger.warning("No QApplication instance found, creating one")
            QApplication(sys.argv)
        
        # Create OpenGL context
        self.context = QOpenGLContext()
        
        # Set OpenGL format
        format = QSurfaceFormat()
        format.setVersion(3, 3)
        format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        format.setDepthBufferSize(24)
        format.setStencilBufferSize(8)
        format.setSwapBehavior(QSurfaceFormat.SwapBehavior.SingleBuffer)
        
        self.context.setFormat(format)
        
        if not self.context.create():
            logger.error("Failed to create PyQt6 OpenGL context")
            return False
        
        # Create offscreen surface
        self.surface = QOffscreenSurface()
        self.surface.setFormat(format)
        self.surface.create()
        
        if not self.surface.isValid():
            logger.error("Failed to create offscreen surface")
            return False
        
        # Make context current
        if not self.context.makeCurrent(self.surface):
            logger.error("Failed to make OpenGL context current")
            return False
        
        self.is_current = True
        self._query_capabilities()
        
        logger.info("PyQt6 OpenGL context initialized successfully")
        return True
    
    def _initialize_glfw(self, width: int, height: int) -> bool:
        """Initialize GLFW OpenGL context"""
        if not GLFW_AVAILABLE:
            return False
        
        # Initialize GLFW
        if not glfw.init():
            logger.error("Failed to initialize GLFW")
            return False
        
        # Set OpenGL version and profile
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)  # Hidden window for offscreen rendering
        
        # Create window
        self.window = glfw.create_window(width, height, "Offscreen Context", None, None)
        if not self.window:
            logger.error("Failed to create GLFW window")
            glfw.terminate()
            return False
        
        # Make context current
        glfw.make_context_current(self.window)
        self.is_current = True
        
        self._query_capabilities()
        
        logger.info("GLFW OpenGL context initialized successfully")
        return True
    
    def _initialize_mock(self) -> bool:
        """Initialize mock OpenGL context for testing"""
        logger.info("Using mock OpenGL context")
        self.is_current = True
        
        # Create mock capabilities
        self.capabilities = OpenGLCapabilities(
            version="3.3 (Mock)",
            vendor="Mock Vendor",
            renderer="Mock Renderer",
            max_texture_size=4096,
            max_framebuffer_size=4096,
            max_color_attachments=8,
            supports_core_profile=True,
            supports_framebuffer_objects=True
        )
        
        return True
    
    def _query_capabilities(self):
        """Query OpenGL capabilities"""
        if not OPENGL_AVAILABLE:
            return
        
        try:
            version = gl.glGetString(gl.GL_VERSION).decode('utf-8')
            vendor = gl.glGetString(gl.GL_VENDOR).decode('utf-8')
            renderer = gl.glGetString(gl.GL_RENDERER).decode('utf-8')
            
            max_texture_size = gl.glGetIntegerv(gl.GL_MAX_TEXTURE_SIZE)
            max_framebuffer_size = gl.glGetIntegerv(gl.GL_MAX_RENDERBUFFER_SIZE)
            max_color_attachments = gl.glGetIntegerv(gl.GL_MAX_COLOR_ATTACHMENTS)
            
            self.capabilities = OpenGLCapabilities(
                version=version,
                vendor=vendor,
                renderer=renderer,
                max_texture_size=max_texture_size,
                max_framebuffer_size=max_framebuffer_size,
                max_color_attachments=max_color_attachments,
                supports_core_profile=True,
                supports_framebuffer_objects=True
            )
            
            logger.info(f"OpenGL Version: {version}")
            logger.info(f"OpenGL Vendor: {vendor}")
            logger.info(f"OpenGL Renderer: {renderer}")
            
        except Exception as e:
            logger.error(f"Failed to query OpenGL capabilities: {e}")
    
    def make_current(self) -> bool:
        """Make this context current"""
        if self.backend == ContextBackend.PYQT6 and self.context and self.surface:
            success = self.context.makeCurrent(self.surface)
            self.is_current = success
            return success
        elif self.backend == ContextBackend.GLFW and self.window:
            glfw.make_context_current(self.window)
            self.is_current = True
            return True
        else:
            self.is_current = True
            return True
    
    def swap_buffers(self):
        """Swap front and back buffers (for GLFW)"""
        if self.backend == ContextBackend.GLFW and self.window:
            glfw.swap_buffers(self.window)
    
    def create_framebuffer(self, name: str, config: FramebufferConfig) -> Optional[OpenGLFramebuffer]:
        """Create a named framebuffer"""
        if not self.is_current:
            logger.error("OpenGL context is not current")
            return None
        
        # Check if framebuffer already exists
        if name in self.framebuffers:
            logger.warning(f"Framebuffer '{name}' already exists, destroying old one")
            self.destroy_framebuffer(name)
        
        # Validate dimensions against capabilities
        if self.capabilities:
            max_size = self.capabilities.max_framebuffer_size
            if config.width > max_size or config.height > max_size:
                logger.error(f"Framebuffer size {config.width}x{config.height} exceeds maximum {max_size}")
                return None
        
        # Create framebuffer (use mock mode for MOCK backend)
        mock_mode = (self.backend == ContextBackend.MOCK)
        framebuffer = OpenGLFramebuffer(config, mock_mode=mock_mode)
        
        if framebuffer.is_valid:
            self.framebuffers[name] = framebuffer
            logger.info(f"Created framebuffer '{name}': {config.width}x{config.height}")
            return framebuffer
        else:
            logger.error(f"Failed to create framebuffer '{name}'")
            return None
    
    def get_framebuffer(self, name: str) -> Optional[OpenGLFramebuffer]:
        """Get framebuffer by name"""
        return self.framebuffers.get(name)
    
    def destroy_framebuffer(self, name: str) -> bool:
        """Destroy a named framebuffer"""
        if name in self.framebuffers:
            self.framebuffers[name].destroy()
            del self.framebuffers[name]
            logger.info(f"Destroyed framebuffer '{name}'")
            return True
        return False
    
    def resize_framebuffer(self, name: str, width: int, height: int) -> bool:
        """Resize a framebuffer"""
        framebuffer = self.get_framebuffer(name)
        if framebuffer:
            framebuffer.resize(width, height)
            return framebuffer.is_valid
        return False
    
    def create_texture_from_data(self, data: np.ndarray, format: int = None) -> Optional[OpenGLTexture]:
        """Create texture from numpy array data"""
        if not OPENGL_AVAILABLE or not self.is_current:
            return None
        
        if data.ndim != 3:
            logger.error("Texture data must be 3D array (height, width, channels)")
            return None
        
        height, width, channels = data.shape
        
        # Determine format
        if format is None:
            if channels == 4:
                format = gl.GL_RGBA
                internal_format = gl.GL_RGBA8
            elif channels == 3:
                format = gl.GL_RGB
                internal_format = gl.GL_RGB8
            elif channels == 1:
                format = gl.GL_RED
                internal_format = gl.GL_R8
            else:
                logger.error(f"Unsupported number of channels: {channels}")
                return None
        
        # Generate texture
        texture_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
        
        # Upload data
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D, 0, internal_format,
            width, height, 0, format, gl.GL_UNSIGNED_BYTE,
            data.tobytes()
        )
        
        # Set texture parameters
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)
        
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        
        return OpenGLTexture(texture_id, width, height, format)
    
    def get_capabilities(self) -> Optional[OpenGLCapabilities]:
        """Get OpenGL capabilities"""
        return self.capabilities
    
    def check_errors(self) -> List[str]:
        """Check for OpenGL errors"""
        if not OPENGL_AVAILABLE or self.backend == ContextBackend.MOCK:
            return []
        
        errors = []
        try:
            while True:
                error = gl.glGetError()
                if error == gl.GL_NO_ERROR:
                    break
                
                error_names = {
                    gl.GL_INVALID_ENUM: "GL_INVALID_ENUM",
                    gl.GL_INVALID_VALUE: "GL_INVALID_VALUE",
                    gl.GL_INVALID_OPERATION: "GL_INVALID_OPERATION",
                    gl.GL_OUT_OF_MEMORY: "GL_OUT_OF_MEMORY",
                    gl.GL_INVALID_FRAMEBUFFER_OPERATION: "GL_INVALID_FRAMEBUFFER_OPERATION"
                }
                
                error_name = error_names.get(error, f"Unknown error: {error}")
                errors.append(error_name)
                logger.error(f"OpenGL Error: {error_name}")
        except Exception as e:
            logger.warning(f"Error checking OpenGL errors: {e}")
        
        return errors
    
    def cleanup(self):
        """Clean up OpenGL context and resources"""
        # Destroy all framebuffers
        for name in list(self.framebuffers.keys()):
            self.destroy_framebuffer(name)
        
        # Clean up context
        if self.backend == ContextBackend.PYQT6:
            if self.context:
                self.context.doneCurrent()
                self.context = None
            if self.surface:
                self.surface.destroy()
                self.surface = None
        elif self.backend == ContextBackend.GLFW:
            if self.window:
                glfw.destroy_window(self.window)
                self.window = None
            glfw.terminate()
        
        self.is_current = False
        logger.info("OpenGL context cleaned up")


# Convenience functions for common operations
def create_offscreen_context(width: int = 1, height: int = 1, 
                           backend: Optional[ContextBackend] = None) -> Optional[OpenGLContext]:
    """Create and initialize an offscreen OpenGL context"""
    context = OpenGLContext(backend)
    if context.initialize(width, height):
        return context
    return None


def create_render_framebuffer(context: OpenGLContext, name: str, 
                            width: int, height: int) -> Optional[OpenGLFramebuffer]:
    """Create a framebuffer suitable for rendering"""
    config = FramebufferConfig(
        width=width,
        height=height,
        use_depth=True,
        use_stencil=False
    )
    return context.create_framebuffer(name, config)


if __name__ == "__main__":
    # Test the OpenGL context system
    print("Testing OpenGL Context System...")
    
    # Create context
    context = create_offscreen_context(800, 600)
    if not context:
        print("Failed to create OpenGL context")
        sys.exit(1)
    
    print(f"Context backend: {context.backend.value}")
    
    # Print capabilities
    caps = context.get_capabilities()
    if caps:
        print(f"OpenGL Version: {caps.version}")
        print(f"Max Texture Size: {caps.max_texture_size}")
        print(f"Max Framebuffer Size: {caps.max_framebuffer_size}")
    
    # Create framebuffer
    framebuffer = create_render_framebuffer(context, "test", 1920, 1080)
    if framebuffer:
        print(f"Created framebuffer: {framebuffer.config.width}x{framebuffer.config.height}")
        
        # Test framebuffer operations
        framebuffer.clear((0.2, 0.3, 0.4, 1.0))
        pixels = framebuffer.read_pixels()
        if pixels is not None:
            print(f"Read pixels: {pixels.shape}")
    
    # Check for errors
    errors = context.check_errors()
    if errors:
        print(f"OpenGL errors: {errors}")
    else:
        print("No OpenGL errors")
    
    # Cleanup
    context.cleanup()
    print("OpenGL context test completed")