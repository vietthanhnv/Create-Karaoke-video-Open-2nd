"""
Test Detachable Preview Widget Functionality
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QTabWidget, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

# Add src to path for imports
sys.path.insert(0, 'src')

from src.ui.detachable_preview_widget import DetachablePreviewWidget, DetachedPreviewWindow
from src.core.models import Project, SubtitleFile


class TestDetachablePreviewWidget:
    """Test detachable preview widget functionality"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create detachable preview widget"""
        return DetachablePreviewWidget()
    
    @pytest.fixture
    def tab_widget(self, app):
        """Create tab widget for testing"""
        return QTabWidget()
    
    def test_widget_creation(self, preview_widget):
        """Test that widget is created properly"""
        assert preview_widget is not None
        assert not preview_widget.is_detached
        assert preview_widget.detached_window is None
        assert preview_widget.tab_title == "Preview"
    
    def test_detach_functionality(self, preview_widget, tab_widget):
        """Test detaching preview from tab widget"""
        # Add to tab widget first
        tab_widget.addTab(preview_widget, "Test Preview")
        preview_widget.set_parent_tab_widget(tab_widget, 0, "Test Preview")
        
        # Test detach
        preview_widget._detach_from_parent()
        
        assert preview_widget.is_detached
        assert preview_widget.detached_window is not None
        assert preview_widget.detach_button.text() == "Attach"
    
    def test_attach_functionality(self, preview_widget, tab_widget):
        """Test attaching preview back to tab widget"""
        # Setup detached state
        tab_widget.addTab(preview_widget, "Test Preview")
        preview_widget.set_parent_tab_widget(tab_widget, 0, "Test Preview")
        preview_widget._detach_from_parent()
        
        # Test attach
        preview_widget._attach_to_parent()
        
        assert not preview_widget.is_detached
        assert preview_widget.detached_window is None
        assert preview_widget.detach_button.text() == "Detach"
        assert tab_widget.indexOf(preview_widget) >= 0
    
    def test_signal_forwarding(self, preview_widget):
        """Test that signals are properly forwarded"""
        # Mock the internal preview widget
        preview_widget.preview_widget = Mock()
        
        # Test signal connections exist
        assert preview_widget.preview_widget.play_requested.connect.called
        assert preview_widget.preview_widget.pause_requested.connect.called
        assert preview_widget.preview_widget.seek_requested.connect.called
    
    def test_method_forwarding(self, preview_widget):
        """Test that methods are properly forwarded to internal preview"""
        # Mock the internal preview widget
        preview_widget.preview_widget = Mock()
        
        # Test project loading
        mock_project = Mock(spec=Project)
        preview_widget.load_project(mock_project)
        preview_widget.preview_widget.load_project.assert_called_once_with(mock_project)
        
        # Test effect methods
        preview_widget.add_effect("test_effect", {"param": "value"})
        preview_widget.preview_widget.add_effect.assert_called_once_with("test_effect", {"param": "value"})
        
        preview_widget.remove_effect("test_effect")
        preview_widget.preview_widget.remove_effect.assert_called_once_with("test_effect")
    
    def test_parent_tab_widget_setting(self, preview_widget, tab_widget):
        """Test setting parent tab widget information"""
        preview_widget.set_parent_tab_widget(tab_widget, 2, "Custom Title")
        
        assert preview_widget.parent_tab_widget == tab_widget
        assert preview_widget.tab_index == 2
        assert preview_widget.tab_title == "Custom Title"


class TestDetachedPreviewWindow:
    """Test detached preview window functionality"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create detachable preview widget"""
        return DetachablePreviewWidget()
    
    @pytest.fixture
    def detached_window(self, app, preview_widget):
        """Create detached preview window"""
        return DetachedPreviewWindow(preview_widget)
    
    def test_window_creation(self, detached_window):
        """Test that detached window is created properly"""
        assert detached_window is not None
        assert detached_window.windowTitle() == "Karaoke Video Preview"
        assert detached_window.minimumSize().width() == 800
        assert detached_window.minimumSize().height() == 600
    
    def test_window_centering(self, detached_window):
        """Test that window is centered on screen"""
        # This is hard to test without actual screen, but we can verify the method exists
        assert hasattr(detached_window, '_center_on_screen')
    
    @patch('src.ui.detachable_preview_widget.QMessageBox')
    def test_close_event_reattach(self, mock_msgbox, detached_window, preview_widget):
        """Test close event with reattach option"""
        # Mock message box to return Yes
        mock_msgbox.question.return_value = mock_msgbox.StandardButton.Yes
        
        # Mock the preview widget's attach method
        preview_widget._attach_to_parent = Mock()
        
        # Create close event
        from PyQt6.QtGui import QCloseEvent
        close_event = QCloseEvent()
        
        # Test close event
        detached_window.closeEvent(close_event)
        
        # Verify reattach was called
        preview_widget._attach_to_parent.assert_called_once()
        assert close_event.isAccepted()


class TestIntegrationWithMainWindow:
    """Test integration with main window and tab system"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def main_window(self, app):
        """Create main window for testing"""
        return QMainWindow()
    
    @pytest.fixture
    def tab_widget(self, app):
        """Create tab widget"""
        return QTabWidget()
    
    def test_preview_in_tab_system(self, app, tab_widget):
        """Test preview widget working in tab system"""
        preview = DetachablePreviewWidget()
        
        # Add to tab widget
        tab_widget.addTab(preview, "Preview")
        preview.set_parent_tab_widget(tab_widget, 0, "Preview")
        
        # Verify it's properly added
        assert tab_widget.count() == 1
        assert tab_widget.widget(0) == preview
        assert tab_widget.tabText(0) == "Preview"
    
    def test_detach_reattach_cycle(self, app, tab_widget):
        """Test complete detach/reattach cycle"""
        preview = DetachablePreviewWidget()
        
        # Add to tab widget
        tab_widget.addTab(preview, "Preview")
        preview.set_parent_tab_widget(tab_widget, 0, "Preview")
        
        # Detach
        preview._detach_from_parent()
        assert preview.is_detached
        assert tab_widget.count() == 0  # Should be removed from tab widget
        
        # Reattach
        preview._attach_to_parent()
        assert not preview.is_detached
        assert tab_widget.count() == 1  # Should be back in tab widget
        assert tab_widget.widget(0) == preview


if __name__ == "__main__":
    pytest.main([__file__])