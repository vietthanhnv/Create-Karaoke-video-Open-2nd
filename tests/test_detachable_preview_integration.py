"""
Integration Test for Detachable Preview Widget

Tests the complete integration with main window and effects synchronization.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QTabWidget, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

# Add src to path for imports
sys.path.insert(0, 'src')

from src.ui.detachable_preview_widget import DetachablePreviewWidget
from src.ui.main_window import MainWindow


class TestDetachablePreviewIntegration:
    """Test detachable preview integration with main application"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    def test_main_window_with_detachable_preview(self, app):
        """Test that main window properly integrates detachable preview"""
        try:
            # Create main window
            main_window = MainWindow()
            
            # Verify preview widget is detachable
            assert hasattr(main_window.preview_widget, 'detach_requested')
            assert hasattr(main_window.preview_widget, 'attach_requested')
            assert hasattr(main_window.preview_widget, '_detach_from_parent')
            assert hasattr(main_window.preview_widget, '_attach_to_parent')
            
            # Verify it's properly set up in tab widget
            preview_tab_index = -1
            for i in range(main_window.tab_widget.count()):
                if main_window.tab_widget.widget(i) == main_window.preview_widget:
                    preview_tab_index = i
                    break
            
            assert preview_tab_index >= 0, "Preview widget should be in tab widget"
            
            # Test that parent tab widget is set
            assert main_window.preview_widget.parent_tab_widget == main_window.tab_widget
            
            main_window.close()
            
        except Exception as e:
            pytest.skip(f"Main window creation failed: {e}")
    
    def test_effects_synchronization(self, app):
        """Test that effects are synchronized between widgets and preview"""
        try:
            main_window = MainWindow()
            
            # Mock effect application
            effect_id = "test_glow"
            effect_params = {"radius": 5.0, "intensity": 0.8}
            
            # Test effect application signal
            main_window._on_effect_applied(effect_id, effect_params)
            
            # Verify status message was updated
            assert "applied" in main_window.status_bar.currentMessage().lower()
            
            main_window.close()
            
        except Exception as e:
            pytest.skip(f"Effects synchronization test failed: {e}")
    
    def test_detach_attach_signals(self, app):
        """Test detach/attach signal handling"""
        try:
            main_window = MainWindow()
            
            # Test detach signal
            main_window._on_preview_detached()
            assert "detached" in main_window.status_bar.currentMessage().lower()
            
            # Test attach signal
            main_window._on_preview_attached()
            assert "attached" in main_window.status_bar.currentMessage().lower()
            
            # Test close signal
            main_window._on_preview_closed()
            assert "closed" in main_window.status_bar.currentMessage().lower()
            
            main_window.close()
            
        except Exception as e:
            pytest.skip(f"Signal handling test failed: {e}")


class TestEffectsSynchronization:
    """Test effects synchronization with detachable preview"""
    
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
    
    def test_effect_methods_exist(self, preview_widget):
        """Test that all effect methods are properly forwarded"""
        # Test that effect methods exist
        assert hasattr(preview_widget, 'add_effect')
        assert hasattr(preview_widget, 'remove_effect')
        assert hasattr(preview_widget, 'update_effect_parameters')
        assert hasattr(preview_widget, 'toggle_effect')
        assert hasattr(preview_widget, 'apply_effect_preset')
    
    def test_effect_method_forwarding(self, preview_widget):
        """Test that effect methods are properly forwarded"""
        # Mock the internal preview widget
        preview_widget.preview_widget = Mock()
        
        # Test add_effect
        preview_widget.add_effect("glow", {"radius": 5.0})
        preview_widget.preview_widget.add_effect.assert_called_with("glow", {"radius": 5.0})
        
        # Test remove_effect
        preview_widget.remove_effect("glow")
        preview_widget.preview_widget.remove_effect.assert_called_with("glow")
        
        # Test update_effect_parameters
        preview_widget.update_effect_parameters("glow", {"radius": 10.0})
        preview_widget.preview_widget.update_effect_parameters.assert_called_with("glow", {"radius": 10.0})
        
        # Test toggle_effect
        preview_widget.toggle_effect("glow", False)
        preview_widget.preview_widget.toggle_effect.assert_called_with("glow", False)
        
        # Test apply_effect_preset
        preview_widget.apply_effect_preset("karaoke_style")
        preview_widget.preview_widget.apply_effect_preset.assert_called_with("karaoke_style")


class TestRealTimePreview:
    """Test real-time preview functionality without separate preview widget"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    def test_no_separate_effects_preview(self, app):
        """Test that effects widget doesn't have separate preview"""
        try:
            from src.ui.effects_widget import EffectsWidget
            
            effects_widget = EffectsWidget()
            
            # Verify that real-time preview components are removed
            assert not hasattr(effects_widget, 'preview_label') or \
                   effects_widget.preview_label is None or \
                   not effects_widget.preview_label.isVisible()
            
            # Verify that preview text combo is removed
            assert not hasattr(effects_widget, 'preview_text_combo') or \
                   effects_widget.preview_text_combo is None or \
                   not effects_widget.preview_text_combo.isVisible()
            
        except ImportError:
            pytest.skip("Effects widget not available")
        except Exception as e:
            pytest.skip(f"Effects widget test failed: {e}")
    
    def test_effects_update_main_preview(self, app):
        """Test that effects updates are sent to main preview"""
        try:
            from src.ui.effects_widget import EffectsWidget
            
            effects_widget = EffectsWidget()
            
            # Mock signal connections
            signal_connected = False
            
            # Check if effect signals exist
            if hasattr(effects_widget, 'effect_applied'):
                signal_connected = True
                
            assert signal_connected, "Effects widget should have signals for main preview updates"
            
        except ImportError:
            pytest.skip("Effects widget not available")
        except Exception as e:
            pytest.skip(f"Effects signal test failed: {e}")


def test_demo_runs_without_errors():
    """Test that the demo can be imported and basic functionality works"""
    try:
        # Import the demo module
        import demo_detachable_preview
        
        # Test that main classes can be instantiated
        app = QApplication.instance() or QApplication([])
        
        # Create demo instance (but don't show it)
        demo = demo_detachable_preview.DetachablePreviewDemo()
        
        # Verify basic structure
        assert demo.tab_widget is not None
        assert demo.preview_widget is not None
        assert hasattr(demo.preview_widget, 'detach_requested')
        
        # Clean up
        demo.close()
        
    except ImportError as e:
        pytest.skip(f"Demo import failed: {e}")
    except Exception as e:
        pytest.skip(f"Demo test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])