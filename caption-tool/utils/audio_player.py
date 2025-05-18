import os
import tempfile
import subprocess
import wave
import pygame
from pygame import mixer
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal

class AudioPlayer(QObject):
    # Define signals
    playback_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Initialize pygame mixer
        pygame.init()
        mixer.init()
        self.current_audio_file = None
        self.temp_files = []
        self.playback_monitor_thread = None
        self.should_monitor = False
        
    def __del__(self):
        """Clean up temporary files when object is destroyed"""
        self.cleanup()
        
    def cleanup(self):
        """Remove all temporary files"""
        self.should_monitor = False
        
        # Wait for monitor thread to end if it exists
        if self.playback_monitor_thread and self.playback_monitor_thread.is_alive():
            self.playback_monitor_thread.join(1.0)
        
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"Error cleaning up {file}: {e}")
                
        self.temp_files = []
        
    def load_audio(self, audio_path):
        """Load the main audio file"""
        self.current_audio_file = audio_path
        
    def extract_segment(self, start_time, duration=5.0):
        """Extract a segment of the audio file using FFmpeg"""
        if not self.current_audio_file:
            raise ValueError("No audio file loaded")
            
        # Create a temporary file for the segment
        temp_file = tempfile.mktemp(suffix=".wav")
        self.temp_files.append(temp_file)
        
        # Extract the segment using FFmpeg
        cmd = [
            "ffmpeg", "-ss", str(start_time),
            "-i", self.current_audio_file,
            "-t", str(duration),
            "-q:a", "0", "-map", "a",
            "-y", temp_file
        ]
        
        subprocess.run(cmd, check=True, 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE)
        
        return temp_file
    
    def monitor_playback(self):
        """Monitor the playback status and emit a signal when finished"""
        self.should_monitor = True
        while self.should_monitor and mixer.music.get_busy():
            time.sleep(0.1)
            
        # Only emit if we didn't manually stop monitoring
        if self.should_monitor:
            self.playback_finished.emit()
        
        self.should_monitor = False
    
    def play_segment(self, start_time, duration=5.0):
        """Play a 5-second segment of audio starting at start_time"""
        # Stop any currently playing audio and monitoring
        self.stop()
        
        # Extract the segment
        segment_file = self.extract_segment(start_time, duration)
        
        # Load and play the segment
        mixer.music.load(segment_file)
        mixer.music.play()
        
        # Start monitoring thread
        self.playback_monitor_thread = threading.Thread(target=self.monitor_playback)
        self.playback_monitor_thread.daemon = True
        self.playback_monitor_thread.start()
        
        return segment_file
    
    def get_audio_duration(self, audio_file=None):
        """Get the duration of an audio file in seconds"""
        if audio_file is None:
            audio_file = self.current_audio_file
            
        if not audio_file:
            raise ValueError("No audio file specified")
            
        # Use wave module for WAV files
        if audio_file.lower().endswith(".wav"):
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
                return duration
        else:
            # Use FFmpeg for other audio formats
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_file
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
            duration = float(result.stdout)
            return duration
    
    def is_playing(self):
        """Check if audio is currently playing"""
        return mixer.music.get_busy()
    
    def stop(self):
        """Stop playback"""
        self.should_monitor = False
        mixer.music.stop() 