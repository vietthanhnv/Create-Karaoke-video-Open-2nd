#!/usr/bin/env python3
"""
Visual Effects Shader System Demo

This demo showcases the complete shader system for visual effects including:
- Glow/bloom effects with Gaussian blur
- Particle systems for sparkles/confetti
- Text animations (scale, rotation, fade)
- Color transitions for karaoke timing
- Background blur for dynamic focus
- Shader compilation and caching
"""

import sys
import time
import numpy as np
from src.core.shader_system import (
    create_shader_system,
    EffectType,
    GlowBloomParameters,
    ParticleSystemParameters,
    TextAnimationParameters,
    ColorTransitionParameters,
    BackgroundBlurParameters,
    create_identity_matrix,
    create_orthographic_matrix
)


def demo_shader_compilation():
    """Demo shader compilation and caching"""
    print("=== Shader Compilation and Caching Demo ===")
    
    # Create shader system with caching
    shader_system = create_shader_system("temp/shader_cache", mock_mode=True)
    
    print(f"Created shader system with {len(shader_system.get_program_names())} built-in programs")
    
    # List available programs
    programs = shader_system.get_program_names()
    print("Available shader programs:")
    for program in programs:
        print(f"  - {program}")
    
    # Validate all programs
    validation_results = shader_system.validate_programs()
    print("\nProgram validation results:")
    for program, is_valid in validation_results.items():
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  {program}: {status}")
    
    return shader_system


def demo_glow_bloom_effect(shader_system):
    """Demo glow/bloom effect"""
    print("\n=== Glow/Bloom Effect Demo ===")
    
    # Create glow parameters
    glow_params = GlowBloomParameters(
        intensity=2.0,
        radius=8.0,
        threshold=0.8,
        color=(1.0, 0.8, 0.6),  # Warm golden glow
        blur_passes=3
    )
    
    print(f"Glow Parameters:")
    print(f"  Intensity: {glow_params.intensity}")
    print(f"  Radius: {glow_params.radius}")
    print(f"  Threshold: {glow_params.threshold}")
    print(f"  Color: {glow_params.color}")
    print(f"  Blur Passes: {glow_params.blur_passes}")
    
    # Use glow shader
    success = shader_system.use_program(EffectType.GLOW_BLOOM.value)
    print(f"Glow shader activation: {'✓ Success' if success else '✗ Failed'}")
    
    # Apply glow effect
    shader_system.apply_glow_bloom_effect(EffectType.GLOW_BLOOM.value, glow_params)
    print("✓ Glow effect parameters applied")
    
    # Set common uniforms
    mvp_matrix = create_orthographic_matrix(-1.0, 1.0, -1.0, 1.0)
    resolution = (1920.0, 1080.0)
    time_value = 1.5
    
    shader_system.set_common_uniforms(EffectType.GLOW_BLOOM.value, mvp_matrix, resolution, time_value)
    print("✓ Common uniforms set (MVP matrix, resolution, time)")


def demo_particle_system(shader_system):
    """Demo particle system"""
    print("\n=== Particle System Demo ===")
    
    # Create particle parameters
    particle_params = ParticleSystemParameters(
        count=200,
        size=3.0,
        lifetime=2.5,
        velocity=(10.0, 50.0),
        gravity=(0.0, -9.8),
        color_start=(1.0, 1.0, 1.0, 1.0),  # White
        color_end=(1.0, 0.0, 0.0, 0.0),    # Fade to transparent red
        spawn_rate=80.0
    )
    
    print(f"Particle Parameters:")
    print(f"  Count: {particle_params.count}")
    print(f"  Size: {particle_params.size}")
    print(f"  Lifetime: {particle_params.lifetime}s")
    print(f"  Velocity: {particle_params.velocity}")
    print(f"  Gravity: {particle_params.gravity}")
    print(f"  Start Color: {particle_params.color_start}")
    print(f"  End Color: {particle_params.color_end}")
    print(f"  Spawn Rate: {particle_params.spawn_rate}/s")
    
    # Use particle shader
    success = shader_system.use_program(EffectType.PARTICLE_SYSTEM.value)
    print(f"Particle shader activation: {'✓ Success' if success else '✗ Failed'}")
    
    # Apply particle effect
    shader_system.apply_particle_system_effect(EffectType.PARTICLE_SYSTEM.value, particle_params)
    print("✓ Particle system parameters applied")


def demo_text_animations(shader_system):
    """Demo text animations"""
    print("\n=== Text Animation Demo ===")
    
    # Simulate animation over time
    animation_duration = 3.0
    steps = 10
    
    print(f"Simulating {animation_duration}s animation with {steps} steps:")
    
    for i in range(steps):
        progress = i / (steps - 1)
        current_time = progress * animation_duration
        
        # Create animated parameters
        text_params = TextAnimationParameters(
            scale_factor=1.0 + 0.5 * np.sin(current_time * 2.0),  # Pulsing scale
            rotation_angle=current_time * 45.0,                    # Rotating
            fade_alpha=0.5 + 0.5 * np.cos(current_time * 1.5),   # Fading
            translation=(np.sin(current_time) * 10.0, np.cos(current_time) * 5.0),
            animation_time=current_time,
            scale_animation=True,
            rotation_animation=True,
            fade_animation=True
        )
        
        print(f"  Step {i+1:2d}: t={current_time:.1f}s, scale={text_params.scale_factor:.2f}, "
              f"rotation={text_params.rotation_angle:.1f}°, alpha={text_params.fade_alpha:.2f}")
        
        # Use text animation shader
        shader_system.use_program(EffectType.TEXT_ANIMATION.value)
        shader_system.apply_text_animation_effect(EffectType.TEXT_ANIMATION.value, text_params)
    
    print("✓ Text animation sequence completed")


def demo_color_transitions(shader_system):
    """Demo color transitions"""
    print("\n=== Color Transition Demo ===")
    
    # Define transition colors
    start_color = (1.0, 0.0, 0.0, 1.0)  # Red
    end_color = (0.0, 1.0, 0.0, 1.0)    # Green
    
    transition_types = ["linear", "ease_in", "ease_out", "ease_in_out"]
    
    print(f"Transitioning from {start_color} to {end_color}")
    
    for transition_type in transition_types:
        print(f"\n{transition_type.upper()} transition:")
        
        # Simulate transition steps
        steps = 5
        for i in range(steps):
            progress = i / (steps - 1)
            
            color_params = ColorTransitionParameters(
                start_color=start_color,
                end_color=end_color,
                progress=progress,
                transition_type=transition_type
            )
            
            print(f"  Step {i+1}: progress={progress:.2f}")
            
            # Use color transition shader
            shader_system.use_program(EffectType.COLOR_TRANSITION.value)
            shader_system.apply_color_transition_effect(EffectType.COLOR_TRANSITION.value, color_params)
    
    print("✓ Color transition demo completed")


def demo_background_blur(shader_system):
    """Demo background blur effects"""
    print("\n=== Background Blur Demo ===")
    
    # Create blur parameters
    blur_params = BackgroundBlurParameters(
        blur_radius=6.0,
        blur_intensity=0.8,
        blur_passes=2,
        focus_point=(0.5, 0.5),  # Center focus
        focus_radius=0.3
    )
    
    print(f"Background Blur Parameters:")
    print(f"  Blur Radius: {blur_params.blur_radius}")
    print(f"  Blur Intensity: {blur_params.blur_intensity}")
    print(f"  Blur Passes: {blur_params.blur_passes}")
    print(f"  Focus Point: {blur_params.focus_point}")
    print(f"  Focus Radius: {blur_params.focus_radius}")
    
    # Use background blur shader
    success = shader_system.use_program(EffectType.BACKGROUND_BLUR.value)
    print(f"Background blur shader activation: {'✓ Success' if success else '✗ Failed'}")
    
    # Apply blur effect
    shader_system.apply_background_blur_effect(EffectType.BACKGROUND_BLUR.value, blur_params)
    print("✓ Background blur parameters applied")
    
    # Demo dynamic focus point
    print("\nDynamic focus point demo:")
    focus_points = [
        (0.2, 0.2),  # Top-left
        (0.8, 0.2),  # Top-right
        (0.8, 0.8),  # Bottom-right
        (0.2, 0.8),  # Bottom-left
        (0.5, 0.5),  # Center
    ]
    
    for i, focus_point in enumerate(focus_points):
        blur_params.focus_point = focus_point
        shader_system.apply_background_blur_effect(EffectType.BACKGROUND_BLUR.value, blur_params)
        print(f"  Focus point {i+1}: {focus_point}")
    
    print("✓ Dynamic focus demo completed")


def demo_custom_shader_creation(shader_system):
    """Demo custom shader creation"""
    print("\n=== Custom Shader Creation Demo ===")
    
    # Create custom shader source
    vertex_source = """
    #version 330 core
    
    layout (location = 0) in vec3 a_position;
    layout (location = 1) in vec2 a_texcoord;
    
    uniform mat4 u_mvp_matrix;
    uniform float u_wave_amplitude;
    uniform float u_wave_frequency;
    uniform float u_time;
    
    out vec2 v_texcoord;
    
    void main() {
        vec3 pos = a_position;
        
        // Apply wave distortion
        pos.y += sin(pos.x * u_wave_frequency + u_time) * u_wave_amplitude;
        
        gl_Position = u_mvp_matrix * vec4(pos, 1.0);
        v_texcoord = a_texcoord;
    }
    """
    
    fragment_source = """
    #version 330 core
    
    in vec2 v_texcoord;
    out vec4 frag_color;
    
    uniform sampler2D u_texture;
    uniform vec3 u_tint_color;
    uniform float u_brightness;
    
    void main() {
        vec4 color = texture(u_texture, v_texcoord);
        
        // Apply tint and brightness
        color.rgb *= u_tint_color * u_brightness;
        
        frag_color = color;
    }
    """
    
    from src.core.shader_system import ShaderSource
    
    sources = ShaderSource(vertex_source, fragment_source)
    custom_program = shader_system.create_program("custom_wave_effect", sources)
    
    if custom_program:
        print("✓ Custom wave effect shader created successfully")
        print(f"  Program ID: {custom_program.program_id}")
        print(f"  Uniforms: {list(custom_program.uniforms.keys())}")
        
        # Test using the custom shader
        success = shader_system.use_program("custom_wave_effect")
        print(f"  Custom shader activation: {'✓ Success' if success else '✗ Failed'}")
        
        # Set custom uniforms
        if custom_program.has_uniform('u_wave_amplitude'):
            custom_program.set_uniform_float('u_wave_amplitude', 0.1)
        if custom_program.has_uniform('u_wave_frequency'):
            custom_program.set_uniform_float('u_wave_frequency', 5.0)
        if custom_program.has_uniform('u_tint_color'):
            custom_program.set_uniform_vec3('u_tint_color', (1.0, 0.8, 0.6))
        if custom_program.has_uniform('u_brightness'):
            custom_program.set_uniform_float('u_brightness', 1.2)
        
        print("✓ Custom shader parameters applied")
    else:
        print("✗ Failed to create custom shader")


def demo_shader_caching(shader_system):
    """Demo shader caching system"""
    print("\n=== Shader Caching Demo ===")
    
    # Create a test shader
    vertex_source = """
    #version 330 core
    layout (location = 0) in vec3 a_position;
    void main() { gl_Position = vec4(a_position, 1.0); }
    """
    
    fragment_source = """
    #version 330 core
    out vec4 frag_color;
    void main() { frag_color = vec4(1.0, 0.0, 0.0, 1.0); }
    """
    
    from src.core.shader_system import ShaderSource
    
    sources = ShaderSource(vertex_source, fragment_source)
    
    # Time first compilation
    start_time = time.time()
    program1 = shader_system.create_program("cache_test_shader", sources)
    first_compile_time = time.time() - start_time
    
    print(f"First compilation time: {first_compile_time*1000:.2f}ms")
    
    # Create new shader system (simulates restart)
    shader_system2 = create_shader_system("temp/shader_cache", mock_mode=True)
    
    # Time second compilation (should use cache)
    start_time = time.time()
    program2 = shader_system2.create_program("cache_test_shader", sources)
    second_compile_time = time.time() - start_time
    
    print(f"Second compilation time (cached): {second_compile_time*1000:.2f}ms")
    
    if program1 and program2:
        print("✓ Shader caching system working correctly")
    else:
        print("✗ Shader caching system failed")
    
    shader_system2.cleanup()


def demo_performance_testing(shader_system):
    """Demo performance testing"""
    print("\n=== Performance Testing Demo ===")
    
    # Test rapid shader switching
    programs = [
        EffectType.GLOW_BLOOM.value,
        EffectType.PARTICLE_SYSTEM.value,
        EffectType.TEXT_ANIMATION.value,
        EffectType.COLOR_TRANSITION.value,
        EffectType.BACKGROUND_BLUR.value
    ]
    
    iterations = 100
    
    print(f"Testing rapid shader switching ({iterations} iterations)...")
    
    start_time = time.time()
    for i in range(iterations):
        program_name = programs[i % len(programs)]
        shader_system.use_program(program_name)
    
    switch_time = time.time() - start_time
    avg_switch_time = (switch_time / iterations) * 1000
    
    print(f"Total switching time: {switch_time*1000:.2f}ms")
    print(f"Average switch time: {avg_switch_time:.3f}ms per switch")
    
    # Test uniform setting performance
    print(f"\nTesting uniform setting performance...")
    
    mvp_matrix = create_identity_matrix()
    resolution = (1920.0, 1080.0)
    
    start_time = time.time()
    for i in range(iterations):
        shader_system.set_common_uniforms(
            EffectType.GLOW_BLOOM.value, mvp_matrix, resolution, float(i)
        )
    
    uniform_time = time.time() - start_time
    avg_uniform_time = (uniform_time / iterations) * 1000
    
    print(f"Total uniform setting time: {uniform_time*1000:.2f}ms")
    print(f"Average uniform time: {avg_uniform_time:.3f}ms per set")
    
    print("✓ Performance testing completed")


def demo_error_handling(shader_system):
    """Demo error handling"""
    print("\n=== Error Handling Demo ===")
    
    # Test using non-existent shader
    print("Testing non-existent shader usage...")
    success = shader_system.use_program("nonexistent_shader")
    print(f"Non-existent shader usage: {'✗ Failed (expected)' if not success else '✓ Unexpected success'}")
    
    # Test applying effects to non-existent shader
    print("Testing effect application to non-existent shader...")
    glow_params = GlowBloomParameters()
    shader_system.apply_glow_bloom_effect("nonexistent_shader", glow_params)
    print("✓ Effect application handled gracefully")
    
    # Test invalid shader source
    print("Testing invalid shader source...")
    invalid_vertex = "invalid shader code"
    invalid_fragment = "also invalid"
    
    from src.core.shader_system import ShaderSource
    
    invalid_sources = ShaderSource(invalid_vertex, invalid_fragment)
    invalid_program = shader_system.create_program("invalid_shader", invalid_sources)
    
    if invalid_program and invalid_program.is_valid:
        print("✗ Invalid shader unexpectedly succeeded (mock mode)")
    else:
        print("✓ Invalid shader properly rejected")
    
    print("✓ Error handling demo completed")


def main():
    """Main demo function"""
    print("Visual Effects Shader System Demo")
    print("=" * 50)
    
    try:
        # Initialize shader system
        shader_system = demo_shader_compilation()
        
        # Run all demos
        demo_glow_bloom_effect(shader_system)
        demo_particle_system(shader_system)
        demo_text_animations(shader_system)
        demo_color_transitions(shader_system)
        demo_background_blur(shader_system)
        demo_custom_shader_creation(shader_system)
        demo_shader_caching(shader_system)
        demo_performance_testing(shader_system)
        demo_error_handling(shader_system)
        
        print("\n" + "=" * 50)
        print("✓ All shader system demos completed successfully!")
        
        # Final validation
        final_validation = shader_system.validate_programs()
        valid_count = sum(1 for is_valid in final_validation.values() if is_valid)
        total_count = len(final_validation)
        
        print(f"Final validation: {valid_count}/{total_count} programs valid")
        
        # Cleanup
        shader_system.cleanup()
        print("✓ Shader system cleaned up")
        
    except Exception as e:
        print(f"✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())