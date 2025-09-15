"""
Tests for OpenGL Framebuffer Operations and Integration
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.core.opengl_context import (
    OpenGLContext, FramebufferConfig, ContextBackend,
    create_offscreen_context, create_render_framebuffer
)


class TestFramebufferOperations:
    """Test comprehensive framebuffer operations"""
    
    def test_framebuffer_lifecycle(self):
        """Test complete framebuffer lifecycle"""
        # Create context
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create framebuffer
        framebuffer = create_render_framebuffer(context, "test", 800, 600)
        assert framebuffer is not None
        assert framebuffer.is_valid
        assert framebuffer.config.width == 800
        assert framebuffer.config.height == 600
        
        # Test bind/unbind
        framebuffer.bind()
        framebuffer.unbind()
        
        # Test clear
        framebuffer.clear((0.2, 0.3, 0.4, 1.0))
        
        # Test resize
        framebuffer.resize(1024, 768)
        assert framebuffer.config.width == 1024
        assert framebuffer.config.height == 768
        assert framebuffer.is_valid
        
        # Test pixel reading
        pixels = framebuffer.read_pixels()
        assert pixels is not None
        assert pixels.shape == (768, 1024, 4)  # height, width, channels
        
        # Cleanup
        framebuffer.destroy()
        assert not framebuffer.is_valid
        
        context.cleanup()
    
    def test_multiple_framebuffers(self):
        """Test managing multiple framebuffers"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create multiple framebuffers with different configurations
        fb1 = context.create_framebuffer("render", FramebufferConfig(
            width=1920, height=1080, use_depth=True, use_stencil=False
        ))
        
        fb2 = context.create_framebuffer("preview", FramebufferConfig(
            width=640, height=360, use_depth=False, use_stencil=True
        ))
        
        fb3 = context.create_framebuffer("export", FramebufferConfig(
            width=3840, height=2160, use_depth=True, use_stencil=True
        ))
        
        assert fb1 is not None and fb1.is_valid
        assert fb2 is not None and fb2.is_valid
        assert fb3 is not None and fb3.is_valid
        
        # Verify configurations
        assert fb1.config.use_depth and not fb1.config.use_stencil
        assert not fb2.config.use_depth and fb2.config.use_stencil
        assert fb3.config.use_depth and fb3.config.use_stencil
        
        # Test operations on each
        for fb in [fb1, fb2, fb3]:
            fb.bind()
            fb.clear()
            pixels = fb.read_pixels()
            assert pixels is not None
            fb.unbind()
        
        # Cleanup
        assert len(context.framebuffers) == 3
        context.cleanup()
        assert len(context.framebuffers) == 0
    
    def test_framebuffer_texture_attachments(self):
        """Test framebuffer texture attachments"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create framebuffer with all attachments
        config = FramebufferConfig(
            width=512, height=512,
            use_depth=True, use_stencil=True
        )
        
        framebuffer = context.create_framebuffer("full", config)
        assert framebuffer is not None
        
        # Check texture attachments
        assert framebuffer.color_texture is not None
        assert framebuffer.depth_texture is not None
        assert framebuffer.stencil_texture is not None
        
        # Verify texture properties
        assert framebuffer.color_texture.width == 512
        assert framebuffer.color_texture.height == 512
        assert framebuffer.depth_texture.width == 512
        assert framebuffer.depth_texture.height == 512
        assert framebuffer.stencil_texture.width == 512
        assert framebuffer.stencil_texture.height == 512
        
        context.cleanup()
    
    def test_framebuffer_performance_operations(self):
        """Test framebuffer operations for performance scenarios"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create high-resolution framebuffer
        config = FramebufferConfig(width=4096, height=4096)
        framebuffer = context.create_framebuffer("hires", config)
        assert framebuffer is not None
        
        # Test rapid bind/unbind cycles
        for i in range(100):
            framebuffer.bind()
            framebuffer.clear((i/100.0, 0.5, 0.5, 1.0))
            framebuffer.unbind()
        
        # Test resize operations
        sizes = [(1024, 1024), (2048, 2048), (512, 512), (4096, 4096)]
        for width, height in sizes:
            framebuffer.resize(width, height)
            assert framebuffer.config.width == width
            assert framebuffer.config.height == height
            assert framebuffer.is_valid
        
        context.cleanup()
    
    def test_texture_management(self):
        """Test texture creation and management"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create test data
        test_data = np.random.randint(0, 255, (256, 256, 4), dtype=np.uint8)
        
        with patch('src.core.opengl_context.OPENGL_AVAILABLE', True):
            with patch('src.core.opengl_context.gl') as mock_gl:
                mock_gl.glGenTextures.return_value = 42
                
                # Create texture from data
                texture = context.create_texture_from_data(test_data)
                
                assert texture is not None
                assert texture.width == 256
                assert texture.height == 256
                assert texture.texture_id == 42
        
        context.cleanup()
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Test invalid texture data
        invalid_data = np.random.randint(0, 255, (256, 256), dtype=np.uint8)  # 2D instead of 3D
        texture = context.create_texture_from_data(invalid_data)
        assert texture is None
        
        # Test framebuffer operations on destroyed framebuffer
        config = FramebufferConfig(width=100, height=100)
        framebuffer = context.create_framebuffer("test", config)
        assert framebuffer is not None
        
        framebuffer.destroy()
        assert not framebuffer.is_valid
        
        # Operations on destroyed framebuffer should be safe
        framebuffer.bind()  # Should not crash
        framebuffer.clear()  # Should not crash
        pixels = framebuffer.read_pixels()  # Should return None
        assert pixels is None
        
        context.cleanup()
    
    def test_context_state_management(self):
        """Test OpenGL context state management"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Test make_current
        assert context.is_current
        result = context.make_current()
        assert result
        assert context.is_current
        
        # Test capabilities
        caps = context.get_capabilities()
        assert caps is not None
        assert caps.supports_core_profile
        assert caps.supports_framebuffer_objects
        assert caps.max_texture_size > 0
        assert caps.max_framebuffer_size > 0
        
        # Test error checking
        errors = context.check_errors()
        assert isinstance(errors, list)
        
        context.cleanup()
    
    def test_framebuffer_format_variations(self):
        """Test different framebuffer format configurations"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Test different format combinations
        configs = [
            FramebufferConfig(width=256, height=256, use_depth=False, use_stencil=False),
            FramebufferConfig(width=256, height=256, use_depth=True, use_stencil=False),
            FramebufferConfig(width=256, height=256, use_depth=False, use_stencil=True),
            FramebufferConfig(width=256, height=256, use_depth=True, use_stencil=True),
            FramebufferConfig(width=256, height=256, samples=4),  # Multisampling
        ]
        
        for i, config in enumerate(configs):
            framebuffer = context.create_framebuffer(f"test_{i}", config)
            assert framebuffer is not None
            assert framebuffer.is_valid
            
            # Verify attachment creation based on config
            assert framebuffer.color_texture is not None
            
            if config.use_depth:
                assert framebuffer.depth_texture is not None
            else:
                assert framebuffer.depth_texture is None
            
            if config.use_stencil:
                assert framebuffer.stencil_texture is not None
            else:
                assert framebuffer.stencil_texture is None
        
        context.cleanup()


class TestFramebufferIntegrationWithRendering:
    """Test framebuffer integration with rendering pipeline"""
    
    def test_render_to_texture_workflow(self):
        """Test complete render-to-texture workflow"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create render target
        render_target = create_render_framebuffer(context, "render_target", 512, 512)
        assert render_target is not None
        
        # Simulate rendering workflow
        render_target.bind()
        render_target.clear((0.1, 0.2, 0.3, 1.0))
        
        # Simulate drawing operations (would normally use shaders here)
        # In mock mode, we just verify the framebuffer state
        assert render_target.is_valid
        
        # Read back rendered result
        pixels = render_target.read_pixels()
        assert pixels is not None
        assert pixels.shape == (512, 512, 4)
        
        render_target.unbind()
        
        # Use rendered texture as input for next pass
        color_texture = render_target.color_texture
        assert color_texture is not None
        assert color_texture.width == 512
        assert color_texture.height == 512
        
        context.cleanup()
    
    def test_multi_pass_rendering(self):
        """Test multi-pass rendering with multiple framebuffers"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create multiple render targets for different passes
        pass1_fb = create_render_framebuffer(context, "pass1", 1024, 1024)
        pass2_fb = create_render_framebuffer(context, "pass2", 1024, 1024)
        final_fb = create_render_framebuffer(context, "final", 1024, 1024)
        
        assert all(fb is not None for fb in [pass1_fb, pass2_fb, final_fb])
        
        # Simulate multi-pass rendering
        # Pass 1: Render base scene
        pass1_fb.bind()
        pass1_fb.clear((0.0, 0.0, 0.0, 1.0))
        # ... render scene geometry ...
        pass1_fb.unbind()
        
        # Pass 2: Apply effects using Pass 1 result
        pass2_fb.bind()
        pass2_fb.clear((0.0, 0.0, 0.0, 0.0))
        # ... apply effects using pass1_fb.color_texture ...
        pass2_fb.unbind()
        
        # Final pass: Composite results
        final_fb.bind()
        final_fb.clear((0.0, 0.0, 0.0, 1.0))
        # ... composite pass1 and pass2 results ...
        final_pixels = final_fb.read_pixels()
        final_fb.unbind()
        
        assert final_pixels is not None
        assert final_pixels.shape == (1024, 1024, 4)
        
        context.cleanup()
    
    def test_framebuffer_chain_operations(self):
        """Test chaining framebuffer operations"""
        context = create_offscreen_context(backend=ContextBackend.MOCK)
        assert context is not None
        
        # Create a chain of framebuffers with different sizes
        sizes = [(128, 128), (256, 256), (512, 512), (1024, 1024)]
        framebuffers = []
        
        for i, (width, height) in enumerate(sizes):
            fb = create_render_framebuffer(context, f"chain_{i}", width, height)
            assert fb is not None
            framebuffers.append(fb)
        
        # Process through the chain
        for i, fb in enumerate(framebuffers):
            fb.bind()
            
            # Clear with different colors for each stage
            color = (i * 0.25, 0.5, 1.0 - i * 0.25, 1.0)
            fb.clear(color)
            
            # Read pixels to verify
            pixels = fb.read_pixels()
            assert pixels is not None
            assert pixels.shape == (fb.config.height, fb.config.width, 4)
            
            fb.unbind()
        
        context.cleanup()


if __name__ == '__main__':
    pytest.main([__file__])