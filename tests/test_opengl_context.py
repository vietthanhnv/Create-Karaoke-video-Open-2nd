"""
Tests for OpenGL Context Initialization and Basic Rendering
"""

import pytest
import sys
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QSurfaceFormat
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from src.ui.preview_widget import OpenGLVideoWidget


class TestOpenGLContext:
    """Test OpenGL context initialization and basic functionality"""
    
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
    
    def test_opengl_context_creation(self, app):
        """Test that OpenGL context can be created"""
        widget = OpenGLVideoWidget()
        
        # Widget should be created successfully
        assert widget is not None
        
        # Check that widget has OpenGL capabilities
        assert hasattr(widget, 'initializeGL')
        assert hasattr(widget, 'paintGL')
        assert hasattr(widget, 'resizeGL')
    
    def test_shader_program_creation(self, app):
        """Test shader program creation without actual OpenGL context"""
        widget = OpenGLVideoWidget()
        
        # Mock QOpenGLShaderProgram to avoid needing actual OpenGL context
        with patch('src.ui.preview_widget.QOpenGLShaderProgram') as mock_program_class:
            mock_program = Mock()
            mock_program.addShaderFromSourceCode.return_value = True
            mock_program.link.return_value = True
            mock_program_class.return_value = mock_program
            
            # Test shader creation
            result = widget._create_shader_program()
            
            # Should succeed
            assert result is True
            assert widget.shader_program is not None
    
    def test_vertex_buffer_creation(self, app):
        """Test vertex buffer creation"""
        widget = OpenGLVideoWidget()
        
        # Create vertex buffer
        widget._create_vertex_buffer()
        
        # Should have vertices defined
        assert hasattr(widget, 'vertices')
        assert widget.vertices is not None
        assert len(widget.vertices) > 0
    
    def test_texture_loading_simulation(self, app):
        """Test texture loading simulation"""
        widget = OpenGLVideoWidget()
        
        # Create test image
        test_image = QImage(256, 256, QImage.Format.Format_RGBA8888)
        test_image.fill(Qt.GlobalColor.red)
        
        # Load frame (this should work without OpenGL context)
        widget.load_frame(test_image)
        
        # Verify frame is stored
        assert widget.current_frame is not None
        assert widget.video_width == 256
        assert widget.video_height == 256
    
    @patch('OpenGL.GL.glViewport')
    def test_resize_handling(self, mock_viewport, app):
        """Test OpenGL viewport resize handling"""
        widget = OpenGLVideoWidget()
        
        # Simulate resize
        widget.resizeGL(800, 600)
        
        # Should call glViewport
        mock_viewport.assert_called_once_with(0, 0, 800, 600)
    
    def test_frame_clearing(self, app):
        """Test frame clearing functionality"""
        widget = OpenGLVideoWidget()
        
        # Load a frame first
        test_image = QImage(128, 128, QImage.Format.Format_RGB888)
        widget.load_frame(test_image)
        
        # Verify frame is loaded
        assert widget.current_frame is not None
        
        # Clear frame
        widget.clear_frame()
        
        # Verify frame is cleared
        assert widget.current_frame is None
        assert widget.video_texture is None


class TestOpenGLIntegrationWithPreview:
    """Test integration between OpenGL widget and preview controls"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    def test_preview_opengl_integration(self, app):
        """Test that preview widget properly integrates OpenGL widget"""
        from src.ui.preview_widget import PreviewWidget
        
        preview = PreviewWidget()
        
        # Should have OpenGL widget
        assert hasattr(preview, 'opengl_widget')
        assert isinstance(preview.opengl_widget, OpenGLVideoWidget)
        
        # Test frame loading through preview
        test_image = QImage(320, 240, QImage.Format.Format_RGB888)
        test_image.fill(Qt.GlobalColor.blue)
        
        # This should work without errors
        preview.load_video_frame(test_image)
        
        # OpenGL widget should have the frame
        assert preview.opengl_widget.current_frame is not None
        assert preview.opengl_widget.video_width == 320
        assert preview.opengl_widget.video_height == 240
    
    def test_preview_frame_clearing(self, app):
        """Test frame clearing through preview widget"""
        from src.ui.preview_widget import PreviewWidget
        
        preview = PreviewWidget()
        
        # Load frame first
        test_image = QImage(160, 120, QImage.Format.Format_RGB888)
        preview.load_video_frame(test_image)
        
        # Clear frame
        preview.load_video_frame(None)
        
        # Should be cleared
        assert preview.opengl_widget.current_frame is None


if __name__ == '__main__':
    pytest.main([__file__])