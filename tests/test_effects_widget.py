"""
Unit tests for the EffectsWidget class.

Tests UI functionality, parameter management, and effect integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock PyQt6 before importing
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()
sys.modules['PyQt6.QtCore'] = MagicMock()
sys.modules['PyQt6.QtGui'] = MagicMock()

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

# Mock the Qt classes we need
class MockQWidget:
    def __init__(self):
        self.signals = {}
    
class MockQListWidgetItem:
    def __init__(self, text=""):
        self.text_value = text
        self.data_value = None
    
    def text(self):
        return self.text_value
    
    def data(self, role):
        return self.data_value
    
    def setData(self, role, value):
        self.data_value = value

class MockQListWidget:
    def __init__(self):
        self.items = []
        self.current_item = None
    
    def addItem(self, item):
        if isinstance(item, str):
            item = MockQListWidgetItem(item)
        self.items.append(item)
    
    def currentItem(self):
        return self.current_item
    
    def setCurrentItem(self, item):
        self.current_item = item
    
    def clear(self):
        self.items.clear()
        self.current_item = None
    
    def currentRow(self):
        if self.current_item and self.current_item in self.items:
            return self.items.index(self.current_item)
        return -1

# Patch the imports
with patch.dict('sys.modules', {
    'PyQt6.QtWidgets': MagicMock(),
    'PyQt6.QtCore': MagicMock(),
    'PyQt6.QtGui': MagicMock()
}):
    from ui.effects_widget import EffectsWidget
    from core.effects_manager import EffectsManager, EffectType


class TestEffectsWidget(unittest.TestCase):
    """Test cases for EffectsWidget functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock PyQt6 components
        with patch('ui.effects_widget.QWidget'), \
             patch('ui.effects_widget.QVBoxLayout'), \
             patch('ui.effects_widget.QHBoxLayout'), \
             patch('ui.effects_widget.QLabel'), \
             patch('ui.effects_widget.QListWidget') as mock_list_widget, \
             patch('ui.effects_widget.QGroupBox'), \
             patch('ui.effects_widget.QPushButton'), \
             patch('ui.effects_widget.QFrame'), \
             patch('ui.effects_widget.QGridLayout'), \
             patch('ui.effects_widget.QDoubleSpinBox'), \
             patch('ui.effects_widget.QComboBox'), \
             patch('ui.effects_widget.QSplitter'), \
             patch('ui.effects_widget.QScrollArea'), \
             patch('ui.effects_widget.QTimer') as mock_timer:
            
            # Set up mock list widget
            mock_list_widget.return_value = MockQListWidget()
            mock_timer.return_value = Mock()
            
            self.widget = EffectsWidget()
            
            # Mock the UI components that are created in _setup_ui
            self.widget.effects_list = MockQListWidget()
            self.widget.applied_effects_list = MockQListWidget()
            self.widget.presets_combo = Mock()
            self.widget.preview_text_combo = Mock()
            self.widget.preview_label = Mock()
            self.widget.params_container = Mock()
            self.widget.params_layout = Mock()
            
            # Mock buttons
            self.widget.add_effect_button = Mock()
            self.widget.remove_button = Mock()
            self.widget.move_up_button = Mock()
            self.widget.move_down_button = Mock()
            self.widget.toggle_button = Mock()
            self.widget.update_preview_button = Mock()
    
    def test_initialization(self):
        """Test widget initialization."""
        self.assertIsInstance(self.widget.effects_manager, EffectsManager)
        self.assertIsNone(self.widget.current_effect_id)
        self.assertIsInstance(self.widget.parameter_widgets, dict)
    
    def test_add_effect(self):
        """Test adding an effect."""
        # Mock current item selection
        mock_item = MockQListWidgetItem("Glow Effect")
        mock_item.setData(Qt.ItemDataRole.UserRole, EffectType.GLOW.value)
        self.widget.effects_list.setCurrentItem(mock_item)
        
        # Mock signal emission
        self.widget.effect_applied = Mock()
        
        # Add effect
        self.widget._add_effect()
        
        # Verify effect was added to manager
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 1)
        self.assertEqual(self.widget.effects_manager.effect_layers[0].effect.type, EffectType.GLOW.value)
    
    def test_remove_effect(self):
        """Test removing an effect."""
        # Add an effect first
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        layer = self.widget.effects_manager.add_effect_layer(glow_effect)
        self.widget.current_effect_id = glow_effect.id
        
        # Mock signal emission
        self.widget.effect_removed = Mock()
        
        # Remove effect
        self.widget._remove_effect()
        
        # Verify effect was removed
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 0)
        self.assertIsNone(self.widget.current_effect_id)
    
    def test_update_parameter(self):
        """Test updating effect parameters."""
        # Add an effect
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {'radius': 5.0})
        self.widget.effects_manager.add_effect_layer(glow_effect)
        self.widget.current_effect_id = glow_effect.id
        
        # Mock signal emission
        self.widget.effect_parameters_changed = Mock()
        
        # Update parameter
        self.widget._update_parameter('radius', 10.0)
        
        # Verify parameter was updated
        layer = self.widget.effects_manager.get_effect_layer(glow_effect.id)
        self.assertEqual(layer.effect.parameters['radius'], 10.0)
    
    def test_toggle_effect(self):
        """Test toggling effect enabled state."""
        # Add an effect
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        layer = self.widget.effects_manager.add_effect_layer(glow_effect)
        self.widget.current_effect_id = glow_effect.id
        
        # Mock signal emission
        self.widget.effect_toggled = Mock()
        
        # Toggle effect
        self.widget._toggle_effect()
        
        # Verify effect was toggled
        self.assertFalse(layer.enabled)
    
    def test_move_effect_up(self):
        """Test moving effect up in order."""
        # Add multiple effects
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.widget.effects_manager.create_effect(EffectType.OUTLINE, {})
        
        self.widget.effects_manager.add_effect_layer(glow_effect, order=0)
        self.widget.effects_manager.add_effect_layer(outline_effect, order=1)
        
        self.widget.current_effect_id = outline_effect.id
        
        # Mock signal emission
        self.widget.effect_reordered = Mock()
        
        # Move effect up
        self.widget._move_effect_up()
        
        # Verify effect was moved
        layer = self.widget.effects_manager.get_effect_layer(outline_effect.id)
        self.assertEqual(layer.order, 0)
    
    def test_move_effect_down(self):
        """Test moving effect down in order."""
        # Add multiple effects
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.widget.effects_manager.create_effect(EffectType.OUTLINE, {})
        
        self.widget.effects_manager.add_effect_layer(glow_effect, order=0)
        self.widget.effects_manager.add_effect_layer(outline_effect, order=1)
        
        self.widget.current_effect_id = glow_effect.id
        
        # Mock signal emission
        self.widget.effect_reordered = Mock()
        
        # Move effect down
        self.widget._move_effect_down()
        
        # Verify effect was moved
        layer = self.widget.effects_manager.get_effect_layer(glow_effect.id)
        self.assertEqual(layer.order, 1)
    
    def test_apply_preset(self):
        """Test applying effect presets."""
        # Mock preset selection
        self.widget.preset_applied = Mock()
        
        # Apply preset
        self.widget._on_preset_selected("Karaoke Classic")
        
        # Verify effects were added
        self.assertGreater(len(self.widget.effects_manager.effect_layers), 0)
    
    def test_parameter_widgets_creation(self):
        """Test creation of parameter widgets for different effect types."""
        # Test glow parameters
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {
            'radius': 8.0,
            'intensity': 0.9,
            'color': [1.0, 0.0, 1.0]
        })
        layer = self.widget.effects_manager.add_effect_layer(glow_effect)
        
        # Mock the parameter layout
        self.widget.params_layout.addWidget = Mock()
        
        # Show parameters
        self.widget._show_effect_parameters(layer)
        
        # Verify parameter widgets were created
        self.assertGreater(self.widget.params_layout.addWidget.call_count, 0)
    
    def test_clear_parameters(self):
        """Test clearing parameter widgets."""
        # Add some mock parameter widgets
        self.widget.parameter_widgets = {'radius': Mock(), 'intensity': Mock()}
        
        # Mock the layout
        self.widget.params_layout.count = Mock(return_value=0)
        
        # Clear parameters
        self.widget._clear_parameters()
        
        # Verify widgets were cleared
        self.assertEqual(len(self.widget.parameter_widgets), 0)
    
    def test_refresh_applied_effects(self):
        """Test refreshing the applied effects list."""
        # Add effects
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        outline_effect = self.widget.effects_manager.create_effect(EffectType.OUTLINE, {})
        
        self.widget.effects_manager.add_effect_layer(glow_effect)
        layer2 = self.widget.effects_manager.add_effect_layer(outline_effect)
        
        # Disable one effect
        layer2.enabled = False
        
        # Mock the applied effects list
        self.widget.applied_effects_list.clear = Mock()
        self.widget.applied_effects_list.addItem = Mock()
        
        # Refresh list
        self.widget._refresh_applied_effects()
        
        # Verify list was updated
        self.widget.applied_effects_list.clear.assert_called_once()
        self.assertEqual(self.widget.applied_effects_list.addItem.call_count, 2)
    
    def test_update_effect_buttons(self):
        """Test updating effect control button states."""
        # Mock buttons
        self.widget.remove_button.setEnabled = Mock()
        self.widget.toggle_button.setEnabled = Mock()
        self.widget.move_up_button.setEnabled = Mock()
        self.widget.move_down_button.setEnabled = Mock()
        
        # Test with no selection
        self.widget.current_effect_id = None
        self.widget._update_effect_buttons()
        
        # Verify buttons are disabled
        self.widget.remove_button.setEnabled.assert_called_with(False)
        self.widget.toggle_button.setEnabled.assert_called_with(False)
        
        # Test with selection
        glow_effect = self.widget.effects_manager.create_effect(EffectType.GLOW, {})
        self.widget.effects_manager.add_effect_layer(glow_effect)
        self.widget.current_effect_id = glow_effect.id
        
        self.widget._update_effect_buttons()
        
        # Verify buttons are enabled
        self.widget.remove_button.setEnabled.assert_called_with(True)
        self.widget.toggle_button.setEnabled.assert_called_with(True)
    
    def test_schedule_preview_update(self):
        """Test preview update scheduling."""
        # Mock timer
        self.widget.preview_timer = Mock()
        
        # Schedule update
        self.widget._schedule_preview_update()
        
        # Verify timer was started
        self.widget.preview_timer.start.assert_called_once_with(300)
    
    def test_get_effects_manager(self):
        """Test getting the effects manager."""
        manager = self.widget.get_effects_manager()
        self.assertIs(manager, self.widget.effects_manager)
    
    def test_refresh_ui(self):
        """Test refreshing the entire UI."""
        # Mock methods
        self.widget._refresh_applied_effects = Mock()
        self.widget._update_effect_buttons = Mock()
        self.widget._update_preview = Mock()
        
        # Refresh UI
        self.widget.refresh_ui()
        
        # Verify all methods were called
        self.widget._refresh_applied_effects.assert_called_once()
        self.widget._update_effect_buttons.assert_called_once()
        self.widget._update_preview.assert_called_once()


class TestEffectsWidgetIntegration(unittest.TestCase):
    """Integration tests for EffectsWidget with EffectsManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('ui.effects_widget.QWidget'), \
             patch('ui.effects_widget.QVBoxLayout'), \
             patch('ui.effects_widget.QHBoxLayout'), \
             patch('ui.effects_widget.QLabel'), \
             patch('ui.effects_widget.QListWidget'), \
             patch('ui.effects_widget.QGroupBox'), \
             patch('ui.effects_widget.QPushButton'), \
             patch('ui.effects_widget.QFrame'), \
             patch('ui.effects_widget.QGridLayout'), \
             patch('ui.effects_widget.QDoubleSpinBox'), \
             patch('ui.effects_widget.QComboBox'), \
             patch('ui.effects_widget.QSplitter'), \
             patch('ui.effects_widget.QScrollArea'), \
             patch('ui.effects_widget.QTimer'):
            
            self.widget = EffectsWidget()
            
            # Mock UI components
            self.widget.effects_list = MockQListWidget()
            self.widget.applied_effects_list = MockQListWidget()
            self.widget.params_layout = Mock()
            self.widget.params_layout.count = Mock(return_value=0)
    
    def test_full_effect_workflow(self):
        """Test complete effect management workflow."""
        # Start with no effects
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 0)
        
        # Add glow effect
        mock_item = MockQListWidgetItem("Glow Effect")
        mock_item.setData(Qt.ItemDataRole.UserRole, EffectType.GLOW.value)
        self.widget.effects_list.setCurrentItem(mock_item)
        
        self.widget._add_effect()
        
        # Verify effect was added
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 1)
        glow_layer = self.widget.effects_manager.effect_layers[0]
        self.assertEqual(glow_layer.effect.type, EffectType.GLOW.value)
        
        # Add outline effect
        mock_item = MockQListWidgetItem("Outline Effect")
        mock_item.setData(Qt.ItemDataRole.UserRole, EffectType.OUTLINE.value)
        self.widget.effects_list.setCurrentItem(mock_item)
        
        self.widget._add_effect()
        
        # Verify both effects exist
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 2)
        
        # Select and modify glow effect
        self.widget.current_effect_id = glow_layer.effect.id
        self.widget._update_parameter('radius', 12.0)
        
        # Verify parameter was updated
        updated_layer = self.widget.effects_manager.get_effect_layer(glow_layer.effect.id)
        self.assertEqual(updated_layer.effect.parameters['radius'], 12.0)
        
        # Toggle effect
        self.widget._toggle_effect()
        self.assertFalse(updated_layer.enabled)
        
        # Remove effect
        self.widget._remove_effect()
        self.assertEqual(len(self.widget.effects_manager.effect_layers), 1)
        
        # Verify only outline effect remains
        remaining_layer = self.widget.effects_manager.effect_layers[0]
        self.assertEqual(remaining_layer.effect.type, EffectType.OUTLINE.value)


if __name__ == '__main__':
    unittest.main()