"""
Unit tests for libass integration system.

Tests the libass integration functionality including context initialization,
ASS file loading, karaoke timing extraction, and bitmap texture generation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import ctypes

from src.core.libass_integration import (
    LibassContext, LibassIntegration, LibassImage, LibassError,
    create_libass_context, load_ass_file_with_libass
)
from src.core.models import SubtitleFile, SubtitleLine, KaraokeTimingInfo, WordTiming


class TestLibassImage:
    """Test LibassImage data structure and conversion methods."""
    
    def test_libass_image_creation(self):
        """Test creating a LibassImage object."""
        image = LibassImage(
            width=100,
            height=50,
            stride=100,
            bitmap=b'\xFF' * (100 * 50),
            dst_x=10,
            dst_y=20,
            color=0xFFFFFFFF
        )
        
        assert image.width == 100
        assert image.height == 50
        assert image.stride == 100
        assert len(image.bitmap) == 5000
        assert image.dst_x == 10
        assert image.dst_y == 20
        assert image.color == 0xFFFFFFFF
    
    def test_to_rgba_bytes_conversion(self):
        """Test conversion of libass bitmap to RGBA format."""
        # Create a small test image
        image = LibassImage(
            width=2,
            height=2,
            stride=2,
            bitmap=b'\xFF\x80\x40\x00',  # 4 pixels with different intensities
            dst_x=0,
            dst_y=0,
            color=0xFF0000FF  # Red color with full alpha
        )
        
        rgba_bytes = image.to_rgba_bytes()
        
        # Should have 4 pixels * 4 bytes (RGBA) = 16 bytes
        assert len(rgba_bytes) == 16
        
        # Check first pixel (intensity 255, should be full red)
        assert rgba_bytes[0] == 255  # R
        assert rgba_bytes[1] == 0    # G
        assert rgba_bytes[2] == 0    # B
        assert rgba_bytes[3] == 255  # A
    
    def test_to_rgba_bytes_with_different_colors(self):
        """Test RGBA conversion with different color values."""
        # Green color
        image = LibassImage(
            width=1,
            height=1,
            stride=1,
            bitmap=b'\xFF',
            dst_x=0,
            dst_y=0,
            color=0xFF00FF00  # Green color
        )
        
        rgba_bytes = image.to_rgba_bytes()
        
        assert rgba_bytes[0] == 0    # R
        assert rgba_bytes[1] == 255  # G
        assert rgba_bytes[2] == 0    # B
        assert rgba_bytes[3] == 255  # A


class TestLibassContext:
    """Test LibassContext initialization and basic operations."""
    
    def test_context_creation_without_libass(self):
        """Test context creation when libass library is not available."""
        with patch('src.core.libass_integration.ctypes.util.find_library', return_value=None):
            with patch('src.core.libass_integration.ctypes.CDLL', side_effect=OSError):
                context = LibassContext(1920, 1080)
                
                assert context.width == 1920
                assert context.height == 1080
                assert context._libass is None
                assert not context.is_available()
    
    @patch('src.core.libass_integration.ctypes.util.find_library')
    @patch('src.core.libass_integration.ctypes.CDLL')
    def test_context_creation_with_libass(self, mock_cdll, mock_find_library):
        """Test context creation when libass library is available."""
        # Mock libass library
        mock_lib = Mock()
        mock_cdll.return_value = mock_lib
        mock_find_library.return_value = '/usr/lib/libass.so'
        
        # Mock libass functions
        mock_lib.ass_library_init.return_value = ctypes.c_void_p(12345)
        mock_lib.ass_renderer_init.return_value = ctypes.c_void_p(67890)
        
        # Mock function prototypes
        mock_lib.ass_library_init.restype = ctypes.c_void_p
        mock_lib.ass_renderer_init.restype = ctypes.c_void_p
        mock_lib.ass_renderer_init.argtypes = [ctypes.c_void_p]
        
        context = LibassContext(1920, 1080)
        
        assert context.width == 1920
        assert context.height == 1080
        assert context._libass is not None
    
    def test_load_subtitle_file_without_libass(self):
        """Test loading subtitle file when libass is not available."""
        context = LibassContext()
        context._libass = None
        
        result = context.load_subtitle_file("test.ass")
        assert result is False
    
    def test_render_frame_without_libass(self):
        """Test rendering frame when libass is not available."""
        context = LibassContext()
        context._libass = None
        
        images = context.render_frame(1000)
        assert images == []
    
    def test_extract_karaoke_timing(self):
        """Test extracting karaoke timing from subtitle file."""
        context = LibassContext()
        
        # Create test subtitle file with karaoke timing
        word_timings = [
            WordTiming("Hello", 0.0, 0.5),
            WordTiming("world", 0.5, 1.0)
        ]
        
        subtitle_line = SubtitleLine(
            start_time=0.0,
            end_time=1.0,
            text="Hello world",
            word_timings=word_timings,
            has_karaoke_tags=True
        )
        
        subtitle_file = SubtitleFile(
            path="test.ass",
            lines=[subtitle_line]
        )
        
        karaoke_data = context.extract_karaoke_timing(subtitle_file)
        
        assert len(karaoke_data) == 1
        assert karaoke_data[0].start_time == 0.0
        assert karaoke_data[0].end_time == 1.0
        assert karaoke_data[0].text == "Hello world"
        assert karaoke_data[0].syllable_count == 2
        assert karaoke_data[0].syllable_timings == [0.5, 0.5]
    
    def test_cleanup(self):
        """Test cleanup of libass resources."""
        context = LibassContext()
        
        # Mock libass objects
        context._libass = Mock()
        context.library = ctypes.c_void_p(12345)
        context.renderer = ctypes.c_void_p(67890)
        context.track = ctypes.c_void_p(11111)
        
        context.cleanup()
        
        # Verify cleanup was called
        context._libass.ass_free_track.assert_called_once()
        context._libass.ass_renderer_done.assert_called_once()
        context._libass.ass_library_done.assert_called_once()
        
        assert context.track is None
        assert context.renderer is None
        assert context.library is None


class TestLibassIntegration:
    """Test high-level LibassIntegration interface."""
    
    def test_integration_initialization(self):
        """Test LibassIntegration initialization."""
        integration = LibassIntegration(1920, 1080)
        
        assert integration.width == 1920
        assert integration.height == 1080
        assert integration.context is not None
        assert integration.current_subtitle_file is None
    
    def test_load_and_parse_subtitle_file_success(self):
        """Test successful loading and parsing of subtitle file."""
        # Create a temporary ASS file
        ass_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\k25}Hello{\\k30}world
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            
            subtitle_file, karaoke_data = integration.load_and_parse_subtitle_file(temp_file)
            
            assert subtitle_file is not None
            assert subtitle_file.path == temp_file
            assert len(subtitle_file.lines) == 1
            assert subtitle_file.lines[0].text == "Hello world"
            assert len(subtitle_file.lines[0].word_timings) == 2
            
            assert isinstance(karaoke_data, list)
            assert integration.current_subtitle_file == subtitle_file
            
        finally:
            os.unlink(temp_file)
    
    def test_load_and_parse_subtitle_file_with_errors(self):
        """Test loading subtitle file with parsing errors."""
        # Create a malformed ASS file
        ass_content = """[Script Info]
Title: Test

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,invalid_time,0:00:02.00,Default,,0,0,0,,Test text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            
            with pytest.raises(LibassError):
                integration.load_and_parse_subtitle_file(temp_file)
                
        finally:
            os.unlink(temp_file)
    
    def test_load_nonexistent_file(self):
        """Test loading a non-existent subtitle file."""
        integration = LibassIntegration()
        
        with pytest.raises(LibassError):
            integration.load_and_parse_subtitle_file("nonexistent.ass")
    
    def test_render_subtitle_frame_without_libass(self):
        """Test rendering subtitle frame when libass is not available."""
        integration = LibassIntegration()
        integration.context._libass = None
        
        images = integration.render_subtitle_frame(1.0)
        assert images == []
    
    def test_generate_bitmap_textures(self):
        """Test generating bitmap textures for multiple timestamps."""
        integration = LibassIntegration()
        
        # Mock the render_subtitle_frame method
        mock_image = LibassImage(100, 50, 100, b'\xFF' * 5000, 0, 0, 0xFFFFFFFF)
        integration.render_subtitle_frame = Mock(return_value=[mock_image])
        
        timestamps = [0.0, 1.0, 2.0]
        textures = integration.generate_bitmap_textures(timestamps)
        
        assert len(textures) == 3
        assert 0.0 in textures
        assert 1.0 in textures
        assert 2.0 in textures
        
        for timestamp in timestamps:
            assert len(textures[timestamp]) == 1
            assert textures[timestamp][0] == mock_image
    
    def test_generate_bitmap_textures_empty_results(self):
        """Test generating bitmap textures when rendering returns empty results."""
        integration = LibassIntegration()
        integration.render_subtitle_frame = Mock(return_value=[])
        
        timestamps = [0.0, 1.0]
        textures = integration.generate_bitmap_textures(timestamps)
        
        assert len(textures) == 0
    
    def test_get_font_info(self):
        """Test getting font information."""
        integration = LibassIntegration()
        
        font_info = integration.get_font_info()
        
        assert isinstance(font_info, dict)
        assert "libass_available" in font_info
        assert "default_font" in font_info
        assert "font_scale" in font_info
        assert font_info["default_font"] == "Arial"
        assert font_info["font_scale"] == 1.0
    
    def test_validate_ass_format_valid_file(self):
        """Test validating a valid ASS file format."""
        # Create a valid ASS file
        ass_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Test text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            
            is_valid, errors = integration.validate_ass_format(temp_file)
            
            assert is_valid is True
            assert len(errors) == 0 or all("Warning" in error for error in errors)
            
        finally:
            os.unlink(temp_file)
    
    def test_validate_ass_format_invalid_file(self):
        """Test validating an invalid ASS file format."""
        # Create an invalid ASS file
        ass_content = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,invalid_time,0:00:02.00,Default,,0,0,0,,Test text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            integration = LibassIntegration()
            
            is_valid, errors = integration.validate_ass_format(temp_file)
            
            assert is_valid is False
            assert len(errors) > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_validate_nonexistent_file(self):
        """Test validating a non-existent file."""
        integration = LibassIntegration()
        
        is_valid, errors = integration.validate_ass_format("nonexistent.ass")
        
        assert is_valid is False
        assert len(errors) > 0
        assert "Validation failed" in errors[0]
    
    def test_cleanup(self):
        """Test cleanup of integration resources."""
        integration = LibassIntegration()
        integration.context.cleanup = Mock()
        
        integration.cleanup()
        
        integration.context.cleanup.assert_called_once()


class TestKaraokeTimingExtraction:
    """Test karaoke timing extraction functionality."""
    
    def test_extract_timing_from_word_timings(self):
        """Test extracting karaoke timing from word timings."""
        context = LibassContext()
        
        # Create subtitle with word timings
        word_timings = [
            WordTiming("Ka", 0.0, 0.25),
            WordTiming("ra", 0.25, 0.5),
            WordTiming("o", 0.5, 0.75),
            WordTiming("ke", 0.75, 1.0)
        ]
        
        subtitle_line = SubtitleLine(
            start_time=0.0,
            end_time=1.0,
            text="Karaoke",
            word_timings=word_timings,
            has_karaoke_tags=True
        )
        
        subtitle_file = SubtitleFile(lines=[subtitle_line])
        karaoke_data = context.extract_karaoke_timing(subtitle_file)
        
        assert len(karaoke_data) == 1
        timing_info = karaoke_data[0]
        
        assert timing_info.start_time == 0.0
        assert timing_info.end_time == 1.0
        assert timing_info.text == "Karaoke"
        assert timing_info.syllable_count == 4
        assert timing_info.syllable_timings == [0.25, 0.25, 0.25, 0.25]
    
    def test_extract_timing_without_word_timings(self):
        """Test extracting timing from lines without word timings."""
        context = LibassContext()
        
        subtitle_line = SubtitleLine(
            start_time=0.0,
            end_time=2.0,
            text="No karaoke timing",
            word_timings=[]
        )
        
        subtitle_file = SubtitleFile(lines=[subtitle_line])
        karaoke_data = context.extract_karaoke_timing(subtitle_file)
        
        # Should not create karaoke data for lines without word timings
        assert len(karaoke_data) == 0
    
    def test_extract_timing_multiple_lines(self):
        """Test extracting timing from multiple subtitle lines."""
        context = LibassContext()
        
        lines = [
            SubtitleLine(
                start_time=0.0,
                end_time=1.0,
                text="First line",
                word_timings=[
                    WordTiming("First", 0.0, 0.5),
                    WordTiming("line", 0.5, 1.0)
                ],
                has_karaoke_tags=True
            ),
            SubtitleLine(
                start_time=1.0,
                end_time=2.0,
                text="Second line",
                word_timings=[],  # No karaoke timing
                has_karaoke_tags=False
            ),
            SubtitleLine(
                start_time=2.0,
                end_time=3.0,
                text="Third line",
                word_timings=[
                    WordTiming("Third", 2.0, 2.5),
                    WordTiming("line", 2.5, 3.0)
                ],
                has_karaoke_tags=True
            )
        ]
        
        subtitle_file = SubtitleFile(lines=lines)
        karaoke_data = context.extract_karaoke_timing(subtitle_file)
        
        # Should only extract timing from lines with word timings
        assert len(karaoke_data) == 2
        assert karaoke_data[0].text == "First line"
        assert karaoke_data[1].text == "Third line"


class TestConvenienceFunctions:
    """Test convenience functions for libass integration."""
    
    def test_create_libass_context(self):
        """Test creating libass context using convenience function."""
        context = create_libass_context(1280, 720)
        
        assert isinstance(context, LibassContext)
        assert context.width == 1280
        assert context.height == 720
    
    def test_create_libass_context_default_size(self):
        """Test creating libass context with default size."""
        context = create_libass_context()
        
        assert isinstance(context, LibassContext)
        assert context.width == 1920
        assert context.height == 1080
    
    def test_load_ass_file_with_libass_success(self):
        """Test loading ASS file using convenience function."""
        # Create a temporary ASS file
        ass_content = """[Script Info]
Title: Test

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Test text
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ass', delete=False, encoding='utf-8') as f:
            f.write(ass_content)
            temp_file = f.name
        
        try:
            subtitle_file, karaoke_data = load_ass_file_with_libass(temp_file, 1280, 720)
            
            assert isinstance(subtitle_file, SubtitleFile)
            assert isinstance(karaoke_data, list)
            assert subtitle_file.path == temp_file
            
        finally:
            os.unlink(temp_file)
    
    def test_load_ass_file_with_libass_failure(self):
        """Test loading non-existent ASS file using convenience function."""
        with pytest.raises(LibassError):
            load_ass_file_with_libass("nonexistent.ass")


class TestLibassError:
    """Test LibassError exception class."""
    
    def test_libass_error_creation(self):
        """Test creating LibassError exception."""
        error = LibassError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_libass_error_raising(self):
        """Test raising LibassError exception."""
        with pytest.raises(LibassError) as exc_info:
            raise LibassError("Custom error")
        
        assert str(exc_info.value) == "Custom error"


if __name__ == "__main__":
    pytest.main([__file__])