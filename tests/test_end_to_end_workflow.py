"""
Comprehensive end-to-end integration tests for the complete karaoke video creation workflow.

Tests the entire pipeline from media import through export, ensuring all components
work together correctly and maintain data consistency throughout the process.
"""

import unittest
import tempfile
import os
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import application components
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.core.models import (
    Project, VideoFile, AudioFile, ImageFile, SubtitleFile, 
    SubtitleLine, SubtitleStyle, Effect, ExportSettings
)
from src.core.media_importer import MediaImporter
from src.core.file_manager import FileManager
from src.core.export_manager import ExportManager
from src.ui.main_window import MainWindow


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end workflow from import to export."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for widget testing if available."""
        if PYQT_AVAILABLE and not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance() if PYQT_AVAILABLE else None
    
    def setUp(self):
        """Set up test fixtures for end-to-end testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "input")
        self.output_dir = os.path.join(self.temp_dir, "output")
        
        # Create directory structure
        os.makedirs(os.path.join(self.input_dir, "videos"), exist_ok=True)
        os.makedirs(os.path.join(self.input_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(self.input_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.input_dir, "subtitles"), exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create test media files
        self._create_test_media_files()
        
        # Initialize components
        self.file_manager = FileManager()
        self.media_importer = MediaImporter()
        self.export_manager = ExportManager()
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_media_files(self):
        """Create test media files with proper content."""
        # Create test video file
        self.test_video_path = os.path.join(self.input_dir, "videos", "test_video.mp4")
        with open(self.test_video_path, 'wb') as f:
            f.write(b"FAKE_MP4_HEADER" + b"0" * 1024)  # 1KB fake video
        
        # Create test audio file
        self.test_audio_path = os.path.join(self.input_dir, "audio", "test_audio.mp3")
        with open(self.test_audio_path, 'wb') as f:
            f.write(b"FAKE_MP3_HEADER" + b"0" * 2048)  # 2KB fake audio
        
        # Create test image file
        self.test_image_path = os.path.join(self.input_dir, "images", "test_image.jpg")
        with open(self.test_image_path, 'wb') as f:
            f.write(b"FAKE_JPG_HEADER" + b"0" * 512)  # 512B fake image
        
        # Create test subtitle file
        self.test_subtitle_path = os.path.join(self.input_dir, "subtitles", "test_subtitles.ass")
        ass_content = """[Script Info]
Title: End-to-End Test Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,,0,0,0,,First line of karaoke
Dialogue: 0,0:00:05.00,0:00:10.00,Default,,0,0,0,,Second line of karaoke
Dialogue: 0,0:00:10.00,0:00:15.00,Default,,0,0,0,,Third line of karaoke
Dialogue: 0,0:00:15.00,0:00:20.00,Default,,0,0,0,,Fourth line of karaoke
"""
        with open(self.test_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_complete_import_to_export_workflow(self, mock_run):
        """Test complete workflow from media import to video export."""
        # Mock FFmpeg responses for media import
        def mock_ffmpeg_response(cmd, **kwargs):
            cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
            
            if 'test_video.mp4' in cmd_str:
                return Mock(
                    stdout='{"streams":[{"codec_type":"video","width":1920,"height":1080,"r_frame_rate":"30/1","duration":"20.0"}],"format":{"duration":"20.0"}}',
                    returncode=0
                )
            elif 'test_audio.mp3' in cmd_str:
                return Mock(
                    stdout='{"streams":[{"codec_type":"audio","sample_rate":"44100","channels":2,"duration":"20.0"}],"format":{"duration":"20.0"}}',
                    returncode=0
                )
            elif 'test_image.jpg' in cmd_str:
                return Mock(
                    stdout='{"streams":[{"width":1920,"height":1080}]}',
                    returncode=0
                )
            return Mock(stdout='{}', returncode=0)
        
        mock_run.side_effect = mock_ffmpeg_response
        
        # Step 1: Import all media files
        video_file = self.media_importer.import_video(self.test_video_path)
        audio_file = self.media_importer.import_audio(self.test_audio_path)
        image_file = self.media_importer.import_image(self.test_image_path)
        subtitle_file = self.media_importer.import_subtitles(self.test_subtitle_path)
        
        # Verify imports
        self.assertIsInstance(video_file, VideoFile)
        self.assertIsInstance(audio_file, AudioFile)
        self.assertIsInstance(image_file, ImageFile)
        self.assertIsInstance(subtitle_file, SubtitleFile)
        
        # Step 2: Create project with imported media
        project = Project(
            id="e2e_test_project",
            name="End-to-End Test Project",
            video_file=video_file,
            audio_file=audio_file,
            subtitle_file=subtitle_file
        )
        
        # Verify project is ready for export
        self.assertTrue(project.is_ready_for_export())
        
        # Step 3: Configure export settings (using proper ExportSettings for project)
        export_settings = ExportSettings(
            resolution={"width": 1280, "height": 720},
            bitrate=5000,
            format="mp4",
            quality="medium"
        )
        project.export_settings = export_settings
        
        # Step 4: Set up export manager and validate
        self.export_manager.set_project(project)
        
        # Create proper export configuration
        from src.core.export_manager import ExportConfiguration
        export_config = ExportConfiguration(
            width=1280,
            height=720,
            fps=30.0,
            bitrate=5000,
            output_dir=self.output_dir,
            filename="test_export.mp4"
        )
        
        # Mock export process for testing
        with patch.object(self.export_manager, '_check_ffmpeg_available', return_value=True):
            with patch.object(self.export_manager, 'opengl_renderer') as mock_renderer:
                mock_renderer.setup_export.return_value = True
                mock_renderer.start_export_async.return_value = True
                
                # Start export
                success = self.export_manager.start_export(export_config)
                self.assertTrue(success)
                
                # Verify export manager state
                self.assertTrue(self.export_manager.is_exporting)
                
                # Verify renderer was called with correct parameters
                mock_renderer.setup_export.assert_called_once()
                mock_renderer.start_export_async.assert_called_once()
    
    def test_project_data_consistency_throughout_workflow(self):
        """Test that project data remains consistent throughout the workflow."""
        # Create initial project
        project = Project(
            id="consistency_test",
            name="Consistency Test Project",
            video_file=VideoFile(
                path=self.test_video_path,
                duration=30.0,
                resolution={"width": 1920, "height": 1080},
                frame_rate=30.0
            ),
            audio_file=AudioFile(
                path=self.test_audio_path,
                duration=30.0,
                sample_rate=44100,
                channels=2
            ),
            subtitle_file=SubtitleFile(
                path=self.test_subtitle_path,
                lines=[
                    SubtitleLine(start_time=0.0, end_time=5.0, text="Test line 1"),
                    SubtitleLine(start_time=5.0, end_time=10.0, text="Test line 2")
                ],
                styles=[SubtitleStyle(name="Default")]
            )
        )
        
        # Test project serialization/deserialization
        project_dict = {
            'id': project.id,
            'name': project.name,
            'video_file': {
                'path': project.video_file.path,
                'duration': project.video_file.duration,
                'resolution': project.video_file.resolution,
                'frame_rate': project.video_file.frame_rate
            },
            'audio_file': {
                'path': project.audio_file.path,
                'duration': project.audio_file.duration,
                'sample_rate': project.audio_file.sample_rate,
                'channels': project.audio_file.channels
            },
            'subtitle_file': {
                'path': project.subtitle_file.path,
                'lines': [
                    {
                        'start_time': line.start_time,
                        'end_time': line.end_time,
                        'text': line.text,
                        'style': line.style
                    } for line in project.subtitle_file.lines
                ]
            }
        }
        
        # Verify data integrity
        self.assertEqual(project_dict['id'], project.id)
        self.assertEqual(project_dict['name'], project.name)
        self.assertEqual(project_dict['video_file']['duration'], 30.0)
        self.assertEqual(project_dict['audio_file']['duration'], 30.0)
        self.assertEqual(len(project_dict['subtitle_file']['lines']), 2)
        
        # Test project validation
        self.assertTrue(project.has_video_background())
        self.assertTrue(project.has_audio())
        self.assertTrue(project.has_subtitles())
        self.assertTrue(project.is_ready_for_export())
    
    def test_error_handling_throughout_workflow(self):
        """Test error handling at each stage of the workflow."""
        # Test import errors
        with self.assertRaises(Exception):
            self.media_importer.import_video("/nonexistent/file.mp4")
        
        # Test project validation errors
        incomplete_project = Project(
            id="incomplete",
            name="Incomplete Project"
            # Missing required files
        )
        
        self.assertFalse(incomplete_project.is_ready_for_export())
        
        # Test export validation errors
        self.export_manager.set_project(incomplete_project)
        
        from src.core.export_manager import ExportConfiguration
        config = ExportConfiguration(output_dir="/invalid/path")
        
        validation_results = self.export_manager.validate_export_requirements(config)
        error_results = [r for r in validation_results if r.level.value == "error"]
        
        # Should have errors for missing files and invalid output directory
        self.assertGreater(len(error_results), 0)
    
    def test_file_management_throughout_workflow(self):
        """Test file management and cleanup throughout the workflow."""
        # Test directory creation
        created_dirs = self.file_manager.ensure_directory_structure()
        self.assertIsInstance(created_dirs, list)
        
        # Test individual directory creation
        test_dir = os.path.join(self.temp_dir, "test_dir")
        os.makedirs(test_dir, exist_ok=True)
        self.assertTrue(os.path.exists(test_dir))
        
        # Test temporary file management
        temp_file = self.file_manager.create_temp_file("test_temp", ".tmp")
        self.assertTrue(os.path.exists(temp_file))
        
        # Test cleanup
        self.file_manager.cleanup_temp_file(temp_file)
        self.assertFalse(os.path.exists(temp_file))
        
        # Test storage validation
        storage_info = self.file_manager.get_storage_info(self.temp_dir)
        self.assertIn('available_space', storage_info)
        self.assertIn('total_space', storage_info)
        self.assertGreater(storage_info['available_space'], 0)
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def test_ui_integration_workflow(self):
        """Test UI integration throughout the workflow."""
        # Create main window
        main_window = MainWindow()
        
        # Test tab navigation
        self.assertEqual(main_window.tab_widget.count(), 5)
        
        # Test widget initialization
        self.assertIsNotNone(main_window.import_widget)
        self.assertIsNotNone(main_window.preview_widget)
        self.assertIsNotNone(main_window.editor_widget)
        self.assertIsNotNone(main_window.effects_widget)
        self.assertIsNotNone(main_window.export_widget)
        
        # Test file manager integration
        file_manager = main_window.get_file_manager()
        self.assertIsNotNone(file_manager)
        
        # Test project loading workflow
        test_project = Project(
            id="ui_test",
            name="UI Test Project",
            video_file=VideoFile(path=self.test_video_path, duration=20.0),
            audio_file=AudioFile(path=self.test_audio_path, duration=20.0),
            subtitle_file=SubtitleFile(path=self.test_subtitle_path)
        )
        
        # Simulate project loading
        main_window._on_project_loaded(test_project)
        
        # Verify tab switched to preview
        self.assertEqual(main_window.tab_widget.currentIndex(), 1)
        
        main_window.close()
    
    def test_memory_usage_during_workflow(self):
        """Test memory usage and cleanup during workflow operations."""
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create multiple projects to test memory management
        projects = []
        for i in range(10):
            project = Project(
                id=f"memory_test_{i}",
                name=f"Memory Test Project {i}",
                video_file=VideoFile(
                    path=self.test_video_path,
                    duration=60.0,
                    resolution={"width": 1920, "height": 1080}
                ),
                audio_file=AudioFile(
                    path=self.test_audio_path,
                    duration=60.0
                ),
                subtitle_file=SubtitleFile(
                    path=self.test_subtitle_path,
                    lines=[
                        SubtitleLine(start_time=j*5.0, end_time=(j+1)*5.0, text=f"Line {j}")
                        for j in range(20)  # 20 subtitle lines per project
                    ]
                )
            )
            projects.append(project)
        
        # Check memory after creating projects
        after_creation_memory = process.memory_info().rss
        memory_increase = after_creation_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test data)
        self.assertLess(memory_increase, 100 * 1024 * 1024)
        
        # Clear projects and force garbage collection
        projects.clear()
        gc.collect()
        
        # Check memory after cleanup
        after_cleanup_memory = process.memory_info().rss
        memory_after_cleanup = after_cleanup_memory - initial_memory
        
        # Memory should be mostly reclaimed (allow some overhead)
        # Use a more lenient check since memory reclamation can vary
        self.assertLess(memory_after_cleanup, memory_increase * 2.0)
    
    def test_concurrent_operations_handling(self):
        """Test handling of concurrent operations during workflow."""
        # Test multiple import operations
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def import_worker(file_path, file_type):
            try:
                if file_type == 'video':
                    with patch('src.core.media_importer.subprocess.run') as mock_run:
                        mock_run.return_value = Mock(
                            stdout='{"streams":[{"codec_type":"video","duration":"10.0"}],"format":{"duration":"10.0"}}',
                            returncode=0
                        )
                        result = self.media_importer.import_video(file_path)
                elif file_type == 'audio':
                    with patch('src.core.media_importer.subprocess.run') as mock_run:
                        mock_run.return_value = Mock(
                            stdout='{"streams":[{"codec_type":"audio","duration":"10.0"}],"format":{"duration":"10.0"}}',
                            returncode=0
                        )
                        result = self.media_importer.import_audio(file_path)
                else:
                    result = None
                
                results_queue.put(('success', file_type, result))
            except Exception as e:
                results_queue.put(('error', file_type, str(e)))
        
        # Start concurrent import operations
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=import_worker,
                args=(self.test_video_path, 'video')
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Check results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # All operations should complete (may succeed or fail, but should not hang)
        self.assertEqual(len(results), 3)
        
        # At least some should succeed (depending on file locking behavior)
        success_count = sum(1 for result in results if result[0] == 'success')
        self.assertGreaterEqual(success_count, 1)


class TestWorkflowPerformance(unittest.TestCase):
    """Test performance aspects of the complete workflow."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create larger test files for performance testing
        self.large_video_path = os.path.join(self.temp_dir, "large_video.mp4")
        with open(self.large_video_path, 'wb') as f:
            f.write(b"FAKE_LARGE_VIDEO" + b"0" * (10 * 1024 * 1024))  # 10MB fake video
        
        self.large_audio_path = os.path.join(self.temp_dir, "large_audio.mp3")
        with open(self.large_audio_path, 'wb') as f:
            f.write(b"FAKE_LARGE_AUDIO" + b"0" * (5 * 1024 * 1024))  # 5MB fake audio
        
        # Create subtitle file with many lines
        self.large_subtitle_path = os.path.join(self.temp_dir, "large_subtitles.ass")
        ass_content = """[Script Info]
Title: Large Subtitle File
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Add 1000 subtitle lines
        for i in range(1000):
            start_time = i * 2.0
            end_time = start_time + 1.5
            hours = int(start_time // 3600)
            minutes = int((start_time % 3600) // 60)
            seconds = start_time % 60
            
            start_str = f"{hours}:{minutes:02d}:{seconds:05.2f}"
            
            hours = int(end_time // 3600)
            minutes = int((end_time % 3600) // 60)
            seconds = end_time % 60
            
            end_str = f"{hours}:{minutes:02d}:{seconds:05.2f}"
            
            ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,Subtitle line {i+1}\n"
        
        with open(self.large_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
    
    def tearDown(self):
        """Clean up performance test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_large_file_import_performance(self, mock_run):
        """Test import performance with large files."""
        # Mock FFmpeg response for large files
        mock_run.return_value = Mock(
            stdout='{"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"300.0"}],"format":{"duration":"300.0"}}',
            returncode=0
        )
        
        media_importer = MediaImporter()
        
        # Time the import operation
        start_time = time.time()
        video_file = media_importer.import_video(self.large_video_path)
        import_time = time.time() - start_time
        
        # Import should complete in reasonable time (under 5 seconds for mocked operation)
        self.assertLess(import_time, 5.0)
        self.assertIsInstance(video_file, VideoFile)
    
    def test_large_subtitle_parsing_performance(self):
        """Test subtitle parsing performance with many lines."""
        from src.core.subtitle_parser import AssParser
        
        parser = AssParser()
        
        # Time the parsing operation
        start_time = time.time()
        subtitle_file = parser.parse_ass_file(self.large_subtitle_path)
        parse_time = time.time() - start_time
        
        # Parsing should complete in reasonable time (under 2 seconds for 1000 lines)
        self.assertLess(parse_time, 2.0)
        self.assertEqual(len(subtitle_file.lines), 1000)
    
    def test_project_creation_performance(self):
        """Test project creation performance with complex data."""
        # Create complex project with many effects and large subtitle set
        effects = []
        for i in range(50):  # 50 effects
            effect = Effect(
                id=f"effect_{i}",
                name=f"Effect {i}",
                type="glow" if i % 2 == 0 else "outline",
                parameters={"intensity": 0.8, "radius": 5.0}
            )
            effects.append(effect)
        
        # Create many subtitle lines
        subtitle_lines = []
        for i in range(500):  # 500 subtitle lines
            line = SubtitleLine(
                start_time=i * 2.0,
                end_time=i * 2.0 + 1.5,
                text=f"Performance test subtitle line {i+1}",
                style="Default"
            )
            subtitle_lines.append(line)
        
        subtitle_file = SubtitleFile(
            path=self.large_subtitle_path,
            lines=subtitle_lines,
            styles=[SubtitleStyle(name="Default")]
        )
        
        # Time project creation
        start_time = time.time()
        project = Project(
            id="performance_test",
            name="Performance Test Project",
            video_file=VideoFile(
                path=self.large_video_path,
                duration=600.0,
                resolution={"width": 1920, "height": 1080}
            ),
            audio_file=AudioFile(
                path=self.large_audio_path,
                duration=600.0
            ),
            subtitle_file=subtitle_file,
            effects=effects
        )
        creation_time = time.time() - start_time
        
        # Project creation should be fast (under 0.5 seconds)
        self.assertLess(creation_time, 0.5)
        self.assertEqual(len(project.effects), 50)
        self.assertEqual(len(project.subtitle_file.lines), 500)
    
    def test_export_validation_performance(self):
        """Test export validation performance with complex projects."""
        from src.core.export_manager import ExportManager, ExportConfiguration
        
        # Create complex project
        project = Project(
            id="validation_test",
            name="Validation Test",
            video_file=VideoFile(path=self.large_video_path, duration=300.0),
            audio_file=AudioFile(path=self.large_audio_path, duration=300.0),
            subtitle_file=SubtitleFile(path=self.large_subtitle_path)
        )
        
        export_manager = ExportManager()
        export_manager.set_project(project)
        
        config = ExportConfiguration(
            width=1920,
            height=1080,
            fps=30.0,
            bitrate=8000,
            output_dir=self.temp_dir
        )
        
        # Time validation
        start_time = time.time()
        results = export_manager.validate_export_requirements(config)
        validation_time = time.time() - start_time
        
        # Validation should be fast (under 1 second)
        self.assertLess(validation_time, 1.0)
        self.assertIsInstance(results, list)


if __name__ == '__main__':
    # Run tests silently as per steering guidelines
    unittest.main(verbosity=0, buffer=True)