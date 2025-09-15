"""
Detachable Preview Widget - Can be used as a standalone window or embedded in tabs
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSlider, QFrame, QMainWindow,
    QDockWidget, QTabWidget, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QFont, QImage, QCloseEvent, QIcon
from typing import Optional, List

try:
    from .preview_widget import OpenGLVideoWidget, PreviewWidget
    from ..core.preview_synchronizer import PreviewSynchronizer
    from ..core.models import Project, SubtitleLine, SubtitleStyle
    from ..core.opengl_subtitle_renderer import RenderedSubtitle
except ImportError:
    from src.ui.preview_widget import OpenGLVideoWidget, PreviewWidget
    from src.core.preview_synchronizer import PreviewSynchronizer
    from src.core.models import Project, SubtitleLine, SubtitleStyle
    from src.core.opengl_subtitle_renderer import RenderedSubtitle


class DetachablePreviewWidget(QWidget):
    """Preview widget that can be detached and reattached to tabs"""
    
    # Signals for communication with parent
    detach_requested = pyqtSignal()
    attach_requested = pyqtSignal()
    closed = pyqtSignal()
    
    # Preview control signals (forwarded from internal preview)
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    seek_requested = pyqtSignal(float)
    
    # Synchronization signals (forwarded from internal preview)
    subtitle_updated = pyqtSignal(list)
    time_changed = pyqtSignal(float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State management
        self.is_detached = False
        self.detached_window = None
        self.parent_tab_widget = None
        self.tab_index = -1
        self.tab_title = "Preview"
        
        # Create internal preview widget
        self.preview_widget = PreviewWidget()
        
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the detachable preview UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with detach/attach controls
        self._create_header(layout)
        
        # Preview content
        layout.addWidget(self.preview_widget)
        
    def _create_header(self, parent_layout):
        """Create header with detach/attach controls"""
        header_frame = QFrame()
        header_frame.setMaximumHeight(40)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        self.title_label = QLabel("Video Preview")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Detach/Attach button
        self.detach_button = QPushButton("Detach")
        self.detach_button.setMaximumWidth(80)
        self.detach_button.clicked.connect(self._toggle_detach)
        header_layout.addWidget(self.detach_button)
        
        parent_layout.addWidget(header_frame)
        
    def _connect_signals(self):
        """Connect internal preview signals to external signals"""
        # Forward preview control signals
        self.preview_widget.play_requested.connect(self.play_requested)
        self.preview_widget.pause_requested.connect(self.pause_requested)
        self.preview_widget.seek_requested.connect(self.seek_requested)
        
        # Forward synchronization signals
        self.preview_widget.subtitle_updated.connect(self.subtitle_updated)
        self.preview_widget.time_changed.connect(self.time_changed)
        
    def _toggle_detach(self):
        """Toggle between detached and attached states"""
        if self.is_detached:
            self._attach_to_parent()
        else:
            self._detach_from_parent()
            
    def _detach_from_parent(self):
        """Detach preview to standalone window"""
        if self.is_detached:
            return
            
        # Store parent information
        parent_widget = self.parent()
        if isinstance(parent_widget, QTabWidget):
            self.parent_tab_widget = parent_widget
            self.tab_index = parent_widget.indexOf(self)
            self.tab_title = parent_widget.tabText(self.tab_index)
            
        # Create detached window
        self.detached_window = DetachedPreviewWindow(self)
        
        # Remove from parent and add to detached window
        if self.parent():
            self.setParent(None)
            
        self.detached_window.setCentralWidget(self)
        self.detached_window.show()
        
        # Update state
        self.is_detached = True
        self.detach_button.setText("Attach")
        
        # Emit signal
        self.detach_requested.emit()
        
    def _attach_to_parent(self):
        """Attach preview back to parent tab widget"""
        if not self.is_detached or not self.parent_tab_widget:
            return
            
        # Remove from detached window
        if self.detached_window:
            self.detached_window.setCentralWidget(QWidget())  # Dummy widget
            self.setParent(None)
            
        # Close detached window first
        if self.detached_window:
            self.detached_window.close()
            self.detached_window = None
            
        # Update state before adding back to parent
        self.is_detached = False
        self.detach_button.setText("Detach")
            
        # Add back to parent tab widget
        if self.tab_index >= 0 and self.tab_index < self.parent_tab_widget.count():
            self.parent_tab_widget.insertTab(self.tab_index, self, self.tab_title)
            self.parent_tab_widget.setCurrentIndex(self.tab_index)
        else:
            self.parent_tab_widget.addTab(self, self.tab_title)
            self.parent_tab_widget.setCurrentWidget(self)
        
        # Emit signal
        self.attach_requested.emit()
        
    def set_parent_tab_widget(self, tab_widget: QTabWidget, tab_index: int = -1, tab_title: str = "Preview"):
        """Set the parent tab widget for reattachment"""
        self.parent_tab_widget = tab_widget
        self.tab_index = tab_index
        self.tab_title = tab_title
        
    def closeEvent(self, event: QCloseEvent):
        """Handle close event"""
        if self.is_detached and self.detached_window:
            # If detached, close the detached window instead
            self.detached_window.close()
            event.ignore()
        else:
            self.closed.emit()
            event.accept()
            
    # Forward all preview widget methods
    def load_project(self, project: Project):
        """Load a project for synchronized preview"""
        return self.preview_widget.load_project(project)
        
    def update_subtitles_realtime(self, subtitle_lines: List[SubtitleLine], subtitle_styles: dict):
        """Update subtitles in real-time during editing"""
        self.preview_widget.update_subtitles_realtime(subtitle_lines, subtitle_styles)
        
    def add_effect(self, effect_id: str, parameters: dict):
        """Add a text effect to the preview"""
        self.preview_widget.add_effect(effect_id, parameters)
        
    def remove_effect(self, effect_id: str):
        """Remove a text effect from the preview"""
        self.preview_widget.remove_effect(effect_id)
        
    def update_effect_parameters(self, effect_id: str, parameters: dict):
        """Update effect parameters in real-time"""
        self.preview_widget.update_effect_parameters(effect_id, parameters)
        
    def toggle_effect(self, effect_id: str, enabled: bool):
        """Toggle an effect on/off"""
        self.preview_widget.toggle_effect(effect_id, enabled)
        
    def apply_effect_preset(self, preset_name: str):
        """Apply an effect preset"""
        self.preview_widget.apply_effect_preset(preset_name)
        
    def load_video_frame(self, frame_image):
        """Load a video frame into the preview"""
        self.preview_widget.load_video_frame(frame_image)
        
    def update_timeline(self, current_time, total_time):
        """Update timeline position and time labels"""
        self.preview_widget.update_timeline(current_time, total_time)
        
    def set_playback_state(self, is_playing):
        """Update playback button state"""
        self.preview_widget.set_playback_state(is_playing)
        
    def reset_playback(self):
        """Reset playback to initial state"""
        self.preview_widget.reset_playback()


class DetachedPreviewWindow(QMainWindow):
    """Standalone window for detached preview"""
    
    def __init__(self, preview_widget: DetachablePreviewWidget):
        super().__init__()
        
        self.preview_widget = preview_widget
        
        # Window setup
        self.setWindowTitle("Karaoke Video Preview")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Center on screen
        self._center_on_screen()
        
        # Set window icon if available
        try:
            self.setWindowIcon(QIcon("assets/icons/preview.png"))
        except:
            pass
            
    def _center_on_screen(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            window_geometry = self.geometry()
            
            x = (screen_geometry.width() - window_geometry.width()) // 2
            y = (screen_geometry.height() - window_geometry.height()) // 2
            
            self.move(x, y)
            
    def closeEvent(self, event: QCloseEvent):
        """Handle window close - reattach preview to parent"""
        if self.preview_widget and self.preview_widget.is_detached:
            # Ask user if they want to reattach or close
            reply = QMessageBox.question(
                self,
                "Close Preview",
                "Do you want to reattach the preview to the main window?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reattach to parent
                self.preview_widget._attach_to_parent()
            else:
                # Just close
                self.preview_widget.closed.emit()
        
        event.accept()


class TabMergeablePreviewWidget(DetachablePreviewWidget):
    """Preview widget that can be merged into other tab widgets"""
    
    # Additional signals for tab merging
    merge_requested = pyqtSignal(QWidget)  # Request to merge into another tab widget
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Add merge button to header
        self._add_merge_controls()
        
    def _add_merge_controls(self):
        """Add merge controls to the header"""
        # Find the header frame
        header_frame = self.findChild(QFrame)
        if header_frame:
            header_layout = header_frame.layout()
            
            # Add merge button before detach button
            self.merge_button = QPushButton("Merge")
            self.merge_button.setMaximumWidth(80)
            self.merge_button.clicked.connect(self._request_merge)
            
            # Insert before the detach button (which should be the last item)
            header_layout.insertWidget(header_layout.count() - 1, self.merge_button)
            
    def _request_merge(self):
        """Request to merge into another tab widget"""
        # This will be handled by the parent application
        self.merge_requested.emit(self)
        
    def merge_into_tab_widget(self, target_tab_widget: QTabWidget, tab_title: str = None):
        """Merge this preview into another tab widget"""
        if not tab_title:
            tab_title = self.tab_title
            
        # Remove from current parent
        if self.parent():
            current_parent = self.parent()
            if isinstance(current_parent, QTabWidget):
                index = current_parent.indexOf(self)
                if index >= 0:
                    current_parent.removeTab(index)
            else:
                self.setParent(None)
                
        # Add to target tab widget
        target_tab_widget.addTab(self, tab_title)
        target_tab_widget.setCurrentWidget(self)
        
        # Update parent information
        self.parent_tab_widget = target_tab_widget
        self.tab_index = target_tab_widget.indexOf(self)
        self.tab_title = tab_title