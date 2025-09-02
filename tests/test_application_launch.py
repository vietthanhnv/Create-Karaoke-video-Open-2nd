"""
Integration test for application launch and basic functionality
"""

import sys
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import main
from ui.main_window import MainWindow


class TestApplicationLaunch:
    """Test application launch and basic integration"""
    
    def test_main_window_can_be_created_and_shown(self):
        """Test that main window can be created and shown without errors"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        
        # Create main window
        window = MainWindow()
        
        # Show window (this should not raise any exceptions)
        window.show()
        
        # Verify window is visible
        assert window.isVisible()
        
        # Test basic functionality
        assert window.windowTitle() == "Karaoke Video Creator"
        assert window.tab_widget.count() == 5
        
        # Close window
        window.close()
        assert not window.isVisible()
    
    def test_application_startup_components(self):
        """Test that all application components initialize correctly"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        
        window = MainWindow()
        
        # Test that all widgets are properly initialized
        assert window.import_widget is not None
        assert window.preview_widget is not None
        assert window.editor_widget is not None
        assert window.effects_widget is not None
        assert window.export_widget is not None
        
        # Test that widgets have their required components
        assert hasattr(window.import_widget, 'media_importer')
        assert hasattr(window.preview_widget, 'opengl_widget')
        assert hasattr(window.editor_widget, 'text_editor')
        assert hasattr(window.effects_widget, 'effects_list')
        assert hasattr(window.export_widget, 'export_button')
        
        window.close()
    
    def test_menu_and_status_bar_functionality(self):
        """Test menu and status bar basic functionality"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        
        window = MainWindow()
        
        # Test menu bar
        menubar = window.menuBar()
        assert menubar is not None
        
        # Test status bar
        status_bar = window.statusBar()
        assert status_bar is not None
        assert window.status_label is not None
        
        # Test tab switching updates status
        for i in range(window.tab_widget.count()):
            window.tab_widget.setCurrentIndex(i)
            window._on_tab_changed(i)
            # Status should be updated
            assert "Current step:" in window.status_label.text()
        
        window.close()


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])