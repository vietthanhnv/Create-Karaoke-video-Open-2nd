"""
Text Effects Widget for Applying and Customizing Subtitle Effects
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QGroupBox, QSlider, QPushButton,
    QFrame, QGridLayout, QSpinBox, QColorDialog,
    QDoubleSpinBox, QCheckBox, QComboBox, QListWidgetItem,
    QScrollArea, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter

try:
    from ..core.effects_manager import EffectsManager, EffectType, EffectLayer
except ImportError:
    from src.core.effects_manager import EffectsManager, EffectType, EffectLayer


class EffectsWidget(QWidget):
    """Widget for applying and customizing text effects with real-time preview"""
    
    # Effect signals
    effect_applied = pyqtSignal(str, dict)  # effect_id, parameters
    effect_removed = pyqtSignal(str)  # effect_id
    effect_parameters_changed = pyqtSignal(str, dict)  # effect_id, parameters
    effect_reordered = pyqtSignal(str, int)  # effect_id, new_order
    effect_toggled = pyqtSignal(str, bool)  # effect_id, enabled
    preset_applied = pyqtSignal(str)  # preset_name
    
    def __init__(self):
        super().__init__()
        self.effects_manager = EffectsManager()
        self.current_effect_id = None
        self.parameter_widgets = {}
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the effects widget UI"""
        layout = QHBoxLayout(self)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Effects library and applied effects
        self._create_effects_library(splitter)
        
        # Right panel - Effect parameters and preview
        self._create_parameters_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([300, 500])
        layout.addWidget(splitter)
        
    def _create_effects_library(self, parent_widget):
        """Create effects library panel"""
        library_frame = QFrame()
        library_layout = QVBoxLayout(library_frame)
        
        # Title
        title = QLabel("Text Effects")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        library_layout.addWidget(title)
        
        # Presets section
        presets_group = QGroupBox("Effect Presets")
        presets_layout = QVBoxLayout(presets_group)
        
        self.presets_combo = QComboBox()
        self.presets_combo.addItem("Select Preset...")
        for preset_name in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_name)
            self.presets_combo.addItem(preset_info.name, preset_name)
        self.presets_combo.currentTextChanged.connect(self._on_preset_selected)
        presets_layout.addWidget(self.presets_combo)
        
        library_layout.addWidget(presets_group)
        
        # Available effects list
        effects_group = QGroupBox("Available Effects")
        effects_layout = QVBoxLayout(effects_group)
        
        self.effects_list = QListWidget()
        effect_items = [
            ("Glow Effect", EffectType.GLOW.value),
            ("Outline Effect", EffectType.OUTLINE.value),
            ("Shadow Effect", EffectType.SHADOW.value),
            ("Fade In/Out", EffectType.FADE.value),
            ("Bounce Animation", EffectType.BOUNCE.value),
            ("Color Transition", EffectType.COLOR_TRANSITION.value),
            ("Wave Animation", EffectType.WAVE.value)
        ]
        
        for display_name, effect_type in effect_items:
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, effect_type)
            self.effects_list.addItem(item)
        
        self.effects_list.currentItemChanged.connect(self._on_available_effect_selected)
        effects_layout.addWidget(self.effects_list)
        
        # Add effect button
        self.add_effect_button = QPushButton("Add Effect")
        self.add_effect_button.clicked.connect(self._add_effect)
        self.add_effect_button.setEnabled(False)
        effects_layout.addWidget(self.add_effect_button)
        
        library_layout.addWidget(effects_group)
        
        # Applied effects list with ordering
        applied_group = QGroupBox("Applied Effects (Render Order)")
        applied_layout = QVBoxLayout(applied_group)
        
        self.applied_effects_list = QListWidget()
        self.applied_effects_list.currentItemChanged.connect(self._on_applied_effect_selected)
        applied_layout.addWidget(self.applied_effects_list)
        
        # Effect control buttons
        buttons_layout = QGridLayout()
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_effect)
        self.remove_button.setEnabled(False)
        buttons_layout.addWidget(self.remove_button, 0, 0)
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(self._move_effect_up)
        self.move_up_button.setEnabled(False)
        buttons_layout.addWidget(self.move_up_button, 0, 1)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(self._move_effect_down)
        self.move_down_button.setEnabled(False)
        buttons_layout.addWidget(self.move_down_button, 1, 1)
        
        self.toggle_button = QPushButton("Toggle")
        self.toggle_button.clicked.connect(self._toggle_effect)
        self.toggle_button.setEnabled(False)
        buttons_layout.addWidget(self.toggle_button, 1, 0)
        
        applied_layout.addLayout(buttons_layout)
        library_layout.addWidget(applied_group)
        
        parent_widget.addWidget(library_frame)
        
    def _create_parameters_panel(self, parent_widget):
        """Create effect parameters adjustment panel"""
        params_frame = QFrame()
        params_layout = QVBoxLayout(params_frame)
        
        # Title
        title = QLabel("Effect Parameters")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        params_layout.addWidget(title)
        
        # Parameters scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.params_container = QGroupBox("No Effect Selected")
        self.params_layout = QGridLayout(self.params_container)
        
        # Default message
        default_label = QLabel("Select an applied effect to adjust its parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.params_layout.addWidget(default_label, 0, 0, 1, 2)
        
        scroll_area.setWidget(self.params_container)
        params_layout.addWidget(scroll_area)
        
        # Note: Real-time preview removed - effects are shown directly in the main video preview
        
        parent_widget.addWidget(params_frame)
        
    def _on_available_effect_selected(self, current, previous):
        """Handle effect selection from available effects library"""
        self.add_effect_button.setEnabled(current is not None)
    
    def _on_applied_effect_selected(self, current, previous):
        """Handle selection of applied effect for parameter editing"""
        if current is None:
            self.current_effect_id = None
            self._clear_parameters()
            self._update_effect_buttons()
            return
        
        effect_id = current.data(Qt.ItemDataRole.UserRole)
        self.current_effect_id = effect_id
        
        # Get effect layer from manager
        layer = self.effects_manager.get_effect_layer(effect_id)
        if layer:
            self._show_effect_parameters(layer)
        
        self._update_effect_buttons()
    
    def _on_preset_selected(self, preset_display_name):
        """Handle preset selection"""
        if preset_display_name == "Select Preset...":
            return
        
        # Find preset by display name
        for preset_key in self.effects_manager.get_available_presets():
            preset_info = self.effects_manager.get_preset_info(preset_key)
            if preset_info.name == preset_display_name:
                self.effects_manager.apply_preset(preset_key)
                self._refresh_applied_effects()
                self.preset_applied.emit(preset_key)
                self._schedule_preview_update()
                break
    
    def _add_effect(self):
        """Add selected effect to applied effects"""
        current_item = self.effects_list.currentItem()
        if not current_item:
            return
        
        effect_type = current_item.data(Qt.ItemDataRole.UserRole)
        effect_enum = EffectType(effect_type)
        
        # Create effect with default parameters
        effect = self.effects_manager.create_effect(effect_enum, {})
        layer = self.effects_manager.add_effect_layer(effect)
        
        self._refresh_applied_effects()
        self.effect_applied.emit(effect.id, effect.parameters)
        self._schedule_preview_update()
    
    def _remove_effect(self):
        """Remove selected applied effect"""
        if not self.current_effect_id:
            return
        
        self.effects_manager.remove_effect_layer(self.current_effect_id)
        self._refresh_applied_effects()
        self.effect_removed.emit(self.current_effect_id)
        self.current_effect_id = None
        self._clear_parameters()
        self._schedule_preview_update()
    
    def _move_effect_up(self):
        """Move selected effect up in render order"""
        if not self.current_effect_id:
            return
        
        layer = self.effects_manager.get_effect_layer(self.current_effect_id)
        if layer and layer.order > 0:
            new_order = layer.order - 1
            self.effects_manager.reorder_effect_layer(self.current_effect_id, new_order)
            self._refresh_applied_effects()
            self.effect_reordered.emit(self.current_effect_id, new_order)
    
    def _move_effect_down(self):
        """Move selected effect down in render order"""
        if not self.current_effect_id:
            return
        
        layer = self.effects_manager.get_effect_layer(self.current_effect_id)
        max_order = len(self.effects_manager.effect_layers) - 1
        if layer and layer.order < max_order:
            new_order = layer.order + 1
            self.effects_manager.reorder_effect_layer(self.current_effect_id, new_order)
            self._refresh_applied_effects()
            self.effect_reordered.emit(self.current_effect_id, new_order)
    
    def _toggle_effect(self):
        """Toggle selected effect on/off"""
        if not self.current_effect_id:
            return
        
        layer = self.effects_manager.get_effect_layer(self.current_effect_id)
        if layer:
            new_state = not layer.enabled
            self.effects_manager.toggle_effect_layer(self.current_effect_id, new_state)
            self._refresh_applied_effects()
            self.effect_toggled.emit(self.current_effect_id, new_state)
            self._schedule_preview_update()
    
    def _refresh_applied_effects(self):
        """Refresh the applied effects list"""
        self.applied_effects_list.clear()
        
        for layer in self.effects_manager.effect_layers:
            item_text = f"{layer.effect.name}"
            if not layer.enabled:
                item_text += " (Disabled)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, layer.effect.id)
            
            # Visual indication of disabled effects
            if not layer.enabled:
                item.setForeground(QColor(128, 128, 128))
            
            self.applied_effects_list.addItem(item)
    
    def _update_effect_buttons(self):
        """Update effect control button states"""
        has_selection = self.current_effect_id is not None
        
        self.remove_button.setEnabled(has_selection)
        self.toggle_button.setEnabled(has_selection)
        
        if has_selection:
            layer = self.effects_manager.get_effect_layer(self.current_effect_id)
            if layer:
                self.move_up_button.setEnabled(layer.order > 0)
                self.move_down_button.setEnabled(layer.order < len(self.effects_manager.effect_layers) - 1)
            else:
                self.move_up_button.setEnabled(False)
                self.move_down_button.setEnabled(False)
        else:
            self.move_up_button.setEnabled(False)
            self.move_down_button.setEnabled(False)
    
    def _show_effect_parameters(self, layer: EffectLayer):
        """Show parameters for selected effect layer"""
        self._clear_parameters()
        
        effect = layer.effect
        self.params_container.setTitle(f"{effect.name} Parameters")
        
        # Add effect-specific parameters
        if effect.type == EffectType.GLOW.value:
            self._add_glow_parameters(effect.parameters)
        elif effect.type == EffectType.OUTLINE.value:
            self._add_outline_parameters(effect.parameters)
        elif effect.type == EffectType.SHADOW.value:
            self._add_shadow_parameters(effect.parameters)
        elif effect.type == EffectType.FADE.value:
            self._add_fade_parameters(effect.parameters)
        elif effect.type == EffectType.BOUNCE.value:
            self._add_bounce_parameters(effect.parameters)
        elif effect.type == EffectType.COLOR_TRANSITION.value:
            self._add_color_transition_parameters(effect.parameters)
        elif effect.type == EffectType.WAVE.value:
            self._add_wave_parameters(effect.parameters)
        else:
            self._add_generic_parameters()
    
    def _clear_parameters(self):
        """Clear all parameter widgets"""
        for i in reversed(range(self.params_layout.count())):
            child = self.params_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.parameter_widgets.clear()
        self.params_container.setTitle("No Effect Selected")
    
    def _add_glow_parameters(self, parameters: dict):
        """Add glow effect parameters"""
        row = 0
        
        # Glow radius
        self.params_layout.addWidget(QLabel("Radius:"), row, 0)
        radius_spin = QDoubleSpinBox()
        radius_spin.setRange(0.1, 50.0)
        radius_spin.setValue(parameters.get('radius', 5.0))
        radius_spin.valueChanged.connect(lambda v: self._update_parameter('radius', v))
        self.parameter_widgets['radius'] = radius_spin
        self.params_layout.addWidget(radius_spin, row, 1)
        row += 1
        
        # Intensity
        self.params_layout.addWidget(QLabel("Intensity:"), row, 0)
        intensity_spin = QDoubleSpinBox()
        intensity_spin.setRange(0.0, 2.0)
        intensity_spin.setSingleStep(0.1)
        intensity_spin.setValue(parameters.get('intensity', 0.8))
        intensity_spin.valueChanged.connect(lambda v: self._update_parameter('intensity', v))
        self.parameter_widgets['intensity'] = intensity_spin
        self.params_layout.addWidget(intensity_spin, row, 1)
        row += 1
        
        # Glow color
        self.params_layout.addWidget(QLabel("Color:"), row, 0)
        color_button = QPushButton("Choose Color")
        color = parameters.get('color', [1.0, 1.0, 0.0])
        color_button.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});")
        color_button.clicked.connect(lambda: self._choose_color('color'))
        self.parameter_widgets['color'] = color_button
        self.params_layout.addWidget(color_button, row, 1)
        row += 1
        
        # Falloff
        self.params_layout.addWidget(QLabel("Falloff:"), row, 0)
        falloff_spin = QDoubleSpinBox()
        falloff_spin.setRange(0.1, 10.0)
        falloff_spin.setValue(parameters.get('falloff', 2.0))
        falloff_spin.valueChanged.connect(lambda v: self._update_parameter('falloff', v))
        self.parameter_widgets['falloff'] = falloff_spin
        self.params_layout.addWidget(falloff_spin, row, 1)
    
    def _add_outline_parameters(self, parameters: dict):
        """Add outline effect parameters"""
        row = 0
        
        # Outline width
        self.params_layout.addWidget(QLabel("Width:"), row, 0)
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.1, 20.0)
        width_spin.setValue(parameters.get('width', 2.0))
        width_spin.valueChanged.connect(lambda v: self._update_parameter('width', v))
        self.parameter_widgets['width'] = width_spin
        self.params_layout.addWidget(width_spin, row, 1)
        row += 1
        
        # Outline color
        self.params_layout.addWidget(QLabel("Color:"), row, 0)
        color_button = QPushButton("Choose Color")
        color = parameters.get('color', [0.0, 0.0, 0.0])
        color_button.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});")
        color_button.clicked.connect(lambda: self._choose_color('color'))
        self.parameter_widgets['color'] = color_button
        self.params_layout.addWidget(color_button, row, 1)
        row += 1
        
        # Softness
        self.params_layout.addWidget(QLabel("Softness:"), row, 0)
        softness_spin = QDoubleSpinBox()
        softness_spin.setRange(0.0, 2.0)
        softness_spin.setSingleStep(0.1)
        softness_spin.setValue(parameters.get('softness', 0.5))
        softness_spin.valueChanged.connect(lambda v: self._update_parameter('softness', v))
        self.parameter_widgets['softness'] = softness_spin
        self.params_layout.addWidget(softness_spin, row, 1)
    
    def _add_shadow_parameters(self, parameters: dict):
        """Add shadow effect parameters"""
        row = 0
        
        # Shadow offset X
        self.params_layout.addWidget(QLabel("Offset X:"), row, 0)
        offset_x_spin = QDoubleSpinBox()
        offset_x_spin.setRange(-50.0, 50.0)
        offset_x_spin.setValue(parameters.get('offset_x', 3.0))
        offset_x_spin.valueChanged.connect(lambda v: self._update_parameter('offset_x', v))
        self.parameter_widgets['offset_x'] = offset_x_spin
        self.params_layout.addWidget(offset_x_spin, row, 1)
        row += 1
        
        # Shadow offset Y
        self.params_layout.addWidget(QLabel("Offset Y:"), row, 0)
        offset_y_spin = QDoubleSpinBox()
        offset_y_spin.setRange(-50.0, 50.0)
        offset_y_spin.setValue(parameters.get('offset_y', 3.0))
        offset_y_spin.valueChanged.connect(lambda v: self._update_parameter('offset_y', v))
        self.parameter_widgets['offset_y'] = offset_y_spin
        self.params_layout.addWidget(offset_y_spin, row, 1)
        row += 1
        
        # Blur radius
        self.params_layout.addWidget(QLabel("Blur Radius:"), row, 0)
        blur_spin = QDoubleSpinBox()
        blur_spin.setRange(0.0, 20.0)
        blur_spin.setValue(parameters.get('blur_radius', 2.0))
        blur_spin.valueChanged.connect(lambda v: self._update_parameter('blur_radius', v))
        self.parameter_widgets['blur_radius'] = blur_spin
        self.params_layout.addWidget(blur_spin, row, 1)
        row += 1
        
        # Shadow color
        self.params_layout.addWidget(QLabel("Color:"), row, 0)
        color_button = QPushButton("Choose Color")
        color = parameters.get('color', [0.0, 0.0, 0.0])
        color_button.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});")
        color_button.clicked.connect(lambda: self._choose_color('color'))
        self.parameter_widgets['color'] = color_button
        self.params_layout.addWidget(color_button, row, 1)
        row += 1
        
        # Opacity
        self.params_layout.addWidget(QLabel("Opacity:"), row, 0)
        opacity_spin = QDoubleSpinBox()
        opacity_spin.setRange(0.0, 1.0)
        opacity_spin.setSingleStep(0.1)
        opacity_spin.setValue(parameters.get('opacity', 0.7))
        opacity_spin.valueChanged.connect(lambda v: self._update_parameter('opacity', v))
        self.parameter_widgets['opacity'] = opacity_spin
        self.params_layout.addWidget(opacity_spin, row, 1)
    
    def _add_fade_parameters(self, parameters: dict):
        """Add fade effect parameters"""
        row = 0
        
        # Fade in duration
        self.params_layout.addWidget(QLabel("Fade In Duration:"), row, 0)
        fade_in_spin = QDoubleSpinBox()
        fade_in_spin.setRange(0.0, 5.0)
        fade_in_spin.setSingleStep(0.1)
        fade_in_spin.setValue(parameters.get('fade_in_duration', 0.5))
        fade_in_spin.valueChanged.connect(lambda v: self._update_parameter('fade_in_duration', v))
        self.parameter_widgets['fade_in_duration'] = fade_in_spin
        self.params_layout.addWidget(fade_in_spin, row, 1)
        row += 1
        
        # Fade out duration
        self.params_layout.addWidget(QLabel("Fade Out Duration:"), row, 0)
        fade_out_spin = QDoubleSpinBox()
        fade_out_spin.setRange(0.0, 5.0)
        fade_out_spin.setSingleStep(0.1)
        fade_out_spin.setValue(parameters.get('fade_out_duration', 0.5))
        fade_out_spin.valueChanged.connect(lambda v: self._update_parameter('fade_out_duration', v))
        self.parameter_widgets['fade_out_duration'] = fade_out_spin
        self.params_layout.addWidget(fade_out_spin, row, 1)
    
    def _add_bounce_parameters(self, parameters: dict):
        """Add bounce animation parameters"""
        row = 0
        
        # Amplitude
        self.params_layout.addWidget(QLabel("Amplitude:"), row, 0)
        amplitude_spin = QDoubleSpinBox()
        amplitude_spin.setRange(0.0, 50.0)
        amplitude_spin.setValue(parameters.get('amplitude', 10.0))
        amplitude_spin.valueChanged.connect(lambda v: self._update_parameter('amplitude', v))
        self.parameter_widgets['amplitude'] = amplitude_spin
        self.params_layout.addWidget(amplitude_spin, row, 1)
        row += 1
        
        # Frequency
        self.params_layout.addWidget(QLabel("Frequency:"), row, 0)
        frequency_spin = QDoubleSpinBox()
        frequency_spin.setRange(0.1, 10.0)
        frequency_spin.setValue(parameters.get('frequency', 2.0))
        frequency_spin.valueChanged.connect(lambda v: self._update_parameter('frequency', v))
        self.parameter_widgets['frequency'] = frequency_spin
        self.params_layout.addWidget(frequency_spin, row, 1)
    
    def _add_color_transition_parameters(self, parameters: dict):
        """Add color transition parameters"""
        row = 0
        
        # Start color
        self.params_layout.addWidget(QLabel("Start Color:"), row, 0)
        start_color_button = QPushButton("Choose Color")
        color = parameters.get('start_color', [1.0, 1.0, 1.0])
        start_color_button.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});")
        start_color_button.clicked.connect(lambda: self._choose_color('start_color'))
        self.parameter_widgets['start_color'] = start_color_button
        self.params_layout.addWidget(start_color_button, row, 1)
        row += 1
        
        # End color
        self.params_layout.addWidget(QLabel("End Color:"), row, 0)
        end_color_button = QPushButton("Choose Color")
        color = parameters.get('end_color', [1.0, 0.0, 0.0])
        end_color_button.setStyleSheet(f"background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});")
        end_color_button.clicked.connect(lambda: self._choose_color('end_color'))
        self.parameter_widgets['end_color'] = end_color_button
        self.params_layout.addWidget(end_color_button, row, 1)
        row += 1
        
        # Duration
        self.params_layout.addWidget(QLabel("Duration:"), row, 0)
        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(0.1, 10.0)
        duration_spin.setValue(parameters.get('duration', 2.0))
        duration_spin.valueChanged.connect(lambda v: self._update_parameter('duration', v))
        self.parameter_widgets['duration'] = duration_spin
        self.params_layout.addWidget(duration_spin, row, 1)
    
    def _add_wave_parameters(self, parameters: dict):
        """Add wave animation parameters"""
        row = 0
        
        # Amplitude
        self.params_layout.addWidget(QLabel("Amplitude:"), row, 0)
        amplitude_spin = QDoubleSpinBox()
        amplitude_spin.setRange(0.0, 30.0)
        amplitude_spin.setValue(parameters.get('amplitude', 5.0))
        amplitude_spin.valueChanged.connect(lambda v: self._update_parameter('amplitude', v))
        self.parameter_widgets['amplitude'] = amplitude_spin
        self.params_layout.addWidget(amplitude_spin, row, 1)
        row += 1
        
        # Frequency
        self.params_layout.addWidget(QLabel("Frequency:"), row, 0)
        frequency_spin = QDoubleSpinBox()
        frequency_spin.setRange(0.1, 5.0)
        frequency_spin.setValue(parameters.get('frequency', 1.0))
        frequency_spin.valueChanged.connect(lambda v: self._update_parameter('frequency', v))
        self.parameter_widgets['frequency'] = frequency_spin
        self.params_layout.addWidget(frequency_spin, row, 1)
    
    def _add_generic_parameters(self):
        """Add generic message for unsupported effects"""
        label = QLabel("This effect type is not yet fully implemented")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #666; font-style: italic;")
        self.params_layout.addWidget(label, 0, 0, 1, 2)
    
    def _update_parameter(self, param_name: str, value):
        """Update a parameter value and emit signal"""
        if not self.current_effect_id:
            return
        
        self.effects_manager.update_effect_parameters(self.current_effect_id, {param_name: value})
        
        # Get updated parameters
        layer = self.effects_manager.get_effect_layer(self.current_effect_id)
        if layer:
            self.effect_parameters_changed.emit(self.current_effect_id, layer.effect.parameters)
        self._schedule_preview_update()
    
    def _choose_color(self, param_name: str):
        """Open color chooser dialog for a parameter"""
        color = QColorDialog.getColor(QColor(255, 255, 255), self)
        if color.isValid():
            # Convert to normalized RGB values
            rgb_values = [color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0]
            
            # Update button color
            sender = self.sender()
            sender.setStyleSheet(f"background-color: {color.name()};")
            
            # Update parameter
            self._update_parameter(param_name, rgb_values)
    
    def _schedule_preview_update(self):
        """Schedule a preview update with debouncing - now updates main video preview"""
        self.preview_timer.start(300)  # 300ms delay
    
    def _update_preview(self):
        """Update the main video preview with current effects"""
        # Effects are now applied directly to the main video preview
        # This method triggers a refresh of the main preview
        
        # Get active effects from effects manager
        active_effects = self.effects_manager.get_active_effects()
        
        # Emit signal to update main preview with current effects
        # The main preview will handle rendering the effects
        for layer in active_effects:
            if layer.enabled:
                self.effect_parameters_changed.emit(layer.effect.id, layer.effect.parameters)
    
    def _render_preview_with_effects(self, text: str, effects: list):
        """Render preview text with applied effects - now handled by main preview"""
        # This method is no longer needed as effects are rendered in the main video preview
        # All effect rendering is handled by the OpenGL subtitle renderer
        pass
    
    def load_project(self, project):
        """Load a project into the effects widget"""
        # This method can be called when a project is loaded
        # to initialize effects from the project
        
        # Reset effects manager for new project
        self.effects_manager = EffectsManager()
        self._refresh_applied_effects()
        
        # No longer update preview here - effects are handled by main video preview
    
    # Public methods for external control
    def get_effects_manager(self) -> EffectsManager:
        """Get the effects manager instance"""
        return self.effects_manager
    
    def refresh_ui(self):
        """Refresh the entire UI state"""
        self._refresh_applied_effects()
        self._update_effect_buttons()
        self._update_preview()