# Video Captioning Tool

A desktop application for semi-manually captioning videos with customizable visual styles and precise timing control.

## Features

- Load video files and navigate through them in 5-second segments
- Manually enter captions with precise timing
- Create and apply visual style presets to captions
- Preview captions over video frames in real-time
- Render final videos with styled captions using FFmpeg
- Save and load caption files in JSON format

## Installation

### Prerequisites

- Python 3.7 or higher
- FFmpeg (must be installed and available in your PATH)

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
4. Enter caption text and select a style preset
5. Save the caption for the current segment
6. When finished, render the final video with captions

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
    "preset": "fadeBottom"
  },
  {
    "start": 5,
    "end": 10,
    "text": "Let's create magic!",
    "preset": "topSlide"
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