"""
Complete Rendering Pipeline Integration

This module integrates libass, OpenGL effects, and FFmpeg export systems into a unified
end-to-end rendering workflow from ASS to MP4. It provides timing synchronization across
all components, memory management, resource cleanup, and comprehensive integration testing.
"""

import os
import time
import threading
import queue
from typing import Optional, Dict, List, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import logging

# Configure logging
logger = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
    from PyQt6.QtGui import QImage
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None

try:
    from .libass_integration import LibassIntegration, LibassContext
    from .opengl_context import OpenGLContext, OpenGLFramebuffer, FramebufferConfig
    from .effects_rendering_pipeline import EffectsRenderingPipeline, RenderingStage
    from .frame_capture_system import FrameCaptureSystem, FrameCaptureSettings, CapturedFrame
    from .enhanced_ffmpeg_integration import EnhancedFFmpegProcessor, EnhancedExportSettings
    from .libass_opengl_integration import LibassOpenGLIntegration, TextureCache
    from .models import Project, SubtitleLine, SubtitleStyle, KaraokeTimingInfo
    from .preview_synchronizer import PreviewSynchronizer, SyncState
except ImportError:
    # For testing without full imports
    import sys
    sys.path.append(os.path.dirname(__file__))
    from libass_integration import LibassIntegration, LibassContext
    from opengl_context import OpenGLContext, OpenGLFramebuffer, FramebufferConfig
    from effects_rendering_pipeline import EffectsRenderingPipeline, RenderingStage
    from frame_capture_system import FrameCaptureSystem, FrameCaptureSettings, CapturedFrame
    from enhanced_ffmpeg_integration import EnhancedFFmpegProcessor, EnhancedExportSettings
    from models import Project, SubtitleLine, SubtitleStyle, KaraokeTimingInfo


class PipelineStage(Enum):
    """Rendering pipeline stages"""
    INITIALIZATION = "initialization"
    SUBTITLE_PROCESSING = "subtitle_processing"
    EFFECTS_RENDERING = "effects_rendering"
    FRAME_CAPTURE = "frame_capture"
    VIDEO_ENCODING = "video_encoding"
    CLEANUP = "cleanup"


class SynchronizationMode(Enum):
    """Timing synchronization modes"""
    AUDIO_MASTER = "audio_master"
    VIDEO_MASTER = "video_master"
    MANUAL = "manual"


@dataclass
class PipelineConfig:
    """Configuration for the complete rendering pipeline"""
    # Video settings
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    duration: float = 0.0
    
    # Quality settings
    quality_preset: str = "high"
    enable_effects: bool = True
    enable_antialiasing: bool = True
    
    # Performance settings
    use_threading: bool = True
    max_threads: int = 4
    buffer_size: int = 10
    
    # Synchronization
    sync_mode: SynchronizationMode = SynchronizationMode.AUDIO_MASTER
    audio_offset: float = 0.0
    
    # Memory management
    max_texture_cache_size: int = 100
    enable_memory_optimization: bool = True
    
    # Debug settings
    enable_debug_output: bool = False
    save_intermediate_frames: bool = False


@dataclass
class PipelineState:
    """Current state of the rendering pipeline"""
    current_stage: PipelineStage = PipelineStage.INITIALIZATION
    current_frame: int = 0
    total_frames: int = 0
    current_time: float = 0.0
    is_running: bool = False
    is_paused: bool = False
    error_message: Optional[str] = None
    
    # Performance metrics
    frames_rendered: int = 0
    frames_dropped: int = 0
    average_render_time: float = 0.0
    memory_usage: float = 0.0
    
    def get_progress_percent(self) -> float:
        """Get rendering progress as percentage"""
        if self.total_frames <= 0:
            return 0.0
        return (self.current_frame / self.total_frames) * 100.0


class CompleteRenderingPipeline(QObject):
    """
    Complete rendering pipeline that integrates all components for end-to-end
    ASS to MP4 video generation with real-time preview capabilities.
    """
    
    # Progress signals
    stage_changed = pyqtSignal(str)  # PipelineStage
    progress_updated = pyqtSignal(float)  # Progress percentage
    frame_rendered = pyqtSignal(dict)  # Frame metadata
    
    # Status signals
    pipeline_started = pyqtSignal()
    pipeline_completed = pyqtSignal(str)  # Output path
    pipeline_failed = pyqtSignal(str)  # Error message
    pipeline_paused = pyqtSignal()
    pipeline_resumed = pyqtSignal()
    
    # Real-time preview signals
    preview_frame_ready = pyqtSignal(QImage, float)  # Frame, timestamp
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        super().__init__()
        
        self.config = config or PipelineConfig()
        self.state = PipelineState()
        
        # Core components
        self.opengl_context: Optional[OpenGLContext] = None
        self.libass_integration: Optional[LibassIntegration] = None
        self.effects_pipeline: Optional[EffectsRenderingPipeline] = None
        self.frame_capture_system: Optional[FrameCaptureSystem] = None
        self.ffmpeg_processor: Optional[EnhancedFFmpegProcessor] = None
        self.preview_synchronizer: Optional[PreviewSynchronizer] = None
        
        # Integration components
        self.libass_opengl_integration: Optional[Any] = None  # LibassOpenGLIntegration
        self.texture_cache: Optional[TextureCache] = None
        
        # Threading and synchronization
        self.render_thread: Optional[threading.Thread] = None
        self.frame_queue: Optional[queue.Queue] = None
        self.should_stop = threading.Event()
        self.pause_event = threading.Event()
        
        # Current project and timing
        self.current_project: Optional[Project] = None
        self.frame_timestamps: List[float] = []
        self.karaoke_timing_map: Dict[float, KaraokeTimingInfo] = {}
        
        # Performance tracking
        self.render_times: List[float] = []
        self.memory_snapshots: List[float] = []
        self.start_time = 0.0
        
        # Resource management
        self.allocated_resources: List[Any] = []
        self.cleanup_callbacks: List[Callable] = []
        
        logger.info("Complete rendering pipeline initialized")
    
    def initialize(self, project: Project) -> bool:
        """Initialize the complete rendering pipeline with a project"""
        try:
            self.current_project = project
            self.state.current_stage = PipelineStage.INITIALIZATION
            self.stage_changed.emit(self.state.current_stage.value)
            
            # Initialize OpenGL context
            if not self._initialize_opengl_context():
                raise Exception("Failed to initialize OpenGL context")
            
            # Initialize libass integration
            if not self._initialize_libass_integration():
                raise Exception("Failed to initialize libass integration")
            
            # Initialize effects pipeline
            if not self._initialize_effects_pipeline():
                raise Exception("Failed to initialize effects pipeline")
            
            # Initialize frame capture system
            if not self._initialize_frame_capture_system():
                raise Exception("Failed to initialize frame capture system")
            
            # Initialize FFmpeg processor
            if not self._initialize_ffmpeg_processor():
                raise Exception("Failed to initialize FFmpeg processor")
            
            # Initialize preview synchronizer
            if not self._initialize_preview_synchronizer():
                raise Exception("Failed to initialize preview synchronizer")
            
            # Generate frame timestamps
            self._generate_frame_timestamps()
            
            # Build karaoke timing map
            self._build_karaoke_timing_map()
            
            logger.info("Pipeline initialization completed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Pipeline initialization failed: {e}"
            logger.error(error_msg)
            self.state.error_message = error_msg
            self.pipeline_failed.emit(error_msg)
            return False
    
    def _initialize_opengl_context(self) -> bool:
        """Initialize OpenGL context for rendering"""
        try:
            from .opengl_context import create_offscreen_context, ContextBackend
            
            # Choose backend based on availability
            backend = None
            if not PYQT_AVAILABLE:
                backend = ContextBackend.MOCK
            
            self.opengl_context = create_offscreen_context(
                self.config.width,
                self.config.height,
                backend
            )
            
            if not self.opengl_context:
                return False
            
            # Create main framebuffer
            framebuffer_config = FramebufferConfig(
                width=self.config.width,
                height=self.config.height,
                use_depth=True,
                use_stencil=False
            )
            
            main_framebuffer = self.opengl_context.create_framebuffer(
                "main_render", framebuffer_config
            )
            
            if not main_framebuffer:
                return False
            
            self.allocated_resources.append(self.opengl_context)
            logger.debug("OpenGL context initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"OpenGL context initialization failed: {e}")
            return False
    
    def _initialize_libass_integration(self) -> bool:
        """Initialize libass integration for subtitle processing"""
        try:
            self.libass_integration = LibassIntegration()
            
            # Check if libass is available
            if not self.libass_integration.context.is_available():
                logger.warning("Libass not available, using fallback mode")
            
            # Load subtitle file if available
            if self.current_project and self.current_project.subtitle_file:
                try:
                    subtitle_file, karaoke_data = self.libass_integration.load_and_parse_subtitle_file(
                        self.current_project.subtitle_file.path
                    )
                    logger.info(f"Loaded subtitle file with {len(karaoke_data)} karaoke entries")
                except Exception as e:
                    logger.warning(f"Failed to load subtitle file: {e}")
            
            # Initialize texture cache
            self.texture_cache = TextureCache(
                max_size=self.config.max_texture_cache_size,
                timeout=30.0
            )
            
            self.allocated_resources.append(self.libass_integration)
            logger.debug("Libass integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Libass integration initialization failed: {e}")
            return False
    
    def _initialize_effects_pipeline(self) -> bool:
        """Initialize effects rendering pipeline"""
        try:
            if not self.opengl_context:
                return False
            
            self.effects_pipeline = EffectsRenderingPipeline(
                self.opengl_context,
                mock_mode=not PYQT_AVAILABLE
            )
            
            # Add default karaoke effects if enabled
            if self.config.enable_effects:
                self._setup_default_effects()
            
            self.allocated_resources.append(self.effects_pipeline)
            logger.debug("Effects pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Effects pipeline initialization failed: {e}")
            return False
    
    def _initialize_frame_capture_system(self) -> bool:
        """Initialize frame capture system"""
        try:
            if not self.opengl_context:
                return False
            
            self.frame_capture_system = FrameCaptureSystem(self.opengl_context)
            
            # Configure capture settings
            capture_settings = FrameCaptureSettings(
                width=self.config.width,
                height=self.config.height,
                fps=self.config.fps,
                use_threading=self.config.use_threading,
                buffer_size=self.config.buffer_size
            )
            
            success = self.frame_capture_system.initialize(
                self.current_project, capture_settings
            )
            
            if not success:
                return False
            
            self.allocated_resources.append(self.frame_capture_system)
            logger.debug("Frame capture system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Frame capture system initialization failed: {e}")
            return False
    
    def _initialize_ffmpeg_processor(self) -> bool:
        """Initialize FFmpeg processor for video encoding"""
        try:
            self.ffmpeg_processor = EnhancedFFmpegProcessor()
            
            # Check FFmpeg capabilities
            capabilities = self.ffmpeg_processor.get_capabilities()
            if not capabilities.available:
                logger.warning(f"FFmpeg not available: {capabilities.error_message}")
                # Continue without FFmpeg for preview-only mode
            
            # Connect signals
            if PYQT_AVAILABLE:
                self.ffmpeg_processor.encoding_started.connect(
                    lambda: self.stage_changed.emit(PipelineStage.VIDEO_ENCODING.value)
                )
                self.ffmpeg_processor.progress_updated.connect(
                    lambda progress: self.progress_updated.emit(progress.get('progress_percent', 0.0))
                )
                self.ffmpeg_processor.encoding_completed.connect(
                    self.pipeline_completed.emit
                )
                self.ffmpeg_processor.encoding_failed.connect(
                    self.pipeline_failed.emit
                )
            
            self.allocated_resources.append(self.ffmpeg_processor)
            logger.debug("FFmpeg processor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"FFmpeg processor initialization failed: {e}")
            return False
    
    def _initialize_preview_synchronizer(self) -> bool:
        """Initialize preview synchronizer for real-time playback"""
        try:
            self.preview_synchronizer = PreviewSynchronizer()
            
            if self.current_project:
                success = self.preview_synchronizer.load_project(self.current_project)
                if not success:
                    logger.warning("Failed to load project into preview synchronizer")
            
            # Connect signals
            if PYQT_AVAILABLE:
                self.preview_synchronizer.frame_updated.connect(
                    self.preview_frame_ready.emit
                )
            
            self.allocated_resources.append(self.preview_synchronizer)
            logger.debug("Preview synchronizer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Preview synchronizer initialization failed: {e}")
            return False
    
    def _setup_default_effects(self):
        """Setup default karaoke effects"""
        if not self.effects_pipeline:
            return
        
        try:
            from .effects_manager import EffectType
            
            # Add outline effect
            self.effects_pipeline.add_effect_layer(EffectType.OUTLINE, {
                'width': 3.0,
                'color': [0.0, 0.0, 0.0, 1.0],
                'softness': 0.3
            })
            
            # Add glow effect
            self.effects_pipeline.add_effect_layer(EffectType.GLOW, {
                'radius': 6.0,
                'intensity': 0.8,
                'color': [1.0, 1.0, 0.0, 1.0]
            })
            
            # Add color transition effect
            self.effects_pipeline.add_effect_layer(EffectType.COLOR_TRANSITION, {
                'start_color': [0.8, 0.8, 0.8, 1.0],
                'end_color': [1.0, 1.0, 0.0, 1.0],
                'transition_speed': 1.0
            })
            
            logger.debug("Default karaoke effects added to pipeline")
            
        except Exception as e:
            logger.warning(f"Failed to setup default effects: {e}")
    
    def _generate_frame_timestamps(self):
        """Generate frame timestamps for the entire video duration"""
        if not self.current_project:
            return
        
        # Determine duration from project
        duration = 0.0
        if self.current_project.audio_file:
            duration = self.current_project.audio_file.duration
        elif self.current_project.video_file:
            duration = self.current_project.video_file.duration
        elif self.current_project.subtitle_file and self.current_project.subtitle_file.lines:
            # Use last subtitle end time + buffer
            last_subtitle = max(self.current_project.subtitle_file.lines, 
                              key=lambda s: s.end_time)
            duration = last_subtitle.end_time + 2.0
        
        if duration <= 0:
            duration = 60.0  # Default 1 minute
        
        self.config.duration = duration
        
        # Generate timestamps
        frame_duration = 1.0 / self.config.fps
        current_time = 0.0
        
        while current_time < duration:
            self.frame_timestamps.append(current_time)
            current_time += frame_duration
        
        self.state.total_frames = len(self.frame_timestamps)
        logger.debug(f"Generated {len(self.frame_timestamps)} frame timestamps for {duration:.2f}s")
    
    def _build_karaoke_timing_map(self):
        """Build mapping of timestamps to karaoke timing information"""
        if not self.current_project or not self.current_project.subtitle_file:
            return
        
        self.karaoke_timing_map.clear()
        
        for subtitle_line in self.current_project.subtitle_file.lines:
            if hasattr(subtitle_line, 'karaoke_timing') and subtitle_line.karaoke_timing:
                # Map timing info to relevant timestamps
                start_time = subtitle_line.start_time
                end_time = subtitle_line.end_time
                
                for timestamp in self.frame_timestamps:
                    if start_time <= timestamp <= end_time:
                        self.karaoke_timing_map[timestamp] = subtitle_line.karaoke_timing
        
        logger.debug(f"Built karaoke timing map with {len(self.karaoke_timing_map)} entries")
    
    def start_rendering(self, output_path: str, preview_mode: bool = False) -> bool:
        """Start the complete rendering pipeline"""
        if self.state.is_running:
            logger.warning("Pipeline is already running")
            return False
        
        try:
            self.state.is_running = True
            self.state.current_frame = 0
            self.state.frames_rendered = 0
            self.state.frames_dropped = 0
            self.start_time = time.time()
            self.should_stop.clear()
            self.pause_event.set()  # Start unpaused
            
            # Emit started signal
            self.pipeline_started.emit()
            
            if preview_mode:
                # Start preview mode
                return self._start_preview_mode()
            else:
                # Start full rendering mode
                return self._start_full_rendering(output_path)
                
        except Exception as e:
            error_msg = f"Failed to start rendering: {e}"
            logger.error(error_msg)
            self.state.error_message = error_msg
            self.state.is_running = False
            self.pipeline_failed.emit(error_msg)
            return False
    
    def _start_preview_mode(self) -> bool:
        """Start real-time preview mode"""
        try:
            if not self.preview_synchronizer:
                return False
            
            # Start preview synchronizer
            self.preview_synchronizer.play()
            
            logger.info("Preview mode started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start preview mode: {e}")
            return False
    
    def _start_full_rendering(self, output_path: str) -> bool:
        """Start full rendering to video file"""
        try:
            # Configure export settings
            export_settings = EnhancedExportSettings(
                output_path=output_path,
                width=self.config.width,
                height=self.config.height,
                fps=self.config.fps
            )
            
            # Start rendering thread
            self.render_thread = threading.Thread(
                target=self._render_worker,
                args=(export_settings,),
                daemon=True
            )
            self.render_thread.start()
            
            logger.info(f"Full rendering started, output: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start full rendering: {e}")
            return False
    
    def _render_worker(self, export_settings: EnhancedExportSettings):
        """Main rendering worker thread"""
        try:
            self.state.current_stage = PipelineStage.SUBTITLE_PROCESSING
            self.stage_changed.emit(self.state.current_stage.value)
            
            # Create frame generator
            def frame_generator():
                return self._generate_next_frame()
            
            # Start FFmpeg encoding
            if self.ffmpeg_processor:
                audio_path = None
                if self.current_project and self.current_project.audio_file:
                    audio_path = self.current_project.audio_file.path
                
                success = self.ffmpeg_processor.start_encoding(
                    export_settings,
                    frame_generator,
                    self.state.total_frames,
                    audio_path
                )
                
                if not success:
                    raise Exception("Failed to start FFmpeg encoding")
            
            # Wait for completion or cancellation
            while self.state.is_running and not self.should_stop.is_set():
                # Wait for pause/resume
                self.pause_event.wait()
                
                if self.should_stop.is_set():
                    break
                
                # Update progress
                if self.state.total_frames > 0:
                    progress = (self.state.current_frame / self.state.total_frames) * 100
                    self.progress_updated.emit(progress)
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
            
            logger.info("Rendering worker completed")
            
        except Exception as e:
            error_msg = f"Rendering worker failed: {e}"
            logger.error(error_msg)
            self.state.error_message = error_msg
            self.pipeline_failed.emit(error_msg)
        
        finally:
            self.state.is_running = False
    
    def _generate_next_frame(self) -> Optional[CapturedFrame]:
        """Generate the next frame in the sequence"""
        if self.state.current_frame >= len(self.frame_timestamps):
            return None
        
        try:
            timestamp = self.frame_timestamps[self.state.current_frame]
            
            # Update pipeline stage
            if self.state.current_stage != PipelineStage.FRAME_CAPTURE:
                self.state.current_stage = PipelineStage.FRAME_CAPTURE
                self.stage_changed.emit(self.state.current_stage.value)
            
            # Render frame at timestamp
            frame = self._render_frame_at_timestamp(timestamp)
            
            if frame:
                self.state.current_frame += 1
                self.state.frames_rendered += 1
                self.state.current_time = timestamp
                
                # Emit frame rendered signal
                self.frame_rendered.emit(frame.to_dict())
            else:
                self.state.frames_dropped += 1
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame generation failed at frame {self.state.current_frame}: {e}")
            self.state.frames_dropped += 1
            return None
    
    def _render_frame_at_timestamp(self, timestamp: float) -> Optional[CapturedFrame]:
        """Render a single frame at the specified timestamp"""
        render_start = time.time()
        
        try:
            # Update effects pipeline timing
            if self.effects_pipeline:
                self.effects_pipeline.update_animation_time(timestamp)
                
                # Set karaoke timing if available
                if timestamp in self.karaoke_timing_map:
                    karaoke_timing = self.karaoke_timing_map[timestamp]
                    self.effects_pipeline.set_karaoke_timing(karaoke_timing)
            
            # Render subtitle textures using libass
            subtitle_texture = None
            if self.libass_integration and self.current_project:
                subtitle_texture = self._render_subtitle_texture(timestamp)
            
            # Render effects
            if self.effects_pipeline:
                success = self.effects_pipeline.render_frame(timestamp, subtitle_texture)
                if not success:
                    logger.warning(f"Effects rendering failed at {timestamp}s")
            
            # Capture frame
            if self.frame_capture_system:
                frame = self.frame_capture_system.rendering_engine.render_frame_at_timestamp(timestamp)
                
                if frame:
                    # Update performance metrics
                    render_time = time.time() - render_start
                    self.render_times.append(render_time)
                    
                    # Keep only recent render times
                    if len(self.render_times) > 100:
                        self.render_times = self.render_times[-100:]
                    
                    self.state.average_render_time = sum(self.render_times) / len(self.render_times)
                
                return frame
            
            return None
            
        except Exception as e:
            logger.error(f"Frame rendering failed at {timestamp}s: {e}")
            return None
    
    def _render_subtitle_texture(self, timestamp: float) -> Optional[Any]:
        """Render subtitle texture for the given timestamp"""
        try:
            if not self.libass_integration or not self.current_project:
                return None
            
            # Get visible subtitles at timestamp
            visible_subtitles = []
            if self.current_project.subtitle_file:
                for subtitle in self.current_project.subtitle_file.lines:
                    if subtitle.start_time <= timestamp <= subtitle.end_time:
                        visible_subtitles.append(subtitle)
            
            if not visible_subtitles:
                return None
            
            # Render using libass
            # This would be implemented with actual libass rendering
            # For now, return a placeholder
            return None
            
        except Exception as e:
            logger.error(f"Subtitle texture rendering failed: {e}")
            return None
    
    def pause_rendering(self):
        """Pause the rendering pipeline"""
        if self.state.is_running and not self.state.is_paused:
            self.state.is_paused = True
            self.pause_event.clear()
            
            if self.preview_synchronizer:
                self.preview_synchronizer.pause()
            
            self.pipeline_paused.emit()
            logger.info("Pipeline paused")
    
    def resume_rendering(self):
        """Resume the rendering pipeline"""
        if self.state.is_running and self.state.is_paused:
            self.state.is_paused = False
            self.pause_event.set()
            
            if self.preview_synchronizer:
                self.preview_synchronizer.play()
            
            self.pipeline_resumed.emit()
            logger.info("Pipeline resumed")
    
    def stop_rendering(self):
        """Stop the rendering pipeline"""
        if not self.state.is_running:
            return
        
        logger.info("Stopping rendering pipeline...")
        
        self.should_stop.set()
        self.pause_event.set()  # Ensure thread can exit
        
        # Stop preview synchronizer
        if self.preview_synchronizer:
            self.preview_synchronizer.stop()
        
        # Stop FFmpeg processor
        if self.ffmpeg_processor and hasattr(self.ffmpeg_processor, 'cancel_encoding'):
            self.ffmpeg_processor.cancel_encoding()
        
        # Wait for render thread to finish
        if self.render_thread and self.render_thread.is_alive():
            self.render_thread.join(timeout=5.0)
        
        self.state.is_running = False
        self.state.is_paused = False
        
        logger.info("Pipeline stopped")
    
    def seek_to_time(self, timestamp: float):
        """Seek to a specific timestamp in preview mode"""
        if self.preview_synchronizer:
            self.preview_synchronizer.seek_to_time(timestamp)
    
    def get_pipeline_state(self) -> PipelineState:
        """Get current pipeline state"""
        return self.state
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            'pipeline_state': {
                'stage': self.state.current_stage.value,
                'progress_percent': self.state.get_progress_percent(),
                'frames_rendered': self.state.frames_rendered,
                'frames_dropped': self.state.frames_dropped,
                'average_render_time': self.state.average_render_time,
                'is_running': self.state.is_running,
                'is_paused': self.state.is_paused
            }
        }
        
        # Add component-specific stats
        if self.effects_pipeline:
            stats['effects_pipeline'] = self.effects_pipeline.get_performance_stats()
        
        if self.frame_capture_system:
            stats['frame_capture'] = self.frame_capture_system.rendering_engine.get_performance_stats()
        
        if self.texture_cache:
            stats['texture_cache'] = {
                'hit_rate': self.texture_cache.hit_count / max(1, self.texture_cache.hit_count + self.texture_cache.miss_count),
                'cache_size': len(self.texture_cache.cache),
                'hit_count': self.texture_cache.hit_count,
                'miss_count': self.texture_cache.miss_count
            }
        
        return stats
    
    def cleanup(self):
        """Clean up all pipeline resources"""
        logger.info("Cleaning up rendering pipeline...")
        
        # Stop rendering if running
        if self.state.is_running:
            self.stop_rendering()
        
        # Clean up components in reverse order
        for resource in reversed(self.allocated_resources):
            try:
                if hasattr(resource, 'cleanup'):
                    resource.cleanup()
                elif hasattr(resource, 'destroy'):
                    resource.destroy()
            except Exception as e:
                logger.warning(f"Error cleaning up resource: {e}")
        
        # Execute cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"Cleanup callback failed: {e}")
        
        # Clear collections
        self.allocated_resources.clear()
        self.cleanup_callbacks.clear()
        self.frame_timestamps.clear()
        self.karaoke_timing_map.clear()
        self.render_times.clear()
        self.memory_snapshots.clear()
        
        # Reset state
        self.state = PipelineState()
        
        logger.info("Pipeline cleanup completed")


# Convenience functions
def create_rendering_pipeline(config: Optional[PipelineConfig] = None) -> CompleteRenderingPipeline:
    """Create a complete rendering pipeline with default configuration"""
    return CompleteRenderingPipeline(config)


def create_preview_pipeline(width: int = 1920, height: int = 1080) -> CompleteRenderingPipeline:
    """Create a pipeline optimized for real-time preview"""
    config = PipelineConfig(
        width=width,
        height=height,
        fps=30.0,
        quality_preset="medium",
        enable_effects=True,
        use_threading=True,
        max_threads=2,
        buffer_size=5,
        enable_memory_optimization=True
    )
    
    return CompleteRenderingPipeline(config)


def create_export_pipeline(width: int = 1920, height: int = 1080, fps: float = 30.0) -> CompleteRenderingPipeline:
    """Create a pipeline optimized for high-quality export"""
    config = PipelineConfig(
        width=width,
        height=height,
        fps=fps,
        quality_preset="high",
        enable_effects=True,
        enable_antialiasing=True,
        use_threading=True,
        max_threads=4,
        buffer_size=10,
        enable_memory_optimization=True
    )
    
    return CompleteRenderingPipeline(config)


if __name__ == "__main__":
    print("Testing Complete Rendering Pipeline...")
    
    # Create test project
    from models import Project, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle
    
    project = Project(
        id="test_pipeline",
        name="Test Pipeline Project",
        audio_file=AudioFile(path="test.mp3", duration=30.0),
        subtitle_file=SubtitleFile(
            path="test.ass",
            lines=[
                SubtitleLine(start_time=1.0, end_time=5.0, text="Test subtitle 1"),
                SubtitleLine(start_time=5.0, end_time=10.0, text="Test subtitle 2")
            ],
            styles=[SubtitleStyle(name="Default")]
        )
    )
    
    # Test pipeline creation
    pipeline = create_preview_pipeline()
    
    # Test initialization
    success = pipeline.initialize(project)
    print(f"Pipeline initialization: {'Success' if success else 'Failed'}")
    
    if success:
        # Test performance stats
        stats = pipeline.get_performance_stats()
        print(f"Performance stats: {stats['pipeline_state']}")
        
        # Test state
        state = pipeline.get_pipeline_state()
        print(f"Pipeline state: {state.current_stage.value}")
    
    # Cleanup
    pipeline.cleanup()
    
    print("Complete rendering pipeline test completed")