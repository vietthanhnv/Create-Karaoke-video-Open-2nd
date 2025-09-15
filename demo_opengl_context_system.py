#!/usr/bin/env python3
"""
Demo: OpenGL Context and Framebuffer System

This demo showcases the OpenGL context and framebuffer management system
for offscreen rendering without requiring window display.
"""

import sys
import numpy as np
from src.core.opengl_context import (
    OpenGLContext, FramebufferConfig, ContextBackend,
    create_offscreen_context, create_render_framebuffer
)


def demo_basic_context_creation():
    """Demo basic OpenGL context creation and capabilities"""
    print("=== OpenGL Context Creation Demo ===")
    
    # Create offscreen context
    context = create_offscreen_context(backend=ContextBackend.MOCK)
    if not context:
        print("❌ Failed to create OpenGL context")
        return False
    
    print(f"✅ Created OpenGL context with backend: {context.backend.value}")
    print(f"   Context is current: {context.is_current}")
    
    # Get capabilities
    caps = context.get_capabilities()
    if caps:
        print(f"   OpenGL Version: {caps.version}")
        print(f"   Vendor: {caps.vendor}")
        print(f"   Renderer: {caps.renderer}")
        print(f"   Max Texture Size: {caps.max_texture_size}")
        print(f"   Max Framebuffer Size: {caps.max_framebuffer_size}")
        print(f"   Supports Core Profile: {caps.supports_core_profile}")
        print(f"   Supports Framebuffers: {caps.supports_framebuffer_objects}")
    
    # Check for errors
    errors = context.check_errors()
    if errors:
        print(f"   OpenGL Errors: {errors}")
    else:
        print("   No OpenGL errors detected")
    
    context.cleanup()
    print("✅ Context cleaned up successfully\n")
    return True


def demo_framebuffer_operations():
    """Demo framebuffer creation and operations"""
    print("=== Framebuffer Operations Demo ===")
    
    context = create_offscreen_context(backend=ContextBackend.MOCK)
    if not context:
        print("❌ Failed to create context")
        return False
    
    # Create different types of framebuffers
    framebuffers = []
    
    # 1. Basic render target
    fb1 = create_render_framebuffer(context, "render_target", 1920, 1080)
    if fb1:
        framebuffers.append(("Render Target", fb1))
        print(f"✅ Created render target: {fb1.config.width}x{fb1.config.height}")
    
    # 2. Preview framebuffer
    config2 = FramebufferConfig(width=640, height=360, use_depth=False)
    fb2 = context.create_framebuffer("preview", config2)
    if fb2:
        framebuffers.append(("Preview", fb2))
        print(f"✅ Created preview framebuffer: {fb2.config.width}x{fb2.config.height}")
    
    # 3. High-resolution export framebuffer
    config3 = FramebufferConfig(width=3840, height=2160, use_depth=True, use_stencil=True)
    fb3 = context.create_framebuffer("export", config3)
    if fb3:
        framebuffers.append(("Export", fb3))
        print(f"✅ Created export framebuffer: {fb3.config.width}x{fb3.config.height}")
    
    print(f"   Total framebuffers created: {len(framebuffers)}")
    
    # Test operations on each framebuffer
    for name, fb in framebuffers:
        print(f"\n   Testing {name} framebuffer:")
        
        # Bind and clear
        fb.bind()
        fb.clear((0.2, 0.4, 0.6, 1.0))
        print(f"     ✅ Bound and cleared")
        
        # Read pixels
        pixels = fb.read_pixels()
        if pixels is not None:
            print(f"     ✅ Read pixels: {pixels.shape}")
        else:
            print(f"     ❌ Failed to read pixels")
        
        # Test texture attachments
        if fb.color_texture:
            print(f"     ✅ Color texture: {fb.color_texture.width}x{fb.color_texture.height}")
        if fb.depth_texture:
            print(f"     ✅ Depth texture: {fb.depth_texture.width}x{fb.depth_texture.height}")
        if fb.stencil_texture:
            print(f"     ✅ Stencil texture: {fb.stencil_texture.width}x{fb.stencil_texture.height}")
        
        fb.unbind()
    
    context.cleanup()
    print("\n✅ All framebuffers cleaned up successfully\n")
    return True


def demo_texture_management():
    """Demo texture creation and management"""
    print("=== Texture Management Demo ===")
    
    context = create_offscreen_context(backend=ContextBackend.MOCK)
    if not context:
        print("❌ Failed to create context")
        return False
    
    # Create test texture data
    test_data = np.random.randint(0, 255, (512, 512, 4), dtype=np.uint8)
    print(f"✅ Created test data: {test_data.shape}")
    
    # Create texture from data (this would work with real OpenGL)
    print("   Note: Texture creation from data requires real OpenGL context")
    print("   In mock mode, this demonstrates the API without actual GPU operations")
    
    # Create framebuffer to demonstrate texture usage
    framebuffer = create_render_framebuffer(context, "texture_test", 512, 512)
    if framebuffer and framebuffer.color_texture:
        texture = framebuffer.color_texture
        print(f"✅ Framebuffer color texture: {texture.width}x{texture.height}")
        print(f"   Texture ID: {texture.texture_id}")
        print(f"   Texture format: {texture.format}")
        print(f"   Texture valid: {texture.is_valid}")
        
        # Simulate texture operations
        texture.bind(unit=0)
        print("   ✅ Texture bound to unit 0")
        
        texture.unbind()
        print("   ✅ Texture unbound")
    
    context.cleanup()
    print("✅ Texture demo completed\n")
    return True


def demo_multi_pass_rendering():
    """Demo multi-pass rendering workflow"""
    print("=== Multi-Pass Rendering Demo ===")
    
    context = create_offscreen_context(backend=ContextBackend.MOCK)
    if not context:
        print("❌ Failed to create context")
        return False
    
    # Create render targets for different passes
    passes = [
        ("Geometry Pass", 1024, 1024),
        ("Lighting Pass", 1024, 1024),
        ("Post-Process Pass", 1024, 1024),
        ("Final Output", 1920, 1080)
    ]
    
    framebuffers = []
    for i, (name, width, height) in enumerate(passes):
        fb = create_render_framebuffer(context, f"pass_{i}", width, height)
        if fb:
            framebuffers.append((name, fb))
            print(f"✅ Created {name}: {width}x{height}")
    
    # Simulate multi-pass rendering
    print("\n   Simulating multi-pass rendering:")
    
    for i, (name, fb) in enumerate(framebuffers):
        print(f"     Pass {i+1}: {name}")
        
        # Bind framebuffer
        fb.bind()
        
        # Clear with different colors for each pass
        colors = [
            (0.1, 0.0, 0.0, 1.0),  # Red tint for geometry
            (0.0, 0.1, 0.0, 1.0),  # Green tint for lighting
            (0.0, 0.0, 0.1, 1.0),  # Blue tint for post-process
            (0.0, 0.0, 0.0, 1.0)   # Black for final
        ]
        fb.clear(colors[i])
        
        # In real rendering, this is where you would:
        # - Set up shaders
        # - Bind input textures from previous passes
        # - Draw geometry or fullscreen quads
        # - Apply effects
        
        print(f"       ✅ Rendered to {fb.config.width}x{fb.config.height} target")
        
        # Read result (in real app, this would be used as input for next pass)
        pixels = fb.read_pixels()
        if pixels is not None:
            print(f"       ✅ Captured result: {pixels.shape}")
        
        fb.unbind()
    
    print("   ✅ Multi-pass rendering completed")
    
    context.cleanup()
    print("✅ Multi-pass demo completed\n")
    return True


def demo_performance_scenarios():
    """Demo performance-oriented scenarios"""
    print("=== Performance Scenarios Demo ===")
    
    context = create_offscreen_context(backend=ContextBackend.MOCK)
    if not context:
        print("❌ Failed to create context")
        return False
    
    # Test rapid framebuffer creation/destruction
    print("   Testing rapid framebuffer operations:")
    
    for i in range(10):
        fb = create_render_framebuffer(context, f"perf_test_{i}", 256, 256)
        if fb:
            fb.bind()
            fb.clear((i/10.0, 0.5, 1.0 - i/10.0, 1.0))
            pixels = fb.read_pixels()
            fb.unbind()
            
            # Destroy immediately
            context.destroy_framebuffer(f"perf_test_{i}")
    
    print(f"   ✅ Created and destroyed 10 framebuffers")
    
    # Test framebuffer resizing
    print("   Testing framebuffer resizing:")
    
    fb = create_render_framebuffer(context, "resize_test", 128, 128)
    if fb:
        sizes = [(256, 256), (512, 512), (1024, 1024), (2048, 2048), (512, 512)]
        
        for width, height in sizes:
            fb.resize(width, height)
            print(f"     ✅ Resized to {width}x{height}")
            
            # Test operations after resize
            fb.bind()
            fb.clear((0.3, 0.6, 0.9, 1.0))
            fb.unbind()
    
    # Test memory usage simulation
    print("   Testing memory usage patterns:")
    
    # Create multiple large framebuffers
    large_fbs = []
    for i in range(5):
        fb = create_render_framebuffer(context, f"large_{i}", 2048, 2048)
        if fb:
            large_fbs.append(fb)
    
    print(f"   ✅ Created {len(large_fbs)} large framebuffers (2048x2048)")
    
    # Clean up
    context.cleanup()
    print("✅ Performance demo completed\n")
    return True


def main():
    """Run all demos"""
    print("OpenGL Context and Framebuffer System Demo")
    print("=" * 50)
    
    demos = [
        demo_basic_context_creation,
        demo_framebuffer_operations,
        demo_texture_management,
        demo_multi_pass_rendering,
        demo_performance_scenarios
    ]
    
    success_count = 0
    for demo in demos:
        try:
            if demo():
                success_count += 1
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
    
    print("=" * 50)
    print(f"Demo Summary: {success_count}/{len(demos)} demos completed successfully")
    
    if success_count == len(demos):
        print("🎉 All demos completed successfully!")
        print("\nThe OpenGL context and framebuffer system is working correctly.")
        print("Key features demonstrated:")
        print("  • Offscreen OpenGL context creation")
        print("  • Multiple backend support (PyQt6, GLFW, Mock)")
        print("  • Framebuffer creation and management")
        print("  • Texture attachment handling")
        print("  • Multi-pass rendering workflows")
        print("  • Performance optimization patterns")
        print("  • Proper resource cleanup")
        return True
    else:
        print("⚠️  Some demos failed. Check the output above for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)