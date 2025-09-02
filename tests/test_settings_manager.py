"""
Unit tests for SettingsManager
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

# Import the module under test
try:
    from src.core.settings_manager import SettingsManager
    from src.core.models import ExportSettings
except ImportError:
    import sys
    sys.path.append('src')
    from core.settings_manager import SettingsManager
    from core.models import ExportSettings


class TestSettingsManager:
    """Test cases for SettingsManager"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app
    
    @pytest.fixture
    def temp_settings(self, app):
        """Create a temporary settings manager for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock QSettings to use temporary location
            with patch('src.core.settings_manager.QSettings') as mock_qsettings:
                mock_settings = MagicMock()
                mock_qsettings.return_value = mock_settings
                
                # Create settings manager
                settings_manager = SettingsManager()
                settings_manager.settings = mock_settings
                
                # Mock settings storage
                settings_manager._storage = {}
                
                def mock_setValue(key, value):
                    settings_manager._storage[key] = value
                
                def mock_value(key, default=None, type=None):
                    value = settings_manager._storage.get(key, default)
                    if type and value is not None:
                        return type(value)
                    return value
                
                def mock_contains(key):
                    return key in settings_manager._storage
                
                def mock_remove(key):
                    if key in settings_manager._storage:
                        del settings_manager._storage[key]
                
                def mock_clear():
                    settings_manager._storage.clear()
                
                def mock_allKeys():
                    return list(settings_manager._storage.keys())
                
                mock_settings.setValue.side_effect = mock_setValue
                mock_settings.value.side_effect = mock_value
                mock_settings.contains.side_effect = mock_contains
                mock_settings.remove.side_effect = mock_remove
                mock_settings.clear.side_effect = mock_clear
                mock_settings.allKeys.side_effect = mock_allKeys
                mock_settings.sync.return_value = None
                
                yield settings_manager
    
    def test_initialization(self, temp_settings):
        """Test settings manager initialization"""
        settings_manager = temp_settings
        
        # Check that default settings are initialized
        assert settings_manager.get_input_directory() is not None
        assert settings_manager.get_output_directory() is not None
        assert settings_manager.get_temp_directory() is not None
        
        # Check default export settings
        export_settings = settings_manager.get_default_export_settings()
        assert export_settings.resolution["width"] == 1920
        assert export_settings.resolution["height"] == 1080
        assert export_settings.bitrate == 5000
        assert export_settings.quality == "high"
    
    def test_directory_settings(self, temp_settings):
        """Test directory settings management"""
        settings_manager = temp_settings
        
        # Test input directory
        test_input_dir = "/test/input"
        settings_manager.set_input_directory(test_input_dir)
        assert settings_manager.get_input_directory() == str(Path(test_input_dir).resolve())
        
        # Test output directory
        test_output_dir = "/test/output"
        settings_manager.set_output_directory(test_output_dir)
        assert settings_manager.get_output_directory() == str(Path(test_output_dir).resolve())
        
        # Test temp directory
        test_temp_dir = "/test/temp"
        settings_manager.set_temp_directory(test_temp_dir)
        assert settings_manager.get_temp_directory() == str(Path(test_temp_dir).resolve())
    
    def test_export_settings(self, temp_settings):
        """Test export settings management"""
        settings_manager = temp_settings
        
        # Create custom export settings
        custom_settings = ExportSettings(
            resolution={"width": 1280, "height": 720},
            bitrate=3000,
            format="mp4",
            quality="medium",
            frame_rate=25.0,
            audio_bitrate=128,
            output_directory="/custom/output"
        )
        
        # Set and retrieve export settings
        settings_manager.set_default_export_settings(custom_settings)
        retrieved_settings = settings_manager.get_default_export_settings()
        
        assert retrieved_settings.resolution["width"] == 1280
        assert retrieved_settings.resolution["height"] == 720
        assert retrieved_settings.bitrate == 3000
        assert retrieved_settings.quality == "medium"
        assert retrieved_settings.frame_rate == 25.0
        assert retrieved_settings.audio_bitrate == 128
    
    def test_ui_state_persistence(self, temp_settings):
        """Test UI state persistence"""
        settings_manager = temp_settings
        
        # Test window geometry
        test_geometry = b"test_geometry_data"
        settings_manager.save_window_geometry(test_geometry)
        assert settings_manager.restore_window_geometry() == test_geometry
        
        # Test window state
        test_state = b"test_state_data"
        settings_manager.save_window_state(test_state)
        assert settings_manager.restore_window_state() == test_state
        
        # Test tab index
        settings_manager.save_last_tab_index(3)
        assert settings_manager.get_last_tab_index() == 3
    
    def test_recent_projects(self, temp_settings):
        """Test recent projects management"""
        settings_manager = temp_settings
        
        # Initially empty
        assert settings_manager.get_recent_projects() == []
        
        # Add projects
        settings_manager.add_recent_project("/path/to/project1.kvc", "Project 1")
        settings_manager.add_recent_project("/path/to/project2.kvc", "Project 2")
        
        recent = settings_manager.get_recent_projects()
        assert len(recent) == 2
        assert recent[0]["name"] == "Project 2"  # Most recent first
        assert recent[1]["name"] == "Project 1"
        
        # Remove project
        settings_manager.remove_recent_project("/path/to/project1.kvc")
        recent = settings_manager.get_recent_projects()
        assert len(recent) == 1
        assert recent[0]["name"] == "Project 2"
        
        # Clear all projects
        settings_manager.clear_recent_projects()
        assert settings_manager.get_recent_projects() == []
    
    def test_recent_projects_limit(self, temp_settings):
        """Test recent projects list limit"""
        settings_manager = temp_settings
        
        # Add more than 10 projects
        for i in range(15):
            settings_manager.add_recent_project(f"/path/to/project{i}.kvc", f"Project {i}")
        
        recent = settings_manager.get_recent_projects()
        assert len(recent) == 10  # Should be limited to 10
        assert recent[0]["name"] == "Project 14"  # Most recent
        assert recent[9]["name"] == "Project 5"   # Oldest kept
    
    def test_application_preferences(self, temp_settings):
        """Test application preferences"""
        settings_manager = temp_settings
        
        # Test auto-save projects
        settings_manager.set_auto_save_projects(False)
        assert settings_manager.get_auto_save_projects() is False
        
        settings_manager.set_auto_save_projects(True)
        assert settings_manager.get_auto_save_projects() is True
        
        # Test cleanup temp on exit
        settings_manager.set_cleanup_temp_on_exit(False)
        assert settings_manager.get_cleanup_temp_on_exit() is False
        
        # Test show tooltips
        settings_manager.set_show_tooltips(False)
        assert settings_manager.get_show_tooltips() is False
    
    def test_generic_settings_access(self, temp_settings):
        """Test generic settings access methods"""
        settings_manager = temp_settings
        
        # Test setting and getting
        settings_manager.set_setting("test/key", "test_value")
        assert settings_manager.get_setting("test/key") == "test_value"
        
        # Test default value
        assert settings_manager.get_setting("nonexistent/key", "default") == "default"
        
        # Test has_setting
        assert settings_manager.has_setting("test/key") is True
        assert settings_manager.has_setting("nonexistent/key") is False
        
        # Test remove setting
        settings_manager.remove_setting("test/key")
        assert settings_manager.has_setting("test/key") is False
    
    def test_settings_export_import(self, temp_settings):
        """Test settings export and import"""
        settings_manager = temp_settings
        
        # Set some test settings
        settings_manager.set_input_directory("/test/input")
        settings_manager.set_auto_save_projects(False)
        settings_manager.add_recent_project("/test/project.kvc", "Test Project")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Export settings
            success = settings_manager.export_settings(temp_path)
            assert success is True
            
            # Verify file exists and has content
            assert Path(temp_path).exists()
            with open(temp_path, 'r') as f:
                exported_data = json.load(f)
            assert len(exported_data) > 0
            
            # Clear settings and import
            settings_manager.reset_to_defaults()
            success = settings_manager.import_settings(temp_path)
            assert success is True
            
            # Verify settings were restored
            assert settings_manager.get_auto_save_projects() is False
            
        finally:
            # Clean up temp file
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    def test_settings_export_import_error_handling(self, temp_settings):
        """Test error handling in export/import"""
        settings_manager = temp_settings
        
        # Mock file operations to simulate errors
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Test export to invalid path
            success = settings_manager.export_settings("/invalid/path/settings.json")
            assert success is False
        
        # Test import from non-existent file
        success = settings_manager.import_settings("/nonexistent/settings.json")
        assert success is False
        
        # Test import from invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_path = temp_file.name
        
        try:
            success = settings_manager.import_settings(temp_path)
            assert success is False
        finally:
            Path(temp_path).unlink()
    
    def test_reset_to_defaults(self, temp_settings):
        """Test resetting settings to defaults"""
        settings_manager = temp_settings
        
        # Change some settings
        settings_manager.set_auto_save_projects(False)
        settings_manager.set_input_directory("/custom/input")
        settings_manager.add_recent_project("/test/project.kvc", "Test Project")
        
        # Reset to defaults
        settings_manager.reset_to_defaults()
        
        # Verify defaults are restored
        assert settings_manager.get_auto_save_projects() is True
        assert settings_manager.get_recent_projects() == []
        
        # Export settings should be defaults
        export_settings = settings_manager.get_default_export_settings()
        assert export_settings.resolution["width"] == 1920
        assert export_settings.quality == "high"
    
    def test_signals_emission(self, temp_settings):
        """Test that signals are emitted correctly"""
        settings_manager = temp_settings
        
        # Mock signal connections
        settings_changed_mock = Mock()
        export_defaults_changed_mock = Mock()
        recent_projects_changed_mock = Mock()
        
        settings_manager.settings_changed.connect(settings_changed_mock)
        settings_manager.export_defaults_changed.connect(export_defaults_changed_mock)
        settings_manager.recent_projects_changed.connect(recent_projects_changed_mock)
        
        # Test settings changed signal
        settings_manager.set_auto_save_projects(False)
        settings_changed_mock.assert_called_with("app/auto_save_projects", False)
        
        # Test export defaults changed signal
        custom_settings = ExportSettings(
            resolution={"width": 1280, "height": 720},
            bitrate=3000,
            format="mp4",
            quality="medium",
            frame_rate=25.0,
            audio_bitrate=128,
            output_directory="/test/output"
        )
        settings_manager.set_default_export_settings(custom_settings)
        export_defaults_changed_mock.assert_called_once()
        
        # Test recent projects changed signal
        settings_manager.add_recent_project("/test/project.kvc", "Test Project")
        recent_projects_changed_mock.assert_called_once()
    
    def test_sync_method(self, temp_settings):
        """Test settings sync method"""
        settings_manager = temp_settings
        
        # Should not raise any exceptions
        settings_manager.sync()
        
        # Verify sync was called on underlying QSettings
        settings_manager.settings.sync.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])