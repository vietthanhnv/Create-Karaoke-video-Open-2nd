"""
Enhanced Text Effects Widget with Comprehensive Font Styling

This widget provides advanced text styling and effects controls including:
- Font properties (family, size, weight, style, color)
- Visual effects (glow, outline, shadow, gradient, etc.)
- Animation effects (fade, bounce, wave, etc.)
- Advanced effects (neon, fire, ice, metal, glass, rainbow)
- Integration with detachable preview system
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QGroupBox, 
    QSlider, QPushButton, QFrame, QGridLayout, QSpinBox, QColorDialog,
    QDoubleSpinBox, QCheckBox, QComboBox, QListWidgetItem, QScrollArea, 
    QSplitter, QTabWidget, QFontComboBox, QLineEdit, QTextEdit, QSpacerItem,
    QSizePolicy, QButtonGroup, QRadioButton, QProgressBar, QToolButton,
    QMenu, QFileDialog, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPixmap, QPainter, QIcon, QAction
from typing import Dict, List, Optional, Any

try:
    from ..core.enhanced_effects_manager import (
        EnhancedEffectsManager, EffectType, FontWeight, FontStyle, 
        TextAlignment, BlendMode, EffectLayer, EffectParameters
    )
except ImportError:
    from src.core.enhanced_effects_manager import (
        EnhancedEffectsManager, EffectType, FontWeight, FontStyle, 
        TextAlignment, BlendMode, EffectLayer, EffectParameters
    )


class EnhancedEffectsWidget(QWidget):
    """Enhanced effects widget with comprehensive font styling and visual effects"""
    
    # Signals for communication with preview system
    font_properties_changed = pyqtSignal(dict)  # Font properties
    effect_applied = pyqtSignal(str, dict)  # effect_id, parameters
    effect_removed = pyqtSignal(str)  # effect_id
    effect_parameters_changed = pyqtSignal(str, dict)  # effect_id, parameters
    effect_toggled = pyqtSignal(str, bool)  # effect_id, enabled
    preset_applied = pyqtSignal(str)  # preset_name
    
    def __init__(self):
        super().__init__()
        
        # Initialize enhanced effects manager
        self.effects_manager = EnhancedEffectsManager()
        self.current_effect_id = None
        self.parameter_widgets = {}
        
        # Update timer for real-time preview
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._emit_updates)
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the enhanced effects widget UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Enhanced Text Effects")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Create tab widget for organized interface
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Font Properties Tab
        self._create_font_properties_tab()
        
        # Visual Effects Tab
        self._create_visual_effects_tab()
        
        # Animation Effects Tab
        self._create_animation_effects_tab()
        
        # Advanced Effects Tab
        self._create_advanced_effects_tab()
        
        # Presets Tab
        self._create_presets_tab()
        
    def _create_font_properties_tab(self):
        """Create font properties configuration tab"""
        font_tab = QWidget()
        layout = QVBoxLayout(font_tab)
        
        # Font Family
        font_group = QGroupBox("Font Properties")
        font_layout = QGridLayout(font_group)
        
        # Font Family
        font_layout.addWidget(QLabel("Family:"), 0, 0)
        self.font_family_combo = QFontComboBox()
        self.font_family_combo.setCurrentFont(QFont(self.effects_manager.font_properties.family))
        self.font_family_combo.currentFontChanged.connect(self._on_font_family_changed)
        font_layout.addWidget(self.font_family_combo, 0, 1)
        
        # Font Size
        font_layout.addWidget(QLabel("Size:"), 1, 0)
        self.font_size_spin = QDoubleSpinBox()
        self.font_size_spin.setRange(8.0, 144.0)
        self.font_size_spin.setValue(self.effects_manager.font_properties.size)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        font_layout.addWidget(self.font_size_spin, 1, 1)
        
        # Font Weight
        font_layout.addWidget(QLabel("Weight:"), 2, 0)
        self.font_weight_combo = QComboBox()
        for weight in FontWeight:
            self.font_weight_combo.addItem(weight.name.replace('_', ' ').title(), weight)
        self.font_weight_combo.currentTextChanged.connect(self._on_font_weight_changed)
        font_layout.addWidget(self.font_weight_combo, 2, 1)
        
        # Font Style
        font_layout.addWidget(QLabel("Style:"), 3, 0)
        self.font_style_combo = QComboBox()
        for style in FontStyle:
            self.font_style_combo.addItem(style.value.title(), style)
        self.font_style_combo.currentTextChanged.connect(self._on_font_style_changed)
        font_layout.addWidget(self.font_style_combo, 3, 1)
        
        # Font Color
        font_layout.addWidget(QLabel("Color:"), 4, 0)
        self.font_color_button = QPushButton("Choose Color")
        self.font_color_button.clicked.connect(self._choose_font_color)
        self._update_color_button(self.font_color_button, self.effects_manager.font_properties.color)
        font_layout.addWidget(self.font_color_button, 4, 1)
        
        # Text Alignment
        font_layout.addWidget(QLabel("Alignment:"), 5, 0)
        self.alignment_combo = QComboBox()
        for alignment in TextAlignment:
            self.alignment_combo.addItem(alignment.value.title(), alignment)
        self.alignment_combo.currentTextChanged.connect(self._on_alignment_changed)
        font_layout.addWidget(self.alignment_combo, 5, 1)
        
        # Line Spacing
        font_layout.addWidget(QLabel("Line Spacing:"), 6, 0)
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.5, 3.0)
        self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.setValue(self.effects_manager.font_properties.line_spacing)
        self.line_spacing_spin.valueChanged.connect(self._on_line_spacing_changed)
        font_layout.addWidget(self.line_spacing_spin, 6, 1)
        
        # Letter Spacing
        font_layout.addWidget(QLabel("Letter Spacing:"), 7, 0)
        self.letter_spacing_spin = QDoubleSpinBox()
        self.letter_spacing_spin.setRange(-10.0, 10.0)
        self.letter_spacing_spin.setValue(self.effects_manager.font_properties.letter_spacing)
        self.letter_spacing_spin.valueChanged.connect(self._on_letter_spacing_changed)
        font_layout.addWidget(self.letter_spacing_spin, 7, 1)
        
        layout.addWidget(font_group)
        layout.addStretch()
        
        self.tab_widget.addTab(font_tab, "Font")
        
    def _create_visual_effects_tab(self):
        """Create visual effects tab"""
        effects_tab = QWidget()
        layout = QHBoxLayout(effects_tab)
        
        # Left side: Available effects
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Available Effects
        available_group = QGroupBox("Available Effects")
        available_layout = QVBoxLayout(available_group)
        
        self.visual_effects_list = QListWidget()
        visual_effects = [
            ("Glow Effect", EffectType.GLOW),
            ("Outline Effect", EffectType.OUTLINE),
            ("Drop Shadow", EffectType.SHADOW),
            ("Gradient Fill", EffectType.GRADIENT),
            ("Texture Fill", EffectType.TEXTURE)
        ]
        
        for name, effect_type in visual_effects:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, effect_type)
            self.visual_effects_list.addItem(item)
            
        available_layout.addWidget(self.visual_effects_list)
        
        add_effect_btn = QPushButton("Add Effect")
        add_effect_btn.clicked.connect(self._add_visual_effect)
        available_layout.addWidget(add_effect_btn)
        
        left_layout.addWidget(available_group)
        
        # Applied Effects
        applied_group = QGroupBox("Applied Effects")
        applied_layout = QVBoxLayout(applied_group)
        
        self.applied_visual_effects = QListWidget()
        self.applied_visual_effects.currentItemChanged.connect(self._on_visual_effect_selected)
        applied_layout.addWidget(self.applied_visual_effects)
        
        # Effect controls
        controls_layout = QHBoxLayout()
        
        self.remove_visual_btn = QPushButton("Remove")
        self.remove_visual_btn.clicked.connect(self._remove_visual_effect)
        self.remove_visual_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_visual_btn)
        
        self.toggle_visual_btn = QPushButton("Toggle")
        self.toggle_visual_btn.clicked.connect(self._toggle_visual_effect)
        self.toggle_visual_btn.setEnabled(False)
        controls_layout.addWidget(self.toggle_visual_btn)
        
        applied_layout.addLayout(controls_layout)
        left_layout.addWidget(applied_group)
        
        layout.addWidget(left_panel)
        
        # Right side: Effect parameters
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        params_group = QGroupBox("Effect Parameters")
        params_layout = QVBoxLayout(params_group)
        
        # Parameters scroll area
        self.visual_params_scroll = QScrollArea()
        self.visual_params_scroll.setWidgetResizable(True)
        
        self.visual_params_widget = QWidget()
        self.visual_params_layout = QGridLayout(self.visual_params_widget)
        
        # Default message
        default_label = QLabel("Select an effect to adjust parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.visual_params_layout.addWidget(default_label, 0, 0)
        
        self.visual_params_scroll.setWidget(self.visual_params_widget)
        params_layout.addWidget(self.visual_params_scroll)
        
        right_layout.addWidget(params_group)
        layout.addWidget(right_panel)
        
        self.tab_widget.addTab(effects_tab, "Visual Effects")
        
    def _create_animation_effects_tab(self):
        """Create animation effects tab"""
        anim_tab = QWidget()
        layout = QHBoxLayout(anim_tab)
        
        # Similar structure to visual effects but for animations
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Available Animations
        available_group = QGroupBox("Available Animations")
        available_layout = QVBoxLayout(available_group)
        
        self.animation_effects_list = QListWidget()
        animation_effects = [
            ("Fade In/Out", EffectType.FADE),
            ("Bounce", EffectType.BOUNCE),
            ("Wave", EffectType.WAVE),
            ("Typewriter", EffectType.TYPEWRITER),
            ("Zoom", EffectType.ZOOM),
            ("Rotate", EffectType.ROTATE),
            ("Slide", EffectType.SLIDE)
        ]
        
        for name, effect_type in animation_effects:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, effect_type)
            self.animation_effects_list.addItem(item)
            
        available_layout.addWidget(self.animation_effects_list)
        
        add_anim_btn = QPushButton("Add Animation")
        add_anim_btn.clicked.connect(self._add_animation_effect)
        available_layout.addWidget(add_anim_btn)
        
        left_layout.addWidget(available_group)
        
        # Applied Animations
        applied_group = QGroupBox("Applied Animations")
        applied_layout = QVBoxLayout(applied_group)
        
        self.applied_animation_effects = QListWidget()
        self.applied_animation_effects.currentItemChanged.connect(self._on_animation_effect_selected)
        applied_layout.addWidget(self.applied_animation_effects)
        
        # Animation controls
        controls_layout = QHBoxLayout()
        
        self.remove_anim_btn = QPushButton("Remove")
        self.remove_anim_btn.clicked.connect(self._remove_animation_effect)
        self.remove_anim_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_anim_btn)
        
        self.toggle_anim_btn = QPushButton("Toggle")
        self.toggle_anim_btn.clicked.connect(self._toggle_animation_effect)
        self.toggle_anim_btn.setEnabled(False)
        controls_layout.addWidget(self.toggle_anim_btn)
        
        applied_layout.addLayout(controls_layout)
        left_layout.addWidget(applied_group)
        
        layout.addWidget(left_panel)
        
        # Right side: Animation parameters
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        params_group = QGroupBox("Animation Parameters")
        params_layout = QVBoxLayout(params_group)
        
        self.anim_params_scroll = QScrollArea()
        self.anim_params_scroll.setWidgetResizable(True)
        
        self.anim_params_widget = QWidget()
        self.anim_params_layout = QGridLayout(self.anim_params_widget)
        
        # Default message
        default_label = QLabel("Select an animation to adjust parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.anim_params_layout.addWidget(default_label, 0, 0)
        
        self.anim_params_scroll.setWidget(self.anim_params_widget)
        params_layout.addWidget(self.anim_params_scroll)
        
        right_layout.addWidget(params_group)
        layout.addWidget(right_panel)
        
        self.tab_widget.addTab(anim_tab, "Animations")
        
    def _create_advanced_effects_tab(self):
        """Create advanced effects tab"""
        advanced_tab = QWidget()
        layout = QHBoxLayout(advanced_tab)
        
        # Left side: Available advanced effects
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Available Advanced Effects
        available_group = QGroupBox("Advanced Effects")
        available_layout = QVBoxLayout(available_group)
        
        self.advanced_effects_list = QListWidget()
        advanced_effects = [
            ("Neon", EffectType.NEON),
            ("Fire", EffectType.FIRE),
            ("Ice", EffectType.ICE),
            ("Metal", EffectType.METAL),
            ("Glass", EffectType.GLASS),
            ("Rainbow", EffectType.RAINBOW)
        ]
        
        for name, effect_type in advanced_effects:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, effect_type)
            self.advanced_effects_list.addItem(item)
            
        available_layout.addWidget(self.advanced_effects_list)
        
        add_advanced_btn = QPushButton("Add Effect")
        add_advanced_btn.clicked.connect(self._add_advanced_effect)
        available_layout.addWidget(add_advanced_btn)
        
        left_layout.addWidget(available_group)
        
        # Applied Advanced Effects
        applied_group = QGroupBox("Applied Advanced Effects")
        applied_layout = QVBoxLayout(applied_group)
        
        self.applied_advanced_effects = QListWidget()
        self.applied_advanced_effects.currentItemChanged.connect(self._on_advanced_effect_selected)
        applied_layout.addWidget(self.applied_advanced_effects)
        
        # Advanced effect controls
        controls_layout = QHBoxLayout()
        
        self.remove_advanced_btn = QPushButton("Remove")
        self.remove_advanced_btn.clicked.connect(self._remove_advanced_effect)
        self.remove_advanced_btn.setEnabled(False)
        controls_layout.addWidget(self.remove_advanced_btn)
        
        self.toggle_advanced_btn = QPushButton("Toggle")
        self.toggle_advanced_btn.clicked.connect(self._toggle_advanced_effect)
        self.toggle_advanced_btn.setEnabled(False)
        controls_layout.addWidget(self.toggle_advanced_btn)
        
        applied_layout.addLayout(controls_layout)
        left_layout.addWidget(applied_group)
        
        layout.addWidget(left_panel)
        
        # Right side: Advanced effect parameters
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        params_group = QGroupBox("Advanced Parameters")
        params_layout = QVBoxLayout(params_group)
        
        self.advanced_params_scroll = QScrollArea()
        self.advanced_params_scroll.setWidgetResizable(True)
        
        self.advanced_params_widget = QWidget()
        self.advanced_params_layout = QGridLayout(self.advanced_params_widget)
        
        # Default message
        default_label = QLabel("Select an advanced effect to adjust parameters")
        default_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        default_label.setStyleSheet("color: #666; font-style: italic;")
        self.advanced_params_layout.addWidget(default_label, 0, 0)
        
        self.advanced_params_scroll.setWidget(self.advanced_params_widget)
        params_layout.addWidget(self.advanced_params_scroll)
        
        right_layout.addWidget(params_group)
        layout.addWidget(right_panel)
        
        self.tab_widget.addTab(advanced_tab, "Advanced")
        
    def _create_presets_tab(self):
        """Create presets management tab"""
        presets_tab = QWidget()
        layout = QVBoxLayout(presets_tab)
        
        # Presets list
        presets_group = QGroupBox("Effect Presets")
        presets_layout = QVBoxLayout(presets_group)
        
        # Category filter
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Category:"))
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        categories = set()
        for preset in self.effects_manager.effect_presets.values():
            categories.add(preset.category)
        for category in sorted(categories):
            self.category_combo.addItem(category)
        self.category_combo.currentTextChanged.connect(self._filter_presets)
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        
        presets_layout.addLayout(category_layout)
        
        # Presets list
        self.presets_list = QListWidget()
        self._populate_presets_list()
        presets_layout.addWidget(self.presets_list)
        
        # Preset controls
        preset_controls = QHBoxLayout()
        
        apply_preset_btn = QPushButton("Apply Preset")
        apply_preset_btn.clicked.connect(self._apply_preset)
        preset_controls.addWidget(apply_preset_btn)
        
        save_preset_btn = QPushButton("Save Current as Preset")
        save_preset_btn.clicked.connect(self._save_preset)
        preset_controls.addWidget(save_preset_btn)
        
        presets_layout.addLayout(preset_controls)
        
        layout.addWidget(presets_group)
        
        # Preset info
        info_group = QGroupBox("Preset Information")
        info_layout = QVBoxLayout(info_group)
        
        self.preset_info_label = QLabel("Select a preset to see information")
        self.preset_info_label.setWordWrap(True)
        self.preset_info_label.setStyleSheet("padding: 10px;")
        info_layout.addWidget(self.preset_info_label)
        
        layout.addWidget(info_group)
        
        self.presets_list.currentItemChanged.connect(self._on_preset_selected)
        
        self.tab_widget.addTab(presets_tab, "Presets")
        
    def _connect_signals(self):
        """Connect internal signals"""
        pass  # Signals are connected in individual methods
        
    # Font property event handlers
    def _on_font_family_changed(self, font):
        """Handle font family change"""
        self.effects_manager.set_font_family(font.family())
        self._schedule_update()
        
    def _on_font_size_changed(self, size):
        """Handle font size change"""
        self.effects_manager.set_font_size(size)
        self._schedule_update()
        
    def _on_font_weight_changed(self, weight_name):
        """Handle font weight change"""
        weight = self.font_weight_combo.currentData()
        if weight:
            self.effects_manager.set_font_weight(weight)
            self._schedule_update()
            
    def _on_font_style_changed(self, style_name):
        """Handle font style change"""
        style = self.font_style_combo.currentData()
        if style:
            self.effects_manager.set_font_style(style)
            self._schedule_update()
            
    def _choose_font_color(self):
        """Open color dialog for font color"""
        current_color = self.effects_manager.font_properties.color
        qcolor = QColor(int(current_color[0]*255), int(current_color[1]*255), 
                       int(current_color[2]*255), int(current_color[3]*255))
        
        color = QColorDialog.getColor(qcolor, self, "Choose Font Color")
        if color.isValid():
            rgba = [color.red()/255.0, color.green()/255.0, color.blue()/255.0, color.alpha()/255.0]
            self.effects_manager.set_font_color(rgba)
            self._update_color_button(self.font_color_button, rgba)
            self._schedule_update()
            
    def _on_alignment_changed(self, alignment_name):
        """Handle text alignment change"""
        alignment = self.alignment_combo.currentData()
        if alignment:
            self.effects_manager.set_text_alignment(alignment)
            self._schedule_update()
            
    def _on_line_spacing_changed(self, spacing):
        """Handle line spacing change"""
        self.effects_manager.set_line_spacing(spacing)
        self._schedule_update()
        
    def _on_letter_spacing_changed(self, spacing):
        """Handle letter spacing change"""
        self.effects_manager.set_letter_spacing(spacing)
        self._schedule_update()
        
    # Visual effects handlers
    def _add_visual_effect(self):
        """Add selected visual effect"""
        current_item = self.visual_effects_list.currentItem()
        if current_item:
            effect_type = current_item.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.add_effect_layer(effect_type)
            self._refresh_applied_effects()
            self.effect_applied.emit(layer.id, layer.parameters.params)
            self._schedule_update()
            
    def _remove_visual_effect(self):
        """Remove selected visual effect"""
        current_item = self.applied_visual_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.effects_manager.remove_effect_layer(layer_id)
            self._refresh_applied_effects()
            self.effect_removed.emit(layer_id)
            self._schedule_update()
            
    def _toggle_visual_effect(self):
        """Toggle selected visual effect"""
        current_item = self.applied_visual_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.get_effect_layer(layer_id)
            if layer:
                enabled = self.effects_manager.toggle_effect_layer(layer_id)
                self._refresh_applied_effects()
                self.effect_toggled.emit(layer_id, enabled)
                self._schedule_update()
                
    def _on_visual_effect_selected(self, current, previous):
        """Handle visual effect selection"""
        if current:
            layer_id = current.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.get_effect_layer(layer_id)
            if layer:
                self._show_effect_parameters(layer, self.visual_params_layout)
                self.current_effect_id = layer_id
                self.remove_visual_btn.setEnabled(True)
                self.toggle_visual_btn.setEnabled(True)
        else:
            self._clear_parameters(self.visual_params_layout)
            self.remove_visual_btn.setEnabled(False)
            self.toggle_visual_btn.setEnabled(False)
            
    # Animation effects handlers (similar pattern)
    def _add_animation_effect(self):
        """Add selected animation effect"""
        current_item = self.animation_effects_list.currentItem()
        if current_item:
            effect_type = current_item.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.add_effect_layer(effect_type)
            self._refresh_applied_effects()
            self.effect_applied.emit(layer.id, layer.parameters.params)
            self._schedule_update()
            
    def _remove_animation_effect(self):
        """Remove selected animation effect"""
        current_item = self.applied_animation_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.effects_manager.remove_effect_layer(layer_id)
            self._refresh_applied_effects()
            self.effect_removed.emit(layer_id)
            self._schedule_update()
            
    def _toggle_animation_effect(self):
        """Toggle selected animation effect"""
        current_item = self.applied_animation_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            enabled = self.effects_manager.toggle_effect_layer(layer_id)
            self._refresh_applied_effects()
            self.effect_toggled.emit(layer_id, enabled)
            self._schedule_update()
            
    def _on_animation_effect_selected(self, current, previous):
        """Handle animation effect selection"""
        if current:
            layer_id = current.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.get_effect_layer(layer_id)
            if layer:
                self._show_effect_parameters(layer, self.anim_params_layout)
                self.current_effect_id = layer_id
                self.remove_anim_btn.setEnabled(True)
                self.toggle_anim_btn.setEnabled(True)
        else:
            self._clear_parameters(self.anim_params_layout)
            self.remove_anim_btn.setEnabled(False)
            self.toggle_anim_btn.setEnabled(False)
            
    # Advanced effects handlers (similar pattern)
    def _add_advanced_effect(self):
        """Add selected advanced effect"""
        current_item = self.advanced_effects_list.currentItem()
        if current_item:
            effect_type = current_item.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.add_effect_layer(effect_type)
            self._refresh_applied_effects()
            self.effect_applied.emit(layer.id, layer.parameters.params)
            self._schedule_update()
            
    def _remove_advanced_effect(self):
        """Remove selected advanced effect"""
        current_item = self.applied_advanced_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.effects_manager.remove_effect_layer(layer_id)
            self._refresh_applied_effects()
            self.effect_removed.emit(layer_id)
            self._schedule_update()
            
    def _toggle_advanced_effect(self):
        """Toggle selected advanced effect"""
        current_item = self.applied_advanced_effects.currentItem()
        if current_item:
            layer_id = current_item.data(Qt.ItemDataRole.UserRole)
            enabled = self.effects_manager.toggle_effect_layer(layer_id)
            self._refresh_applied_effects()
            self.effect_toggled.emit(layer_id, enabled)
            self._schedule_update()
            
    def _on_advanced_effect_selected(self, current, previous):
        """Handle advanced effect selection"""
        if current:
            layer_id = current.data(Qt.ItemDataRole.UserRole)
            layer = self.effects_manager.get_effect_layer(layer_id)
            if layer:
                self._show_effect_parameters(layer, self.advanced_params_layout)
                self.current_effect_id = layer_id
                self.remove_advanced_btn.setEnabled(True)
                self.toggle_advanced_btn.setEnabled(True)
        else:
            self._clear_parameters(self.advanced_params_layout)
            self.remove_advanced_btn.setEnabled(False)
            self.toggle_advanced_btn.setEnabled(False)
            
    # Preset handlers
    def _populate_presets_list(self):
        """Populate presets list"""
        self.presets_list.clear()
        for preset_name, preset in self.effects_manager.effect_presets.items():
            item = QListWidgetItem(f"{preset.name} ({preset.category})")
            item.setData(Qt.ItemDataRole.UserRole, preset_name)
            self.presets_list.addItem(item)
            
    def _filter_presets(self, category):
        """Filter presets by category"""
        self.presets_list.clear()
        for preset_name, preset in self.effects_manager.effect_presets.items():
            if category == "All Categories" or preset.category == category:
                item = QListWidgetItem(f"{preset.name} ({preset.category})")
                item.setData(Qt.ItemDataRole.UserRole, preset_name)
                self.presets_list.addItem(item)
                
    def _on_preset_selected(self, current, previous):
        """Handle preset selection"""
        if current:
            preset_name = current.data(Qt.ItemDataRole.UserRole)
            preset = self.effects_manager.get_preset_info(preset_name)
            if preset:
                info_text = f"<b>{preset.name}</b><br><br>"
                info_text += f"<b>Category:</b> {preset.category}<br>"
                info_text += f"<b>Description:</b> {preset.description}<br><br>"
                info_text += f"<b>Effects:</b> {len(preset.effect_layers)} layers<br>"
                info_text += f"<b>Font:</b> {preset.font_properties.family} {preset.font_properties.size}pt"
                self.preset_info_label.setText(info_text)
                
    def _apply_preset(self):
        """Apply selected preset"""
        current_item = self.presets_list.currentItem()
        if current_item:
            preset_name = current_item.data(Qt.ItemDataRole.UserRole)
            if self.effects_manager.apply_preset(preset_name):
                self._refresh_all_ui()
                self.preset_applied.emit(preset_name)
                self._schedule_update()
                
    def _save_preset(self):
        """Save current configuration as preset"""
        
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name:
            description, ok = QInputDialog.getText(self, "Save Preset", "Description:")
            if ok:
                self.effects_manager.save_preset(name, description or "Custom preset")
                self._populate_presets_list()
                
    # Utility methods
    def _refresh_applied_effects(self):
        """Refresh all applied effects lists"""
        # Visual effects
        self.applied_visual_effects.clear()
        # Animation effects
        self.applied_animation_effects.clear()
        # Advanced effects
        self.applied_advanced_effects.clear()
        
        for layer in self.effects_manager.effect_layers:
            item_text = layer.name
            if not layer.parameters.enabled:
                item_text += " (Disabled)"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, layer.id)
            
            if not layer.parameters.enabled:
                item.setForeground(QColor(128, 128, 128))
                
            # Add to appropriate list based on effect type
            if layer.effect_type in [EffectType.GLOW, EffectType.OUTLINE, EffectType.SHADOW, EffectType.GRADIENT, EffectType.TEXTURE]:
                self.applied_visual_effects.addItem(item)
            elif layer.effect_type in [EffectType.FADE, EffectType.BOUNCE, EffectType.WAVE, EffectType.TYPEWRITER, EffectType.ZOOM, EffectType.ROTATE, EffectType.SLIDE]:
                self.applied_animation_effects.addItem(item)
            elif layer.effect_type in [EffectType.NEON, EffectType.FIRE, EffectType.ICE, EffectType.METAL, EffectType.GLASS, EffectType.RAINBOW]:
                self.applied_advanced_effects.addItem(item)
                
    def _show_effect_parameters(self, layer: EffectLayer, layout: QGridLayout):
        """Show parameters for an effect layer"""
        self._clear_parameters(layout)
        
        row = 0
        
        # Common parameters
        # Enabled checkbox
        enabled_cb = QCheckBox("Enabled")
        enabled_cb.setChecked(layer.parameters.enabled)
        enabled_cb.toggled.connect(lambda v: self._update_parameter(layer.id, 'enabled', v))
        layout.addWidget(enabled_cb, row, 0, 1, 2)
        row += 1
        
        # Opacity slider
        layout.addWidget(QLabel("Opacity:"), row, 0)
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(0, 100)
        opacity_slider.setValue(int(layer.parameters.opacity * 100))
        opacity_slider.valueChanged.connect(lambda v: self._update_parameter(layer.id, 'opacity', v / 100.0))
        layout.addWidget(opacity_slider, row, 1)
        row += 1
        
        # Effect-specific parameters
        for param_name, param_value in layer.parameters.params.items():
            layout.addWidget(QLabel(f"{param_name.replace('_', ' ').title()}:"), row, 0)
            
            if isinstance(param_value, bool):
                widget = QCheckBox()
                widget.setChecked(param_value)
                widget.toggled.connect(lambda v, p=param_name: self._update_parameter(layer.id, p, v))
            elif isinstance(param_value, (int, float)):
                widget = QDoubleSpinBox()
                widget.setRange(-1000.0, 1000.0)
                widget.setValue(float(param_value))
                widget.valueChanged.connect(lambda v, p=param_name: self._update_parameter(layer.id, p, v))
            elif isinstance(param_value, list) and len(param_value) >= 3:
                # Color parameter
                widget = QPushButton("Choose Color")
                if len(param_value) >= 3:
                    color = QColor(int(param_value[0]*255), int(param_value[1]*255), int(param_value[2]*255))
                    widget.setStyleSheet(f"background-color: {color.name()};")
                widget.clicked.connect(lambda _, p=param_name: self._choose_parameter_color(layer.id, p))
            else:
                widget = QLineEdit(str(param_value))
                widget.textChanged.connect(lambda v, p=param_name: self._update_parameter(layer.id, p, v))
                
            layout.addWidget(widget, row, 1)
            row += 1
            
    def _clear_parameters(self, layout: QGridLayout):
        """Clear parameter widgets from layout"""
        for i in reversed(range(layout.count())):
            child = layout.itemAt(i).widget()
            if child:
                child.setParent(None)
                
    def _update_parameter(self, layer_id: str, param_name: str, value):
        """Update effect parameter"""
        layer = self.effects_manager.get_effect_layer(layer_id)
        if layer:
            if param_name == 'enabled':
                layer.parameters.enabled = value
            elif param_name == 'opacity':
                layer.parameters.opacity = value
            else:
                layer.parameters.set(param_name, value)
            
            self.effect_parameters_changed.emit(layer_id, layer.parameters.params)
            self._schedule_update()
            
    def _choose_parameter_color(self, layer_id: str, param_name: str):
        """Choose color for parameter"""
        layer = self.effects_manager.get_effect_layer(layer_id)
        if layer:
            current_color = layer.parameters.get(param_name, [1.0, 1.0, 1.0, 1.0])
            qcolor = QColor(int(current_color[0]*255), int(current_color[1]*255), 
                           int(current_color[2]*255), int(current_color[3]*255) if len(current_color) > 3 else 255)
            
            color = QColorDialog.getColor(qcolor, self)
            if color.isValid():
                rgba = [color.red()/255.0, color.green()/255.0, color.blue()/255.0, color.alpha()/255.0]
                self._update_parameter(layer_id, param_name, rgba)
                
                # Update button color
                sender = self.sender()
                sender.setStyleSheet(f"background-color: {color.name()};")
                
    def _update_color_button(self, button: QPushButton, color: List[float]):
        """Update color button appearance"""
        if len(color) >= 3:
            qcolor = QColor(int(color[0]*255), int(color[1]*255), int(color[2]*255))
            button.setStyleSheet(f"background-color: {qcolor.name()};")
            
    def _refresh_all_ui(self):
        """Refresh all UI elements to match current state"""
        # Update font properties
        self.font_family_combo.setCurrentFont(QFont(self.effects_manager.font_properties.family))
        self.font_size_spin.setValue(self.effects_manager.font_properties.size)
        
        # Update font weight combo
        for i in range(self.font_weight_combo.count()):
            if self.font_weight_combo.itemData(i) == self.effects_manager.font_properties.weight:
                self.font_weight_combo.setCurrentIndex(i)
                break
                
        # Update font style combo
        for i in range(self.font_style_combo.count()):
            if self.font_style_combo.itemData(i) == self.effects_manager.font_properties.style:
                self.font_style_combo.setCurrentIndex(i)
                break
                
        # Update alignment combo
        for i in range(self.alignment_combo.count()):
            if self.alignment_combo.itemData(i) == self.effects_manager.font_properties.alignment:
                self.alignment_combo.setCurrentIndex(i)
                break
                
        self.line_spacing_spin.setValue(self.effects_manager.font_properties.line_spacing)
        self.letter_spacing_spin.setValue(self.effects_manager.font_properties.letter_spacing)
        self._update_color_button(self.font_color_button, self.effects_manager.font_properties.color)
        
        # Refresh effects lists
        self._refresh_applied_effects()
        
    def _schedule_update(self):
        """Schedule update to preview system"""
        self.update_timer.start(100)  # 100ms delay for debouncing
        
    def _emit_updates(self):
        """Emit updates to preview system"""
        # Emit font properties change
        self.font_properties_changed.emit(self.effects_manager.font_properties.to_dict())
        
        # Emit effect updates for all active effects
        for layer in self.effects_manager.effect_layers:
            if layer.parameters.enabled:
                self.effect_parameters_changed.emit(layer.id, layer.parameters.params)
                
    # Public interface methods
    def load_project(self, project):
        """Load project configuration"""
        # Reset to defaults
        self.effects_manager = EnhancedEffectsManager()
        self._refresh_all_ui()
        
    def get_effects_manager(self) -> EnhancedEffectsManager:
        """Get the effects manager instance"""
        return self.effects_manager
        
    def apply_preset_by_name(self, preset_name: str) -> bool:
        """Apply preset by name (for external use)"""
        return self.effects_manager.apply_preset(preset_name)