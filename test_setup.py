#!/usr/bin/env python3
"""
Test script to verify the basic application setup
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test PyQt6 imports
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtOpenGLWidgets import QOpenGLWidget
        print("✓ PyQt6 imports successful")
        
        # Test application modules
        from ui.main_window import MainWindow
        from ui.import_widget import ImportWidget
        from ui.preview_widget import PreviewWidget
        from ui.editor_widget import EditorWidget
        from ui.effects_widget import EffectsWidget
        from ui.export_widget import ExportWidget
        print("✓ Application module imports successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_directory_structure():
    """Test that required directories exist"""
    required_dirs = [
        "src",
        "src/ui", 
        "src/core",
        "src/video",
        "src/audio",
        "input/videos",
        "input/audio",
        "input/images", 
        "input/subtitles",
        "output",
        "temp"
    ]
    
    print("Testing directory structure...")
    all_exist = True
    
    for directory in required_dirs:
        if Path(directory).exists():
            print(f"✓ {directory}")
        else:
            print(f"✗ {directory} - missing")
            all_exist = False
            
    return all_exist


def test_application_creation():
    """Test that the application can be created"""
    try:
        print("Testing application creation...")
        
        # Import QApplication
        from PyQt6.QtWidgets import QApplication
        
        # Create QApplication (required for Qt widgets)
        app = QApplication([])
        
        # Import and create main window
        from ui.main_window import MainWindow
        window = MainWindow()
        
        print("✓ Application and main window created successfully")
        
        # Clean up
        app.quit()
        return True
        
    except Exception as e:
        print(f"✗ Application creation failed: {e}")
        return False


def main():
    """Run all tests"""
    print("Karaoke Video Creator - Setup Verification")
    print("=" * 45)
    
    tests = [
        ("Directory Structure", test_directory_structure),
        ("Module Imports", test_imports),
        ("Application Creation", test_application_creation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append(result)
        
    print("\n" + "=" * 45)
    print("Test Results:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"{test_name}: {status}")
        
    if all(results):
        print("\n✓ All tests passed! Setup is complete.")
        return 0
    else:
        print("\n✗ Some tests failed. Please check the setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main())