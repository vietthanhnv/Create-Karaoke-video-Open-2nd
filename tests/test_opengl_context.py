"""
Tests for OpenGL Context and Framebuffer System
"""

import pytest
import sys
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QSurfaceFormat

from src.core.opengl_context import (
    OpenGLContext, OpenGLFramebuffer, OpenGLTexture, FramebufferConfig,
    ContextBackend, OpenGLCapabilities, create_offscreen_context,
    create_render_framebuffer
)


class TestOpenGLContext:
    """Test OpenGL context creation and management"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication with OpenGL support"""
        if not QApplication.instance():
            app = QApplication(sys.argv)
            # Set up OpenGL format
            format = QSurfaceFormat()
            format.setVersion(3, 3)
            format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            QSurfaceFormat.setDefaultFormat(format)
            return app
        return QApplication.instance()
    
    def test_context_backend_detection(self):
        """Test automatic backend detection"""
        context = OpenGLContext()
        
        # Should detect a valid backend
        assert context.backend in [ContextBackend.PYQT6, ContextBackend.GLFW, ContextBackend.MOCK]
        
        # Should prefer PyQt6 if available
        with patch('src.core.opengl_context.PYQT_AVAILABLE', True):
            context = OpenGLContext()
            assert context.backend == ContextBackend.PYQT6
    
    def test_mock_context_initialization(self):
        """Test mock context initialization for testing"""
        context = OpenGLContext(ContextBackend.MOCK)
        
        # Should initialize successfully
        assert context.initialize()
        assert context.is_current
        
        # Should have mock capabilities
        caps = context.get_capabilities()
        assert caps is not None
        assert caps.version == "3.3 (Mock)"
        assert caps.supports_core_profile
        assert caps.supports_framebuffer_objects
    
    @patch('src.core.opengl_context.PYQT_AVAILABLE', True)
    def test_pyqt6_context_initialization(self, app):
        """Test PyQt6 context initialization"""
        with patch('src.core.opengl_context.QOpenGLContext') as mock_context_class:
            with patch('src.core.opengl_context.QOffscreenSurface') as mock_surface_class:
                # Mock successful context creation
                mock_context = Mock()
                mock_context.create.return_value = True
                mock_context.makeCurrent.return_value = True
                mock_context_class.return_value = mock_context
                
                mock_surface = Mock()
                mock_surface.isValid.return_value = True
                mock_surface_class.return_value = mock_surface
                
                # Mock OpenGL queries
                with patch('src.core.opengl_context.gl') as mock_gl:
                    mock_gl.glGetString.side_effect = lambda x: b"Mock OpenGL"
                    mock_gl.glGetIntegerv.return_value = 4096
                    
                    context = OpenGLContext(ContextBackend.PYQT6)
                    result = context.initialize()
                    
                    assert result
                    assert context.is_current
                    assert context.context is not None
                    assert context.surface is not None
    
    @patch('src.core.opengl_context.GLFW_AVAILABLE', True)
    def test_glfw_context_initialization(self):
        """Test GLFW context initialization"""
        with patch('src.core.opengl_context.glfw') as mock_glfw:
            # Mock successful GLFW initialization
            mock_glfw.init.return_value = True
            mock_glfw.create_window.return_value = "mock_window"
            
            # Mock OpenGL queries
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGetString.side_effect = lambda x: b"Mock OpenGL"
                mock_gl.glGetIntegerv.return_value = 4096
                
                context = OpenGLContext(ContextBackend.GLFW)
                result = context.initialize(800, 600)
                
                assert result
                assert context.is_current
                assert context.window is not None
    
    def test_context_make_current(self):
        """Test making context current"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Should be current after initialization
        assert context.is_current
        
        # Test make_current method
        result = context.make_current()
        assert result
        assert context.is_current
    
    def test_context_cleanup(self):
        """Test context cleanup"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Add a test framebuffer
        config = FramebufferConfig(width=800, height=600)
        framebuffer = context.create_framebuffer("test", config)
        assert framebuffer is not None
        
        # Cleanup should destroy all resources
        context.cleanup()
        
        assert not context.is_current
        assert len(context.framebuffers) == 0


class TestFramebufferConfig:
    """Test framebuffer configuration"""
    
    def test_default_config(self):
        """Test default framebuffer configuration"""
        config = FramebufferConfig(width=1920, height=1080)
        
        assert config.width == 1920
        assert config.height == 1080
        assert config.use_depth
        assert not config.use_stencil
        assert config.samples == 0
    
    def test_custom_config(self):
        """Test custom framebuffer configuration"""
        config = FramebufferConfig(
            width=800, height=600,
            use_depth=False, use_stencil=True,
            samples=4
        )
        
        assert config.width == 800
        assert config.height == 600
        assert not config.use_depth
        assert config.use_stencil
        assert config.samples == 4


class TestOpenGLFramebuffer:
    """Test OpenGL framebuffer operations"""
    
    def test_framebuffer_creation_mock(self):
        """Test framebuffer creation with mock OpenGL"""
        config = FramebufferConfig(width=800, height=600)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', False):
            framebuffer = OpenGLFramebuffer(config)
            
            # Should create without errors but not be valid
            assert framebuffer.config == config
            assert not framebuffer.is_valid
    
    @patch('src.core.opengl_context.OPENGL_AVAILABLE', True)
    def test_framebuffer_creation_with_opengl(self):
        """Test framebuffer creation with OpenGL"""
        config = FramebufferConfig(width=800, height=600)
        
        with patch('src.core.opengl_context.gl') as mock_gl:
            # Mock successful framebuffer creation
            mock_gl.glGenFramebuffers.return_value = 1
            mock_gl.glGenTextures.return_value = 2
            mock_gl.glCheckFramebufferStatus.return_value = mock_gl.GL_FRAMEBUFFER_COMPLETE
            
            framebuffer = OpenGLFramebuffer(config)
            
            # Should be valid
            assert framebuffer.is_valid
            assert framebuffer.framebuffer_id == 1
            assert framebuffer.color_texture is not None
    
    def test_framebuffer_bind_unbind(self):
        """Test framebuffer bind/unbind operations"""
        config = FramebufferConfig(width=800, height=600)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenFramebuffers.return_value = 1
                mock_gl.glGenTextures.return_value = 2
                mock_gl.glCheckFramebufferStatus.return_value = mock_gl.GL_FRAMEBUFFER_COMPLETE
                
                framebuffer = OpenGLFramebuffer(config)
                
                # Test bind
                framebuffer.bind()
                mock_gl.glBindFramebuffer.assert_called_with(mock_gl.GL_FRAMEBUFFER, 1)
                mock_gl.glViewport.assert_called_with(0, 0, 800, 600)
                
                # Test unbind
                framebuffer.unbind()
                mock_gl.glBindFramebuffer.assert_called_with(mock_gl.GL_FRAMEBUFFER, 0)
    
    def test_framebuffer_clear(self):
        """Test framebuffer clearing"""
        config = FramebufferConfig(width=800, height=600, use_depth=True, use_stencil=True)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenFramebuffers.return_value = 1
                mock_gl.glGenTextures.return_value = 2
                mock_gl.glCheckFramebufferStatus.return_value = mock_gl.GL_FRAMEBUFFER_COMPLETE
                
                framebuffer = OpenGLFramebuffer(config)
                
                # Test clear with custom color
                framebuffer.clear((0.2, 0.3, 0.4, 1.0))
                
                mock_gl.glClearColor.assert_called_with(0.2, 0.3, 0.4, 1.0)
                mock_gl.glClearDepth.assert_called_with(1.0)
                mock_gl.glClearStencil.assert_called_with(0)
    
    def test_framebuffer_resize(self):
        """Test framebuffer resizing"""
        config = FramebufferConfig(width=800, height=600)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenFramebuffers.return_value = 1
                mock_gl.glGenTextures.return_value = 2
                mock_gl.glCheckFramebufferStatus.return_value = mock_gl.GL_FRAMEBUFFER_COMPLETE
                
                framebuffer = OpenGLFramebuffer(config)
                original_id = framebuffer.framebuffer_id
                
                # Resize to new dimensions
                framebuffer.resize(1920, 1080)
                
                # Should have new dimensions
                assert framebuffer.config.width == 1920
                assert framebuffer.config.height == 1080
                
                # Should have recreated framebuffer
                assert framebuffer.framebuffer_id != 0
    
    def test_framebuffer_read_pixels(self):
        """Test reading pixels from framebuffer"""
        config = FramebufferConfig(width=100, height=100)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenFramebuffers.return_value = 1
                mock_gl.glGenTextures.return_value = 2
                mock_gl.glCheckFramebufferStatus.return_value = mock_gl.GL_FRAMEBUFFER_COMPLETE
                
                # Mock pixel data
                mock_pixels = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
                mock_gl.glReadPixels.return_value = mock_pixels.tobytes()
                
                framebuffer = OpenGLFramebuffer(config)
                
                # Read pixels
                pixels = framebuffer.read_pixels()
                
                assert pixels is not None
                assert pixels.shape == (100, 100, 4)


class TestOpenGLTexture:
    """Test OpenGL texture management"""
    
    def test_texture_creation(self):
        """Test texture creation and properties"""
        texture = OpenGLTexture(texture_id=1, width=256, height=256, format=0x1908)  # GL_RGBA
        
        assert texture.texture_id == 1
        assert texture.width == 256
        assert texture.height == 256
        assert texture.format == 0x1908
        assert texture.is_valid
    
    def test_texture_bind_unbind(self):
        """Test texture bind/unbind operations"""
        texture = OpenGLTexture(texture_id=1, width=256, height=256, format=0x1908)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                # Set up mock constants
                mock_gl.GL_TEXTURE0 = 0x84C0
                mock_gl.GL_TEXTURE_2D = 0x0DE1
                
                # Test bind
                texture.bind(unit=0)
                mock_gl.glActiveTexture.assert_called_with(0x84C0)
                mock_gl.glBindTexture.assert_called_with(0x0DE1, 1)
                
                # Test bind to different unit
                texture.bind(unit=2)
                mock_gl.glActiveTexture.assert_called_with(0x84C0 + 2)
                
                # Test unbind
                texture.unbind()
                mock_gl.glBindTexture.assert_called_with(0x0DE1, 0)
    
    def test_texture_destroy(self):
        """Test texture destruction"""
        texture = OpenGLTexture(texture_id=1, width=256, height=256, format=0x1908)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                texture.destroy()
                
                mock_gl.glDeleteTextures.assert_called_with(1, [1])
                assert not texture.is_valid


class TestOpenGLContextIntegration:
    """Test integration between context and framebuffers"""
    
    def test_context_framebuffer_creation(self):
        """Test creating framebuffers through context"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Create framebuffer
        config = FramebufferConfig(width=800, height=600)
        framebuffer = context.create_framebuffer("test", config)
        
        assert framebuffer is not None
        assert "test" in context.framebuffers
        assert context.get_framebuffer("test") == framebuffer
    
    def test_context_framebuffer_management(self):
        """Test framebuffer management operations"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Create multiple framebuffers
        config1 = FramebufferConfig(width=800, height=600)
        config2 = FramebufferConfig(width=1920, height=1080)
        
        fb1 = context.create_framebuffer("render", config1)
        fb2 = context.create_framebuffer("export", config2)
        
        assert fb1 is not None
        assert fb2 is not None
        assert len(context.framebuffers) == 2
        
        # Test resize
        success = context.resize_framebuffer("render", 1024, 768)
        assert success
        
        # Test destruction
        success = context.destroy_framebuffer("render")
        assert success
        assert len(context.framebuffers) == 1
        assert "render" not in context.framebuffers
    
    def test_context_texture_creation(self):
        """Test texture creation from data"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Create test data
        data = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenTextures.return_value = 1
                
                texture = context.create_texture_from_data(data)
                
                assert texture is not None
                assert texture.width == 100
                assert texture.height == 100
    
    def test_context_error_checking(self):
        """Test OpenGL error checking"""
        # Create a PyQt6 context for this test to bypass MOCK backend
        context = OpenGLContext(ContextBackend.PYQT6)
        context.backend = ContextBackend.PYQT6  # Force non-mock backend
        context.is_current = True
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                # Set up mock constants
                mock_gl.GL_NO_ERROR = 0
                mock_gl.GL_INVALID_ENUM = 0x0500
                
                # Mock no errors
                mock_gl.glGetError.return_value = mock_gl.GL_NO_ERROR
                
                errors = context.check_errors()
                assert len(errors) == 0
                
                # Mock error
                mock_gl.glGetError.side_effect = [mock_gl.GL_INVALID_ENUM, mock_gl.GL_NO_ERROR]
                
                errors = context.check_errors()
                assert len(errors) == 1
                assert "GL_INVALID_ENUM" in errors[0]


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_create_offscreen_context(self):
        """Test offscreen context creation"""
        context = create_offscreen_context(800, 600, ContextBackend.MOCK)
        
        assert context is not None
        assert context.is_current
        assert context.backend == ContextBackend.MOCK
    
    def test_create_render_framebuffer(self):
        """Test render framebuffer creation"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        framebuffer = create_render_framebuffer(context, "render", 1920, 1080)
        
        assert framebuffer is not None
        assert framebuffer.config.width == 1920
        assert framebuffer.config.height == 1080
        assert framebuffer.config.use_depth
        assert not framebuffer.config.use_stencil


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_framebuffer_size(self):
        """Test handling of invalid framebuffer sizes"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        # Set mock capabilities with size limit
        context.capabilities = OpenGLCapabilities(
            version="3.3", vendor="Mock", renderer="Mock",
            max_texture_size=4096, max_framebuffer_size=4096,
            max_color_attachments=8, supports_core_profile=True,
            supports_framebuffer_objects=True
        )
        
        # Try to create oversized framebuffer
        config = FramebufferConfig(width=8192, height=8192)
        framebuffer = context.create_framebuffer("oversized", config)
        
        assert framebuffer is None
        assert "oversized" not in context.framebuffers
    
    def test_context_not_current(self):
        """Test operations when context is not current"""
        context = OpenGLContext(ContextBackend.MOCK)
        # Don't initialize context
        
        config = FramebufferConfig(width=800, height=600)
        framebuffer = context.create_framebuffer("test", config)
        
        assert framebuffer is None
    
    def test_duplicate_framebuffer_name(self):
        """Test handling of duplicate framebuffer names"""
        context = OpenGLContext(ContextBackend.MOCK)
        context.initialize()
        
        config = FramebufferConfig(width=800, height=600)
        
        # Create first framebuffer
        fb1 = context.create_framebuffer("test", config)
        assert fb1 is not None
        
        # Create second with same name (should replace first)
        fb2 = context.create_framebuffer("test", config)
        assert fb2 is not None
        assert fb2 != fb1
        assert len(context.framebuffers) == 1


if __name__ == '__main__':
    pytest.main([__file__])