#!/usr/bin/env python3
"""
Demonstration of the Text Effects System for Karaoke Video Creator.

This script demonstrates the key features of the text effects system:
- Effect creation and management
- Shader generation
- Effect layering and ordering
- Parameter adjustment
- Preset application
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.effects_manager import EffectsManager, EffectType
from core.opengl_subtitle_renderer import OpenGLSubtitleRenderer


def demonstrate_effects_system():
    """Demonstrate the text effects system capabilities."""
    print("=== Karaoke Video Creator - Text Effects System Demo ===\n")
    
    # Initialize the effects system
    print("1. Initializing Effects System...")
    effects_manager = EffectsManager()
    renderer = OpenGLSubtitleRenderer()
    
    print(f"   - Effects Manager initialized with {len(effects_manager.default_effects)} default effect types")
    print(f"   - Available presets: {', '.join(effects_manager.get_available_presets())}")
    print()
    
    # Demonstrate effect creation
    print("2. Creating Individual Effects...")
    
    # Create glow effect
    glow_effect = effects_manager.create_effect(EffectType.GLOW, {
        'radius': 8.0,
        'intensity': 0.9,
        'color': [1.0, 1.0, 0.0],  # Yellow
        'falloff': 2.0
    })
    glow_layer = effects_manager.add_effect_layer(glow_effect, order=2)
    print(f"   - Created Glow Effect: radius={glow_effect.parameters['radius']}, color=yellow")
    
    # Create outline effect
    outline_effect = effects_manager.create_effect(EffectType.OUTLINE, {
        'width': 3.0,
        'color': [0.0, 0.0, 0.0],  # Black
        'softness': 0.3
    })
    outline_layer = effects_manager.add_effect_layer(outline_effect, order=1)
    print(f"   - Created Outline Effect: width={outline_effect.parameters['width']}, color=black")
    
    # Create shadow effect
    shadow_effect = effects_manager.create_effect(EffectType.SHADOW, {
        'offset_x': 4.0,
        'offset_y': 4.0,
        'blur_radius': 2.0,
        'color': [0.2, 0.2, 0.2],  # Dark gray
        'opacity': 0.8
    })
    shadow_layer = effects_manager.add_effect_layer(shadow_effect, order=0)
    print(f"   - Created Shadow Effect: offset=({shadow_effect.parameters['offset_x']}, {shadow_effect.parameters['offset_y']})")
    
    # Create bounce animation
    bounce_effect = effects_manager.create_effect(EffectType.BOUNCE, {
        'amplitude': 12.0,
        'frequency': 2.0,
        'damping': 0.8
    })
    bounce_layer = effects_manager.add_effect_layer(bounce_effect, order=3)
    print(f"   - Created Bounce Animation: amplitude={bounce_effect.parameters['amplitude']}")
    print()
    
    # Demonstrate effect layering
    print("3. Effect Layering and Ordering...")
    active_effects = effects_manager.get_active_effects()
    print(f"   - Total effects: {len(active_effects)}")
    print("   - Render order (bottom to top):")
    for i, layer in enumerate(active_effects):
        print(f"     {i+1}. {layer.effect.name} (order: {layer.order})")
    print()
    
    # Demonstrate shader generation
    print("4. Generating OpenGL Shaders...")
    vertex_shader, fragment_shader = effects_manager.generate_shader_code()
    
    print(f"   - Vertex shader: {len(vertex_shader)} characters")
    print(f"   - Fragment shader: {len(fragment_shader)} characters")
    
    # Show shader features
    shader_features = []
    if 'glow' in fragment_shader.lower():
        shader_features.append("Glow effects")
    if 'outline' in fragment_shader.lower():
        shader_features.append("Outline effects")
    if 'shadow' in fragment_shader.lower():
        shader_features.append("Shadow effects")
    if 'bounce' in vertex_shader.lower():
        shader_features.append("Bounce animation")
    
    print(f"   - Shader includes: {', '.join(shader_features)}")
    print()
    
    # Demonstrate uniform generation
    print("5. Generating Shader Uniforms...")
    uniforms = effects_manager.get_effect_uniforms()
    
    print(f"   - Total uniforms: {len(uniforms)}")
    print("   - Key uniforms:")
    for key, value in list(uniforms.items())[:8]:  # Show first 8
        if isinstance(value, list):
            value_str = f"[{', '.join(f'{v:.1f}' for v in value)}]"
        elif isinstance(value, float):
            value_str = f"{value:.1f}"
        else:
            value_str = str(value)
        print(f"     {key}: {value_str}")
    print()
    
    # Demonstrate parameter updates
    print("6. Updating Effect Parameters...")
    
    # Update glow radius
    old_radius = glow_effect.parameters['radius']
    effects_manager.update_effect_parameters(glow_effect.id, {'radius': 12.0})
    new_radius = glow_effect.parameters['radius']
    print(f"   - Updated glow radius: {old_radius} → {new_radius}")
    
    # Update shadow offset
    old_offset = (shadow_effect.parameters['offset_x'], shadow_effect.parameters['offset_y'])
    effects_manager.update_effect_parameters(shadow_effect.id, {'offset_x': 6.0, 'offset_y': 6.0})
    new_offset = (shadow_effect.parameters['offset_x'], shadow_effect.parameters['offset_y'])
    print(f"   - Updated shadow offset: {old_offset} → {new_offset}")
    print()
    
    # Demonstrate effect reordering
    print("7. Reordering Effects...")
    print("   - Moving glow effect to first position...")
    
    effects_manager.reorder_effect_layer(glow_effect.id, 0)
    reordered_effects = effects_manager.get_active_effects()
    
    print("   - New render order:")
    for i, layer in enumerate(reordered_effects):
        print(f"     {i+1}. {layer.effect.name} (order: {layer.order})")
    print()
    
    # Demonstrate effect toggling
    print("8. Toggling Effects...")
    
    # Disable outline effect
    effects_manager.toggle_effect_layer(outline_effect.id, False)
    active_after_toggle = effects_manager.get_active_effects()
    
    print(f"   - Disabled outline effect")
    print(f"   - Active effects: {len(active_after_toggle)} (was {len(active_effects)})")
    
    # Re-enable outline effect
    effects_manager.toggle_effect_layer(outline_effect.id, True)
    print(f"   - Re-enabled outline effect")
    print()
    
    # Demonstrate presets
    print("9. Applying Effect Presets...")
    
    # Clear current effects
    effects_manager.clear_all_effects()
    print("   - Cleared all effects")
    
    # Apply karaoke classic preset
    effects_manager.apply_preset('karaoke_classic')
    preset_effects = effects_manager.get_active_effects()
    
    print(f"   - Applied 'Karaoke Classic' preset")
    print(f"   - Preset includes {len(preset_effects)} effects:")
    for layer in preset_effects:
        print(f"     - {layer.effect.name}")
    print()
    
    # Demonstrate configuration export/import
    print("10. Configuration Export/Import...")
    
    # Export current configuration
    config = effects_manager.export_configuration()
    print(f"   - Exported configuration: {len(config['effect_layers'])} effect layers")
    
    # Clear and import
    effects_manager.clear_all_effects()
    effects_manager.import_configuration(config)
    imported_effects = effects_manager.get_active_effects()
    
    print(f"   - Imported configuration: {len(imported_effects)} effect layers restored")
    print()
    
    # Demonstrate renderer integration
    print("11. Renderer Integration...")
    
    # Add effects through renderer
    renderer_glow_id = renderer.add_effect('glow', {'radius': 10.0, 'color': [0.0, 1.0, 1.0]})
    renderer_outline_id = renderer.add_effect('outline', {'width': 2.5})
    
    renderer_effects = renderer.get_active_effects()
    print(f"   - Added effects through renderer: {len(renderer_effects)} effects")
    
    # Update parameters through renderer
    renderer.update_effect_parameters(renderer_glow_id, {'intensity': 1.2})
    print("   - Updated effect parameters through renderer")
    
    # Apply preset through renderer
    renderer.apply_effect_preset('neon_style')
    neon_effects = renderer.get_active_effects()
    print(f"   - Applied 'Neon Style' preset: {len(neon_effects)} effects")
    print()
    
    # Performance statistics
    print("12. Performance Statistics...")
    stats = renderer.get_performance_stats()
    
    print("   - Renderer statistics:")
    for key, value in stats.items():
        print(f"     {key}: {value}")
    print()
    
    print("=== Demo Complete ===")
    print("\nThe text effects system provides:")
    print("✓ Multiple effect types (glow, outline, shadow, animations)")
    print("✓ Dynamic shader generation")
    print("✓ Effect layering and ordering")
    print("✓ Real-time parameter adjustment")
    print("✓ Effect presets")
    print("✓ Configuration export/import")
    print("✓ OpenGL renderer integration")
    print("✓ Performance monitoring")


if __name__ == "__main__":
    try:
        demonstrate_effects_system()
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)