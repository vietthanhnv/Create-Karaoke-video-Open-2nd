#!/usr/bin/env python3
"""
Setup script for Karaoke Video Creator
"""

import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True


def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    try:
        # Install from requirements.txt
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


def check_ffmpeg():
    """Check if FFmpeg is available"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      capture_output=True, check=True)
        print("FFmpeg found and available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: FFmpeg not found in PATH")
        print("Please install FFmpeg for video processing functionality")
        print("Download from: https://ffmpeg.org/download.html")
        return False


def create_directories():
    """Create necessary directories"""
    directories = [
        "input/videos",
        "input/audio", 
        "input/images",
        "input/subtitles",
        "output",
        "temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")


def main():
    """Main setup function"""
    print("Karaoke Video Creator Setup")
    print("=" * 30)
    
    # Check Python version
    if not check_python_version():
        return 1
        
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        return 1
        
    # Check FFmpeg
    check_ffmpeg()
    
    print("\nSetup completed!")
    print("Run the application with: python src/main.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())