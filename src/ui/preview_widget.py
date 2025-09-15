"""
Preview Widget with OpenGL Video Display and Playback Controls
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLTexture, QOpenGLShader, QOpenGLShaderProgram
import OpenGL.GL as gl
import numpy as np
from typing import Optional, List

try:
    from src.core.preview_synchronizer import PreviewSynchronizer
    from src.core.models import Project, SubtitleLine, SubtitleStyle
    from src.core.opengl_subtitle_renderer import RenderedSubtitle
except ImportError:
    from preview_synchronizer import PreviewSynchronizer
    from models import Project, SubtitleLine, SubtitleStyle
    from opengl_subtitle_renderer import RenderedSubtitle


class OpenGLVideoWidget(QOpenGLWidget):
    """OpenGL widget for hardware-accelerated video rendering"""
    
    def __init__(self):
        super().__init__()
        self.video_texture = None
        self.shader_program = None
        self.vertex_buffer = None
        self.current_frame = None
        self.video_width = 0
        self.video_height = 0
        
    def initializeGL(self):
        """Initialize OpenGL context and resources"""
        # Enable blending for transparency
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        
        # Set clear color to black
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        
        # Create shader program for video rendering
        self._create_shader_program()
        
        # Create vertex buffer for quad rendering
        self._create_vertex_buffer()
        
    def _create_shader_program(self):
        """Create OpenGL shader program for video rendering"""
        vertex_shader_source = """
        #version 330 core
        layout (location = 0) in vec3 position;
        layout (location = 1) in vec2 texCoord;
        
        out vec2 TexCoord;
        
        uniform mat4 projection;
        uniform mat4 model;
        
        void main()
        {
            gl_Position = projection * model * vec4(position, 1.0);
            TexCoord = texCoord;
        }
        """
        
        fragment_shader_source = """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        
        uniform sampler2D videoTexture;
        uniform float alpha;
        
        void main()
        {
            FragColor = texture(videoTexture, TexCoord) * vec4(1.0, 1.0, 1.0, alpha);
        }
        """
        
        self.shader_program = QOpenGLShaderProgram()
        
        # Add vertex shader
        if not self.shader_program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vertex_shader_source):
            print("Failed to compile vertex shader")
            return False
            
        # Add fragment shader
        if not self.shader_program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragment_shader_source):
            print("Failed to compile fragment shader")
            return False
            
        # Link shader program
        if not self.shader_program.link():
            print("Failed to link shader program")
            return False
            
        return True
        
    def _create_vertex_buffer(self):
        """Create vertex buffer for rendering a textured quad"""
        # Quad vertices with texture coordinates
        vertices = np.array([
            # Positions      # Texture Coords
            -1.0, -1.0, 0.0,  0.0, 1.0,  # Bottom left
             1.0, -1.0, 0.0,  1.0, 1.0,  # Bottom right
             1.0,  1.0, 0.0,  1.0, 0.0,  # Top right
            -1.0,  1.0, 0.0,  0.0, 0.0   # Top left
        ], dtype=np.float32)
        
        # Store vertices for later use
        self.vertices = vertices
        
    def resizeGL(self, width, height):
        """Handle widget resize"""
        gl.glViewport(0, 0, width, height)
        
    def paintGL(self):
        """Render the current video frame"""
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
        if self.current_frame is not None and self.shader_program is not None:
            self._render_video_frame()
            
    def _render_video_frame(self):
        """Render the current video frame using OpenGL with proper aspect ratio"""
        if not self.shader_program.bind():
            return
            
        # Update video texture if needed
        if self.video_texture is None:
            self._create_video_texture()
            
        # Bind texture
        if self.video_texture:
            self.video_texture.bind()
            
        # Set uniforms
        self.shader_program.setUniformValue("videoTexture", 0)
        self.shader_program.setUniformValue("alpha", 1.0)
        
        # Calculate aspect ratio correction
        widget_width = self.width()
        widget_height = self.height()
        widget_aspect = widget_width / widget_height if widget_height > 0 else 1.0
        
        video_aspect = self.video_width / self.video_height if self.video_height > 0 else 1.0
        
        # Calculate scaling to maintain aspect ratio
        if video_aspect > widget_aspect:
            # Video is wider - fit to width
            scale_x = 1.0
            scale_y = widget_aspect / video_aspect
        else:
            # Video is taller - fit to height
            scale_x = video_aspect / widget_aspect
            scale_y = 1.0
        
        # Convert numpy matrices to QMatrix4x4 for PyQt6 compatibility
        from PyQt6.QtGui import QMatrix4x4
        
        # Create projection matrix (orthographic)
        proj_matrix = QMatrix4x4()
        proj_matrix.setToIdentity()
        proj_matrix.ortho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        
        # Create model matrix with aspect ratio correction
        model_matrix = QMatrix4x4()
        model_matrix.setToIdentity()
        model_matrix.scale(scale_x, scale_y, 1.0)
        
        self.shader_program.setUniformValue("projection", proj_matrix)
        self.shader_program.setUniformValue("model", model_matrix)
        
        # Enable vertex attributes
        self.shader_program.enableAttributeArray(0)  # position
        self.shader_program.enableAttributeArray(1)  # texCoord
        
        # Set vertex data - reshape the 1D array to 2D for proper indexing
        vertices_2d = self.vertices.reshape(-1, 5)  # 4 vertices, 5 components each (x,y,z,u,v)
        self.shader_program.setAttributeArray(0, vertices_2d[:, :3])  # positions (x,y,z)
        self.shader_program.setAttributeArray(1, vertices_2d[:, 3:])  # texture coords (u,v)
        
        # Draw quad
        gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)
        
        # Disable attributes
        self.shader_program.disableAttributeArray(0)
        self.shader_program.disableAttributeArray(1)
        
        # Release shader program
        self.shader_program.release()
        
    def _create_video_texture(self):
        """Create OpenGL texture from current frame"""
        if self.current_frame is None:
            return
            
        # Convert QImage to format suitable for OpenGL
        image = self.current_frame.convertToFormat(QImage.Format.Format_RGBA8888)
        
        # Create texture
        self.video_texture = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
        self.video_texture.setData(image)
        self.video_texture.setMinificationFilter(QOpenGLTexture.Filter.Linear)
        self.video_texture.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
        self.video_texture.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
        
    def load_frame(self, frame_image):
        """Load a new video frame for rendering"""
        self.current_frame = frame_image
        if self.current_frame:
            self.video_width = self.current_frame.width()
            self.video_height = self.current_frame.height()
            
        # Clear existing texture to force recreation
        if self.video_texture:
            self.video_texture = None
            
        # Trigger repaint
        self.update()
        
    def clear_frame(self):
        """Clear the current frame"""
        self.current_frame = None
        if self.video_texture:
            self.video_texture = None
        self.update()


class PreviewWidget(QWidget):
    """Widget for video preview with OpenGL rendering and playback controls"""
    
    # Playback control signals
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    
    # Synchronization signals
    subtitle_updated = pyqtSignal(list)  # List of visible subtitles
    time_changed = pyqtSignal(float, float)  # current_time, duration
    
    def __init__(self):
        super().__init__()
        
        # Initialize synchronization system
        self.synchronizer = PreviewSynchronizer()
        self.current_project: Optional[Project] = None
        self.is_seeking = False  # Flag to prevent feedback loops
        
        # Enhanced rendering pipeline integration
        self.rendering_pipeline: Optional[Any] = None  # CompleteRenderingPipeline
        self.frame_capture_enabled = False
        self.quality_settings = {
            'resolution_scale': 1.0,
            'effects_quality': 'high',
            'frame_rate_limit': 30.0
        }
        
        self._setup_ui()
        self._connect_synchronizer_signals()
        
    def _setup_ui(self):
        """Set up the preview widget UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Preview Karaoke Video")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # OpenGL preview area
        self._create_preview_area(layout)
        
        # Playback controls
        self._create_playback_controls(layout)
        
    def _create_preview_area(self, parent_layout):
        """Create OpenGL preview display area"""
        # Preview container
        preview_frame = QFrame()
        preview_frame.setFrameStyle(QFrame.Shape.Box)
        preview_frame.setMinimumHeight(400)
        preview_frame.setStyleSheet("background-color: black;")
        
        preview_layout = QVBoxLayout(preview_frame)
        
        # OpenGL widget for video rendering
        self.opengl_widget = OpenGLVideoWidget()
        self.opengl_widget.setMinimumSize(640, 360)
        preview_layout.addWidget(self.opengl_widget)
        
        # Placeholder label (will be replaced by actual video)
        self.placeholder_label = QLabel("Video preview will appear here")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("color: white; font-size: 14px;")
        preview_layout.addWidget(self.placeholder_label)
        
        parent_layout.addWidget(preview_frame)
        
    def _create_playback_controls(self, parent_layout):
        """Create playback control buttons and timeline"""
        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        
        # Timeline slider
        timeline_layout = QHBoxLayout()
        
        self.time_label_start = QLabel("00:00")
        timeline_layout.addWidget(self.time_label_start)
        
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(100)
        self.timeline_slider.setValue(0)
        self.timeline_slider.valueChanged.connect(self._on_timeline_changed)
        timeline_layout.addWidget(self.timeline_slider)
        
        self.time_label_end = QLabel("00:00")
        timeline_layout.addWidget(self.time_label_end)
        
        controls_layout.addLayout(timeline_layout)
        
        # Playback buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self._toggle_playback)
        buttons_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._stop_playback)
        buttons_layout.addWidget(self.stop_button)
        
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)
        
        parent_layout.addWidget(controls_frame)
        
        # Initialize state
        self.is_playing = False
        
    def _connect_synchronizer_signals(self):
        """Connect synchronizer signals to UI updates"""
        # Connect synchronizer to UI updates
        self.synchronizer.frame_updated.connect(self._on_frame_updated)
        self.synchronizer.time_position_changed.connect(self._on_time_position_changed)
        self.synchronizer.playback_state_changed.connect(self._on_playback_state_changed)
        self.synchronizer.subtitle_updated.connect(self._on_subtitle_updated)
        
        # Connect UI controls to synchronizer
        self.play_requested.connect(self._on_play_requested)
        self.pause_requested.connect(self._on_pause_requested)
        self.seek_requested.connect(self._on_seek_requested)
        
    def _toggle_playback(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.is_playing = False
            self.play_button.setText("Play")
            self.pause_requested.emit()
        else:
            self.is_playing = True
            self.play_button.setText("Pause")
            self.play_requested.emit()
            
    def _stop_playback(self):
        """Stop playback and reset to beginning"""
        self.is_playing = False
        self.play_button.setText("Play")
        self.timeline_slider.setValue(0)
        
    def _on_timeline_changed(self, value):
        """Handle timeline slider changes"""
        # Convert slider value to time position
        position = value / 100.0  # Normalize to 0-1 range
        self.seek_requested.emit(position)
        
    def load_video_frame(self, frame_image):
        """Load a video frame into the OpenGL widget"""
        if frame_image and isinstance(frame_image, QImage):
            self.opengl_widget.load_frame(frame_image)
            # Hide placeholder when video is loaded
            self.placeholder_label.hide()
        else:
            self.opengl_widget.clear_frame()
            # Show placeholder when no video
            self.placeholder_label.show()
            
    def update_timeline(self, current_time, total_time):
        """Update timeline position and time labels"""
        if total_time > 0:
            progress = int((current_time / total_time) * 100)
            self.timeline_slider.setValue(progress)
            
        # Format time labels
        current_str = self._format_time(current_time)
        total_str = self._format_time(total_time)
        
        self.time_label_start.setText(current_str)
        self.time_label_end.setText(total_str)
        
    def _format_time(self, seconds):
        """Format time in MM:SS format"""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def set_playback_state(self, is_playing):
        """Update playback button state"""
        self.is_playing = is_playing
        if is_playing:
            self.play_button.setText("Pause")
        else:
            self.play_button.setText("Play")
            
    def reset_playback(self):
        """Reset playback to initial state"""
        self.is_playing = False
        self.play_button.setText("Play")
        self.timeline_slider.setValue(0)
        self.time_label_start.setText("00:00")
        self.opengl_widget.clear_frame()
        self.placeholder_label.show()
        
        # Reset synchronizer
        if self.synchronizer:
            self.synchronizer.stop()
    
    def load_project(self, project: Project):
        """Load a project for synchronized preview"""
        self.current_project = project
        
        # Load project into synchronizer
        success = self.synchronizer.load_project(project)
        
        if success:
            # Initialize enhanced rendering pipeline if available
            self._initialize_rendering_pipeline(project)
            
            # Update UI to show project is loaded
            self.placeholder_label.hide()
            
            # Update timeline with duration
            duration = self.synchronizer.get_duration()
            self.time_label_end.setText(self._format_time(duration))
            
            # Seek to beginning to show first frame
            self.synchronizer.seek_to_time(0.0)
        else:
            # Show error state
            self.placeholder_label.setText("Failed to load project")
            self.placeholder_label.show()
            
        return success
    
    def update_subtitles_realtime(self, subtitle_lines: List[SubtitleLine], subtitle_styles: dict):
        """Update subtitles in real-time during editing"""
        if self.synchronizer:
            self.synchronizer.update_subtitles(subtitle_lines, subtitle_styles)
    
    def add_effect(self, effect_id: str, parameters: dict):
        """Add a text effect to the preview"""
        if self.synchronizer and hasattr(self.synchronizer, 'subtitle_renderer'):
            # Add effect to subtitle renderer
            self.synchronizer.subtitle_renderer.add_effect(effect_id, parameters)
            # Force immediate preview update
            self.synchronizer._update_sync()
    
    def remove_effect(self, effect_id: str):
        """Remove a text effect from the preview"""
        if self.synchronizer and hasattr(self.synchronizer, 'subtitle_renderer'):
            # Remove effect from subtitle renderer
            self.synchronizer.subtitle_renderer.remove_effect(effect_id)
            # Force immediate preview update
            self.synchronizer._update_sync()
    
    def update_effect_parameters(self, effect_id: str, parameters: dict):
        """Update effect parameters in real-time"""
        if self.synchronizer and hasattr(self.synchronizer, 'subtitle_renderer'):
            # Update effect parameters
            self.synchronizer.subtitle_renderer.update_effect_parameters(effect_id, parameters)
            # Force immediate preview update
            self.synchronizer._update_sync()
    
    def toggle_effect(self, effect_id: str, enabled: bool):
        """Toggle an effect on/off"""
        if self.synchronizer and hasattr(self.synchronizer, 'subtitle_renderer'):
            # Toggle effect
            self.synchronizer.subtitle_renderer.toggle_effect(effect_id, enabled)
            # Force immediate preview update
            self.synchronizer._update_sync()
    
    def apply_effect_preset(self, preset_name: str):
        """Apply an effect preset"""
        if self.synchronizer and hasattr(self.synchronizer, 'subtitle_renderer'):
            # Apply preset
            self.synchronizer.subtitle_renderer.apply_effect_preset(preset_name)
            # Force immediate preview update
            self.synchronizer._update_sync()
    
    def _on_frame_updated(self, frame: QImage, timestamp: float):
        """Handle frame updates from synchronizer"""
        if frame and not frame.isNull():
            self.opengl_widget.load_frame(frame)
            self.placeholder_label.hide()
        
    def _on_time_position_changed(self, current_time: float, duration: float):
        """Handle time position changes from synchronizer"""
        # Update timeline slider (avoid feedback loop)
        if not self.is_seeking:
            self.update_timeline(current_time, duration)
            
        # Emit time change signal for external listeners
        self.time_changed.emit(current_time, duration)
        
    def _on_playback_state_changed(self, is_playing: bool):
        """Handle playback state changes from synchronizer"""
        self.set_playback_state(is_playing)
        
    def _on_subtitle_updated(self, visible_subtitles: List[RenderedSubtitle]):
        """Handle subtitle updates from synchronizer"""
        # Emit subtitle update signal for external listeners
        self.subtitle_updated.emit(visible_subtitles)
        
    def _on_play_requested(self):
        """Handle play request from UI"""
        if self.synchronizer:
            self.synchronizer.play()
            
    def _on_pause_requested(self):
        """Handle pause request from UI"""
        if self.synchronizer:
            self.synchronizer.pause()
            
    def _on_seek_requested(self, position: float):
        """Handle seek request from UI"""
        if self.synchronizer:
            # Convert normalized position to timestamp
            duration = self.synchronizer.get_duration()
            timestamp = position * duration
            
            # Set seeking flag to prevent feedback
            self.is_seeking = True
            self.synchronizer.seek_to_time(timestamp)
            
            # Also seek rendering pipeline if available
            if self.rendering_pipeline:
                self.rendering_pipeline.seek_to_time(timestamp)
            
            self.is_seeking = False
    
    def _initialize_rendering_pipeline(self, project: Project):
        """Initialize enhanced rendering pipeline for high-quality preview"""
        try:
            from src.core.complete_rendering_pipeline import create_preview_pipeline
            
            # Create preview-optimized pipeline
            self.rendering_pipeline = create_preview_pipeline(
                width=int(1920 * self.quality_settings['resolution_scale']),
                height=int(1080 * self.quality_settings['resolution_scale'])
            )
            
            # Initialize with project
            success = self.rendering_pipeline.initialize(project)
            
            if success:
                # Connect pipeline signals
                self.rendering_pipeline.preview_frame_ready.connect(self._on_pipeline_frame_ready)
                self.rendering_pipeline.pipeline_failed.connect(self._on_pipeline_error)
                
                # Start preview mode
                self.rendering_pipeline.start_rendering("", preview_mode=True)
                
                print("Enhanced rendering pipeline initialized for preview")
            else:
                print("Failed to initialize rendering pipeline, using fallback")
                self.rendering_pipeline = None
                
        except Exception as e:
            print(f"Error initializing rendering pipeline: {e}")
            self.rendering_pipeline = None
    
    def _on_pipeline_frame_ready(self, frame: QImage, timestamp: float):
        """Handle frame ready from enhanced rendering pipeline"""
        if frame and not frame.isNull():
            # Use high-quality frame from pipeline
            self.opengl_widget.load_frame(frame)
            self.placeholder_label.hide()
    
    def _on_pipeline_error(self, error_message: str):
        """Handle rendering pipeline errors"""
        print(f"Rendering pipeline error: {error_message}")
        # Fall back to basic synchronizer
        self.rendering_pipeline = None
    
    def enable_frame_capture(self, enabled: bool):
        """Enable/disable frame capture for export preview"""
        self.frame_capture_enabled = enabled
        
        if self.rendering_pipeline:
            # Configure pipeline for frame capture
            if enabled:
                print("Frame capture enabled for preview")
            else:
                print("Frame capture disabled for preview")
    
    def set_quality_settings(self, settings: dict):
        """Update preview quality settings"""
        self.quality_settings.update(settings)
        
        # Reinitialize pipeline if settings changed significantly
        if self.rendering_pipeline and self.current_project:
            resolution_changed = (
                'resolution_scale' in settings and 
                settings['resolution_scale'] != self.quality_settings.get('resolution_scale', 1.0)
            )
            
            if resolution_changed:
                print("Reinitializing pipeline due to resolution change")
                self.rendering_pipeline.cleanup()
                self._initialize_rendering_pipeline(self.current_project)
    
    def get_performance_stats(self) -> dict:
        """Get preview performance statistics"""
        stats = {
            'synchronizer_stats': {},
            'pipeline_stats': {},
            'opengl_stats': {}
        }
        
        # Get synchronizer stats
        if self.synchronizer:
            stats['synchronizer_stats'] = self.synchronizer.get_performance_stats()
        
        # Get pipeline stats
        if self.rendering_pipeline:
            stats['pipeline_stats'] = self.rendering_pipeline.get_performance_stats()
        
        # Get OpenGL widget stats (if available)
        if hasattr(self.opengl_widget, 'get_performance_stats'):
            stats['opengl_stats'] = self.opengl_widget.get_performance_stats()
        
        return stats
    
    def cleanup_resources(self):
        """Clean up preview resources"""
        if self.rendering_pipeline:
            self.rendering_pipeline.cleanup()
            self.rendering_pipeline = None
        
        if self.synchronizer:
            self.synchronizer.cleanup()
        
        self.opengl_widget.clear_frame()