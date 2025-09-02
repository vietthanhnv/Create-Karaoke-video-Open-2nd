"""
Tests for OpenGL Preview Widget
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtTest import QTest

# Import the widgets to test
from src.ui.preview_widget import OpenGLVideoWidget, PreviewWidget


class TestOpenGLVideoWidget:
    """Test cases for OpenGL video rendering widget"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def widget(self, app):
        """Create OpenGL widget instance for testing"""
        widget = OpenGLVideoWidget()
        return widget
    
    def test_widget_initialization(self, widget):
        """Test that OpenGL widget initializes correctly"""
        assert widget is not None
        assert widget.video_texture is None
        assert widget.shader_program is None
        assert widget.current_frame is None
        assert widget.video_width == 0
        assert widget.video_height == 0
    
    def test_load_frame_with_valid_image(self, widget):
        """Test loading a valid image frame"""
        # Create a test image
        test_image = QImage(640, 480, QImage.Format.Format_RGB888)
        test_image.fill(Qt.GlobalColor.red)
        
        # Load the frame
        widget.load_frame(test_image)
        
        # Verify frame is loaded
        assert widget.current_frame is not None
        assert widget.video_width == 640
        assert widget.video_height == 480
    
    def test_load_frame_with_none(self, widget):
        """Test loading None as frame"""
        widget.load_frame(None)
        
        # Should handle None gracefully
        assert widget.current_frame is None
        assert widget.video_width == 0
        assert widget.video_height == 0
    
    def test_clear_frame(self, widget):
        """Test clearing the current frame"""
        # First load a frame
        test_image = QImage(320, 240, QImage.Format.Format_RGB888)
        widget.load_frame(test_image)
        
        # Then clear it
        widget.clear_frame()
        
        # Verify frame is cleared
        assert widget.current_frame is None
        assert widget.video_texture is None
    
    @patch('OpenGL.GL.glClearColor')
    @patch('OpenGL.GL.glEnable')
    @patch('OpenGL.GL.glBlendFunc')
    def test_initialize_gl_context(self, mock_blend, mock_enable, mock_clear, widget):
        """Test OpenGL context initialization"""
        # Mock shader program creation
        with patch.object(widget, '_create_shader_program', return_value=True), \
             patch.object(widget, '_create_vertex_buffer'):
            
            widget.initializeGL()
            
            # Verify OpenGL setup calls
            mock_enable.assert_called()
            mock_blend.assert_called()
            mock_clear.assert_called_with(0.0, 0.0, 0.0, 1.0)


class TestPreviewWidget:
    """Test cases for the main preview widget"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def widget(self, app):
        """Create preview widget instance for testing"""
        widget = PreviewWidget()
        return widget
    
    def test_widget_initialization(self, widget):
        """Test that preview widget initializes correctly"""
        assert widget is not None
        assert hasattr(widget, 'opengl_widget')
        assert hasattr(widget, 'play_button')
        assert hasattr(widget, 'timeline_slider')
        assert hasattr(widget, 'time_label_start')
        assert hasattr(widget, 'time_label_end')
        assert widget.is_playing is False
    
    def test_playback_controls_initialization(self, widget):
        """Test that playback controls are properly initialized"""
        assert widget.play_button.text() == "Play"
        assert widget.timeline_slider.minimum() == 0
        assert widget.timeline_slider.maximum() == 100
        assert widget.timeline_slider.value() == 0
        assert widget.time_label_start.text() == "00:00"
        assert widget.time_label_end.text() == "00:00"
    
    def test_toggle_playback_from_stopped(self, widget):
        """Test toggling playback from stopped state"""
        # Initially stopped
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
        
        # Click play button
        widget._toggle_playback()
        
        # Should now be playing
        assert widget.is_playing is True
        assert widget.play_button.text() == "Pause"
    
    def test_toggle_playback_from_playing(self, widget):
        """Test toggling playback from playing state"""
        # Set to playing state
        widget.is_playing = True
        widget.play_button.setText("Pause")
        
        # Click pause button
        widget._toggle_playback()
        
        # Should now be paused
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
    
    def test_stop_playback(self, widget):
        """Test stop playback functionality"""
        # Set to playing state
        widget.is_playing = True
        widget.play_button.setText("Pause")
        widget.timeline_slider.setValue(50)
        
        # Stop playback
        widget._stop_playback()
        
        # Should be stopped and reset
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
        assert widget.timeline_slider.value() == 0
    
    def test_timeline_change_signal(self, widget):
        """Test that timeline changes emit seek signal"""
        with patch.object(widget, 'seek_requested') as mock_signal:
            # Change timeline position
            widget.timeline_slider.setValue(25)
            widget._on_timeline_changed(25)
            
            # Should emit seek signal with normalized position
            mock_signal.emit.assert_called_with(0.25)
    
    def test_load_video_frame_with_image(self, widget):
        """Test loading video frame into OpenGL widget"""
        test_image = QImage(640, 480, QImage.Format.Format_RGB888)
        test_image.fill(Qt.GlobalColor.blue)
        
        # Mock the OpenGL widget
        widget.opengl_widget = Mock()
        
        # Load frame
        widget.load_video_frame(test_image)
        
        # Verify OpenGL widget received the frame
        widget.opengl_widget.load_frame.assert_called_once_with(test_image)
    
    def test_load_video_frame_with_none(self, widget):
        """Test loading None as video frame"""
        # Mock the OpenGL widget
        widget.opengl_widget = Mock()
        
        # Load None frame
        widget.load_video_frame(None)
        
        # Should clear the frame
        widget.opengl_widget.clear_frame.assert_called_once()
    
    def test_update_timeline_with_valid_times(self, widget):
        """Test updating timeline with valid time values"""
        current_time = 30.0  # 30 seconds
        total_time = 120.0   # 2 minutes
        
        widget.update_timeline(current_time, total_time)
        
        # Timeline should be at 25% (30/120)
        assert widget.timeline_slider.value() == 25
        assert widget.time_label_start.text() == "00:30"
        assert widget.time_label_end.text() == "02:00"
    
    def test_update_timeline_with_zero_total(self, widget):
        """Test updating timeline when total time is zero"""
        current_time = 10.0
        total_time = 0.0
        
        widget.update_timeline(current_time, total_time)
        
        # Should handle gracefully without division by zero
        assert widget.time_label_start.text() == "00:10"
        assert widget.time_label_end.text() == "00:00"
    
    def test_format_time_function(self, widget):
        """Test time formatting function"""
        assert widget._format_time(0) == "00:00"
        assert widget._format_time(30) == "00:30"
        assert widget._format_time(90) == "01:30"
        assert widget._format_time(3661) == "61:01"  # Over an hour
        assert widget._format_time(-5) == "00:00"    # Negative time
    
    def test_set_playback_state_playing(self, widget):
        """Test setting playback state to playing"""
        widget.set_playback_state(True)
        
        assert widget.is_playing is True
        assert widget.play_button.text() == "Pause"
    
    def test_set_playback_state_stopped(self, widget):
        """Test setting playback state to stopped"""
        widget.set_playback_state(False)
        
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
    
    def test_reset_playback(self, widget):
        """Test resetting playback to initial state"""
        # Set some non-initial state
        widget.is_playing = True
        widget.play_button.setText("Pause")
        widget.timeline_slider.setValue(75)
        widget.time_label_start.setText("01:30")
        
        # Mock OpenGL widget
        widget.opengl_widget = Mock()
        
        # Reset playback
        widget.reset_playback()
        
        # Should be back to initial state
        assert widget.is_playing is False
        assert widget.play_button.text() == "Play"
        assert widget.timeline_slider.value() == 0
        assert widget.time_label_start.text() == "00:00"
        widget.opengl_widget.clear_frame.assert_called_once()
    
    def test_signals_exist(self, widget):
        """Test that required signals are defined"""
        assert hasattr(widget, 'play_requested')
        assert hasattr(widget, 'pause_requested')
        assert hasattr(widget, 'seek_requested')


class TestOpenGLIntegration:
    """Integration tests for OpenGL functionality"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication instance for testing"""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    def test_opengl_widget_in_preview(self, app):
        """Test that OpenGL widget is properly integrated in preview"""
        preview = PreviewWidget()
        
        # Verify OpenGL widget is present and correct type
        assert hasattr(preview, 'opengl_widget')
        assert isinstance(preview.opengl_widget, OpenGLVideoWidget)
        
        # Verify minimum size is set
        assert preview.opengl_widget.minimumSize().width() >= 640
        assert preview.opengl_widget.minimumSize().height() >= 360
    
    @patch('src.ui.preview_widget.gl')
    def test_opengl_rendering_pipeline(self, mock_gl, app):
        """Test the OpenGL rendering pipeline"""
        widget = OpenGLVideoWidget()
        
        # Create test image
        test_image = QImage(320, 240, QImage.Format.Format_RGBA8888)
        test_image.fill(Qt.GlobalColor.green)
        
        # Load frame
        widget.load_frame(test_image)
        
        # Verify frame properties
        assert widget.current_frame is not None
        assert widget.video_width == 320
        assert widget.video_height == 240


if __name__ == '__main__':
    pytest.main([__file__])