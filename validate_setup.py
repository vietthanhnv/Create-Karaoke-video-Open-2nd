#!/usr/bin/env python3
"""
Validation script to check the complete setup
"""

import sys
import subprocess
import os
from pathlib import Path


def check_ffmpeg():
    """Check FFmpeg installation"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            # Extract version info
            version_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg found: {version_line}")
            return True
        else:
            print("✗ FFmpeg command failed")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found in PATH")
        print("  Please install FFmpeg from: https://ffmpeg.org/download.html")
        return False
    except subprocess.TimeoutExpired:
        print("✗ FFmpeg command timed out")
        return False


def check_python_packages():
    """Check required Python packages"""
    required_packages = [
        "PyQt6",
        "PyOpenGL", 
        "opencv-python",
        "Pillow",
        "numpy"
    ]
    
    print("Checking Python packages...")
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_").lower())
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - not installed")
            all_installed = False
            
    return all_installed


def show_project_structure():
    """Display the current project structure"""
    print("\nProject Structure:")
    print("=" * 30)
    
    def print_tree(path, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
            
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir() and not item.name.startswith('.') and current_depth < max_depth - 1:
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_tree(item, next_prefix, max_depth, current_depth + 1)
    
    print_tree(Path("."))


def main():
    """Main validation function"""
    print("Karaoke Video Creator - Setup Validation")
    print("=" * 45)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check packages
    packages_ok = check_python_packages()
    
    # Check FFmpeg
    ffmpeg_ok = check_ffmpeg()
    
    # Show project structure
    show_project_structure()
    
    print("\n" + "=" * 45)
    print("Validation Summary:")
    print(f"Python packages: {'✓ OK' if packages_ok else '✗ Missing packages'}")
    print(f"FFmpeg: {'✓ OK' if ffmpeg_ok else '✗ Not available'}")
    
    if packages_ok and ffmpeg_ok:
        print("\n✓ Setup is complete and ready for development!")
        print("Run the application with: python src/main.py")
    else:
        print("\n⚠ Setup needs attention:")
        if not packages_ok:
            print("  - Install missing Python packages: pip install -r requirements.txt")
        if not ffmpeg_ok:
            print("  - Install FFmpeg for video processing")


if __name__ == "__main__":
    main()