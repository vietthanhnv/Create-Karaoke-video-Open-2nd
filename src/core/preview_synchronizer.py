"""
Real-time Preview Synchronization System

This module provides synchronized audio-video-subtitle playback with frame-accurate
seeking and real-time updates for the karaoke video creator.
"""

import time
from typing import Optional, List, Callable, Dict, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage
from dataclasses import dataclass

try:
    from .models import Project, SubtitleLine, SubtitleStyle
    from .opengl_subtitle_renderer import OpenGLSubtitleRenderer, RenderedSubtitle
except ImportError:
    from models import Project, SubtitleLine, SubtitleStyle
    from opengl_subtitle_renderer import OpenGLSubtitleRenderer, RenderedSubtitle


@dataclass
class SyncState:
    """Current synchronization state"""
    current_time: float = 0.0
    is_playing: bool = False
    duration: float = 0.0
    frame_rate: float = 30.0
    last_update_time: float = 0.0


class MediaDecoder(QObject):
    """Handles video frame decoding and audio playback"""
    
    frame_ready = pyqtSignal(QImage, float)  # frame, timestamp
    audio_position_changed = pyqtSignal(float)  # current time
    
    def __init__(self):
        super().__init__()
        self.current_project: Optional[Project] = None
        self.is_initialized = False
        
        # Initialize audio player
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            self.audio_player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.positionChanged.connect(self._on_audio_position_changed)
            self.has_audio = True
        except ImportError:
            self.audio_player = None
            self.audio_output = None
            self.has_audio = False
            print("Warning: PyQt6 multimedia not available - no audio playback")
        
    def load_project(self, project: Project) -> bool:
        """Load a project for playback"""
        self.current_project = project
        
        # Load audio if available
        if self.has_audio and project.audio_file:
            from PyQt6.QtCore import QUrl
            audio_url = QUrl.fromLocalFile(project.audio_file.path)
            self.audio_player.setSource(audio_url)
        
        # Set duration and frame rate
        if project.video_file:
            self.duration = project.video_file.duration
            self.frame_rate = project.video_file.frame_rate or 30.0
        elif project.image_file and project.audio_file:
            self.duration = project.audio_file.duration
            self.frame_rate = 30.0
        else:
            return False
            
        self.is_initialized = True
        return True
    
    def play_audio(self):
        """Start audio playback"""
        if self.has_audio and self.audio_player:
            self.audio_player.play()
    
    def pause_audio(self):
        """Pause audio playback"""
        if self.has_audio and self.audio_player:
            self.audio_player.pause()
    
    def seek_audio(self, position_ms: int):
        """Seek audio to position in milliseconds"""
        if self.has_audio and self.audio_player:
            self.audio_player.setPosition(position_ms)
    
    def _on_audio_position_changed(self, position_ms: int):
        """Handle audio position changes"""
        position_seconds = position_ms / 1000.0
        self.audio_position_changed.emit(position_seconds)
    
    def seek_to_time(self, timestamp: float) -> QImage:
        """Seek to specific timestamp and return frame"""
        if not self.is_initialized or not self.current_project:
            return QImage()
            
        # Mock frame generation - in real implementation would decode actual frame
        if self.current_project.video_file:
            # Generate mock video frame
            frame = QImage(640, 480, QImage.Format.Format_RGB888)
            frame.fill(0x404040)  # Gray background
        elif self.current_project.image_file:
            # Load and return image
            frame = QImage(self.current_project.image_file.path)
            if frame.isNull():
                frame = QImage(640, 480, QImage.Format.Format_RGB888)
                frame.fill(0x404040)
        else:
            frame = QImage(640, 480, QImage.Format.Format_RGB888)
            frame.fill(0x000000)  # Black background
            
        return frame
    
    def get_duration(self) -> float:
        """Get media duration"""
        return getattr(self, 'duration', 0.0)
    
    def get_frame_rate(self) -> float:
        """Get video frame rate"""
        return getattr(self, 'frame_rate', 30.0)


class PreviewSynchronizer(QObject):
    """
    Main synchronization engine for real-time preview playback.
    
    Coordinates audio, video, and subtitle rendering with frame-accurate timing
    and provides real-time updates when content is modified.
    """
    
    # Synchronization signals
    frame_updated = pyqtSignal(QImage, float)  # frame with subtitles, timestamp
    time_position_changed = pyqtSignal(float, float)  # current_time, duration
    playback_state_changed = pyqtSignal(bool)  # is_playing
    subtitle_updated = pyqtSignal(list)  # list of visible subtitles
    
    def __init__(self):
        super().__init__()
        
        # Core components
        self.media_decoder = MediaDecoder()
        self.subtitle_renderer = OpenGLSubtitleRenderer()
        
        # Synchronization state
        self.sync_state = SyncState()
        
        # Timing control
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._update_sync)
        self.sync_timer.setInterval(33)  # ~30 FPS
        
        # Current project and data
        self.current_project: Optional[Project] = None
        self.subtitle_lines: List[SubtitleLine] = []
        self.subtitle_styles: Dict[str, SubtitleStyle] = {}
        
        # Callbacks for real-time updates
        self.subtitle_change_callbacks: List[Callable] = []
        
        # Performance tracking
        self.last_render_time = 0.0
        self.frame_count = 0
        
        # Connect media decoder signals
        self.media_decoder.frame_ready.connect(self._on_frame_ready)
        self.media_decoder.audio_position_changed.connect(self._on_audio_position_changed)
        
    def load_project(self, project: Project) -> bool:
        """Load a project for synchronized playback"""
        self.current_project = project
        
        # Load media
        if not self.media_decoder.load_project(project):
            return False
            
        # Load subtitles
        if project.subtitle_file:
            self.subtitle_lines = project.subtitle_file.lines.copy()
            self.subtitle_styles = {style.name: style for style in project.subtitle_file.styles}
        else:
            self.subtitle_lines = []
            self.subtitle_styles = {}
            
        # Initialize subtitle renderer (skip OpenGL for now, use QPainter compositing)
        # self.subtitle_renderer.initialize_opengl()
        
        # Update sync state
        self.sync_state.duration = self.media_decoder.get_duration()
        self.sync_state.frame_rate = self.media_decoder.get_frame_rate()
        self.sync_state.current_time = 0.0
        self.sync_state.is_playing = False
        
        # Emit initial state
        self.time_position_changed.emit(0.0, self.sync_state.duration)
        self.playback_state_changed.emit(False)
        
        return True
    
    def play(self):
        """Start synchronized playback"""
        if not self.current_project:
            return
            
        self.sync_state.is_playing = True
        self.sync_state.last_update_time = time.time()
        
        # Start audio playback
        self.media_decoder.play_audio()
        
        # Start sync timer
        self.sync_timer.start()
        
        # Emit state change
        self.playback_state_changed.emit(True)
        
    def pause(self):
        """Pause synchronized playback"""
        self.sync_state.is_playing = False
        
        # Pause audio playback
        self.media_decoder.pause_audio()
        
        self.sync_timer.stop()
        
        # Emit state change
        self.playback_state_changed.emit(False)
        
    def stop(self):
        """Stop playback and reset to beginning"""
        self.pause()
        self.seek_to_time(0.0)
        
    def seek_to_time(self, timestamp: float):
        """Seek to specific timestamp with frame-accurate positioning"""
        if not self.current_project:
            return
            
        # Clamp timestamp to valid range
        timestamp = max(0.0, min(timestamp, self.sync_state.duration))
        
        # Seek audio to matching position
        self.media_decoder.seek_audio(int(timestamp * 1000))  # Convert to milliseconds
        
        # Update sync state
        self.sync_state.current_time = timestamp
        self.sync_state.last_update_time = time.time()
        
        # Force immediate update
        self._update_sync()
        
        # Emit position change
        self.time_position_changed.emit(timestamp, self.sync_state.duration)
        
    def seek_to_progress(self, progress: float):
        """Seek to position based on progress (0.0 to 1.0)"""
        if self.sync_state.duration > 0:
            timestamp = progress * self.sync_state.duration
            self.seek_to_time(timestamp)
            
    def update_subtitles(self, subtitle_lines: List[SubtitleLine], subtitle_styles: Dict[str, SubtitleStyle]):
        """Update subtitle content in real-time"""
        self.subtitle_lines = subtitle_lines.copy()
        self.subtitle_styles = subtitle_styles.copy()
        
        # Clear subtitle renderer cache to force re-rendering
        self.subtitle_renderer.texture_cache.clear()
        
        # Trigger immediate update if playing
        if self.sync_state.is_playing or True:  # Always update for real-time editing
            self._update_sync()
            
        # Notify callbacks
        for callback in self.subtitle_change_callbacks:
            try:
                callback(subtitle_lines, subtitle_styles)
            except Exception as e:
                print(f"Subtitle change callback error: {e}")
                
    def add_subtitle_change_callback(self, callback: Callable):
        """Add callback for subtitle changes"""
        self.subtitle_change_callbacks.append(callback)
        
    def remove_subtitle_change_callback(self, callback: Callable):
        """Remove subtitle change callback"""
        if callback in self.subtitle_change_callbacks:
            self.subtitle_change_callbacks.remove(callback)
            
    def get_current_time(self) -> float:
        """Get current playback time"""
        return self.sync_state.current_time
        
    def get_duration(self) -> float:
        """Get total duration"""
        return self.sync_state.duration
        
    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.sync_state.is_playing
        
    def _update_sync(self):
        """Main synchronization update loop"""
        current_real_time = time.time()
        
        # Update playback time if playing
        if self.sync_state.is_playing:
            time_delta = current_real_time - self.sync_state.last_update_time
            self.sync_state.current_time += time_delta
            
            # Check for end of media
            if self.sync_state.current_time >= self.sync_state.duration:
                self.sync_state.current_time = self.sync_state.duration
                self.pause()
                
        self.sync_state.last_update_time = current_real_time
        
        # Get current video frame
        video_frame = self.media_decoder.seek_to_time(self.sync_state.current_time)
        
        # Render subtitles onto frame
        final_frame = self._render_frame_with_subtitles(video_frame, self.sync_state.current_time)
        
        # Emit updated frame
        self.frame_updated.emit(final_frame, self.sync_state.current_time)
        
        # Emit time position
        self.time_position_changed.emit(self.sync_state.current_time, self.sync_state.duration)
        
        # Update performance tracking
        self.frame_count += 1
        
    def _render_frame_with_subtitles(self, video_frame: QImage, timestamp: float) -> QImage:
        """Render subtitles onto video frame"""
        if not video_frame or video_frame.isNull():
            return video_frame
            
        # Get visible subtitles at current timestamp
        visible_subtitles = self._get_visible_subtitles(timestamp)
        
        if not visible_subtitles:
            return video_frame
            
        # Create a copy of the frame to draw subtitles on
        composited_frame = video_frame.copy()
        
        # Use QPainter to composite subtitles onto the frame
        try:
            from PyQt6.QtGui import QPainter, QFont, QColor, QPen, QFontMetrics
            from PyQt6.QtCore import QRect, Qt
            
            painter = QPainter(composited_frame)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
            
            # Draw each visible subtitle with karaoke animation
            for line in self.subtitle_lines:
                if line.start_time <= timestamp <= line.end_time:
                    # Get style for this line
                    style = self.subtitle_styles.get(line.style)
                    if not style:
                        # Use default style
                        style = SubtitleStyle(name="Default")
                    
                    # Set up font - make it larger and bold for better visibility
                    font_size = max(32, int(style.font_size * composited_frame.height() / 480))  # Larger font
                    font = QFont(style.font_name, font_size)
                    font.setBold(True)  # Always bold for better visibility
                    font.setItalic(style.italic)
                    painter.setFont(font)
                    
                    # Calculate text position
                    metrics = QFontMetrics(font)
                    text_rect = metrics.boundingRect(line.text)
                    
                    # Position at bottom center by default
                    x = (composited_frame.width() - text_rect.width()) // 2
                    y = composited_frame.height() - style.margin_v - text_rect.height()
                    
                    # Draw karaoke-style text with word-by-word animation
                    self._draw_karaoke_text(painter, line, timestamp, x, y, metrics, style)
            
            painter.end()
            
        except Exception as e:
            print(f"Error compositing subtitles: {e}")
            # Return original frame if compositing fails
            return video_frame
        
        # Emit visible subtitles for external use
        self.subtitle_updated.emit(visible_subtitles)
        
        # Subtitle compositing completed successfully
        
        return composited_frame
    
    def _draw_karaoke_text(self, painter, line: SubtitleLine, timestamp: float, x: int, y: int, metrics, style):
        """Draw karaoke-style text with word-by-word highlighting."""
        from PyQt6.QtGui import QColor, QPen
        from PyQt6.QtCore import Qt
        
        # Colors for karaoke effect
        unsung_color = QColor(200, 200, 200, 255)  # Light gray for unsung text
        sung_color = QColor(255, 255, 100, 255)    # Bright yellow for sung text
        outline_color = QColor(0, 0, 0, 255)       # Black outline
        
        if not line.word_timings:
            # No word timings - draw simple text with progress-based coloring
            progress = line.get_progress_ratio(timestamp)
            
            # Draw outline
            outline_pen = QPen(outline_color)
            outline_pen.setWidth(3)
            painter.setPen(outline_pen)
            
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:
                        painter.drawText(x + dx, y + dy, line.text)
            
            # Draw main text with gradient effect based on progress
            if progress >= 1.0:
                painter.setPen(QPen(sung_color))
            elif progress <= 0.0:
                painter.setPen(QPen(unsung_color))
            else:
                # Blend colors based on progress
                blend_color = QColor()
                blend_color.setRed(int(unsung_color.red() * (1 - progress) + sung_color.red() * progress))
                blend_color.setGreen(int(unsung_color.green() * (1 - progress) + sung_color.green() * progress))
                blend_color.setBlue(int(unsung_color.blue() * (1 - progress) + sung_color.blue() * progress))
                painter.setPen(QPen(blend_color))
            
            painter.drawText(x, y, line.text)
        else:
            # Word-by-word karaoke timing
            current_x = x
            
            for word_timing in line.word_timings:
                word_text = word_timing.word + " "  # Add space after each word
                word_width = metrics.horizontalAdvance(word_text)
                
                # Determine word color based on timing
                if timestamp >= word_timing.end_time:
                    # Word has been sung
                    word_color = sung_color
                elif timestamp >= word_timing.start_time:
                    # Word is currently being sung - animate
                    word_progress = (timestamp - word_timing.start_time) / (word_timing.end_time - word_timing.start_time)
                    
                    # Create animated color transition
                    word_color = QColor()
                    word_color.setRed(int(unsung_color.red() * (1 - word_progress) + sung_color.red() * word_progress))
                    word_color.setGreen(int(unsung_color.green() * (1 - word_progress) + sung_color.green() * word_progress))
                    word_color.setBlue(int(unsung_color.blue() * (1 - word_progress) + sung_color.blue() * word_progress))
                else:
                    # Word hasn't been sung yet
                    word_color = unsung_color
                
                # Draw word outline
                outline_pen = QPen(outline_color)
                outline_pen.setWidth(2)
                painter.setPen(outline_pen)
                
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            painter.drawText(current_x + dx, y + dy, word_text)
                
                # Draw main word text
                painter.setPen(QPen(word_color))
                painter.drawText(current_x, y, word_text)
                
                current_x += word_width
        
    def _get_visible_subtitles(self, timestamp: float) -> List[RenderedSubtitle]:
        """Get subtitles that should be visible at the given timestamp"""
        visible_subtitles = []
        
        for line in self.subtitle_lines:
            if line.start_time <= timestamp <= line.end_time:
                # Get style for this line
                style = self.subtitle_styles.get(line.style)
                if not style:
                    # Use default style
                    style = SubtitleStyle(name="Default")
                    
                # Create a simple RenderedSubtitle without OpenGL texture
                rendered = RenderedSubtitle(
                    texture=None,  # No OpenGL texture needed for QPainter compositing
                    position=(0, 0),  # Will be calculated during compositing
                    size=(0, 0),  # Will be calculated during compositing
                    start_time=line.start_time,
                    end_time=line.end_time,
                    text=line.text,
                    style_name=style.name
                )
                
                visible_subtitles.append(rendered)
                    
        return visible_subtitles
        
    def _on_frame_ready(self, frame: QImage, timestamp: float):
        """Handle frame ready from media decoder"""
        # This would be used in a full FFmpeg implementation
        pass
        
    def _on_audio_position_changed(self, position: float):
        """Handle audio position changes for synchronization"""
        # Update sync state to match audio position
        if self.sync_state.is_playing:
            self.sync_state.current_time = position
            self.sync_state.last_update_time = time.time()
            
            # Force frame update to stay in sync
            self._update_sync()
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'frame_count': self.frame_count,
            'current_time': self.sync_state.current_time,
            'is_playing': self.sync_state.is_playing,
            'duration': self.sync_state.duration,
            'frame_rate': self.sync_state.frame_rate,
            'subtitle_cache_size': len(self.subtitle_renderer.texture_cache.textures) if self.subtitle_renderer.texture_cache else 0
        }
        
    def cleanup(self):
        """Clean up resources"""
        self.pause()
        if self.subtitle_renderer:
            self.subtitle_renderer.cleanup()
        self.subtitle_change_callbacks.clear()


if __name__ == "__main__":
    print("Testing Preview Synchronizer...")
    
    # Create test project
    from models import Project, VideoFile, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle
    
    project = Project(
        id="test",
        name="Test Project",
        video_file=VideoFile(path="test.mp4", duration=60.0, frame_rate=30.0),
        audio_file=AudioFile(path="test.mp3", duration=60.0),
        subtitle_file=SubtitleFile(
            path="test.ass",
            lines=[
                SubtitleLine(start_time=0.0, end_time=5.0, text="Test subtitle 1"),
                SubtitleLine(start_time=5.0, end_time=10.0, text="Test subtitle 2")
            ],
            styles=[SubtitleStyle(name="Default")]
        )
    )
    
    # Test synchronizer
    sync = PreviewSynchronizer()
    success = sync.load_project(project)
    print(f"Project loaded: {success}")
    print(f"Performance stats: {sync.get_performance_stats()}")
    
    # Test seeking
    sync.seek_to_time(2.5)
    print(f"Seeked to 2.5s, current time: {sync.get_current_time()}")
    
    sync.cleanup()
    print("Synchronizer test completed")