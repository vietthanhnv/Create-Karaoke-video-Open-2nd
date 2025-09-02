"""
Integration tests for settings system with main window
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication

# Import the modules under test
try:
    from src.ui.main_window import MainWindow
    from src.core.settings_manager import SettingsManager
except ImportError:
    import sys
    sys.path.append('src')
    from ui.main_window import MainWindow
    from core.settings_manager import SettingsManager


class TestSettingsIntegration:
    """Test cases for settings system integration"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app
    
    @patch('src.core.settings_manager.QSettings')
    def test_main_window_with_settings(self, mock_qsettings, app):
        """Test that main window can be created with settings manager"""
        # Mock QSettings
        mock_settings = Mock()
        mock_qsettings.return_value = mock_settings
        
        # Mock settings storage
        storage = {}
        
        def mock_setValue(key, value):
            storage[key] = value
        
        def mock_value(key, default=None, type=None):
            value = storage.get(key, default)
            if type and value is not None:
                return type(value)
            return value
        
        def mock_contains(key):
            return key in storage
        
        mock_settings.setValue.side_effect = mock_setValue
        mock_settings.value.side_effect = mock_value
        mock_settings.contains.side_effect = mock_contains
        mock_settings.sync.return_value = None
        mock_settings.allKeys.return_value = list(storage.keys())
        
        # Create main window
        window = MainWindow()
        
        try:
            # Verify settings manager exists
            assert hasattr(window, 'settings_manager')
            assert isinstance(window.settings_manager, SettingsManager)
            
            # Verify settings manager is properly initialized
            assert window.settings_manager.get_input_directory() is not None
            assert window.settings_manager.get_output_directory() is not None
            
            # Verify default export settings
            export_settings = window.settings_manager.get_default_export_settings()
            assert export_settings.resolution["width"] == 1920
            assert export_settings.resolution["height"] == 1080
            
            # Verify window has settings menu
            menubar = window.menuBar()
            tools_menu = None
            for action in menubar.actions():
                if action.text() == "&Tools":
                    tools_menu = action.menu()
                    break
            
            assert tools_menu is not None
            
            # Check for settings action in tools menu
            settings_action = None
            for action in tools_menu.actions():
                if "Settings" in action.text():
                    settings_action = action
                    break
            
            assert settings_action is not None
            
        finally:
            window.close()
    
    @patch('src.core.settings_manager.QSettings')
    def test_settings_persistence_on_close(self, mock_qsettings, app):
        """Test that settings are saved when window closes"""
        # Mock QSettings
        mock_settings = Mock()
        mock_qsettings.return_value = mock_settings
        
        storage = {}
        
        def mock_setValue(key, value):
            storage[key] = value
        
        def mock_value(key, default=None, type=None):
            value = storage.get(key, default)
            if type and value is not None:
                return type(value)
            return value
        
        def mock_contains(key):
            return key in storage
        
        mock_settings.setValue.side_effect = mock_setValue
        mock_settings.value.side_effect = mock_value
        mock_settings.contains.side_effect = mock_contains
        mock_settings.sync.return_value = None
        mock_settings.allKeys.return_value = list(storage.keys())
        
        # Create and close main window
        window = MainWindow()
        
        # Simulate window close
        window.close()
        
        # Verify sync was called
        mock_settings.sync.assert_called()
    
    @patch('src.core.settings_manager.QSettings')
    def test_export_widget_receives_default_settings(self, mock_qsettings, app):
        """Test that export widget receives default settings from settings manager"""
        # Mock QSettings
        mock_settings = Mock()
        mock_qsettings.return_value = mock_settings
        
        storage = {
            "export/default_resolution_width": 1280,
            "export/default_resolution_height": 720,
            "export/default_bitrate": 3000,
            "export/default_quality": "medium"
        }
        
        def mock_setValue(key, value):
            storage[key] = value
        
        def mock_value(key, default=None, type=None):
            value = storage.get(key, default)
            if type and value is not None:
                return type(value)
            return value
        
        def mock_contains(key):
            return key in storage
        
        mock_settings.setValue.side_effect = mock_setValue
        mock_settings.value.side_effect = mock_value
        mock_settings.contains.side_effect = mock_contains
        mock_settings.sync.return_value = None
        mock_settings.allKeys.return_value = list(storage.keys())
        
        # Create main window
        window = MainWindow()
        
        try:
            # Get export settings from settings manager
            export_settings = window.settings_manager.get_default_export_settings()
            
            # Verify custom settings are loaded
            assert export_settings.resolution["width"] == 1280
            assert export_settings.resolution["height"] == 720
            assert export_settings.bitrate == 3000
            assert export_settings.quality == "medium"
            
            # Verify export widget has update method
            assert hasattr(window.export_widget, 'update_default_settings')
            
        finally:
            window.close()


if __name__ == "__main__":
    pytest.main([__file__])