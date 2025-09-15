"""
Test Complete Rendering Pipeline Integration

This module tests the complete rendering pipeline integration that combines
libass, OpenGL effects, and FFmpeg export systems into a unified workflow.
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage

from src.core.complete_rendering_pipeline import (
    CompleteRenderingPipeline, PipelineConfig, PipelineState, PipelineStage,
    SynchronizationMode, create_rendering_pipeline, create_preview_pipeline,
    create_export_pipeline
)
from src.core.models import Project, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle


@pytest.fixture
def app():
    """Create QApplication for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return Project(
        id="test_pipeline",
        name="Test Pipeline Project",
        audio_file=AudioFile(path="test.mp3", duration=30.0),
        subtitle_file=SubtitleFile(
            path="test.ass",
            lines=[
                SubtitleLine(start_time=1.0, end_time=5.0, text="Test subtitle 1"),
                SubtitleLine(start_time=5.0, end_time=10.0, text="Test subtitle 2"),
                SubtitleLine(start_time=10.0, end_time=15.0, text="Test subtitle 3")
            ],
            styles=[SubtitleStyle(name="Default")]
        )
    )


@pytest.fixture
def pipeline_config():
    """Create test pipeline configuration."""
    return PipelineConfig(
        width=1280,
        height=720,
        fps=30.0,
        quality_preset="medium",
        enable_effects=True,
        use_threading=False,  # Disable threading for testing
        max_threads=1,
        buffer_size=5
    )


def test_pipeline_creation(app):
    """Test pipeline creation with different configurations."""
    # Test default pipeline
    pipeline = create_rendering_pipeline()
    assert pipeline is not None
    assert isinstance(pipeline.config, PipelineConfig)
    assert pipeline.state.current_stage == PipelineStage.INITIALIZATION
    
    # Test preview pipeline
    preview_pipeline = create_preview_pipeline(1920, 1080)
    assert preview_pipeline.config.width == 1920
    assert preview_pipeline.config.height == 1080
    assert preview_pipeline.config.quality_preset == "medium"
    
    # Test export pipeline
    export_pipeline = create_export_pipeline(1920, 1080, 60.0)
    assert export_pipeline.config.fps == 60.0
    assert export_pipeline.config.quality_preset == "high"
    
    # Cleanup
    pipeline.cleanup()
    preview_pipeline.cleanup()
    export_pipeline.cleanup()


def test_pipeline_state_management(app, pipeline_config):
    """Test pipeline state management."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Test initial state
    state = pipeline.get_pipeline_state()
    assert state.current_stage == PipelineStage.INITIALIZATION
    assert state.current_frame == 0
    assert state.total_frames == 0
    assert not state.is_running
    assert not state.is_paused
    assert state.error_message is None
    
    # Test progress calculation
    state.current_frame = 50
    state.total_frames = 100
    assert state.get_progress_percent() == 50.0
    
    # Test edge cases
    state.total_frames = 0
    assert state.get_progress_percent() == 0.0
    
    pipeline.cleanup()


@patch('src.core.complete_rendering_pipeline.FrameCaptureSystem')
@patch('src.core.complete_rendering_pipeline.EnhancedFFmpegProcessor')
@patch('src.core.complete_rendering_pipeline.PreviewSynchronizer')
@patch('src.core.complete_rendering_pipeline.OpenGLContext')
@patch('src.core.complete_rendering_pipeline.LibassIntegration')
@patch('src.core.complete_rendering_pipeline.EffectsRenderingPipeline')
def test_pipeline_initialization(mock_effects, mock_libass, mock_opengl, 
                                mock_preview, mock_ffmpeg, mock_frame_capture,
                                app, sample_project, pipeline_config):
    """Test pipeline initialization with mocked components."""
    # Setup mocks
    mock_opengl_instance = Mock()
    mock_opengl_instance.create_framebuffer.return_value = Mock()
    mock_opengl.return_value = mock_opengl_instance
    
    mock_libass_instance = Mock()
    mock_libass_instance.initialize.return_value = True
    mock_libass_instance.load_subtitle_file.return_value = True
    mock_libass.return_value = mock_libass_instance
    
    mock_effects_instance = Mock()
    mock_effects.return_value = mock_effects_instance
    
    mock_frame_capture_instance = Mock()
    mock_frame_capture_instance.initialize.return_value = True
    mock_frame_capture.return_value = mock_frame_capture_instance
    
    mock_ffmpeg_instance = Mock()
    mock_ffmpeg_instance.get_capabilities.return_value = Mock(available=True)
    mock_ffmpeg.return_value = mock_ffmpeg_instance
    
    mock_preview_instance = Mock()
    mock_preview_instance.load_project.return_value = True
    mock_preview.return_value = mock_preview_instance
    
    # Test initialization
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    with patch('src.core.opengl_context.create_offscreen_context') as mock_create_context:
        mock_create_context.return_value = mock_opengl_instance
        
        success = pipeline.initialize(sample_project)
        assert success
        assert pipeline.current_project == sample_project
        assert pipeline.opengl_context == mock_opengl_instance
        assert pipeline.libass_integration == mock_libass_instance
        assert pipeline.effects_pipeline == mock_effects_instance
        assert pipeline.frame_capture_system == mock_frame_capture_instance
        assert pipeline.ffmpeg_processor == mock_ffmpeg_instance
        assert pipeline.preview_synchronizer == mock_preview_instance
    
    pipeline.cleanup()


def test_frame_timestamp_generation(app, sample_project, pipeline_config):
    """Test frame timestamp generation."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    pipeline.current_project = sample_project
    
    # Test timestamp generation
    pipeline._generate_frame_timestamps()
    
    # Should generate timestamps for audio duration (30s) at 30fps
    expected_frames = int(30.0 * 30.0)  # 30 seconds * 30 fps
    assert len(pipeline.frame_timestamps) == expected_frames
    assert pipeline.state.total_frames == expected_frames
    
    # Check timestamp values
    assert pipeline.frame_timestamps[0] == 0.0
    assert abs(pipeline.frame_timestamps[1] - (1.0/30.0)) < 0.001
    assert pipeline.frame_timestamps[-1] < 30.0
    
    pipeline.cleanup()


def test_karaoke_timing_map_building(app, sample_project, pipeline_config):
    """Test karaoke timing map building."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    pipeline.current_project = sample_project
    
    # Generate timestamps first
    pipeline._generate_frame_timestamps()
    
    # Add karaoke timing to subtitles
    for subtitle in sample_project.subtitle_file.lines:
        subtitle.karaoke_timing = Mock()
        subtitle.karaoke_timing.start_time = subtitle.start_time
        subtitle.karaoke_timing.end_time = subtitle.end_time
    
    # Build timing map
    pipeline._build_karaoke_timing_map()
    
    # Check that timing map contains entries for subtitle time ranges
    timing_timestamps = [ts for ts in pipeline.karaoke_timing_map.keys()]
    assert len(timing_timestamps) > 0
    
    # Check that timestamps within subtitle ranges have timing info
    for timestamp in pipeline.frame_timestamps:
        if 1.0 <= timestamp <= 15.0:  # Within subtitle time range
            if timestamp in pipeline.karaoke_timing_map:
                assert pipeline.karaoke_timing_map[timestamp] is not None
    
    pipeline.cleanup()


@patch('src.core.complete_rendering_pipeline.PreviewSynchronizer')
def test_preview_mode(mock_preview_sync, app, sample_project, pipeline_config):
    """Test preview mode functionality."""
    # Setup mock
    mock_sync_instance = Mock()
    mock_sync_instance.load_project.return_value = True
    mock_preview_sync.return_value = mock_sync_instance
    
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock initialization components
    with patch.object(pipeline, '_initialize_opengl_context', return_value=True), \
         patch.object(pipeline, '_initialize_libass_integration', return_value=True), \
         patch.object(pipeline, '_initialize_effects_pipeline', return_value=True), \
         patch.object(pipeline, '_initialize_frame_capture_system', return_value=True), \
         patch.object(pipeline, '_initialize_ffmpeg_processor', return_value=True):
        
        success = pipeline.initialize(sample_project)
        assert success
        
        # Test preview mode start
        success = pipeline.start_rendering("", preview_mode=True)
        assert success
        
        # Verify preview synchronizer was called
        mock_sync_instance.play.assert_called_once()
    
    pipeline.cleanup()


def test_performance_stats(app, pipeline_config):
    """Test performance statistics collection."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Add some mock render times
    pipeline.render_times = [0.016, 0.017, 0.015, 0.018, 0.016]  # ~60fps
    pipeline.state.frames_rendered = 100
    pipeline.state.frames_dropped = 2
    
    stats = pipeline.get_performance_stats()
    
    # Check pipeline state stats
    assert 'pipeline_state' in stats
    pipeline_stats = stats['pipeline_state']
    assert pipeline_stats['frames_rendered'] == 100
    assert pipeline_stats['frames_dropped'] == 2
    assert pipeline_stats['is_running'] == False
    assert pipeline_stats['is_paused'] == False
    
    pipeline.cleanup()


def test_pipeline_pause_resume(app, sample_project, pipeline_config):
    """Test pipeline pause and resume functionality."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock preview synchronizer
    mock_sync = Mock()
    pipeline.preview_synchronizer = mock_sync
    
    # Test pause
    pipeline.state.is_running = True
    pipeline.state.is_paused = False
    pipeline.pause_rendering()
    
    assert pipeline.state.is_paused == True
    mock_sync.pause.assert_called_once()
    
    # Test resume
    pipeline.resume_rendering()
    
    assert pipeline.state.is_paused == False
    mock_sync.play.assert_called_once()
    
    pipeline.cleanup()


def test_pipeline_stop(app, pipeline_config):
    """Test pipeline stop functionality."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock components
    mock_sync = Mock()
    mock_ffmpeg = Mock()
    pipeline.preview_synchronizer = mock_sync
    pipeline.ffmpeg_processor = mock_ffmpeg
    
    # Set running state
    pipeline.state.is_running = True
    
    # Test stop
    pipeline.stop_rendering()
    
    assert pipeline.state.is_running == False
    assert pipeline.state.is_paused == False
    mock_sync.stop.assert_called_once()
    
    pipeline.cleanup()


def test_seek_functionality(app, pipeline_config):
    """Test seek functionality in preview mode."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock preview synchronizer
    mock_sync = Mock()
    pipeline.preview_synchronizer = mock_sync
    
    # Test seek
    timestamp = 15.5
    pipeline.seek_to_time(timestamp)
    
    mock_sync.seek_to_time.assert_called_once_with(timestamp)
    
    pipeline.cleanup()


@patch('src.core.complete_rendering_pipeline.EnhancedFFmpegProcessor')
def test_ffmpeg_integration(mock_ffmpeg_class, app, sample_project, pipeline_config):
    """Test FFmpeg integration for video export."""
    # Setup mock
    mock_ffmpeg_instance = Mock()
    mock_ffmpeg_instance.get_capabilities.return_value = Mock(available=True)
    mock_ffmpeg_instance.start_encoding.return_value = True
    mock_ffmpeg_class.return_value = mock_ffmpeg_instance
    
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock other initialization components
    with patch.object(pipeline, '_initialize_opengl_context', return_value=True), \
         patch.object(pipeline, '_initialize_libass_integration', return_value=True), \
         patch.object(pipeline, '_initialize_effects_pipeline', return_value=True), \
         patch.object(pipeline, '_initialize_frame_capture_system', return_value=True), \
         patch.object(pipeline, '_initialize_preview_synchronizer', return_value=True):
        
        success = pipeline.initialize(sample_project)
        assert success
        assert pipeline.ffmpeg_processor == mock_ffmpeg_instance
        
        # Test capabilities check
        mock_ffmpeg_instance.get_capabilities.assert_called_once()
    
    pipeline.cleanup()


def test_memory_management(app, pipeline_config):
    """Test memory management and resource cleanup."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Add mock resources
    mock_resource1 = Mock()
    mock_resource2 = Mock()
    pipeline.allocated_resources = [mock_resource1, mock_resource2]
    
    # Add cleanup callback
    cleanup_called = False
    def cleanup_callback():
        nonlocal cleanup_called
        cleanup_called = True
    
    pipeline.cleanup_callbacks.append(cleanup_callback)
    
    # Test cleanup
    pipeline.cleanup()
    
    # Verify resources were cleaned up
    mock_resource1.cleanup.assert_called_once()
    mock_resource2.cleanup.assert_called_once()
    
    # Verify callback was called
    assert cleanup_called == True
    
    # Verify collections were cleared
    assert len(pipeline.allocated_resources) == 0
    assert len(pipeline.cleanup_callbacks) == 0
    assert len(pipeline.frame_timestamps) == 0
    assert len(pipeline.karaoke_timing_map) == 0


def test_error_handling(app, sample_project, pipeline_config):
    """Test error handling in pipeline initialization and rendering."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Test initialization failure
    with patch.object(pipeline, '_initialize_opengl_context', return_value=False):
        success = pipeline.initialize(sample_project)
        assert success == False
        assert pipeline.state.error_message is not None
    
    pipeline.cleanup()


def test_frame_generation_mock(app, sample_project, pipeline_config):
    """Test frame generation with mocked components."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    pipeline.current_project = sample_project
    
    # Generate timestamps
    pipeline._generate_frame_timestamps()
    
    # Mock frame capture system
    mock_frame = Mock()
    mock_frame.to_dict.return_value = {'frame_number': 1, 'timestamp': 0.0}
    
    mock_capture_system = Mock()
    mock_capture_system.rendering_engine.render_frame_at_timestamp.return_value = mock_frame
    pipeline.frame_capture_system = mock_capture_system
    
    # Mock effects pipeline
    mock_effects = Mock()
    mock_effects.render_frame.return_value = True
    pipeline.effects_pipeline = mock_effects
    
    # Test frame generation
    frame = pipeline._generate_next_frame()
    
    assert frame == mock_frame
    assert pipeline.state.current_frame == 1
    assert pipeline.state.frames_rendered == 1
    
    pipeline.cleanup()


def test_subtitle_texture_rendering(app, sample_project, pipeline_config):
    """Test subtitle texture rendering."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    pipeline.current_project = sample_project
    
    # Mock libass integration
    mock_libass = Mock()
    pipeline.libass_integration = mock_libass
    
    # Test subtitle texture rendering
    timestamp = 2.5  # Within first subtitle range
    texture = pipeline._render_subtitle_texture(timestamp)
    
    # Should return None for now (placeholder implementation)
    assert texture is None
    
    pipeline.cleanup()


def test_effects_integration(app, sample_project, pipeline_config):
    """Test effects pipeline integration."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Mock effects pipeline
    mock_effects = Mock()
    pipeline.effects_pipeline = mock_effects
    
    # Test frame rendering with effects
    timestamp = 1.5
    result = pipeline._render_frame_at_timestamp(timestamp)
    
    # Verify effects pipeline was called
    mock_effects.update_animation_time.assert_called_with(timestamp)
    mock_effects.render_frame.assert_called_once()
    
    pipeline.cleanup()


def test_signal_emissions(app, sample_project, pipeline_config):
    """Test that pipeline emits appropriate signals."""
    pipeline = CompleteRenderingPipeline(pipeline_config)
    
    # Connect signal handlers
    stage_changes = []
    progress_updates = []
    
    pipeline.stage_changed.connect(lambda stage: stage_changes.append(stage))
    pipeline.progress_updated.connect(lambda progress: progress_updates.append(progress))
    
    # Mock successful initialization
    with patch.object(pipeline, '_initialize_opengl_context', return_value=True), \
         patch.object(pipeline, '_initialize_libass_integration', return_value=True), \
         patch.object(pipeline, '_initialize_effects_pipeline', return_value=True), \
         patch.object(pipeline, '_initialize_frame_capture_system', return_value=True), \
         patch.object(pipeline, '_initialize_ffmpeg_processor', return_value=True), \
         patch.object(pipeline, '_initialize_preview_synchronizer', return_value=True):
        
        success = pipeline.initialize(sample_project)
        assert success
        
        # Check that initialization stage was emitted
        assert PipelineStage.INITIALIZATION.value in stage_changes
    
    pipeline.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])