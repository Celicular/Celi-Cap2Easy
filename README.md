# Video Captioning Tool

A powerful and intuitive video captioning tool with automatic speech recognition and custom font support.

## Features

- 📽️ Video preview with real-time captioning
- 🎙️ Automatic speech transcription using OpenAI's Whisper model
- 🎭 Custom caption style presets
- 🔤 Custom TTF font support
- 🗣️ Multi-language support, including mixed language detection
- 🖥️ GPU acceleration with automatic detection
- 🎬 High-quality video rendering with perfect captions

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg (must be installed and available in your PATH)
- PyQt6
- NVIDIA GPU (optional, for faster transcription)

### Install Steps

1. Clone the repository:
```bash
git clone https://github.com/yourusername/captioner.git
cd captioner
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python caption-tool/main.py
```

## Usage

### Basic Workflow

1. Load a video file using the "Load Video" button
2. Navigate through the video using the playback controls
3. Download the Whisper model if you haven't already (one-time setup)
4. Use auto-transcribe for automatic captions or manually type captions
5. Apply style presets to your captions
6. Render the final video with embedded captions

### Using Custom Fonts

1. Go to the caption editor by clicking "Edit Presets"
2. Click "Upload TTF..." to upload your own TTF font files
3. Select your custom font from the dropdown when creating or editing presets
4. Your custom fonts will be used when rendering the final video

### Language Support

The tool supports multiple languages for transcription:
- English
- Hindi (Romanized)
- Mixed language detection

### GPU Acceleration

The tool automatically detects and uses your GPU for faster transcription. If your GPU isn't being used, check the "GPU Diagnostics" section in the application.

## Technical Details

### Project Structure

```
caption-tool/
├── data/                  # Stores captions data
├── gui/                   # UI components
│   ├── caption_preview.py # Video preview widget
│   ├── main_ui.py         # Main application window
│   └── preset_editor.py   # Caption style editor
├── presets/               # Caption style presets
│   ├── fonts/             # Custom TTF fonts directory
│   └── presets.json       # Preset configurations
├── utils/                 # Utility modules
│   ├── audio_player.py    # Audio playback handling
│   ├── ffmpeg.py          # FFmpeg integration
│   ├── preset_manager.py  # Manages caption presets
│   └── whisper_transcriber.py # Speech recognition
└── main.py                # Application entry point
```

### Key Components

#### Main UI (`main_ui.py`)

The main application window that manages the overall workflow:

- **Video Preview**: Displays the current video frame with captions
- **Playback Controls**: Navigate through the video in 5-second segments
- **Transcription**: Integrates with Whisper for automatic speech recognition
- **Caption Editing**: UI for creating and editing captions
- **Rendering**: Exports videos with embedded captions

#### FFmpeg Handler (`ffmpeg.py`)

Manages all video and audio processing:

- **Video Information**: Extracts metadata from video files
- **Frame Extraction**: Captures specific frames for preview
- **Audio Extraction**: Separates audio for transcription
- **Caption Rendering**: Generates drawtext filters for captions
- **Final Rendering**: Combines video, audio, and captions into output file

#### Whisper Transcriber (`whisper_transcriber.py`)

Handles speech recognition:

- **Model Management**: Downloads and loads Whisper models
- **Transcription**: Processes audio segments to text
- **GPU Acceleration**: Automatically uses GPU when available
- **Language Support**: Handles multiple languages and mixed speech

#### Preset Manager (`preset_manager.py`)

Manages caption style presets:

- **Preset Storage**: Saves and loads presets from JSON
- **Font Management**: Handles custom TTF fonts
- **Style Application**: Applies styles to captions in preview and rendering

### Recent Optimizations

1. **Navigation Anti-Glitch**
   - Added timer-based cooldown between navigation actions
   - Prevents rapid clicking that can cause playback issues
   - Disabled navigation during active playback

2. **Playback Monitoring**
   - Implemented thread-based playback monitoring
   - Properly signals when audio playback completes
   - Updates UI state automatically after playback

3. **Aspect Ratio Handling**
   - Improved aspect ratio calculation based on original video dimensions
   - Fixed 9:16 conversion issues by calculating appropriate dimensions
   - Ensured minimum dimensions to prevent encoder errors

4. **Font Handling**
   - Enhanced font path handling for custom TTF fonts
   - Added validation to check if font files exist
   - Implemented proper fallback to system fonts

5. **Error Prevention**
   - Added validation for directories before file operations
   - Implemented comprehensive error handling in FFmpeg operations
   - Added better diagnostics for rendering issues

6. **Open Folder Integration**
   - Added button to directly open the render output folder
   - Provides easier access to rendered videos

7. **UI Responsiveness**
   - Added proper signals and slots for background operations
   - Ensured UI updates during long-running processes

## Customization

### Caption Presets

Create and customize caption presets with:
- Font selection
- Size
- Color
- Position
- Animation effects

### Advanced Options

The tool supports:
- Custom aspect ratios
- Different scaling modes
- Fine-tuned caption positioning

## Troubleshooting

### GPU Not Detected

If your GPU isn't being utilized:
1. Check that you have the latest NVIDIA drivers installed
2. Try using the "Force GPU" option in the GPU Diagnostics dialog
3. Ensure you have PyTorch installed with CUDA support

### Performance Tips

- For faster transcription, use a smaller Whisper model (tiny or base)
- Close other GPU-intensive applications while transcribing
- For higher quality, use the "medium" or "large-v3" models (requires more GPU memory)

### Rendering Issues

- If custom fonts aren't appearing, check that TTF files are properly installed
- For aspect ratio problems, try the "contain" mode instead of "cover"
- If FFmpeg errors occur, check the detailed error message in the render dialog

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition
- [FFmpeg](https://ffmpeg.org/) for video processing
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI 