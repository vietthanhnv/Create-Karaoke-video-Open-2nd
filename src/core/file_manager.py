"""
File Management and Cleanup System for the Karaoke Video Creator application.

This module provides comprehensive file management capabilities including:
- Automatic directory structure creation
- Temporary file management with automatic cleanup
- Storage space validation before processing
- File integrity validation and accessibility checks
"""

import os
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import psutil
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class StorageLevel(Enum):
    """Storage space warning levels."""
    CRITICAL = "critical"  # < 100MB
    LOW = "low"           # < 500MB
    WARNING = "warning"   # < 1GB
    ADEQUATE = "adequate" # >= 1GB


@dataclass
class StorageInfo:
    """Information about storage space."""
    total_bytes: int
    free_bytes: int
    used_bytes: int
    free_percentage: float
    level: StorageLevel
    
    @property
    def free_mb(self) -> float:
        """Free space in megabytes."""
        return self.free_bytes / (1024 * 1024)
    
    @property
    def free_gb(self) -> float:
        """Free space in gigabytes."""
        return self.free_bytes / (1024 * 1024 * 1024)


@dataclass
class DirectoryStructure:
    """Represents the application's directory structure."""
    root: Path
    input_dir: Path
    output_dir: Path
    temp_dir: Path
    input_videos: Path
    input_audio: Path
    input_images: Path
    input_subtitles: Path
    
    def __post_init__(self):
        """Ensure all paths are Path objects."""
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, Path(value))


class FileManagerError(Exception):
    """Custom exception for file manager errors."""
    pass


class TempFileTracker:
    """Tracks temporary files for automatic cleanup."""
    
    def __init__(self):
        self._temp_files: Dict[str, float] = {}  # file_path -> creation_time
        self._lock = threading.Lock()
    
    def register_temp_file(self, file_path: str) -> None:
        """Register a temporary file for tracking."""
        with self._lock:
            self._temp_files[file_path] = time.time()
    
    def unregister_temp_file(self, file_path: str) -> None:
        """Unregister a temporary file."""
        with self._lock:
            self._temp_files.pop(file_path, None)
    
    def get_temp_files(self) -> List[str]:
        """Get list of tracked temporary files."""
        with self._lock:
            return list(self._temp_files.keys())
    
    def cleanup_old_files(self, max_age_hours: float = 24.0) -> List[str]:
        """Clean up temporary files older than specified age."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_files = []
        
        with self._lock:
            files_to_remove = []
            for file_path, creation_time in self._temp_files.items():
                if current_time - creation_time > max_age_seconds:
                    try:
                        if os.path.exists(file_path):
                            os.unlink(file_path)
                        files_to_remove.append(file_path)
                        cleaned_files.append(file_path)
                    except OSError:
                        # File might be in use or permission denied
                        pass
            
            for file_path in files_to_remove:
                self._temp_files.pop(file_path, None)
        
        return cleaned_files


class FileManager(QObject):
    """
    Comprehensive file management system for the Karaoke Video Creator.
    
    Handles directory structure creation, temporary file management,
    storage validation, and automatic cleanup operations.
    """
    
    # Signals for file management events
    directory_created = pyqtSignal(str)  # directory_path
    storage_warning = pyqtSignal(str, str)  # level, message
    cleanup_completed = pyqtSignal(int, list)  # files_cleaned, file_list
    temp_file_created = pyqtSignal(str)  # file_path
    temp_file_removed = pyqtSignal(str)  # file_path
    
    # Storage thresholds in bytes
    CRITICAL_THRESHOLD = 100 * 1024 * 1024   # 100MB
    LOW_THRESHOLD = 500 * 1024 * 1024        # 500MB
    WARNING_THRESHOLD = 1024 * 1024 * 1024   # 1GB
    
    def __init__(self, root_directory: Optional[str] = None):
        """
        Initialize the FileManager.
        
        Args:
            root_directory: Root directory for the application. If None, uses current directory.
        """
        super().__init__()
        
        # Set up directory structure
        self.root_dir = Path(root_directory) if root_directory else Path.cwd()
        self.directory_structure = self._create_directory_structure()
        
        # Initialize temporary file tracking
        self.temp_tracker = TempFileTracker()
        
        # Set up automatic cleanup timer
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._periodic_cleanup)
        self.cleanup_timer.start(300000)  # 5 minutes
        
        # Create directories on initialization
        self.ensure_directory_structure()
    
    def _create_directory_structure(self) -> DirectoryStructure:
        """Create the directory structure definition."""
        root = self.root_dir
        input_dir = root / "input"
        output_dir = root / "output"
        temp_dir = root / "temp"
        
        return DirectoryStructure(
            root=root,
            input_dir=input_dir,
            output_dir=output_dir,
            temp_dir=temp_dir,
            input_videos=input_dir / "videos",
            input_audio=input_dir / "audio",
            input_images=input_dir / "images",
            input_subtitles=input_dir / "subtitles"
        )
    
    def ensure_directory_structure(self) -> List[str]:
        """
        Create the necessary directory structure if it doesn't exist.
        
        Returns:
            List of directories that were created
            
        Raises:
            FileManagerError: If directory creation fails
        """
        created_dirs = []
        
        directories_to_create = [
            self.directory_structure.input_dir,
            self.directory_structure.output_dir,
            self.directory_structure.temp_dir,
            self.directory_structure.input_videos,
            self.directory_structure.input_audio,
            self.directory_structure.input_images,
            self.directory_structure.input_subtitles
        ]
        
        for directory in directories_to_create:
            try:
                if not directory.exists():
                    directory.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(directory))
                    self.directory_created.emit(str(directory))
            except OSError as e:
                raise FileManagerError(f"Failed to create directory {directory}: {e}")
        
        return created_dirs
    
    def get_storage_info(self, path: Optional[str] = None) -> StorageInfo:
        """
        Get storage information for the specified path or root directory.
        
        Args:
            path: Path to check storage for. If None, uses root directory.
            
        Returns:
            StorageInfo object with storage details
        """
        check_path = Path(path) if path else self.directory_structure.root
        
        try:
            # Get disk usage statistics
            usage = shutil.disk_usage(check_path)
            total_bytes = usage.total
            free_bytes = usage.free
            used_bytes = total_bytes - free_bytes
            free_percentage = (free_bytes / total_bytes) * 100
            
            # Determine storage level
            if free_bytes < self.CRITICAL_THRESHOLD:
                level = StorageLevel.CRITICAL
            elif free_bytes < self.LOW_THRESHOLD:
                level = StorageLevel.LOW
            elif free_bytes < self.WARNING_THRESHOLD:
                level = StorageLevel.WARNING
            else:
                level = StorageLevel.ADEQUATE
            
            return StorageInfo(
                total_bytes=total_bytes,
                free_bytes=free_bytes,
                used_bytes=used_bytes,
                free_percentage=free_percentage,
                level=level
            )
            
        except OSError as e:
            raise FileManagerError(f"Failed to get storage info for {check_path}: {e}")
    
    def validate_storage_before_processing(self, estimated_size_mb: float = 0) -> Tuple[bool, str]:
        """
        Validate that there's sufficient storage space before processing.
        
        Args:
            estimated_size_mb: Estimated size needed in megabytes
            
        Returns:
            Tuple of (is_sufficient, warning_message)
        """
        storage_info = self.get_storage_info()
        estimated_bytes = estimated_size_mb * 1024 * 1024
        
        # Check if we have enough space for the estimated size plus buffer
        buffer_bytes = 200 * 1024 * 1024  # 200MB buffer
        required_bytes = estimated_bytes + buffer_bytes
        
        if storage_info.free_bytes < required_bytes:
            message = (
                f"Insufficient storage space. "
                f"Required: {required_bytes / (1024*1024):.1f}MB, "
                f"Available: {storage_info.free_mb:.1f}MB"
            )
            self.storage_warning.emit("critical", message)
            return False, message
        
        # Check storage level and emit warnings
        if storage_info.level == StorageLevel.CRITICAL:
            message = f"Critical storage warning: Only {storage_info.free_mb:.1f}MB remaining"
            self.storage_warning.emit("critical", message)
            return False, message
        elif storage_info.level == StorageLevel.LOW:
            message = f"Low storage warning: Only {storage_info.free_mb:.1f}MB remaining"
            self.storage_warning.emit("low", message)
        elif storage_info.level == StorageLevel.WARNING:
            message = f"Storage warning: Only {storage_info.free_gb:.1f}GB remaining"
            self.storage_warning.emit("warning", message)
        
        return True, ""
    
    def create_temp_file(self, suffix: str = "", prefix: str = "karaoke_", 
                        content: Optional[str] = None, binary_content: Optional[bytes] = None) -> str:
        """
        Create a temporary file with automatic cleanup tracking.
        
        Args:
            suffix: File suffix (e.g., '.mp4', '.ass')
            prefix: File prefix
            content: Text content to write to file
            binary_content: Binary content to write to file
            
        Returns:
            Path to the created temporary file
            
        Raises:
            FileManagerError: If file creation fails
        """
        try:
            # Create temporary file in our temp directory
            temp_dir = self.directory_structure.temp_dir
            
            with tempfile.NamedTemporaryFile(
                mode='w+b',
                suffix=suffix,
                prefix=prefix,
                dir=temp_dir,
                delete=False
            ) as temp_file:
                temp_path = temp_file.name
                
                # Write content if provided
                if content is not None:
                    temp_file.write(content.encode('utf-8'))
                elif binary_content is not None:
                    temp_file.write(binary_content)
            
            # Register for tracking
            self.temp_tracker.register_temp_file(temp_path)
            self.temp_file_created.emit(temp_path)
            
            return temp_path
            
        except OSError as e:
            raise FileManagerError(f"Failed to create temporary file: {e}")
    
    def create_temp_directory(self, prefix: str = "karaoke_") -> str:
        """
        Create a temporary directory with automatic cleanup tracking.
        
        Args:
            prefix: Directory prefix
            
        Returns:
            Path to the created temporary directory
            
        Raises:
            FileManagerError: If directory creation fails
        """
        try:
            temp_dir = self.directory_structure.temp_dir
            temp_path = tempfile.mkdtemp(prefix=prefix, dir=temp_dir)
            
            # Register for tracking
            self.temp_tracker.register_temp_file(temp_path)
            self.temp_file_created.emit(temp_path)
            
            return temp_path
            
        except OSError as e:
            raise FileManagerError(f"Failed to create temporary directory: {e}")
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Clean up a specific temporary file.
        
        Args:
            file_path: Path to the temporary file to clean up
            
        Returns:
            True if cleanup was successful
        """
        try:
            path = Path(file_path)
            
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            
            self.temp_tracker.unregister_temp_file(file_path)
            self.temp_file_removed.emit(file_path)
            return True
            
        except OSError:
            return False
    
    def cleanup_all_temp_files(self) -> Tuple[int, List[str]]:
        """
        Clean up all tracked temporary files.
        
        Returns:
            Tuple of (files_cleaned_count, list_of_cleaned_files)
        """
        temp_files = self.temp_tracker.get_temp_files()
        cleaned_files = []
        
        for file_path in temp_files:
            if self.cleanup_temp_file(file_path):
                cleaned_files.append(file_path)
        
        self.cleanup_completed.emit(len(cleaned_files), cleaned_files)
        return len(cleaned_files), cleaned_files
    
    def cleanup_old_temp_files(self, max_age_hours: float = 24.0) -> Tuple[int, List[str]]:
        """
        Clean up temporary files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Tuple of (files_cleaned_count, list_of_cleaned_files)
        """
        cleaned_files = self.temp_tracker.cleanup_old_files(max_age_hours)
        
        for file_path in cleaned_files:
            self.temp_file_removed.emit(file_path)
        
        self.cleanup_completed.emit(len(cleaned_files), cleaned_files)
        return len(cleaned_files), cleaned_files
    
    def validate_file_integrity(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate file integrity and accessibility.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return False, f"File does not exist: {file_path}"
            
            # Check if it's actually a file (not a directory)
            if not path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            # Check read permissions
            if not os.access(path, os.R_OK):
                return False, f"File is not readable: {file_path}"
            
            # Check file size (empty files might be corrupted)
            if path.stat().st_size == 0:
                return False, f"File is empty: {file_path}"
            
            # Try to open the file to verify it's not corrupted
            try:
                with open(path, 'rb') as f:
                    f.read(1)  # Read first byte
            except OSError as e:
                return False, f"File appears to be corrupted: {e}"
            
            return True, ""
            
        except OSError as e:
            return False, f"Error validating file: {e}"
    
    def get_directory_size(self, directory_path: str) -> int:
        """
        Calculate the total size of a directory and its contents.
        
        Args:
            directory_path: Path to the directory
            
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        # Skip files that can't be accessed
                        pass
        except OSError:
            # Directory doesn't exist or can't be accessed
            pass
        
        return total_size
    
    def _periodic_cleanup(self) -> None:
        """Periodic cleanup of old temporary files."""
        try:
            self.cleanup_old_temp_files(max_age_hours=24.0)
        except Exception:
            # Don't let cleanup errors crash the application
            pass
    
    def get_temp_directory_info(self) -> Dict[str, Union[int, float, str]]:
        """
        Get information about the temporary directory.
        
        Returns:
            Dictionary with temp directory statistics
        """
        temp_dir = self.directory_structure.temp_dir
        temp_files = self.temp_tracker.get_temp_files()
        
        return {
            'path': str(temp_dir),
            'tracked_files_count': len(temp_files),
            'directory_size_bytes': self.get_directory_size(str(temp_dir)),
            'directory_size_mb': self.get_directory_size(str(temp_dir)) / (1024 * 1024),
            'tracked_files': temp_files
        }
    
    def emergency_cleanup(self) -> Dict[str, Union[int, List[str]]]:
        """
        Perform emergency cleanup of all temporary files and directories.
        
        Returns:
            Dictionary with cleanup results
        """
        results = {
            'tracked_files_cleaned': 0,
            'tracked_files_list': [],
            'orphaned_files_cleaned': 0,
            'orphaned_files_list': [],
            'errors': []
        }
        
        # Clean up tracked files
        tracked_count, tracked_files = self.cleanup_all_temp_files()
        results['tracked_files_cleaned'] = tracked_count
        results['tracked_files_list'] = tracked_files
        
        # Clean up orphaned files in temp directory
        temp_dir = self.directory_structure.temp_dir
        orphaned_files = []
        
        try:
            if temp_dir.exists():
                for item in temp_dir.iterdir():
                    if str(item) not in tracked_files:
                        try:
                            if item.is_file():
                                item.unlink()
                                orphaned_files.append(str(item))
                            elif item.is_dir():
                                shutil.rmtree(item)
                                orphaned_files.append(str(item))
                        except OSError as e:
                            results['errors'].append(f"Failed to remove {item}: {e}")
        except OSError as e:
            results['errors'].append(f"Failed to access temp directory: {e}")
        
        results['orphaned_files_cleaned'] = len(orphaned_files)
        results['orphaned_files_list'] = orphaned_files
        
        return results