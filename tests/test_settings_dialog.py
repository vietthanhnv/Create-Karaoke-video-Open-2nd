"""
Unit tests for SettingsDialog
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QDialogButtonBox
from PyQt6.QtCore import Qt

# Import the modules under test
try:
    from src.ui.settings_dialog import SettingsDialog
    from src.core.settings_manager import SettingsManager
    from src.core.models import ExportSettings
except ImportError:
    import sys
    sys.path.append('src')
    from ui.settings_dialog import SettingsDialog
    from core.settings_manager import SettingsManager
    from core.models import ExportSettings


class TestSettingsDialog:
    """Test cases for SettingsDialog"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            app = QApplication([])
        else:
            app = QApplication.instance()
        yield app
    
    @pytest.fixture
    def mock_settings_manager(self):
        """Create a mock settings manager"""
        mock_manager = Mock(spec=SettingsManager)
        
        # Set up default return values
        mock_manager.get_auto_save_projects.return_value = True
        mock_manager.get_cleanup_temp_on_exit.return_value = True
        mock_manager.get_show_tooltips.return_value = True
        
        mock_manager.get_input_directory.return_value = "input"
        mock_manager.get_output_directory.return_value = "output"
        mock_manager.get_temp_directory.return_value = "temp"
        
        mock_manager.get_default_export_settings.return_value = ExportSettings(
            resolution={"width": 1920, "height": 1080},
            bitrate=5000,
            format="mp4",
            quality="high",
            frame_rate=30.0,
            audio_bitrate=192,
            output_directory="output"
        )
        
        mock_manager.get_recent_projects.return_value = [
            {"name": "Test Project 1", "path": "/path/to/project1.kvc"},
            {"name": "Test Project 2", "path": "/path/to/project2.kvc"}
        ]
        
        return mock_manager
    
    @pytest.fixture
    def settings_dialog(self, app, mock_settings_manager):
        """Create a settings dialog for testing"""
        dialog = SettingsDialog(mock_settings_manager)
        yield dialog
        dialog.close()
    
    def test_dialog_initialization(self, settings_dialog, mock_settings_manager):
        """Test dialog initialization"""
        dialog = settings_dialog
        
        # Check that dialog is created
        assert dialog is not None
        assert dialog.windowTitle() == "Settings"
        assert dialog.isModal() is True
        
        # Check that settings manager is set
        assert dialog.settings_manager == mock_settings_manager
        
        # Check that tabs are created
        assert dialog.tab_widget.count() == 4
        tab_titles = [dialog.tab_widget.tabText(i) for i in range(4)]
        assert "General" in tab_titles
        assert "Export Defaults" in tab_titles
        assert "Directories" in tab_titles
        assert "Projects & Settings" in tab_titles
    
    def test_load_current_settings(self, settings_dialog, mock_settings_manager):
        """Test loading current settings into dialog"""
        dialog = settings_dialog
        
        # Verify general settings are loaded
        assert dialog.auto_save_checkbox.isChecked() is True
        assert dialog.cleanup_temp_checkbox.isChecked() is True
        assert dialog.show_tooltips_checkbox.isChecked() is True
        
        # Verify export settings are loaded
        assert dialog.width_spinbox.value() == 1920
        assert dialog.height_spinbox.value() == 1080
        assert dialog.video_bitrate_spinbox.value() == 5000
        assert dialog.audio_bitrate_spinbox.value() == 192
        assert dialog.quality_combo.currentText() == "high"
        
        # Verify directory settings are loaded
        assert dialog.input_dir_edit.text() == "input"
        assert dialog.output_dir_edit.text() == "output"
        assert dialog.temp_dir_edit.text() == "temp"
        
        # Verify recent projects are loaded
        assert dialog.projects_list.count() == 2
    
    def test_apply_preset_720p(self, settings_dialog):
        """Test applying 720p preset"""
        dialog = settings_dialog
        
        # Click 720p preset button
        dialog.preset_720p_btn.click()
        
        # Verify settings are updated
        assert dialog.width_spinbox.value() == 1280
        assert dialog.height_spinbox.value() == 720
        assert dialog.frame_rate_spinbox.value() == 30.0
        assert dialog.video_bitrate_spinbox.value() == 3000
        assert dialog.quality_combo.currentText() == "custom"
    
    def test_apply_preset_1080p(self, settings_dialog):
        """Test applying 1080p preset"""
        dialog = settings_dialog
        
        # Click 1080p preset button
        dialog.preset_1080p_btn.click()
        
        # Verify settings are updated
        assert dialog.width_spinbox.value() == 1920
        assert dialog.height_spinbox.value() == 1080
        assert dialog.frame_rate_spinbox.value() == 30.0
        assert dialog.video_bitrate_spinbox.value() == 5000
        assert dialog.quality_combo.currentText() == "custom"
    
    def test_apply_preset_4k(self, settings_dialog):
        """Test applying 4K preset"""
        dialog = settings_dialog
        
        # Click 4K preset button
        dialog.preset_4k_btn.click()
        
        # Verify settings are updated
        assert dialog.width_spinbox.value() == 3840
        assert dialog.height_spinbox.value() == 2160
        assert dialog.frame_rate_spinbox.value() == 30.0
        assert dialog.video_bitrate_spinbox.value() == 15000
        assert dialog.quality_combo.currentText() == "custom"
    
    def test_quality_preset_changes(self, settings_dialog):
        """Test quality preset changes"""
        dialog = settings_dialog
        
        # Test low quality
        dialog.quality_combo.setCurrentText("low")
        dialog._on_quality_changed("low")
        assert dialog.width_spinbox.value() == 1280
        assert dialog.height_spinbox.value() == 720
        assert dialog.video_bitrate_spinbox.value() == 2000
        
        # Test medium quality
        dialog.quality_combo.setCurrentText("medium")
        dialog._on_quality_changed("medium")
        assert dialog.width_spinbox.value() == 1920
        assert dialog.height_spinbox.value() == 1080
        assert dialog.video_bitrate_spinbox.value() == 3500
        
        # Test high quality
        dialog.quality_combo.setCurrentText("high")
        dialog._on_quality_changed("high")
        assert dialog.width_spinbox.value() == 1920
        assert dialog.height_spinbox.value() == 1080
        assert dialog.video_bitrate_spinbox.value() == 5000
    
    @patch('src.ui.settings_dialog.QFileDialog.getExistingDirectory')
    def test_browse_directory(self, mock_file_dialog, settings_dialog):
        """Test directory browsing"""
        dialog = settings_dialog
        mock_file_dialog.return_value = "/new/test/directory"
        
        # Test browsing input directory
        dialog._browse_directory(dialog.input_dir_edit)
        assert dialog.input_dir_edit.text() == "/new/test/directory"
        
        # Test browsing with no selection (empty string)
        mock_file_dialog.return_value = ""
        original_text = dialog.output_dir_edit.text()
        dialog._browse_directory(dialog.output_dir_edit)
        assert dialog.output_dir_edit.text() == original_text  # Should not change
    
    def test_project_selection_handling(self, settings_dialog):
        """Test project selection handling"""
        dialog = settings_dialog
        
        # Initially no selection, remove button should be disabled
        assert dialog.remove_project_btn.isEnabled() is False
        
        # Select first project
        dialog.projects_list.setCurrentRow(0)
        dialog._on_project_selection_changed()
        assert dialog.remove_project_btn.isEnabled() is True
        
        # Clear selection
        dialog.projects_list.clearSelection()
        dialog._on_project_selection_changed()
        assert dialog.remove_project_btn.isEnabled() is False
    
    def test_remove_selected_project(self, settings_dialog, mock_settings_manager):
        """Test removing selected project"""
        dialog = settings_dialog
        
        # Select first project and remove it
        dialog.projects_list.setCurrentRow(0)
        dialog._remove_selected_project()
        
        # Verify remove_recent_project was called
        mock_settings_manager.remove_recent_project.assert_called_once()
    
    @patch('src.ui.settings_dialog.QMessageBox.question')
    def test_clear_all_projects(self, mock_question, settings_dialog, mock_settings_manager):
        """Test clearing all projects"""
        from PyQt6.QtWidgets import QMessageBox
        dialog = settings_dialog
        
        # Test user confirms clearing
        mock_question.return_value = QMessageBox.StandardButton.Yes
        dialog._clear_all_projects()
        mock_settings_manager.clear_recent_projects.assert_called_once()
        
        # Reset mock
        mock_settings_manager.reset_mock()
        
        # Test user cancels clearing
        mock_question.return_value = QMessageBox.StandardButton.No
        dialog._clear_all_projects()
        mock_settings_manager.clear_recent_projects.assert_not_called()
    
    @patch('src.ui.settings_dialog.QFileDialog.getSaveFileName')
    @patch('src.ui.settings_dialog.QMessageBox.information')
    def test_export_settings_success(self, mock_info, mock_save_dialog, settings_dialog, mock_settings_manager):
        """Test successful settings export"""
        dialog = settings_dialog
        
        mock_save_dialog.return_value = ("/test/settings.json", "JSON Files (*.json)")
        mock_settings_manager.export_settings.return_value = True
        
        dialog._export_settings()
        
        mock_settings_manager.export_settings.assert_called_once_with("/test/settings.json")
        mock_info.assert_called_once()
    
    @patch('src.ui.settings_dialog.QFileDialog.getSaveFileName')
    @patch('src.ui.settings_dialog.QMessageBox.warning')
    def test_export_settings_failure(self, mock_warning, mock_save_dialog, settings_dialog, mock_settings_manager):
        """Test failed settings export"""
        dialog = settings_dialog
        
        mock_save_dialog.return_value = ("/test/settings.json", "JSON Files (*.json)")
        mock_settings_manager.export_settings.return_value = False
        
        dialog._export_settings()
        
        mock_settings_manager.export_settings.assert_called_once_with("/test/settings.json")
        mock_warning.assert_called_once()
    
    @patch('src.ui.settings_dialog.QFileDialog.getOpenFileName')
    @patch('src.ui.settings_dialog.QMessageBox.question')
    @patch('src.ui.settings_dialog.QMessageBox.information')
    def test_import_settings_success(self, mock_info, mock_question, mock_open_dialog, settings_dialog, mock_settings_manager):
        """Test successful settings import"""
        from PyQt6.QtWidgets import QMessageBox
        dialog = settings_dialog
        
        mock_open_dialog.return_value = ("/test/settings.json", "JSON Files (*.json)")
        mock_question.return_value = QMessageBox.StandardButton.Yes
        mock_settings_manager.import_settings.return_value = True
        
        dialog._import_settings()
        
        mock_settings_manager.import_settings.assert_called_once_with("/test/settings.json")
        mock_info.assert_called_once()
    
    def test_apply_settings(self, settings_dialog, mock_settings_manager):
        """Test applying settings"""
        dialog = settings_dialog
        
        # Change some settings in the dialog
        dialog.auto_save_checkbox.setChecked(False)
        dialog.width_spinbox.setValue(1280)
        dialog.height_spinbox.setValue(720)
        dialog.input_dir_edit.setText("/new/input")
        
        # Apply settings
        dialog._apply_settings()
        
        # Verify settings manager methods were called
        mock_settings_manager.set_auto_save_projects.assert_called_with(False)
        mock_settings_manager.set_default_export_settings.assert_called_once()
        mock_settings_manager.set_input_directory.assert_called_with("/new/input")
        mock_settings_manager.sync.assert_called_once()
    
    def test_apply_and_accept(self, settings_dialog, mock_settings_manager):
        """Test apply and accept functionality"""
        dialog = settings_dialog
        
        # Mock the accept method
        dialog.accept = Mock()
        
        # Call apply and accept
        dialog._apply_and_accept()
        
        # Verify settings were applied and dialog was accepted
        mock_settings_manager.sync.assert_called_once()
        dialog.accept.assert_called_once()
    
    @patch('src.ui.settings_dialog.QMessageBox.question')
    @patch('src.ui.settings_dialog.QMessageBox.information')
    def test_restore_defaults(self, mock_info, mock_question, settings_dialog, mock_settings_manager):
        """Test restoring default settings"""
        from PyQt6.QtWidgets import QMessageBox
        dialog = settings_dialog
        
        # Test user confirms restore
        mock_question.return_value = QMessageBox.StandardButton.Yes
        dialog._restore_defaults()
        
        mock_settings_manager.reset_to_defaults.assert_called_once()
        mock_info.assert_called_once()
        
        # Reset mock
        mock_settings_manager.reset_mock()
        
        # Test user cancels restore
        mock_question.return_value = QMessageBox.StandardButton.No
        dialog._restore_defaults()
        
        mock_settings_manager.reset_to_defaults.assert_not_called()
    
    def test_button_box_connections(self, settings_dialog):
        """Test button box connections"""
        dialog = settings_dialog
        
        # Test that buttons exist
        ok_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        apply_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Apply)
        defaults_button = dialog.button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        
        assert ok_button is not None
        assert cancel_button is not None
        assert apply_button is not None
        assert defaults_button is not None
        
        # Test that buttons are enabled
        assert ok_button.isEnabled()
        assert cancel_button.isEnabled()
        assert apply_button.isEnabled()
        assert defaults_button.isEnabled()


if __name__ == "__main__":
    pytest.main([__file__])