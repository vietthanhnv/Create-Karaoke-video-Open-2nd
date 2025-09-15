# Integrated Editor Widget

## Overview

The Integrated Editor Widget combines the preview, subtitle editing, and effects management into a single, cohesive interface. This provides a much more efficient workflow for creating karaoke videos by allowing real-time feedback as you edit.

## Key Features

### 1. Real-time Preview Integration

- **OpenGL Video Rendering**: Hardware-accelerated video display
- **Live Subtitle Overlay**: See subtitle changes immediately as you type
- **Effect Preview**: Visual feedback for text effects in real-time
- **Playback Controls**: Integrated play/pause/seek controls
- **Current Subtitle Display**: Shows currently active subtitles with karaoke highlighting

### 2. Tabbed Editing Interface

The editor uses a tabbed interface for different editing modes:

#### Text Editor Tab

- **Syntax Highlighting**: ASS format syntax highlighting for better readability
- **Auto-formatting**: Automatic formatting and validation of subtitle content
- **Quick Actions**: Add new lines, format text, and validate content
- **Real-time Validation**: Immediate feedback on subtitle format errors

#### Timeline Tab

- **Visual Timeline**: Drag-and-drop interface for adjusting subtitle timing
- **Individual Line Editor**: Edit specific subtitle properties (timing, text, style)
- **Timeline Synchronization**: Visual representation synced with preview playback
- **Precise Timing Controls**: Numeric inputs for exact timing adjustments

#### Effects Tab

- **Effects Library**: Browse and apply various text effects
- **Parameter Adjustment**: Real-time parameter tweaking with immediate preview
- **Effect Layering**: Manage multiple effects with proper render order
- **Preset System**: Apply pre-configured effect combinations

### 3. Unified Workflow Benefits

#### Immediate Feedback

- Changes in any tab are immediately reflected in the preview
- No need to switch between separate windows or tabs to see results
- Real-time validation prevents errors before they become problems

#### Contextual Editing

- Preview shows current playback position and active subtitles
- Timeline editing is synchronized with preview playback
- Effect parameters can be adjusted while watching their impact

#### Efficient Layout

- 60/40 split between preview and editing panels
- Resizable splitters for customizable workspace
- All tools accessible without losing preview context

## Technical Implementation

### Architecture

```
IntegratedEditorWidget
├── Preview Panel (Left 60%)
│   ├── OpenGL Video Widget
│   ├── Playback Controls
│   └── Current Subtitle Display
└── Editing Panel (Right 40%)
    ├── Tabbed Interface
    │   ├── Text Editor Tab
    │   ├── Timeline Tab
    │   └── Effects Tab
    └── Validation & Status Area
```

### Real-time Updates

- **Debounced Updates**: Text changes trigger updates after 200ms delay to prevent excessive processing
- **Signal-based Communication**: Qt signals ensure proper decoupling between components
- **Efficient Rendering**: Only updates preview when content actually changes

### Data Flow

1. **User Input** → Text Editor, Timeline, or Effects
2. **Validation** → Parse and validate subtitle content
3. **Synchronizer Update** → Update preview synchronizer with new content
4. **Preview Render** → OpenGL widget renders updated frame with effects
5. **UI Feedback** → Status updates and validation messages

## Usage Examples

### Basic Editing Workflow

1. **Load Project**: File → New Project or Load existing
2. **Edit Content**: Use Text Editor tab to modify subtitle content
3. **Adjust Timing**: Switch to Timeline tab for visual timing adjustments
4. **Add Effects**: Use Effects tab to enhance subtitle appearance
5. **Preview**: Use playback controls to see final result
6. **Save**: File → Save Subtitles when satisfied

### Advanced Features

- **Individual Line Editing**: Select subtitle in timeline, edit in dedicated form
- **Effect Layering**: Add multiple effects and adjust their render order
- **Real-time Parameter Tuning**: Adjust effect parameters while preview plays
- **Auto-formatting**: Automatically fix common subtitle format issues

## Benefits Over Separate Tabs

### Traditional Approach Problems

- **Context Switching**: Constantly switching between preview and editing tabs
- **Delayed Feedback**: Changes not visible until switching to preview
- **Workflow Interruption**: Losing editing context when checking preview
- **Inefficient Layout**: Wasted screen space with separate interfaces

### Integrated Approach Solutions

- **Continuous Context**: Always see preview while editing
- **Immediate Feedback**: Changes visible instantly
- **Efficient Workflow**: All tools accessible simultaneously
- **Better Space Usage**: Optimized layout for both preview and editing

## Testing

The integrated editor includes comprehensive unit tests covering:

- Widget initialization and UI component creation
- Project and subtitle file loading
- Real-time update mechanisms
- Playback control functionality
- Effects management
- Timeline integration
- Individual subtitle editing
- Validation and formatting
- File operations

Run tests with:

```bash
python -m pytest tests/test_integrated_editor_widget.py -v
```

## Demo

A complete demo application is available in `demo_integrated_editor.py`:

```bash
python demo_integrated_editor.py
```

The demo showcases:

- Complete integrated interface
- Sample project creation
- File loading dialogs
- Real-time editing capabilities
- Effect management
- All major features in action

## Future Enhancements

### Planned Features

- **Audio Waveform Display**: Visual audio representation in timeline
- **Karaoke Word Timing**: Individual word timing for karaoke effects
- **Advanced Effect Presets**: More sophisticated effect combinations
- **Undo/Redo System**: Full editing history management
- **Multi-track Support**: Multiple subtitle tracks for different languages

### Performance Optimizations

- **Lazy Loading**: Load preview content only when needed
- **Caching**: Cache rendered frames for better scrubbing performance
- **Background Processing**: Move heavy operations to background threads
- **Memory Management**: Optimize memory usage for large projects

## Conclusion

The Integrated Editor Widget represents a significant improvement in user experience for karaoke video creation. By combining all editing tools in a single, cohesive interface with real-time feedback, it eliminates the inefficiencies of the traditional tab-based approach and provides a much more intuitive and productive workflow.

The integrated approach allows users to:

- See changes immediately as they edit
- Maintain context while switching between different editing modes
- Work more efficiently with better screen space utilization
- Reduce errors through real-time validation and preview
- Create better karaoke videos with less effort and time
