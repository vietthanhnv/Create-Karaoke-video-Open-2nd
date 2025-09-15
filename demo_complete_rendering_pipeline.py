#!/usr/bin/env python3
"""
Demo: Complete Rendering Pipeline Integration

This demo showcases the complete rendering pipeline that integrates libass,
OpenGL effects, and FFmpeg export systems into a unified end-to-end workflow.
"""

import sys
import time
import tempfile
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, 'src')

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QProgressBar
from PyQt6.QtCore import QTimer, pyqtSignal

from core.complete_rendering_pipeline import (
    CompleteRenderingPipeline, PipelineConfig, PipelineStage,
    create_preview_pipeline, create_export_pipeline
)
from core.models import Project, AudioFile, SubtitleFile, SubtitleLine, SubtitleStyle, WordTiming


class PipelineDemoWindow(QMainWindow):
    """Demo window for complete rendering pipeline"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Complete Rendering Pipeline Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Pipeline instances
        self.preview_pipeline = None
        self.export_pipeline = None
        self.current_project = None
        
        self.setup_ui()
        self.create_sample_project()
        
    def setup_ui(self):
        """Setup the demo UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Complete Rendering Pipeline Demo")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Status display
        self.status_label = QLabel("Ready to start pipeline demo")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Performance stats
        self.stats_label = QLabel("Performance stats will appear here")
        self.stats_label.setStyleSheet("font-family: monospace; background: #f0f0f0; padding: 10px;")
        layout.addWidget(self.stats_label)
        
        # Control buttons
        self.preview_button = QPushButton("Start Preview Pipeline")
        self.preview_button.clicked.connect(self.start_preview_pipeline)
        layout.addWidget(self.preview_button)
        
        self.export_button = QPushButton("Start Export Pipeline")
        self.export_button.clicked.connect(self.start_export_pipeline)
        layout.addWidget(self.export_button)
        
        self.stop_button = QPushButton("Stop Pipeline")
        self.stop_button.clicked.connect(self.stop_pipeline)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        
        # Stats update timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)  # Update every second
        
    def create_sample_project(self):
        """Create a sample project for demonstration"""
        # Create word timings for karaoke effect
        word_timings = [
            WordTiming("Hello", 1.0, 1.5),
            WordTiming("world", 1.5, 2.0),
            WordTiming("this", 2.0, 2.3),
            WordTiming("is", 2.3, 2.5),
            WordTiming("karaoke", 2.5, 3.0)
        ]
        
        # Create subtitle lines with karaoke timing
        subtitle_lines = [
            SubtitleLine(
                start_time=1.0,
                end_time=3.0,
                text="Hello world this is karaoke",
                style="Default",
                word_timings=word_timings
            ),
            SubtitleLine(
                start_time=4.0,
                end_time=6.0,
                text="With amazing visual effects",
                style="Default"
            ),
            SubtitleLine(
                start_time=7.0,
                end_time=9.0,
                text="Rendered in real-time",
                style="Default"
            )
        ]
        
        # Create subtitle style
        subtitle_style = SubtitleStyle(
            name="Default",
            font_name="Arial",
            font_size=48,
            primary_color="&H00FFFFFF",  # White
            secondary_color="&H0000FFFF",  # Yellow
            outline_color="&H00000000",  # Black
            back_color="&H80808080"  # Semi-transparent gray
        )
        
        # Create subtitle file
        subtitle_file = SubtitleFile(
            path="demo.ass",
            lines=subtitle_lines,
            styles=[subtitle_style]
        )
        
        # Create audio file (mock)
        audio_file = AudioFile(
            path="demo_audio.mp3",
            duration=10.0,
            sample_rate=44100,
            channels=2
        )
        
        # Create project
        self.current_project = Project(
            id="demo_project",
            name="Complete Pipeline Demo",
            audio_file=audio_file,
            subtitle_file=subtitle_file
        )
        
        self.status_label.setText(f"Sample project created: {len(subtitle_lines)} subtitles, {audio_file.duration}s duration")
    
    def start_preview_pipeline(self):
        """Start the preview pipeline"""
        try:
            self.status_label.setText("Initializing preview pipeline...")
            
            # Create preview pipeline
            self.preview_pipeline = create_preview_pipeline(1280, 720)
            
            # Connect signals
            self.preview_pipeline.pipeline_started.connect(
                lambda: self.status_label.setText("Preview pipeline started")
            )
            self.preview_pipeline.stage_changed.connect(
                lambda stage: self.status_label.setText(f"Pipeline stage: {stage}")
            )
            self.preview_pipeline.progress_updated.connect(
                self.update_progress
            )
            self.preview_pipeline.pipeline_completed.connect(
                lambda path: self.status_label.setText(f"Preview completed: {path}")
            )
            self.preview_pipeline.pipeline_failed.connect(
                lambda error: self.status_label.setText(f"Preview failed: {error}")
            )
            
            # Initialize with project
            success = self.preview_pipeline.initialize(self.current_project)
            
            if success:
                # Start preview mode
                self.preview_pipeline.start_rendering("", preview_mode=True)
                
                self.preview_button.setEnabled(False)
                self.export_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.progress_bar.setVisible(True)
                
                self.status_label.setText("Preview pipeline running...")
            else:
                self.status_label.setText("Failed to initialize preview pipeline")
                
        except Exception as e:
            self.status_label.setText(f"Error starting preview: {e}")
    
    def start_export_pipeline(self):
        """Start the export pipeline"""
        try:
            self.status_label.setText("Initializing export pipeline...")
            
            # Create export pipeline
            self.export_pipeline = create_export_pipeline(1920, 1080, 30.0)
            
            # Connect signals
            self.export_pipeline.pipeline_started.connect(
                lambda: self.status_label.setText("Export pipeline started")
            )
            self.export_pipeline.stage_changed.connect(
                lambda stage: self.status_label.setText(f"Export stage: {stage}")
            )
            self.export_pipeline.progress_updated.connect(
                self.update_progress
            )
            self.export_pipeline.pipeline_completed.connect(
                lambda path: self.status_label.setText(f"Export completed: {path}")
            )
            self.export_pipeline.pipeline_failed.connect(
                lambda error: self.status_label.setText(f"Export failed: {error}")
            )
            
            # Initialize with project
            success = self.export_pipeline.initialize(self.current_project)
            
            if success:
                # Create temporary output file
                output_path = os.path.join(tempfile.gettempdir(), "demo_output.mp4")
                
                # Start export
                self.export_pipeline.start_rendering(output_path, preview_mode=False)
                
                self.preview_button.setEnabled(False)
                self.export_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                self.progress_bar.setVisible(True)
                
                self.status_label.setText(f"Export pipeline running, output: {output_path}")
            else:
                self.status_label.setText("Failed to initialize export pipeline")
                
        except Exception as e:
            self.status_label.setText(f"Error starting export: {e}")
    
    def stop_pipeline(self):
        """Stop the current pipeline"""
        try:
            if self.preview_pipeline:
                self.preview_pipeline.stop_rendering()
                self.preview_pipeline.cleanup()
                self.preview_pipeline = None
            
            if self.export_pipeline:
                self.export_pipeline.stop_rendering()
                self.export_pipeline.cleanup()
                self.export_pipeline = None
            
            self.preview_button.setEnabled(True)
            self.export_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_bar.setVisible(False)
            
            self.status_label.setText("Pipeline stopped")
            
        except Exception as e:
            self.status_label.setText(f"Error stopping pipeline: {e}")
    
    def update_progress(self, progress):
        """Update progress bar"""
        self.progress_bar.setValue(int(progress))
    
    def update_stats(self):
        """Update performance statistics display"""
        try:
            stats_text = "Performance Statistics:\n"
            
            # Get stats from active pipeline
            active_pipeline = self.preview_pipeline or self.export_pipeline
            
            if active_pipeline:
                stats = active_pipeline.get_performance_stats()
                
                # Pipeline state
                pipeline_stats = stats.get('pipeline_state', {})
                stats_text += f"Stage: {pipeline_stats.get('stage', 'N/A')}\n"
                stats_text += f"Progress: {pipeline_stats.get('progress_percent', 0):.1f}%\n"
                stats_text += f"Frames Rendered: {pipeline_stats.get('frames_rendered', 0)}\n"
                stats_text += f"Frames Dropped: {pipeline_stats.get('frames_dropped', 0)}\n"
                stats_text += f"Avg Render Time: {pipeline_stats.get('average_render_time', 0):.3f}s\n"
                stats_text += f"Running: {pipeline_stats.get('is_running', False)}\n"
                stats_text += f"Paused: {pipeline_stats.get('is_paused', False)}\n"
                
                # Effects pipeline stats
                effects_stats = stats.get('effects_pipeline', {})
                if effects_stats:
                    stats_text += f"\nEffects Pipeline:\n"
                    stats_text += f"Frame Count: {effects_stats.get('frame_count', 0)}\n"
                    stats_text += f"FPS Estimate: {effects_stats.get('fps_estimate', 0):.1f}\n"
                    stats_text += f"Active Passes: {effects_stats.get('active_passes', 0)}\n"
                
                # Texture cache stats
                cache_stats = stats.get('texture_cache', {})
                if cache_stats:
                    stats_text += f"\nTexture Cache:\n"
                    stats_text += f"Hit Rate: {cache_stats.get('hit_rate', 0):.2f}\n"
                    stats_text += f"Cache Size: {cache_stats.get('cache_size', 0)}\n"
                
            else:
                stats_text += "No active pipeline\n"
                stats_text += f"Project: {self.current_project.name if self.current_project else 'None'}\n"
                if self.current_project and self.current_project.subtitle_file:
                    stats_text += f"Subtitles: {len(self.current_project.subtitle_file.lines)}\n"
                if self.current_project and self.current_project.audio_file:
                    stats_text += f"Audio Duration: {self.current_project.audio_file.duration}s\n"
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            self.stats_label.setText(f"Error updating stats: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.stop_pipeline()
        event.accept()


def main():
    """Main demo function"""
    print("Complete Rendering Pipeline Demo")
    print("=" * 40)
    
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Create and show demo window
    demo_window = PipelineDemoWindow()
    demo_window.show()
    
    print("Demo window opened. You can:")
    print("1. Click 'Start Preview Pipeline' for real-time preview")
    print("2. Click 'Start Export Pipeline' for video export")
    print("3. Monitor performance statistics")
    print("4. Close window to exit")
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()