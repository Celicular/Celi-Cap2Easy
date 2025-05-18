# Video Captioning Tool

An open source video captioning tool with automatic speech recognition, custom font support, and high-quality output.

**Authored by Himadri**

## Features

- 📽️ Video preview with real-time captioning
- 🎙️ Automatic speech transcription using OpenAI's Whisper model
- 🎭 Custom caption style presets
- 🔤 Custom TTF font support
- 🗣️ Multi-language support, including mixed language detection
- 🖥️ GPU acceleration with automatic detection
- 🎬 High-quality video rendering with perfect captions

## Getting Started

### Prerequisites

- Python 3.8 or higher
- FFmpeg (must be installed and available in your PATH)
- GPU optional but recommended for faster transcription

### Quick Start

1. Clone the repository:
```bash
git clone https://github.com/yourusername/captioner.git
cd captioner
```

2. Run the application using the batch file:
```
run_captioner.bat
```

The batch file will automatically check for requirements and install them if needed.

### Manual Installation

If you prefer to set up manually:

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python caption-tool/main.py
```

## Usage

### Basic Workflow

1. Load a video using the "Load Video" button
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for the speech recognition
- [FFmpeg](https://ffmpeg.org/) for video processing
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI 