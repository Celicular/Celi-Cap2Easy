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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition
- [FFmpeg](https://ffmpeg.org/) for video processing
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI 