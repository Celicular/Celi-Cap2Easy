# Video Captioning Tool

A desktop application for semi-manually captioning videos with customizable visual styles and precise timing control. Features AI-assisted transcription for mixed language content (Hindi-English).

## Features

- Load video files and navigate through them in 5-second segments
- Manually enter captions with precise timing
- **AI-assisted transcription** using OpenAI's Whisper model
- Support for **mixed language transcription** (Hindi-English with Romanization)
- GPU acceleration for faster transcription (when available)
- Model download management with progress tracking
- Create and apply visual style presets to captions
- Preview captions over video frames in real-time
- Render final videos with styled captions using FFmpeg
- Save and load caption files in JSON format

## Installation

### Prerequisites

- Python 3.7 or higher
- FFmpeg (must be installed and available in your PATH)
- For AI transcription: CUDA-compatible GPU recommended (but not required)

### Setup

1. Clone or download this repository
2. Install the required Python packages:

```
pip install -r requirements.txt
```

### FFmpeg Installation

This application requires FFmpeg to be installed on your system.

- **Windows**: 
  - Download from [FFmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  - Add the FFmpeg `bin` directory to your system PATH

- **macOS**:
  - Install with Homebrew: `brew install ffmpeg`

- **Linux**:
  - Debian/Ubuntu: `sudo apt install ffmpeg`
  - Fedora: `sudo dnf install ffmpeg`
  - Arch Linux: `sudo pacman -S ffmpeg`

## Usage

1. Run the application:

```
python main.py
```

2. Load a video file using the "Load Video" button
3. Navigate through the video using the playback controls
4. For AI-assisted transcription:
   - Select the language mode (English, Hindi, or Mixed)
   - Select a model size (smaller models are faster but less accurate)
   - If the model isn't downloaded yet, click "Download Model"
   - Click "Auto-Transcribe" to transcribe the current 5-second segment
   - Edit the transcription as needed (low-confidence sections are highlighted in orange)
   - Enable "Auto-transcribe next segment" for continuous transcription
5. Select a style preset for your caption
6. Save the caption for the current segment
7. When finished, render the final video with captions

## Mixed Language Support

The application is designed to handle mixed Hindi-English content:

- For Hindi speech, it uses phonetic Romanization (e.g., "kaise ho" instead of "कैसे हो")
- You can choose between English-only, Hindi-only, or Mixed language modes
- In Mixed mode, the AI will automatically detect the language being spoken

## Whisper Models

The application uses OpenAI's Whisper models for transcription:

- **Tiny**: Smallest model (~75MB), fastest but least accurate
- **Base**: Small model (~142MB), good for short, clear speech
- **Small**: Medium-sized model (~466MB), good balance of accuracy and speed
- **Medium**: Larger model (~1.5GB), more accurate but slower
- **Large**: Largest model (~3GB), most accurate but requires a powerful GPU

Models are downloaded automatically when needed. GPU acceleration is used when available.

## Caption Presets

The application comes with predefined caption style presets. You can:

- Create new presets with custom fonts, sizes, colors, and animations
- Edit existing presets
- Apply presets to individual captions

## Caption JSON Format

Captions are stored in a JSON file with the following structure:

```json
[
  {
    "start": 0,
    "end": 5,
    "text": "Welcome to the tool",
    "preset": "fadeBottom",
    "language": "English",
    "auto_generated": true
  },
  {
    "start": 5,
    "end": 10,
    "text": "Kaise ho? Let's create magic!",
    "preset": "topSlide",
    "language": "Mixed (Auto-detect)",
    "auto_generated": false
  }
]
```

## License

[MIT License](LICENSE)

## Acknowledgements

This application uses the following open-source libraries:

- PyQt6 for the graphical user interface
- FFmpeg for video and audio processing
- Pygame for audio playback
- OpenAI Whisper for AI-powered transcription 