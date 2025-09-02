"""
Test suite for MainWindow UI components and functionality
"""

import sys
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QTabWidget, QMenuBar, QStatusBar
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from ui.main_window import MainWindow
from ui.import_widget import ImportWidget
from ui.preview_widget import PreviewWidget
from ui.editor_widget import EditorWidget
from ui.effects_widget import EffectsWidget
from ui.export_widget import ExportWidget


@pytest.fixture
def app():
    """Create QApplication instance for testing"""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def main_window(app):
    """Create MainWindow instance for testing"""
    window = MainWindow()
    yield window
    window.close()


class TestMainWindow:
    """Test cases for MainWindow functionality"""
    
    def test_window_initialization(self, main_window):
        """Test that main window initializes correctly"""
        assert main_window.windowTitle() == "Karaoke Video Creator"
        assert main_window.minimumSize().width() == 1200
        assert main_window.minimumSize().height() == 800
    
    def test_tabbed_interface(self, main_window):
        """Test that tabbed interface is set up correctly"""
        # Check tab widget exists
        assert hasattr(main_window, 'tab_widget')
        assert isinstance(main_window.tab_widget, QTabWidget)
        
        # Check correct number of tabs
        assert main_window.tab_widget.count() == 5
        
        # Check tab titles
        expected_tabs = [
            "1. Import Media",
            "2. Preview", 
            "3. Edit Subtitles",
            "4. Text Effects",
            "5. Export Video"
        ]
        
        for i, expected_title in enumerate(expected_tabs):
            assert main_window.tab_widget.tabText(i) == expected_title
    
    def test_widget_instances(self, main_window):
        """Test that all widget instances are created correctly"""
        assert isinstance(main_window.import_widget, ImportWidget)
        assert isinstance(main_window.preview_widget, PreviewWidget)
        assert isinstance(main_window.editor_widget, EditorWidget)
        assert isinstance(main_window.effects_widget, EffectsWidget)
        assert isinstance(main_window.export_widget, ExportWidget)
    
    def test_menu_bar(self, main_window):
        """Test that menu bar is set up correctly"""
        menubar = main_window.menuBar()
        assert isinstance(menubar, QMenuBar)
        
        # Check menu items exist
        menus = [action.text() for action in menubar.actions()]
        assert "&File" in menus
        assert "&Edit" in menus
        assert "&Help" in menus
        
        # Check File menu actions
        file_menu = None
        for action in menubar.actions():
            if action.text() == "&File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
        file_actions = [action.text() for action in file_menu.actions() if action.text()]
        assert "&New Project" in file_actions
        assert "&Open Project" in file_actions
        assert "&Save Project" in file_actions
        assert "E&xit" in file_actions
    
    def test_status_bar(self, main_window):
        """Test that status bar is set up correctly"""
        status_bar = main_window.statusBar()
        assert isinstance(status_bar, QStatusBar)
        
        # Check status label exists
        assert hasattr(main_window, 'status_label')
        assert main_window.status_label.text() == "Ready"
    
    def test_tab_change_handling(self, main_window):
        """Test that tab changes update status correctly"""
        # Change to different tabs and check status updates
        tab_names = [
            "Import Media", "Preview", "Edit Subtitles", 
            "Text Effects", "Export Video"
        ]
        
        for i, expected_name in enumerate(tab_names):
            main_window.tab_widget.setCurrentIndex(i)
            # Manually trigger the signal handler to test the logic
            main_window._on_tab_changed(i)
            expected_status = f"Current step: {expected_name}"
            assert main_window.status_label.text() == expected_status
    
    def test_menu_actions(self, main_window):
        """Test that menu actions work without errors"""
        # Test new project action
        main_window._new_project()
        # Should not raise any exceptions
        
        # Test open project action
        main_window._open_project()
        # Should not raise any exceptions
        
        # Test save project action
        main_window._save_project()
        # Should not raise any exceptions
    
    def test_about_dialog(self, main_window):
        """Test that about dialog can be shown"""
        # This should not raise any exceptions
        # Note: We don't actually show the dialog to avoid blocking tests
        try:
            # Just test that the method exists and is callable
            assert callable(main_window._show_about)
        except Exception as e:
            pytest.fail(f"About dialog method failed: {e}")


class TestImportWidget:
    """Test cases for ImportWidget functionality"""
    
    def test_import_widget_initialization(self, main_window):
        """Test that import widget initializes correctly"""
        import_widget = main_window.import_widget
        
        # Check that media importer is initialized
        assert hasattr(import_widget, 'media_importer')
        assert hasattr(import_widget, '_imported_files')
        assert isinstance(import_widget._imported_files, dict)
    
    def test_import_widget_ui_elements(self, main_window):
        """Test that import widget UI elements exist"""
        import_widget = main_window.import_widget
        
        # Check that info display exists
        assert hasattr(import_widget, 'info_display')
        
        # Check drag and drop is enabled
        assert import_widget.acceptDrops()
    
    def test_file_management_methods(self, main_window):
        """Test import widget file management methods"""
        import_widget = main_window.import_widget
        
        # Test get_imported_files
        files = import_widget.get_imported_files()
        assert isinstance(files, dict)
        
        # Test clear_imports
        import_widget.clear_imports()
        assert len(import_widget._imported_files) == 0
        
        # Test has_required_files
        assert not import_widget.has_required_files()


class TestOtherWidgets:
    """Test cases for other UI widgets"""
    
    def test_preview_widget(self, main_window):
        """Test that preview widget is functional"""
        preview_widget = main_window.preview_widget
        
        # Check OpenGL widget exists
        assert hasattr(preview_widget, 'opengl_widget')
        
        # Check playback controls exist
        assert hasattr(preview_widget, 'play_button')
        assert hasattr(preview_widget, 'stop_button')
        assert hasattr(preview_widget, 'timeline_slider')
        
        # Test playback state
        assert not preview_widget.is_playing
    
    def test_editor_widget(self, main_window):
        """Test that editor widget is functional"""
        editor_widget = main_window.editor_widget
        
        # Check text editor exists
        assert hasattr(editor_widget, 'text_editor')
        
        # Check validation display exists
        assert hasattr(editor_widget, 'validation_display')
    
    def test_effects_widget(self, main_window):
        """Test that effects widget is functional"""
        effects_widget = main_window.effects_widget
        
        # Check effects list exists
        assert hasattr(effects_widget, 'effects_list')
        assert hasattr(effects_widget, 'applied_effects_list')
        
        # Check that effects are populated
        assert effects_widget.effects_list.count() > 0
    
    def test_export_widget(self, main_window):
        """Test that export widget is functional"""
        export_widget = main_window.export_widget
        
        # Check export controls exist
        assert hasattr(export_widget, 'export_button')
        assert hasattr(export_widget, 'cancel_button')
        assert hasattr(export_widget, 'progress_bar')
        
        # Check settings controls exist
        assert hasattr(export_widget, 'quality_combo')
        assert hasattr(export_widget, 'width_spinbox')
        assert hasattr(export_widget, 'height_spinbox')


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])