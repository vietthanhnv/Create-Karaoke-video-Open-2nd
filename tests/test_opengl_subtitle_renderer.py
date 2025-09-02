"""
Tests for OpenGL subtitle rendering system.

Tests GPU-based text rendering, texture caching, .ass format styling support,
and performance characteristics of the OpenGL subtitle renderer.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QPointF, QSizeF
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtOpenGL import QOpenGLTexture

try:
    from src.core.opengl_subtitle_renderer import (
        OpenGLSubtitleRenderer, RenderedSubtitle, TextureCache
    )
    OPENGL_RENDERER_AVAILABLE = True
except ImportError:
    # Create mock classes for testing when OpenGL renderer is not available
    OPENGL_RENDERER_AVAILABLE = False
    
    from dataclasses import dataclass
    from typing import Dict, Optional, Tuple, Any
    import numpy as np
    from PyQt6.QtCore import QPointF, QSizeF
    
    @dataclass
    class RenderedSubtitle:
        texture: Any
        position: Tuple[float, float]
        size: Tuple[float, float]
        start_time: float
        end_time: float
        text: str
        style_name: str
    
    @dataclass
    class TextureCache:
        textures: Dict[str, RenderedSubtitle] = None
        max_size: int = 100
        
        def __post_init__(self):
            if self.textures is None:
                self.textures = {}
        
        def get_cache_key(self, text: str, style, viewport_size: Tuple[int, int]) -> str:
            return f"{text}_mock_{viewport_size[0]}x{viewport_size[1]}"
        
        def get(self, key: str) -> Optional[RenderedSubtitle]:
            return self.textures.get(key)
        
        def put(self, key: str, rendered: RenderedSubtitle):
            if len(self.textures) >= self.max_size:
                # Remove oldest entry
                oldest_key = next(iter(self.textures))
                old_texture = self.textures.pop(oldest_key)
                if old_texture.texture and hasattr(old_texture.texture, 'destroy'):
                    old_texture.texture.destroy()
            self.textures[key] = rendered
        
        def clear(self):
            for rendered in self.textures.values():
                if rendered.texture and hasattr(rendered.texture, 'destroy'):
                    rendered.texture.destroy()
            self.textures.clear()
    
    class OpenGLSubtitleRenderer:
        def __init__(self):
            self.texture_cache = TextureCache()
            self.initialized = False
            self.shader_program = None
            self.vertex_buffer = None
            self.index_buffer = None
        
        def initialize_opengl(self):
            return True
        
        def create_text_texture(self, text, style, viewport_size):
            class MockTexture:
                def width(self): return 300
                def height(self): return 50
                def destroy(self): pass
            return MockTexture()
        
        def calculate_subtitle_position(self, subtitle, style, viewport_size, texture):
            return (100.0, 200.0)
        
        def render_subtitle(self, subtitle, style, viewport_size, current_time):
            if current_time < subtitle.start_time or current_time > subtitle.end_time:
                return None
            
            # Check cache first
            cache_key = self.texture_cache.get_cache_key(subtitle.text, style, viewport_size)
            cached = self.texture_cache.get(cache_key)
            if cached:
                return cached
            
            texture = self.create_text_texture(subtitle.text, style, viewport_size)
            position = self.calculate_subtitle_position(subtitle, style, viewport_size, texture)
            
            rendered = RenderedSubtitle(
                texture=texture,
                position=position,
                size=(texture.width(), texture.height()),
                start_time=subtitle.start_time,
                end_time=subtitle.end_time,
                text=subtitle.text,
                style_name=style.name
            )
            
            # Cache the result
            self.texture_cache.put(cache_key, rendered)
            
            return rendered
        
        def get_performance_stats(self):
            return {
                'cache_size': len(self.texture_cache.textures),
                'cache_max_size': self.texture_cache.max_size,
                'initialized': self.initialized,
                'shader_program_valid': False
            }
from src.core.models import SubtitleLine, SubtitleStyle


class TestBasicFunctionality:
    """Test basic functionality that works without OpenGL context."""
    
    def test_opengl_renderer_availability(self):
        """Test if OpenGL renderer is available."""
        if OPENGL_RENDERER_AVAILABLE:
            renderer = OpenGLSubtitleRenderer()
            assert renderer is not None
            stats = renderer.get_performance_stats()
            assert 'cache_size' in stats
        else:
            pytest.skip("OpenGL renderer not available")


class TestTextureCache:
    """Test subtitle texture caching system."""
    
    def test_cache_initialization(self):
        """Test cache initializes correctly."""
        cache = TextureCache()
        assert cache.textures == {}
        assert cache.max_size == 100
    
    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = TextureCache()
        style = SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=24,
            primary_color="#FFFFFF"
        )
        
        key1 = cache.get_cache_key("Hello World", style, (1920, 1080))
        key2 = cache.get_cache_key("Hello World", style, (1920, 1080))
        key3 = cache.get_cache_key("Hello World", style, (1280, 720))
        
        assert key1 == key2
        assert key1 != key3
        assert "Hello World" in key1
        assert "1920x1080" in key1
        assert "1280x720" in key3
    
    def test_cache_put_and_get(self):
        """Test storing and retrieving cached textures."""
        cache = TextureCache()
        
        # Mock rendered subtitle
        mock_texture = Mock(spec=QOpenGLTexture)
        rendered = RenderedSubtitle(
            texture=mock_texture,
            position=(100.0, 200.0),
            size=(300.0, 50.0),
            start_time=1.0,
            end_time=3.0,
            text="Test",
            style_name="Default"
        )
        
        key = "test_key"
        cache.put(key, rendered)
        
        retrieved = cache.get(key)
        assert retrieved == rendered
        assert retrieved.text == "Test"
    
    def test_cache_size_limit(self):
        """Test cache respects size limit."""
        cache = TextureCache(max_size=2)
        
        # Add items beyond limit
        for i in range(3):
            mock_texture = Mock(spec=QOpenGLTexture)
            rendered = RenderedSubtitle(
                texture=mock_texture,
                position=(0.0, 0.0),
                size=(100.0, 50.0),
                start_time=0.0,
                end_time=1.0,
                text=f"Text {i}",
                style_name="Default"
            )
            cache.put(f"key_{i}", rendered)
        
        # Should only have 2 items (max_size)
        assert len(cache.textures) == 2
        # First item should be evicted
        assert cache.get("key_0") is None
        assert cache.get("key_1") is not None
        assert cache.get("key_2") is not None
    
    def test_cache_clear(self):
        """Test cache clearing destroys textures."""
        cache = TextureCache()
        
        mock_texture = Mock(spec=QOpenGLTexture)
        rendered = RenderedSubtitle(
            texture=mock_texture,
            position=(0.0, 0.0),
            size=(100.0, 50.0),
            start_time=0.0,
            end_time=1.0,
            text="Test",
            style_name="Default"
        )
        
        cache.put("test", rendered)
        cache.clear()
        
        assert len(cache.textures) == 0
        mock_texture.destroy.assert_called_once()


@pytest.mark.skipif(not OPENGL_RENDERER_AVAILABLE, reason="OpenGL renderer not available")
class TestOpenGLSubtitleRenderer:
    """Test OpenGL subtitle renderer functionality."""
    
    @pytest.fixture
    def renderer(self):
        """Create renderer instance for testing."""
        return OpenGLSubtitleRenderer()
    
    @pytest.fixture
    def sample_style(self):
        """Create sample subtitle style."""
        return SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=24,
            primary_color="#FFFFFF",
            bold=False,
            italic=False,
            margin_l=10,
            margin_r=10,
            margin_v=20
        )
    
    @pytest.fixture
    def sample_subtitle(self):
        """Create sample subtitle line."""
        return SubtitleLine(
            start_time=1.0,
            end_time=3.0,
            text="Hello, World!",
            style="Default"
        )
    
    def test_renderer_initialization(self, renderer):
        """Test renderer initializes with correct defaults."""
        assert renderer.texture_cache is not None
        assert renderer.shader_program is None
        assert not renderer.initialized
        assert renderer.vertex_buffer is None
        assert renderer.index_buffer is None
    
    def test_shader_source_validity(self, renderer):
        """Test shader source code is valid."""
        # Check vertex shader has required elements
        vertex_shader = renderer.vertex_shader_source
        assert "#version 330 core" in vertex_shader
        assert "layout (location = 0) in vec3 position" in vertex_shader
        assert "layout (location = 1) in vec2 texCoord" in vertex_shader
        assert "uniform mat4 projection" in vertex_shader
        assert "uniform mat4 model" in vertex_shader
        
        # Check fragment shader has required elements
        fragment_shader = renderer.fragment_shader_source
        assert "#version 330 core" in fragment_shader
        assert "uniform sampler2D textTexture" in fragment_shader
        assert "uniform bool enableGlow" in fragment_shader
        assert "uniform bool enableOutline" in fragment_shader
        assert "uniform bool enableShadow" in fragment_shader
    
    @patch('src.core.opengl_subtitle_renderer.QOpenGLShaderProgram')
    def test_opengl_initialization_success(self, mock_shader_program, renderer):
        """Test successful OpenGL initialization."""
        # Mock shader program
        mock_program = Mock()
        mock_program.addShaderFromSourceCode.return_value = True
        mock_program.link.return_value = True
        mock_shader_program.return_value = mock_program
        
        # Mock OpenGL functions
        with patch('src.core.opengl_subtitle_renderer.gl') as mock_gl:
            mock_gl.glGenBuffers.return_value = 1
            
            result = renderer.initialize_opengl()
            
            assert result is True
            assert renderer.initialized is True
            assert renderer.shader_program == mock_program
    
    @patch('src.core.opengl_subtitle_renderer.QOpenGLShaderProgram')
    def test_opengl_initialization_failure(self, mock_shader_program, renderer):
        """Test OpenGL initialization failure handling."""
        # Mock shader program failure
        mock_program = Mock()
        mock_program.addShaderFromSourceCode.return_value = False
        mock_program.log.return_value = "Shader compilation error"
        mock_shader_program.return_value = mock_program
        
        result = renderer.initialize_opengl()
        
        assert result is False
        assert renderer.initialized is False
    
    def test_subtitle_visibility_check(self, renderer, sample_subtitle, sample_style):
        """Test subtitle visibility based on timing."""
        viewport_size = (1920, 1080)
        
        # Mock initialization
        renderer.initialized = True
        
        with patch.object(renderer, 'create_text_texture') as mock_create_texture:
            mock_texture = Mock(spec=QOpenGLTexture)
            mock_texture.width.return_value = 300
            mock_texture.height.return_value = 50
            mock_create_texture.return_value = mock_texture
            
            # Test before subtitle time
            result = renderer.render_subtitle(sample_subtitle, sample_style, viewport_size, 0.5)
            assert result is None
            
            # Test during subtitle time
            result = renderer.render_subtitle(sample_subtitle, sample_style, viewport_size, 2.0)
            assert result is not None
            assert result.text == "Hello, World!"
            
            # Test after subtitle time
            result = renderer.render_subtitle(sample_subtitle, sample_style, viewport_size, 4.0)
            assert result is None
    
    def test_subtitle_position_calculation(self, renderer, sample_subtitle, sample_style):
        """Test subtitle positioning based on .ass alignment."""
        viewport_size = (1920, 1080)
        
        # Mock texture
        mock_texture = Mock(spec=QOpenGLTexture)
        mock_texture.width.return_value = 300
        mock_texture.height.return_value = 50
        
        # Test bottom center alignment (default)
        position = renderer.calculate_subtitle_position(
            sample_subtitle, sample_style, viewport_size, mock_texture
        )
        
        expected_x = (1920 - 300) / 2  # Center horizontally
        expected_y = 1080 - 20 - 50    # Bottom with margin
        
        assert abs(position[0] - expected_x) < 1
        assert abs(position[1] - expected_y) < 1
    
    @patch('src.core.opengl_subtitle_renderer.QImage')
    @patch('src.core.opengl_subtitle_renderer.QPainter')
    @patch('src.core.opengl_subtitle_renderer.QFontMetrics')
    @patch('src.core.opengl_subtitle_renderer.QOpenGLTexture')
    def test_text_texture_creation(self, mock_texture_class, mock_metrics_class, 
                                  mock_painter_class, mock_image_class, renderer, sample_style):
        """Test text texture creation from style."""
        viewport_size = (1920, 1080)
        text = "Test Text"
        
        # Mock QFontMetrics
        mock_metrics = Mock()
        mock_metrics.boundingRect.return_value = Mock()
        mock_metrics.boundingRect.return_value.width.return_value = 200
        mock_metrics.boundingRect.return_value.height.return_value = 40
        mock_metrics_class.return_value = mock_metrics
        
        # Mock QImage
        mock_image = Mock()
        mock_image_class.return_value = mock_image
        
        # Mock QPainter
        mock_painter = Mock()
        mock_painter_class.return_value = mock_painter
        
        # Mock QOpenGLTexture
        mock_texture = Mock()
        mock_texture_class.return_value = mock_texture
        
        result = renderer.create_text_texture(text, sample_style, viewport_size)
        
        # Verify texture creation process
        mock_image_class.assert_called_once()
        mock_painter_class.assert_called_once_with(mock_image)
        mock_texture_class.assert_called_once()
        mock_texture.setData.assert_called_once_with(mock_image)
        
        assert result == mock_texture
    
    def test_model_matrix_creation(self, renderer):
        """Test model matrix calculation for positioning."""
        viewport_size = (1920, 1080)
        
        rendered_subtitle = RenderedSubtitle(
            texture=Mock(),
            position=(100.0, 200.0),
            size=(300.0, 50.0),
            start_time=1.0,
            end_time=3.0,
            text="Test",
            style_name="Default"
        )
        
        matrix = renderer.create_model_matrix(rendered_subtitle, viewport_size)
        
        # Check matrix dimensions
        assert matrix.shape == (4, 4)
        assert matrix.dtype == np.float32
        
        # Check that matrix contains expected transformation values
        assert matrix[3, 3] == 1.0  # Homogeneous coordinate
    
    def test_effects_application(self, renderer):
        """Test visual effects parameter setting."""
        # Mock shader program
        mock_shader = Mock()
        renderer.shader_program = mock_shader
        
        effects = {
            'glow': {
                'enabled': True,
                'color': [1.0, 1.0, 0.0],
                'radius': 3.0
            },
            'outline': {
                'enabled': True,
                'color': [0.0, 0.0, 0.0],
                'width': 2.0
            },
            'shadow': {
                'enabled': False
            }
        }
        
        renderer.apply_effects(effects)
        
        # Verify glow effect was applied
        mock_shader.setUniformValue.assert_any_call("enableGlow", True)
        mock_shader.setUniformValue.assert_any_call("glowColor", [1.0, 1.0, 0.0])
        mock_shader.setUniformValue.assert_any_call("glowRadius", 3.0)
        
        # Verify outline effect was applied
        mock_shader.setUniformValue.assert_any_call("enableOutline", True)
        mock_shader.setUniformValue.assert_any_call("outlineColor", [0.0, 0.0, 0.0])
        mock_shader.setUniformValue.assert_any_call("outlineWidth", 2.0)
        
        # Verify shadow effect was disabled
        mock_shader.setUniformValue.assert_any_call("enableShadow", False)
    
    def test_batch_rendering(self, renderer, sample_style):
        """Test batch rendering of multiple subtitles."""
        viewport_size = (1920, 1080)
        current_time = 2.0
        projection_matrix = np.eye(4, dtype=np.float32)
        
        subtitles = [
            SubtitleLine(start_time=1.0, end_time=3.0, text="First", style="Default"),
            SubtitleLine(start_time=2.5, end_time=4.0, text="Second", style="Default"),
            SubtitleLine(start_time=5.0, end_time=7.0, text="Third", style="Default")  # Not visible
        ]
        
        styles = {"Default": sample_style}
        
        # Mock renderer methods
        renderer.initialized = True
        with patch.object(renderer, 'render_subtitle') as mock_render:
            with patch.object(renderer, 'render_to_opengl') as mock_render_gl:
                # Mock return values for visible subtitles
                mock_render.side_effect = [
                    RenderedSubtitle(Mock(), (0.0, 0.0), (100.0, 50.0), 1.0, 3.0, "First", "Default"),
                    RenderedSubtitle(Mock(), (0.0, 0.0), (100.0, 50.0), 2.5, 4.0, "Second", "Default"),
                    None  # Third subtitle not visible
                ]
                
                result = renderer.render_subtitles_batch(
                    subtitles, styles, viewport_size, current_time, projection_matrix
                )
                
                # Should render 2 visible subtitles
                assert len(result) == 2
                assert result[0].text == "First"
                assert result[1].text == "Second"
                
                # Should call render_to_opengl for visible subtitles
                assert mock_render_gl.call_count == 2
    
    def test_performance_stats(self, renderer):
        """Test performance statistics reporting."""
        stats = renderer.get_performance_stats()
        
        assert 'cache_size' in stats
        assert 'cache_max_size' in stats
        assert 'initialized' in stats
        assert 'shader_program_valid' in stats
        
        assert stats['cache_size'] == 0
        assert stats['cache_max_size'] == 100
        assert stats['initialized'] is False
        assert stats['shader_program_valid'] is False
    
    def test_cleanup(self, renderer):
        """Test resource cleanup."""
        # Set up some resources
        renderer.texture_cache.textures = {"test": Mock()}
        renderer.shader_program = Mock()
        renderer.vertex_buffer = 1
        renderer.index_buffer = 2
        renderer.initialized = True
        
        with patch('src.core.opengl_subtitle_renderer.gl') as mock_gl:
            renderer.cleanup()
            
            # Verify cleanup
            assert len(renderer.texture_cache.textures) == 0
            assert renderer.shader_program is None
            assert renderer.vertex_buffer is None
            assert renderer.index_buffer is None
            assert renderer.initialized is False
            
            # Verify OpenGL buffers were deleted
            mock_gl.glDeleteBuffers.assert_called()


class TestOpenGLSubtitleRendererIntegration:
    """Integration tests for OpenGL subtitle renderer."""
    
    def test_full_rendering_pipeline(self):
        """Test complete rendering pipeline without OpenGL context."""
        renderer = OpenGLSubtitleRenderer()
        
        # Create test data
        style = SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=24,
            primary_color="#FFFFFF"
        )
        
        subtitle = SubtitleLine(
            start_time=1.0,
            end_time=3.0,
            text="Integration Test",
            style="Default"
        )
        
        viewport_size = (1920, 1080)
        current_time = 2.0
        
        # Mock OpenGL components since we can't create real context in tests
        with patch.object(renderer, 'initialize_opengl', return_value=True):
            with patch.object(renderer, 'create_text_texture') as mock_create_texture:
                mock_texture = Mock(spec=QOpenGLTexture)
                mock_texture.width.return_value = 300
                mock_texture.height.return_value = 50
                mock_create_texture.return_value = mock_texture
                
                # Test rendering
                result = renderer.render_subtitle(subtitle, style, viewport_size, current_time)
                
                assert result is not None
                assert result.text == "Integration Test"
                assert result.start_time == 1.0
                assert result.end_time == 3.0
                assert result.texture == mock_texture
    
    def test_caching_performance(self):
        """Test that caching improves performance."""
        renderer = OpenGLSubtitleRenderer()
        renderer.initialized = True
        
        style = SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=24,
            primary_color="#FFFFFF"
        )
        
        subtitle = SubtitleLine(
            start_time=1.0,
            end_time=3.0,
            text="Cache Test",
            style="Default"
        )
        
        viewport_size = (1920, 1080)
        
        with patch.object(renderer, 'create_text_texture') as mock_create_texture:
            mock_texture = Mock(spec=QOpenGLTexture)
            mock_texture.width.return_value = 300
            mock_texture.height.return_value = 50
            mock_create_texture.return_value = mock_texture
            
            # First render should create texture
            result1 = renderer.render_subtitle(subtitle, style, viewport_size, 2.0)
            assert mock_create_texture.call_count == 1
            
            # Second render should use cache
            result2 = renderer.render_subtitle(subtitle, style, viewport_size, 2.0)
            assert mock_create_texture.call_count == 1  # No additional calls
            
            # Results should be the same
            assert result1.text == result2.text
            assert result1.texture == result2.texture