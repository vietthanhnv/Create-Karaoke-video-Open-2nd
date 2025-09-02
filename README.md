# Karaoke Video Creator

A professional PyQt6-based application for creating karaoke videos with synchronized subtitles, word-by-word animation, and real-time text effects.

## 🎤 Features

### Core Functionality

- **Multi-format Media Import**: Support for video (MP4, AVI, MOV), audio (MP3, WAV, AAC), and subtitle (ASS) files
- **Real-time Preview**: Hardware-accelerated OpenGL preview with synchronized audio-video-subtitle playback
- **Professional Export**: High-quality video export with customizable settings

### Advanced Subtitle System

- **Word-by-word Karaoke Animation**: Precise timing with color-coded word highlighting
- **ASS Format Support**: Full compatibility with Advanced SubStation Alpha format including karaoke timing tags
- **Real-time Editing**: Live preview updates as you edit subtitle text and timing
- **Timeline Editor**: Visual timeline with drag-and-drop timing adjustment

### Text Effects & Styling

- **Real-time Effect Preview**: See effects applied instantly as you adjust parameters
- **Multiple Effect Types**: Glow, outline, shadow, fade, bounce, color transitions, and wave animations
- **Effect Layering**: Combine multiple effects with customizable render order
- **Preset System**: One-click professional effect combinations

### User Experience

- **Tabbed Workflow**: Intuitive step-by-step interface (Import → Preview → Edit → Effects → Export)
- **Cross-widget Integration**: Real-time synchronization between editor, effects, and preview
- **Performance Optimized**: Debounced updates and hardware acceleration for smooth operation

## 🚀 Current Status

**Version**: 1.0.0-alpha (First Release - Development Version)

⚠️ **Note**: This is the first version of the application. While it contains comprehensive functionality, it may have some rough edges and is intended for development and testing purposes.

### What's Working

✅ Complete UI framework with all major components  
✅ Word-by-word karaoke timing and animation  
✅ Real-time preview in editor and effects sections  
✅ ASS subtitle format parsing with karaoke support  
✅ Text effects system with live preview  
✅ OpenGL-accelerated rendering  
✅ Cross-widget real-time synchronization

### Known Limitations

⚠️ Some advanced export features may need refinement  
⚠️ Error handling could be more robust  
⚠️ Performance optimization ongoing

## 📋 Requirements

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Graphics**: OpenGL 3.3+ support recommended
- **Memory**: 4GB RAM minimum, 8GB recommended

### Dependencies

- **PyQt6**: GUI framework and multimedia support
- **OpenGL**: Hardware-accelerated rendering
- **NumPy**: Mathematical operations and array handling
- **FFmpeg**: Video/audio processing (optional but recommended)

## 🛠️ Installation

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/karaoke-video-creator.git
cd karaoke-video-creator

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run demo scripts
python demo_karaoke_system.py
python demo_realtime_preview.py
```

## 📖 Usage Guide

### Basic Workflow

1. **Import Media**: Load your video/image background, audio track, and subtitle file
2. **Preview**: Check synchronization and overall timing
3. **Edit Subtitles**: Fine-tune text and timing with real-time preview
4. **Apply Effects**: Add glow, outline, shadow, and animation effects
5. **Export**: Generate your final karaoke video

### Advanced Features

- **Karaoke Timing**: Use ASS format with `{\k}` tags for precise word timing
- **Effect Combinations**: Layer multiple effects for professional results
- **Real-time Editing**: See changes instantly in the preview as you edit
- **Timeline Manipulation**: Drag subtitle blocks to adjust timing visually

## 🏗️ Architecture

### Project Structure

```
karaoke-video-creator/
├── src/
│   ├── core/           # Core functionality (models, parsers, renderers)
│   ├── ui/             # User interface components
│   └── main.py         # Application entry point
├── tests/              # Unit tests and integration tests
├── docs/               # Documentation and specifications
├── assets/             # Static resources and templates
└── demos/              # Demo scripts and examples
```

### Key Components

- **Models**: Data structures for projects, subtitles, and effects
- **Parsers**: ASS subtitle format parsing with karaoke support
- **Renderers**: OpenGL-accelerated subtitle and effect rendering
- **Synchronizer**: Real-time audio-video-subtitle synchronization
- **Effects Manager**: Text effect system with parameter management

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_karaoke_*.py -v  # Karaoke functionality
python -m pytest tests/test_realtime_*.py -v  # Real-time preview
python -m pytest tests/test_effects_*.py -v   # Text effects

# Run demo applications
python demo_karaoke_system.py      # Karaoke timing demo
python demo_realtime_preview.py    # Real-time preview demo
python test_realtime_functionality.py  # Functionality verification
```

## 📚 Documentation

- **[Karaoke Fixes Summary](KARAOKE_FIXES_SUMMARY.md)**: Word-by-word animation implementation
- **[Real-time Preview Summary](REALTIME_PREVIEW_SUMMARY.md)**: Live preview functionality
- **[Export System Summary](EXPORT_SYSTEM_SUMMARY.md)**: Video export capabilities
- **[FFmpeg Integration Summary](FFMPEG_INTEGRATION_SUMMARY.md)**: Media processing integration

## 🤝 Contributing

This project is in active development. Contributions are welcome!

### Development Guidelines

1. Follow PEP 8 style guidelines
2. Add unit tests for new functionality
3. Update documentation for significant changes
4. Test on multiple platforms when possible

### Areas for Contribution

- Performance optimization
- Additional text effects
- Export format support
- UI/UX improvements
- Bug fixes and error handling

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- PyQt6 team for the excellent GUI framework
- FFmpeg project for media processing capabilities
- OpenGL community for rendering specifications
- ASS subtitle format specification contributors

---

**Note**: This is the first version of the Karaoke Video Creator. While functional, it's primarily intended for development and testing. Future versions will include additional features, performance improvements, and enhanced stability.
