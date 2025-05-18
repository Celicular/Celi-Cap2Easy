#!/usr/bin/env python3
"""
Video Captioning Tool - A desktop application for manually adding styled captions to videos

Features:
- Load a video file and navigate through it in 5-second segments
- Manually add captions with precise timing
- Apply visual style presets to captions
- Live preview of captions over video frames
- Render final video with captions using FFmpeg
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox

# Add the project directory to the Python path
project_dir = Path(__file__).parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Import application modules
try:
    from gui.main_ui import MainWindow
    from utils.ffmpeg import FFmpegHandler
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def check_requirements():
    """Check if all required dependencies are available"""
    try:
        # Check for FFmpeg
        ffmpeg = FFmpegHandler()
        ffmpeg.check_ffmpeg()
        
        # Check for PyQt6
        import PyQt6
        
        # Check for other packages
        import json
        import tempfile
        import pygame
        
        return True
    except Exception as e:
        # Show error message
        if 'QApplication' in globals():
            QMessageBox.critical(
                None, 
                "Missing Dependencies", 
                f"Required dependencies are missing:\n{str(e)}\n\n"
                "Please install the missing packages and try again."
            )
        else:
            print(f"Error: {e}")
        return False

def create_required_directories():
    """Create required directories if they don't exist"""
    directories = [
        "presets",
        "data",
    ]
    
    for directory in directories:
        dir_path = project_dir / directory
        os.makedirs(dir_path, exist_ok=True)

def main():
    """Main application entry point"""
    # Create required directories
    create_required_directories()
    
    # Check dependencies
    if not check_requirements():
        sys.exit(1)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Video Captioning Tool")
    app.setOrganizationName("Caption Tool")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 