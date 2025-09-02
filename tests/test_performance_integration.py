"""
Performance integration tests for large video files and complex effects.

Tests the application's performance under stress conditions including
large media files, complex effect combinations, and resource-intensive operations.
"""

import unittest
import tempfile
import os
import shutil
import time
import threading
import psutil
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.models import (
    Project, VideoFile, AudioFile, SubtitleFile, 
    SubtitleLine, SubtitleStyle, Effect
)
from src.core.media_importer import MediaImporter
from src.core.effects_manager import EffectsManager, EffectType
from src.core.export_manager import ExportManager, ExportConfiguration
from src.core.opengl_export_renderer import OpenGLExportRenderer


class TestLargeFilePerformance(unittest.TestCase):
    """Test performance with large media files."""
    
    def setUp(self):
        """Set up large file performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create large test files
        self.large_video_path = os.path.join(self.temp_dir, "large_video.mp4")
        self.large_audio_path = os.path.join(self.temp_dir, "large_audio.mp3")
        self.large_subtitle_path = os.path.join(self.temp_dir, "large_subtitles.ass")
        
        # Create 50MB fake video file
        with open(self.large_video_path, 'wb') as f:
            f.write(b"FAKE_LARGE_VIDEO_HEADER")
            # Write in chunks to avoid memory issues
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(50):  # 50MB total
                f.write(b"0" * chunk_size)
        
        # Create 20MB fake audio file
        with open(self.large_audio_path, 'wb') as f:
            f.write(b"FAKE_LARGE_AUDIO_HEADER")
            chunk_size = 1024 * 1024  # 1MB chunks
            for _ in range(20):  # 20MB total
                f.write(b"0" * chunk_size)
        
        # Create subtitle file with 5000 lines
        self._create_large_subtitle_file()
        
        # Initialize performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
    
    def tearDown(self):
        """Clean up large file test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_large_subtitle_file(self):
        """Create a large subtitle file with many lines."""
        ass_content = """[Script Info]
Title: Large Performance Test Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Add 5000 subtitle lines (about 2.5 hours of content)
        for i in range(5000):
            start_time = i * 1.8  # 1.8 seconds per line
            end_time = start_time + 1.5
            
            # Convert to ASS time format
            start_h = int(start_time // 3600)
            start_m = int((start_time % 3600) // 60)
            start_s = start_time % 60
            
            end_h = int(end_time // 3600)
            end_m = int((end_time % 3600) // 60)
            end_s = end_time % 60
            
            start_str = f"{start_h}:{start_m:02d}:{start_s:05.2f}"
            end_str = f"{end_h}:{end_m:02d}:{end_s:05.2f}"
            
            ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,Performance test subtitle line {i+1} with some longer text to test rendering performance\n"
        
        with open(self.large_subtitle_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_large_video_import_performance(self, mock_run):
        """Test import performance with large video files."""
        # Mock FFmpeg response for large video
        mock_run.return_value = Mock(
            stdout='{"streams":[{"codec_type":"video","width":1920,"height":1080,"duration":"1800.0","r_frame_rate":"30/1"}],"format":{"duration":"1800.0","size":"52428800"}}',
            returncode=0
        )
        
        media_importer = MediaImporter()
        
        # Measure import time
        start_time = time.time()
        video_file = media_importer.import_video(self.large_video_path)
        import_time = time.time() - start_time
        
        # Verify import succeeded
        self.assertIsInstance(video_file, VideoFile)
        self.assertEqual(video_file.duration, 1800.0)  # 30 minutes
        
        # Import should complete in reasonable time (under 10 seconds for metadata extraction)
        self.assertLess(import_time, 10.0, f"Large video import took {import_time:.2f}s")
        
        # Check memory usage
        current_memory = self.process.memory_info().rss
        memory_increase = current_memory - self.initial_memory
        
        # Memory increase should be reasonable (under 100MB for metadata only)
        self.assertLess(memory_increase, 100 * 1024 * 1024, 
            f"Memory increase too high: {memory_increase / 1024 / 1024:.1f}MB")
    
    def test_large_subtitle_parsing_performance(self):
        """Test subtitle parsing performance with many lines."""
        from src.core.subtitle_parser import SubtitleParser
        
        parser = SubtitleParser()
        
        # Measure parsing time
        start_time = time.time()
        subtitle_file = parser.parse_ass_file(self.large_subtitle_path)
        parse_time = time.time() - start_time
        
        # Verify parsing succeeded
        self.assertIsInstance(subtitle_file, SubtitleFile)
        self.assertEqual(len(subtitle_file.lines), 5000)
        
        # Parsing should complete in reasonable time (under 5 seconds for 5000 lines)
        self.assertLess(parse_time, 5.0, f"Large subtitle parsing took {parse_time:.2f}s")
        
        # Check memory usage
        current_memory = self.process.memory_info().rss
        memory_increase = current_memory - self.initial_memory
        
        # Memory increase should be reasonable (under 50MB for 5000 lines)
        self.assertLess(memory_increase, 50 * 1024 * 1024, 
            f"Memory increase too high: {memory_increase / 1024 / 1024:.1f}MB")
    
    def test_large_project_creation_performance(self):
        """Test project creation performance with large datasets."""
        # Create large subtitle dataset
        large_lines = []
        for i in range(2000):  # 2000 subtitle lines
            line = SubtitleLine(
                start_time=i * 2.0,
                end_time=i * 2.0 + 1.5,
                text=f"Large project test subtitle line {i+1} with extended text content for performance testing",
                style="Default"
            )
            large_lines.append(line)
        
        # Create large effects list
        large_effects = []
        for i in range(100):  # 100 effects
            effect = Effect(
                id=f"perf_effect_{i}",
                name=f"Performance Effect {i}",
                type="glow" if i % 3 == 0 else "outline" if i % 3 == 1 else "shadow",
                parameters={
                    "intensity": 0.8,
                    "radius": 5.0 + (i % 10),
                    "color": [1.0, 0.5, 0.0]
                }
            )
            large_effects.append(effect)
        
        # Measure project creation time
        start_time = time.time()
        
        project = Project(
            id="large_performance_test",
            name="Large Performance Test Project",
            video_file=VideoFile(
                path=self.large_video_path,
                duration=1800.0,  # 30 minutes
                resolution={"width": 1920, "height": 1080},
                frame_rate=30.0,
                file_size=50 * 1024 * 1024  # 50MB
            ),
            audio_file=AudioFile(
                path=self.large_audio_path,
                duration=1800.0,
                sample_rate=44100,
                channels=2,
                file_size=20 * 1024 * 1024  # 20MB
            ),
            subtitle_file=SubtitleFile(
                path=self.large_subtitle_path,
                lines=large_lines,
                styles=[SubtitleStyle(name="Default")]
            ),
            effects=large_effects
        )
        
        creation_time = time.time() - start_time
        
        # Verify project creation succeeded
        self.assertEqual(len(project.subtitle_file.lines), 2000)
        self.assertEqual(len(project.effects), 100)
        self.assertTrue(project.is_ready_for_export())
        
        # Project creation should be fast (under 1 second)
        self.assertLess(creation_time, 1.0, f"Large project creation took {creation_time:.2f}s")
        
        # Check memory usage
        current_memory = self.process.memory_info().rss
        memory_increase = current_memory - self.initial_memory
        
        # Memory increase should be reasonable (under 200MB for large project)
        self.assertLess(memory_increase, 200 * 1024 * 1024, 
            f"Memory increase too high: {memory_increase / 1024 / 1024:.1f}MB")


class TestComplexEffectsPerformance(unittest.TestCase):
    """Test performance with complex effect combinations."""
    
    def setUp(self):
        """Set up complex effects performance test fixtures."""
        self.effects_manager = EffectsManager()
        
        # Initialize performance monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss
    
    def test_many_effects_performance(self):
        """Test performance with many simultaneous effects."""
        # Add many different effects
        effect_configs = [
            (EffectType.GLOW, {"radius": 8.0, "intensity": 0.9}),
            (EffectType.OUTLINE, {"width": 3.0, "color": [0.0, 0.0, 0.0]}),
            (EffectType.SHADOW, {"offset_x": 5.0, "offset_y": 5.0}),
            (EffectType.BOUNCE, {"amplitude": 10.0, "frequency": 2.0}),
            (EffectType.WAVE, {"amplitude": 8.0, "frequency": 1.5}),
        ]
        
        # Add each effect type multiple times with different parameters
        start_time = time.time()
        
        for i in range(20):  # 20 iterations of each effect type (100 total effects)
            for effect_type, base_params in effect_configs:
                # Vary parameters for each iteration
                params = base_params.copy()
                if "radius" in params:
                    params["radius"] += i * 0.5
                if "width" in params:
                    params["width"] += i * 0.2
                if "amplitude" in params:
                    params["amplitude"] += i * 0.3
                
                effect = self.effects_manager.create_effect(effect_type, params)
                self.effects_manager.add_effect_layer(effect)
        
        setup_time = time.time() - start_time
        
        # Verify all effects were added
        self.assertEqual(len(self.effects_manager.effect_layers), 100)
        
        # Setup should complete in reasonable time (under 2 seconds)
        self.assertLess(setup_time, 2.0, f"Effect setup took {setup_time:.2f}s")
        
        # Test shader generation performance
        start_time = time.time()
        vertex_shader, fragment_shader = self.effects_manager.generate_shader_code()
        shader_time = time.time() - start_time
        
        # Shader generation should be fast (under 1 second)
        self.assertLess(shader_time, 1.0, f"Shader generation took {shader_time:.2f}s")
        
        # Verify shaders were generated
        self.assertIsInstance(vertex_shader, str)
        self.assertIsInstance(fragment_shader, str)
        self.assertGreater(len(vertex_shader), 100)
        self.assertGreater(len(fragment_shader), 100)
        
        # Test uniform generation performance
        start_time = time.time()
        uniforms = self.effects_manager.get_effect_uniforms()
        uniform_time = time.time() - start_time
        
        # Uniform generation should be very fast (under 0.1 seconds)
        self.assertLess(uniform_time, 0.1, f"Uniform generation took {uniform_time:.2f}s")
        
        # Verify uniforms were generated
        self.assertIsInstance(uniforms, dict)
        self.assertGreater(len(uniforms), 50)  # Should have many uniforms
    
    def test_effect_parameter_update_performance(self):
        """Test performance of updating effect parameters."""
        # Add several effects
        effect_ids = []
        for i in range(50):
            effect = self.effects_manager.create_effect(EffectType.GLOW, {
                "radius": 5.0 + i,
                "intensity": 0.5 + (i * 0.01)
            })
            effect_id = self.effects_manager.add_effect_layer(effect)
            effect_ids.append(effect_id)
        
        # Test parameter update performance
        start_time = time.time()
        
        for i, effect_id in enumerate(effect_ids):
            new_params = {
                "radius": 10.0 + i,
                "intensity": 0.8 + (i * 0.005)
            }
            success = self.effects_manager.update_effect_parameters(effect_id, new_params)
            self.assertTrue(success)
        
        update_time = time.time() - start_time
        
        # Parameter updates should be fast (under 0.5 seconds for 50 effects)
        self.assertLess(update_time, 0.5, f"Parameter updates took {update_time:.2f}s")
        
        # Verify parameters were updated
        updated_uniforms = self.effects_manager.get_effect_uniforms()
        self.assertIsInstance(updated_uniforms, dict)
    
    def test_effect_reordering_performance(self):
        """Test performance of effect reordering operations."""
        # Add many effects
        effect_ids = []
        for i in range(30):
            effect_type = [EffectType.GLOW, EffectType.OUTLINE, EffectType.SHADOW][i % 3]
            effect = self.effects_manager.create_effect(effect_type, {})
            effect_id = self.effects_manager.add_effect_layer(effect)
            effect_ids.append(effect_id)
        
        # Test reordering performance
        start_time = time.time()
        
        # Perform many reordering operations
        for i in range(100):
            from_index = i % len(effect_ids)
            to_index = (i + 10) % len(effect_ids)
            
            success = self.effects_manager.reorder_effect_layer(from_index, to_index)
            self.assertTrue(success)
        
        reorder_time = time.time() - start_time
        
        # Reordering should be fast (under 1 second for 100 operations)
        self.assertLess(reorder_time, 1.0, f"Reordering took {reorder_time:.2f}s")
        
        # Verify effects are still present
        self.assertEqual(len(self.effects_manager.effect_layers), 30)
    
    def test_memory_usage_with_complex_effects(self):
        """Test memory usage with complex effect combinations."""
        initial_memory = self.process.memory_info().rss
        
        # Add complex effects with large parameter sets
        for i in range(50):
            # Create effects with many parameters
            complex_params = {
                "radius": 5.0 + i,
                "intensity": 0.8,
                "color": [1.0, 0.5, 0.0],
                "offset_x": i * 0.5,
                "offset_y": i * 0.3,
                "frequency": 2.0 + (i * 0.1),
                "amplitude": 8.0 + (i * 0.2),
                "custom_param_1": i * 1.5,
                "custom_param_2": i * 2.0,
                "custom_param_3": [i, i+1, i+2],
            }
            
            effect = self.effects_manager.create_effect(EffectType.GLOW, complex_params)
            self.effects_manager.add_effect_layer(effect)
        
        # Generate shaders multiple times to test memory accumulation
        for i in range(10):
            vertex_shader, fragment_shader = self.effects_manager.generate_shader_code()
            uniforms = self.effects_manager.get_effect_uniforms()
        
        final_memory = self.process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (under 100MB for complex effects)
        self.assertLess(memory_increase, 100 * 1024 * 1024, 
            f"Memory increase too high: {memory_increase / 1024 / 1024:.1f}MB")


class TestConcurrentOperationsPerformance(unittest.TestCase):
    """Test performance under concurrent operations."""
    
    def setUp(self):
        """Set up concurrent operations test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_files = []
        for i in range(10):
            file_path = os.path.join(self.temp_dir, f"test_file_{i}.mp4")
            with open(file_path, 'wb') as f:
                f.write(b"FAKE_VIDEO_" + str(i).encode() + b"0" * 1024)
            self.test_files.append(file_path)
    
    def tearDown(self):
        """Clean up concurrent operations test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('src.core.media_importer.subprocess.run')
    def test_concurrent_import_performance(self, mock_run):
        """Test performance of concurrent import operations."""
        # Mock FFmpeg responses
        mock_run.return_value = Mock(
            stdout='{"streams":[{"codec_type":"video","duration":"10.0"}],"format":{"duration":"10.0"}}',
            returncode=0
        )
        
        def import_worker(file_path):
            media_importer = MediaImporter()
            start_time = time.time()
            try:
                result = media_importer.import_video(file_path)
                import_time = time.time() - start_time
                return ("success", import_time, result)
            except Exception as e:
                import_time = time.time() - start_time
                return ("error", import_time, str(e))
        
        # Test concurrent imports
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(import_worker, file_path) 
                      for file_path in self.test_files]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        total_time = time.time() - start_time
        
        # Verify all imports completed
        self.assertEqual(len(results), len(self.test_files))
        
        # Check success rate
        successful_imports = [r for r in results if r[0] == "success"]
        success_rate = len(successful_imports) / len(results)
        
        # At least 80% should succeed (some may fail due to file locking)
        self.assertGreaterEqual(success_rate, 0.8, 
            f"Success rate too low: {success_rate:.1%}")
        
        # Concurrent imports should be faster than sequential
        # (Total time should be less than sum of individual times)
        individual_times = [r[1] for r in successful_imports]
        sequential_time_estimate = sum(individual_times)
        
        # Concurrent execution should provide some speedup
        self.assertLess(total_time, sequential_time_estimate * 0.8, 
            f"Concurrent execution not efficient: {total_time:.2f}s vs estimated {sequential_time_estimate:.2f}s")
    
    def test_concurrent_effect_operations(self):
        """Test performance of concurrent effect operations."""
        effects_managers = [EffectsManager() for _ in range(5)]
        
        def effect_worker(manager_index):
            manager = effects_managers[manager_index]
            operations = []
            
            start_time = time.time()
            
            # Add effects
            for i in range(20):
                effect = manager.create_effect(EffectType.GLOW, {"radius": 5.0 + i})
                manager.add_effect_layer(effect)
            
            # Generate shaders
            for i in range(10):
                vertex_shader, fragment_shader = manager.generate_shader_code()
                uniforms = manager.get_effect_uniforms()
            
            operation_time = time.time() - start_time
            return ("success", operation_time, len(manager.effect_layers))
        
        # Test concurrent effect operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(effect_worker, i) for i in range(5)]
            
            results = []
            for future in as_completed(futures):
                results.append(future.result())
        
        total_time = time.time() - start_time
        
        # Verify all operations completed successfully
        self.assertEqual(len(results), 5)
        successful_operations = [r for r in results if r[0] == "success"]
        self.assertEqual(len(successful_operations), 5)
        
        # Verify each manager has correct number of effects
        for result in successful_operations:
            self.assertEqual(result[2], 20)  # 20 effects per manager
        
        # Operations should complete in reasonable time (under 5 seconds)
        self.assertLess(total_time, 5.0, f"Concurrent operations took {total_time:.2f}s")
    
    def test_memory_pressure_performance(self):
        """Test performance under memory pressure conditions."""
        import gc
        
        initial_memory = psutil.Process().memory_info().rss
        
        # Create memory pressure by allocating large objects
        large_objects = []
        
        try:
            # Allocate memory in chunks
            for i in range(10):
                # Create 10MB objects
                large_obj = bytearray(10 * 1024 * 1024)
                large_objects.append(large_obj)
                
                # Test operations under memory pressure
                effects_manager = EffectsManager()
                
                # Add effects
                start_time = time.time()
                for j in range(10):
                    effect = effects_manager.create_effect(EffectType.GLOW, {"radius": j})
                    effects_manager.add_effect_layer(effect)
                
                # Generate shaders
                vertex_shader, fragment_shader = effects_manager.generate_shader_code()
                operation_time = time.time() - start_time
                
                # Operations should still complete in reasonable time
                self.assertLess(operation_time, 2.0, 
                    f"Operation under memory pressure took {operation_time:.2f}s")
                
                # Verify operations succeeded
                self.assertEqual(len(effects_manager.effect_layers), 10)
                self.assertIsInstance(vertex_shader, str)
                self.assertIsInstance(fragment_shader, str)
        
        finally:
            # Clean up large objects
            large_objects.clear()
            gc.collect()
        
        # Memory should be mostly reclaimed
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Allow some memory overhead but should be reasonable
        self.assertLess(memory_increase, 50 * 1024 * 1024, 
            f"Memory not properly reclaimed: {memory_increase / 1024 / 1024:.1f}MB")


if __name__ == '__main__':
    # Run tests silently as per steering guidelines
    unittest.main(verbosity=0, buffer=True)