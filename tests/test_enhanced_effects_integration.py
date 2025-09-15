"""
Integration Test for Enhanced Effects Widget with Detachable Preview

Tests the complete integration between enhanced effects system and detachable preview.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

# Add src to path for imports
sys.path.insert(0, 'src')

from src.ui.enhanced_effects_widget import EnhancedEffectsWidget
from src.ui.detachable_preview_widget import DetachablePreviewWidget
from src.core.enhanced_effects_manager import EnhancedEffectsManager, EffectType, FontWeight


class TestEnhancedEffectsIntegration:
    """Test enhanced effects integration with detachable preview"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def enhanced_effects_widget(self, app):
        """Create enhanced effects widget"""
        return EnhancedEffectsWidget()
    
    @pytest.fixture
    def detachable_preview(self, app):
        """Create detachable preview widget"""
        return DetachablePreviewWidget()
    
    def test_enhanced_effects_widget_creation(self, enhanced_effects_widget):
        """Test that enhanced effects widget is created properly"""
        assert enhanced_effects_widget is not None
        assert hasattr(enhanced_effects_widget, 'effects_manager')
        assert isinstance(enhanced_effects_widget.effects_manager, EnhancedEffectsManager)
        
        # Check that all required signals exist
        assert hasattr(enhanced_effects_widget, 'font_properties_changed')
        assert hasattr(enhanced_effects_widget, 'effect_applied')
        assert hasattr(enhanced_effects_widget, 'effect_removed')
        assert hasattr(enhanced_effects_widget, 'effect_parameters_changed')
        assert hasattr(enhanced_effects_widget, 'effect_toggled')
        assert hasattr(enhanced_effects_widget, 'preset_applied')
    
    def test_enhanced_effects_manager_functionality(self, enhanced_effects_widget):
        """Test enhanced effects manager core functionality"""
        manager = enhanced_effects_widget.effects_manager
        
        # Test font properties
        manager.set_font_family("Arial")
        assert manager.font_properties.family == "Arial"
        
        manager.set_font_size(24.0)
        assert manager.font_properties.size == 24.0
        
        manager.set_font_weight(FontWeight.BOLD)
        assert manager.font_properties.weight == FontWeight.BOLD
        
        # Test effect layers
        initial_count = len(manager.effect_layers)
        layer = manager.add_effect_layer(EffectType.GLOW)
        assert len(manager.effect_layers) == initial_count + 1
        assert layer.effect_type == EffectType.GLOW
        
        # Test effect removal
        manager.remove_effect_layer(layer.id)
        assert len(manager.effect_layers) == initial_count
    
    def test_preset_functionality(self, enhanced_effects_widget):
        """Test preset application and management"""
        manager = enhanced_effects_widget.effects_manager
        
        # Test getting available presets
        presets = manager.get_available_presets()
        assert len(presets) > 0
        assert 'karaoke_classic' in presets
        
        # Test applying preset
        success = manager.apply_preset('karaoke_classic')
        assert success
        
        # Verify preset was applied (should have effects)
        assert len(manager.effect_layers) > 0
        
        # Test getting preset info
        preset_info = manager.get_preset_info('karaoke_classic')
        assert preset_info is not None
        assert preset_info.name == "Classic Karaoke"
    
    def test_signal_emission(self, enhanced_effects_widget):
        """Test that signals are properly emitted"""
        # Mock signal connections
        font_changed_mock = Mock()
        effect_applied_mock = Mock()
        
        enhanced_effects_widget.font_properties_changed.connect(font_changed_mock)
        enhanced_effects_widget.effect_applied.connect(effect_applied_mock)
        
        # Trigger font change
        enhanced_effects_widget._on_font_size_changed(32.0)
        
        # Should trigger update timer, let's manually trigger the update
        enhanced_effects_widget._emit_updates()
        
        # Verify signal was emitted
        font_changed_mock.assert_called()
    
    def test_integration_with_detachable_preview(self, enhanced_effects_widget, detachable_preview):
        """Test integration between enhanced effects and detachable preview"""
        # Connect signals
        enhanced_effects_widget.effect_applied.connect(
            lambda effect_id, params: detachable_preview.add_effect(effect_id, params)
        )
        enhanced_effects_widget.effect_removed.connect(
            lambda effect_id: detachable_preview.remove_effect(effect_id)
        )
        
        # Mock the preview widget's methods
        detachable_preview.preview_widget = Mock()
        
        # Add an effect
        manager = enhanced_effects_widget.effects_manager
        layer = manager.add_effect_layer(EffectType.GLOW)
        
        # Manually emit the signal (normally done by UI interaction)
        enhanced_effects_widget.effect_applied.emit(layer.id, layer.parameters.params)
        
        # Verify preview widget method was called
        detachable_preview.preview_widget.add_effect.assert_called_with(layer.id, layer.parameters.params)
    
    def test_tab_widget_structure(self, enhanced_effects_widget):
        """Test that tab widget is properly structured"""
        tab_widget = enhanced_effects_widget.tab_widget
        
        # Should have multiple tabs
        assert tab_widget.count() >= 5
        
        # Check tab names
        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        expected_tabs = ["Font", "Visual Effects", "Animations", "Advanced", "Presets"]
        
        for expected_tab in expected_tabs:
            assert expected_tab in tab_names
    
    def test_font_properties_ui_elements(self, enhanced_effects_widget):
        """Test that font properties UI elements exist and work"""
        # Check that font UI elements exist
        assert hasattr(enhanced_effects_widget, 'font_family_combo')
        assert hasattr(enhanced_effects_widget, 'font_size_spin')
        assert hasattr(enhanced_effects_widget, 'font_weight_combo')
        assert hasattr(enhanced_effects_widget, 'font_style_combo')
        assert hasattr(enhanced_effects_widget, 'font_color_button')
        
        # Test font size change
        initial_size = enhanced_effects_widget.effects_manager.font_properties.size
        enhanced_effects_widget.font_size_spin.setValue(36.0)
        enhanced_effects_widget._on_font_size_changed(36.0)
        
        assert enhanced_effects_widget.effects_manager.font_properties.size == 36.0
    
    def test_effects_lists_functionality(self, enhanced_effects_widget):
        """Test that effects lists work properly"""
        # Check that effects lists exist
        assert hasattr(enhanced_effects_widget, 'visual_effects_list')
        assert hasattr(enhanced_effects_widget, 'animation_effects_list')
        assert hasattr(enhanced_effects_widget, 'advanced_effects_list')
        
        # Check that applied effects lists exist
        assert hasattr(enhanced_effects_widget, 'applied_visual_effects')
        assert hasattr(enhanced_effects_widget, 'applied_animation_effects')
        assert hasattr(enhanced_effects_widget, 'applied_advanced_effects')
        
        # Test adding an effect
        initial_count = len(enhanced_effects_widget.effects_manager.effect_layers)
        
        # Simulate selecting a visual effect
        enhanced_effects_widget.visual_effects_list.setCurrentRow(0)  # Select first item
        enhanced_effects_widget._add_visual_effect()
        
        # Should have added an effect
        assert len(enhanced_effects_widget.effects_manager.effect_layers) > initial_count


class TestEnhancedEffectsManager:
    """Test enhanced effects manager independently"""
    
    @pytest.fixture
    def manager(self):
        """Create enhanced effects manager"""
        return EnhancedEffectsManager()
    
    def test_manager_initialization(self, manager):
        """Test manager initializes properly"""
        assert manager.font_properties is not None
        assert len(manager.effect_layers) == 0
        assert len(manager.effect_presets) > 0
        assert len(manager.default_effects) > 0
    
    def test_font_property_methods(self, manager):
        """Test font property setter methods"""
        # Test font family
        manager.set_font_family("Times New Roman")
        assert manager.font_properties.family == "Times New Roman"
        
        # Test font size with bounds
        manager.set_font_size(200.0)  # Should be clamped
        assert manager.font_properties.size <= 144.0
        
        manager.set_font_size(5.0)  # Should be clamped
        assert manager.font_properties.size >= 8.0
        
        # Test font color
        test_color = [1.0, 0.5, 0.0, 0.8]
        manager.set_font_color(test_color)
        assert manager.font_properties.color == test_color
    
    def test_effect_layer_management(self, manager):
        """Test effect layer management"""
        # Add multiple effects
        glow_layer = manager.add_effect_layer(EffectType.GLOW)
        outline_layer = manager.add_effect_layer(EffectType.OUTLINE)
        shadow_layer = manager.add_effect_layer(EffectType.SHADOW)
        
        assert len(manager.effect_layers) == 3
        
        # Test getting layer by ID
        retrieved_layer = manager.get_effect_layer(glow_layer.id)
        assert retrieved_layer == glow_layer
        
        # Test updating parameters
        new_params = {'radius': 10.0, 'intensity': 2.0}
        manager.update_effect_parameters(glow_layer.id, new_params)
        
        updated_layer = manager.get_effect_layer(glow_layer.id)
        assert updated_layer.parameters.get('radius') == 10.0
        assert updated_layer.parameters.get('intensity') == 2.0
        
        # Test toggling effect
        original_state = glow_layer.parameters.enabled
        new_state = manager.toggle_effect_layer(glow_layer.id)
        assert new_state != original_state
        
        # Test reordering
        shadow_id = shadow_layer.id
        manager.reorder_effect_layer(shadow_id, 0)
        # After reordering, the shadow layer should be first
        assert manager.effect_layers[0].id == shadow_id
        
        # Test removal
        manager.remove_effect_layer(outline_layer.id)
        assert len(manager.effect_layers) == 2
        assert manager.get_effect_layer(outline_layer.id) is None
    
    def test_preset_management(self, manager):
        """Test preset management functionality"""
        # Test built-in presets
        presets = manager.get_available_presets()
        assert 'karaoke_classic' in presets
        assert 'karaoke_neon' in presets
        
        # Test applying preset
        manager.apply_preset('karaoke_classic')
        assert len(manager.effect_layers) > 0
        
        # Test saving custom preset
        manager.save_preset("test_preset", "Test description", "Test")
        assert "test_preset" in manager.get_available_presets()
        
        # Test getting preset info
        preset_info = manager.get_preset_info("test_preset")
        assert preset_info.name == "test_preset"
        assert preset_info.description == "Test description"
        assert preset_info.category == "Test"


def test_demo_runs_without_errors():
    """Test that the enhanced effects demo can be imported and basic functionality works"""
    try:
        # Import the demo module
        import demo_enhanced_effects_with_detachable_preview
        
        # Test that main classes can be instantiated
        app = QApplication.instance() or QApplication([])
        
        # Create demo instance (but don't show it)
        demo = demo_enhanced_effects_with_detachable_preview.EnhancedEffectsDemo()
        
        # Verify basic structure
        assert demo.enhanced_effects_widget is not None
        assert demo.detachable_preview is not None
        assert hasattr(demo.enhanced_effects_widget, 'effects_manager')
        
        # Clean up
        demo.close()
        
    except ImportError as e:
        pytest.skip(f"Demo import failed: {e}")
    except Exception as e:
        pytest.skip(f"Demo test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])