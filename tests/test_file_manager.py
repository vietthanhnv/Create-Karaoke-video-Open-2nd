"""
Unit tests for the FileManager class.

Tests file management functionality including directory creation,
temporary file management, storage validation, and cleanup operations.
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtCore import QObject
from PyQt6.QtTest import QSignalSpy

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.file_manager import (
    FileManager, StorageInfo, StorageLevel, DirectoryStructure,
    TempFileTracker, FileManagerError
)


class TestTempFileTracker(unittest.TestCase):
    """Test cases for TempFileTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = TempFileTracker()
    
    def test_register_temp_file(self):
        """Test registering temporary files."""
        file_path = "/tmp/test_file.txt"
        self.tracker.register_temp_file(file_path)
        
        temp_files = self.tracker.get_temp_files()
        self.assertIn(file_path, temp_files)
    
    def test_unregister_temp_file(self):
        """Test unregistering temporary files."""
        file_path = "/tmp/test_file.txt"
        self.tracker.register_temp_file(file_path)
        self.tracker.unregister_temp_file(file_path)
        
        temp_files = self.tracker.get_temp_files()
        self.assertNotIn(file_path, temp_files)
    
    def test_cleanup_old_files(self):
        """Test cleanup of old temporary files."""
        # Create a real temporary file for testing
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test content")
        
        try:
            # Register the file
            self.tracker.register_temp_file(temp_path)
            
            # Cleanup with very short age (should clean up immediately)
            cleaned_files = self.tracker.cleanup_old_files(max_age_hours=0.0)
            
            # File should be cleaned up
            self.assertIn(temp_path, cleaned_files)
            self.assertFalse(os.path.exists(temp_path))
            
            # File should be unregistered
            temp_files = self.tracker.get_temp_files()
            self.assertNotIn(temp_path, temp_files)
            
        finally:
            # Cleanup in case test failed
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestStorageInfo(unittest.TestCase):
    """Test cases for StorageInfo class."""
    
    def test_storage_info_properties(self):
        """Test StorageInfo property calculations."""
        storage_info = StorageInfo(
            total_bytes=1024 * 1024 * 1024,  # 1GB
            free_bytes=512 * 1024 * 1024,    # 512MB
            used_bytes=512 * 1024 * 1024,    # 512MB
            free_percentage=50.0,
            level=StorageLevel.WARNING
        )
        
        self.assertEqual(storage_info.free_mb, 512.0)
        self.assertEqual(storage_info.free_gb, 0.5)
        self.assertEqual(storage_info.level, StorageLevel.WARNING)


class TestDirectoryStructure(unittest.TestCase):
    """Test cases for DirectoryStructure class."""
    
    def test_directory_structure_creation(self):
        """Test directory structure initialization."""
        root = Path("/test/root")
        structure = DirectoryStructure(
            root=root,
            input_dir=root / "input",
            output_dir=root / "output", 
            temp_dir=root / "temp",
            input_videos=root / "input" / "videos",
            input_audio=root / "input" / "audio",
            input_images=root / "input" / "images",
            input_subtitles=root / "input" / "subtitles"
        )
        
        self.assertEqual(structure.root, root)
        self.assertEqual(structure.input_dir, root / "input")
        self.assertEqual(structure.output_dir, root / "output")
        self.assertEqual(structure.temp_dir, root / "temp")
    
    def test_string_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        structure = DirectoryStructure(
            root="/test/root",
            input_dir="/test/root/input",
            output_dir="/test/root/output",
            temp_dir="/test/root/temp",
            input_videos="/test/root/input/videos",
            input_audio="/test/root/input/audio",
            input_images="/test/root/input/images",
            input_subtitles="/test/root/input/subtitles"
        )
        
        self.assertIsInstance(structure.root, Path)
        self.assertIsInstance(structure.input_dir, Path)


class TestFileManager(unittest.TestCase):
    """Test cases for FileManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.file_manager = FileManager(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up the test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_directory_structure_creation(self):
        """Test automatic directory structure creation."""
        # Directories should be created automatically
        self.assertTrue(self.file_manager.directory_structure.input_dir.exists())
        self.assertTrue(self.file_manager.directory_structure.output_dir.exists())
        self.assertTrue(self.file_manager.directory_structure.temp_dir.exists())
        self.assertTrue(self.file_manager.directory_structure.input_videos.exists())
        self.assertTrue(self.file_manager.directory_structure.input_audio.exists())
        self.assertTrue(self.file_manager.directory_structure.input_images.exists())
        self.assertTrue(self.file_manager.directory_structure.input_subtitles.exists())
    
    def test_ensure_directory_structure(self):
        """Test manual directory structure creation."""
        # Remove a directory and recreate it
        test_dir = self.file_manager.directory_structure.input_videos
        shutil.rmtree(test_dir)
        self.assertFalse(test_dir.exists())
        
        created_dirs = self.file_manager.ensure_directory_structure()
        self.assertTrue(test_dir.exists())
        self.assertIn(str(test_dir), created_dirs)
    
    @patch('shutil.disk_usage')
    def test_get_storage_info(self, mock_disk_usage):
        """Test storage information retrieval."""
        # Mock disk usage
        mock_disk_usage.return_value = (
            1024 * 1024 * 1024,  # total: 1GB
            512 * 1024 * 1024,   # free: 512MB
            512 * 1024 * 1024    # used: 512MB
        )
        
        storage_info = self.file_manager.get_storage_info()
        
        self.assertEqual(storage_info.total_bytes, 1024 * 1024 * 1024)
        self.assertEqual(storage_info.free_bytes, 512 * 1024 * 1024)
        self.assertEqual(storage_info.level, StorageLevel.WARNING)
    
    @patch('shutil.disk_usage')
    def test_validate_storage_before_processing(self, mock_disk_usage):
        """Test storage validation before processing."""
        # Test with sufficient storage
        mock_disk_usage.return_value = (
            10 * 1024 * 1024 * 1024,  # total: 10GB
            5 * 1024 * 1024 * 1024,   # free: 5GB
            5 * 1024 * 1024 * 1024    # used: 5GB
        )
        
        is_sufficient, message = self.file_manager.validate_storage_before_processing(100)
        self.assertTrue(is_sufficient)
        self.assertEqual(message, "")
        
        # Test with insufficient storage
        mock_disk_usage.return_value = (
            1024 * 1024 * 1024,  # total: 1GB
            50 * 1024 * 1024,    # free: 50MB
            974 * 1024 * 1024    # used: 974MB
        )
        
        is_sufficient, message = self.file_manager.validate_storage_before_processing(100)
        self.assertFalse(is_sufficient)
        self.assertIn("Insufficient storage", message)
    
    def test_create_temp_file(self):
        """Test temporary file creation."""
        # Test text content
        temp_path = self.file_manager.create_temp_file(
            suffix=".txt",
            prefix="test_",
            content="Hello, World!"
        )
        
        self.assertTrue(os.path.exists(temp_path))
        self.assertIn(temp_path, self.file_manager.temp_tracker.get_temp_files())
        
        # Verify content
        with open(temp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "Hello, World!")
        
        # Test binary content
        binary_temp_path = self.file_manager.create_temp_file(
            suffix=".bin",
            binary_content=b"Binary data"
        )
        
        self.assertTrue(os.path.exists(binary_temp_path))
        
        with open(binary_temp_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, b"Binary data")
    
    def test_create_temp_directory(self):
        """Test temporary directory creation."""
        temp_dir_path = self.file_manager.create_temp_directory(prefix="test_dir_")
        
        self.assertTrue(os.path.exists(temp_dir_path))
        self.assertTrue(os.path.isdir(temp_dir_path))
        self.assertIn(temp_dir_path, self.file_manager.temp_tracker.get_temp_files())
    
    def test_cleanup_temp_file(self):
        """Test temporary file cleanup."""
        # Create a temp file
        temp_path = self.file_manager.create_temp_file(content="test")
        self.assertTrue(os.path.exists(temp_path))
        
        # Clean it up
        success = self.file_manager.cleanup_temp_file(temp_path)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(temp_path))
        self.assertNotIn(temp_path, self.file_manager.temp_tracker.get_temp_files())
    
    def test_cleanup_all_temp_files(self):
        """Test cleanup of all temporary files."""
        # Create multiple temp files
        temp_paths = []
        for i in range(3):
            temp_path = self.file_manager.create_temp_file(content=f"test {i}")
            temp_paths.append(temp_path)
        
        # Verify they exist
        for temp_path in temp_paths:
            self.assertTrue(os.path.exists(temp_path))
        
        # Clean them all up
        count, cleaned_files = self.file_manager.cleanup_all_temp_files()
        
        self.assertEqual(count, 3)
        self.assertEqual(len(cleaned_files), 3)
        
        # Verify they're gone
        for temp_path in temp_paths:
            self.assertFalse(os.path.exists(temp_path))
    
    def test_validate_file_integrity(self):
        """Test file integrity validation."""
        # Create a valid test file
        test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Test valid file
        is_valid, message = self.file_manager.validate_file_integrity(test_file)
        self.assertTrue(is_valid)
        self.assertEqual(message, "")
        
        # Test non-existent file
        is_valid, message = self.file_manager.validate_file_integrity("nonexistent.txt")
        self.assertFalse(is_valid)
        self.assertIn("does not exist", message)
        
        # Test empty file
        empty_file = os.path.join(self.test_dir, "empty_file.txt")
        with open(empty_file, 'w') as f:
            pass  # Create empty file
        
        is_valid, message = self.file_manager.validate_file_integrity(empty_file)
        self.assertFalse(is_valid)
        self.assertIn("empty", message)
    
    def test_get_directory_size(self):
        """Test directory size calculation."""
        # Create some test files
        test_files = []
        for i in range(3):
            file_path = os.path.join(self.test_dir, f"test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write("x" * 100)  # 100 bytes each
            test_files.append(file_path)
        
        size = self.file_manager.get_directory_size(self.test_dir)
        self.assertGreaterEqual(size, 300)  # At least 300 bytes
    
    def test_get_temp_directory_info(self):
        """Test temporary directory information."""
        # Create some temp files
        temp_path1 = self.file_manager.create_temp_file(content="test1")
        temp_path2 = self.file_manager.create_temp_file(content="test2")
        
        info = self.file_manager.get_temp_directory_info()
        
        self.assertEqual(info['tracked_files_count'], 2)
        self.assertIn(temp_path1, info['tracked_files'])
        self.assertIn(temp_path2, info['tracked_files'])
        self.assertGreater(info['directory_size_bytes'], 0)
    
    def test_emergency_cleanup(self):
        """Test emergency cleanup functionality."""
        # Create tracked temp files
        temp_path1 = self.file_manager.create_temp_file(content="tracked1")
        temp_path2 = self.file_manager.create_temp_file(content="tracked2")
        
        # Create orphaned file directly in temp directory
        orphaned_file = os.path.join(self.file_manager.directory_structure.temp_dir, "orphaned.txt")
        with open(orphaned_file, 'w') as f:
            f.write("orphaned content")
        
        # Perform emergency cleanup
        results = self.file_manager.emergency_cleanup()
        
        # Check results
        self.assertEqual(results['tracked_files_cleaned'], 2)
        self.assertEqual(results['orphaned_files_cleaned'], 1)
        self.assertIn(orphaned_file, results['orphaned_files_list'])
        
        # Verify files are gone
        self.assertFalse(os.path.exists(temp_path1))
        self.assertFalse(os.path.exists(temp_path2))
        self.assertFalse(os.path.exists(orphaned_file))
    
    def test_signals_emitted(self):
        """Test that appropriate signals are emitted."""
        # Test directory creation signal
        spy = QSignalSpy(self.file_manager.directory_created)
        
        # Remove and recreate a directory to trigger signal
        test_dir = self.file_manager.directory_structure.input_videos
        shutil.rmtree(test_dir)
        self.file_manager.ensure_directory_structure()
        
        self.assertGreater(len(spy), 0)
        
        # Test temp file creation signal
        spy = QSignalSpy(self.file_manager.temp_file_created)
        temp_path = self.file_manager.create_temp_file(content="test")
        
        self.assertEqual(len(spy), 1)
        self.assertEqual(spy[0][0], temp_path)
        
        # Test temp file removal signal
        spy = QSignalSpy(self.file_manager.temp_file_removed)
        self.file_manager.cleanup_temp_file(temp_path)
        
        self.assertEqual(len(spy), 1)
        self.assertEqual(spy[0][0], temp_path)


if __name__ == '__main__':
    unittest.main()