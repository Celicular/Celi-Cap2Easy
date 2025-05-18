import os
import tempfile
import whisper
import torch
import numpy as np
from threading import Lock
import subprocess
import shutil
from pathlib import Path
import urllib.request
import tqdm
import sys
import platform

class WhisperTranscriber:
    """
    Handles transcription of audio using OpenAI's Whisper model.
    Optimized for mixed language (Hindi-English) with Roman script output.
    """
    
    # Singleton pattern to avoid loading model multiple times
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WhisperTranscriber, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, model_size="small"):
        """Initialize with specified model size"""
        if self._initialized:
            return
            
        self.model_size = model_size
        self.model = None
        self.gpu_info = self._check_gpu()
        self.device = self.gpu_info["device"]
        self.has_gpu = self.gpu_info["has_gpu"]
        self._initialized = True
        
    def _check_hardware_gpu(self):
        """
        Use direct hardware detection to identify NVIDIA GPUs regardless of PyTorch detection
        
        Returns:
            Dictionary with hardware GPU information
        """
        result = {
            "hardware_detected": False,
            "gpu_name": None,
            "driver_version": None,
            "vram_total": None,
            "detection_method": None
        }
        
        # First try Windows Management Instrumentation (WMI) if on Windows
        if platform.system() == "Windows":
            try:
                import wmi
                w = wmi.WMI()
                for gpu in w.Win32_VideoController():
                    if "NVIDIA" in gpu.Name:
                        result["hardware_detected"] = True
                        result["gpu_name"] = gpu.Name
                        result["driver_version"] = gpu.DriverVersion
                        result["detection_method"] = "WMI"
                        # WMI doesn't provide VRAM info reliably
                        return result
            except Exception as e:
                print(f"WMI detection failed: {e}")
        
        # Try NVIDIA-SMI command
        try:
            nvidia_smi = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if nvidia_smi.returncode == 0 and nvidia_smi.stdout.strip():
                # Parse the CSV output
                for line in nvidia_smi.stdout.strip().split('\n'):
                    parts = line.split(',')
                    if len(parts) >= 3:
                        gpu_name = parts[0].strip()
                        driver_version = parts[1].strip()
                        vram_total = parts[2].strip()
                        
                        result["hardware_detected"] = True
                        result["gpu_name"] = gpu_name
                        result["driver_version"] = driver_version
                        result["vram_total"] = vram_total
                        result["detection_method"] = "nvidia-smi"
                        return result
        except Exception as e:
            print(f"NVIDIA-SMI detection failed: {e}")
        
        # Try direct registry access as a last resort on Windows
        if platform.system() == "Windows":
            try:
                import winreg
                hklm = winreg.HKEY_LOCAL_MACHINE
                reg_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000"
                
                with winreg.OpenKey(hklm, reg_path) as key:
                    driver_desc = winreg.QueryValueEx(key, "DriverDesc")[0]
                    if "NVIDIA" in driver_desc:
                        result["hardware_detected"] = True
                        result["gpu_name"] = driver_desc
                        result["detection_method"] = "Windows Registry"
                        return result
            except Exception as e:
                print(f"Registry detection failed: {e}")
        
        return result
    
    def _check_gpu(self):
        """
        Perform detailed check for GPU availability using multiple methods
        Returns a dict with information about GPU status
        """
        result = {
            "has_gpu": False,
            "device": "cpu",
            "gpu_name": None,
            "cuda_version": None,
            "reason": None,
            "cuda_available": False,
            "device_count": 0,
            "hardware_gpu": None,
            "force_gpu": False
        }
        
        # Get hardware GPU information first
        hardware_gpu = self._check_hardware_gpu()
        result["hardware_gpu"] = hardware_gpu
        
        # Consider forcing GPU usage if hardware is detected but PyTorch doesn't see it
        force_gpu = os.environ.get("FORCE_GPU", "").lower() in ("1", "true", "yes")
        result["force_gpu"] = force_gpu
        
        try:
            # Check if CUDA is available through PyTorch
            cuda_available = torch.cuda.is_available()
            result["cuda_available"] = cuda_available
            
            # Check hardware detection
            hardware_detected = hardware_gpu["hardware_detected"]
            
            if not cuda_available:
                if hardware_detected:
                    result["reason"] = f"PyTorch cannot access GPU, but hardware detected: {hardware_gpu['gpu_name']}"
                    
                    # If hardware is detected but CUDA is not available, suggest solutions
                    if force_gpu:
                        # Try to force GPU usage
                        result["has_gpu"] = True
                        result["device"] = "cuda:0"
                        result["gpu_name"] = hardware_gpu["gpu_name"]
                        return result
                else:
                    result["reason"] = "CUDA not available and no GPU hardware detected"
                    return result
                
            # Get device count
            device_count = torch.cuda.device_count()
            result["device_count"] = device_count
            
            if device_count == 0:
                if hardware_detected:
                    result["reason"] = f"PyTorch reports 0 CUDA devices, but hardware detected: {hardware_gpu['gpu_name']}"
                    
                    # If hardware is detected but no CUDA devices, suggest solutions
                    if force_gpu:
                        # Try to force GPU usage
                        result["has_gpu"] = True
                        result["device"] = "cuda:0"
                        result["gpu_name"] = hardware_gpu["gpu_name"]
                        return result
                else:
                    result["reason"] = "No CUDA devices found"
                    return result
                
            # Get device name
            try:
                # Get first GPU
                gpu_name = torch.cuda.get_device_name(0)
                result["gpu_name"] = gpu_name
                result["cuda_version"] = torch.version.cuda
            except Exception as e:
                result["reason"] = f"Error getting GPU name: {str(e)}"
                return result
                
            # Try to force enable GPU by initializing a small tensor
            try:
                # Try explicit device setting
                device = torch.device("cuda:0")
                # Create a small tensor on GPU
                test_tensor = torch.zeros(1, 1).to(device)
                # If we get here, GPU is working
                result["has_gpu"] = True
                result["device"] = "cuda:0" 
                # Free memory
                del test_tensor
                torch.cuda.empty_cache()
            except Exception as e:
                result["reason"] = f"Error initializing tensor on GPU: {str(e)}"
                
                # If initializing tensor fails but hardware is detected, consider forcing GPU
                if hardware_detected and force_gpu:
                    result["has_gpu"] = True
                    result["device"] = "cuda:0"
                    result["gpu_name"] = hardware_gpu["gpu_name"]
                
                return result
            
            return result
        except Exception as e:
            result["reason"] = f"Unexpected error: {str(e)}"
            
            # If an exception occurs but hardware is detected, consider forcing GPU
            if hardware_gpu["hardware_detected"] and force_gpu:
                result["has_gpu"] = True
                result["device"] = "cuda:0"
                result["gpu_name"] = hardware_gpu["gpu_name"]
                
            return result
        
    def force_gpu_mode(self):
        """Force GPU mode regardless of automatic detection"""
        os.environ["FORCE_GPU"] = "1"
        # Re-run GPU check
        self.gpu_info = self._check_gpu()
        self.device = self.gpu_info["device"]
        self.has_gpu = self.gpu_info["has_gpu"]
        # Clear any loaded model to force reload with new device
        self.model = None
        return self.has_gpu
        
    def get_gpu_info(self):
        """Return detailed GPU information for diagnostics"""
        return self.gpu_info
        
    def check_model(self):
        """
        Check if the model is already downloaded, and if not, 
        return False to prompt the user to download it
        """
        # Get the expected model path
        model_path = self._get_model_path()
        return os.path.exists(model_path)
    
    def _get_model_path(self):
        """Get the path where the Whisper model should be located"""
        # Whisper models are stored in ~/.cache/whisper
        home = Path.home()
        model_path = home / ".cache" / "whisper" / f"{self.model_size}.pt"
        return model_path
        
    def download_model(self, callback=None):
        """
        Download the specified model
        
        Args:
            callback: Progress callback function (percent, message)
        """
        model_path = self._get_model_path()
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Model URLs
        model_urls = {
            "tiny": "https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.pt",
            "base": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
            "small": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
            "medium": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            "large-v3": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b6a8318/large-v3.pt",
        }
        
        if self.model_size not in model_urls:
            raise ValueError(f"Invalid model size: {self.model_size}")
        
        url = model_urls[self.model_size]
        
        # Download with progress
        if callback:
            callback(0, f"Downloading {self.model_size} model...")
        
        # Custom progress bar
        class DownloadProgressBar(tqdm.tqdm):
            def update_to(self, b=1, bsize=1, tsize=None):
                if tsize is not None:
                    self.total = tsize
                self.update(b * bsize - self.n)
                if callback:
                    callback(int(self.n / self.total * 100), f"Downloading {self.n / 1024 / 1024:.1f} MB / {self.total / 1024 / 1024:.1f} MB")
        
        with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=self.model_size) as t:
            urllib.request.urlretrieve(url, model_path, reporthook=t.update_to)
        
        if callback:
            callback(100, f"Downloaded {self.model_size} model successfully!")
        
        return True
        
    def load_model(self, callback=None):
        """Load the Whisper model (lazy loading to save memory)"""
        if self.model is None:
            if callback:
                callback(-1, f"Loading Whisper model '{self.model_size}' on {self.device}...")
                if self.has_gpu:
                    callback(-1, f"Using GPU: {self.gpu_info.get('gpu_name', 'Unknown')}")
                else:
                    callback(-1, f"Using CPU mode (GPU not available: {self.gpu_info.get('reason', 'Unknown reason')})")
            else:
                print(f"Loading Whisper model '{self.model_size}' on {self.device}...")
                
            # Check if model exists first
            if not self.check_model():
                raise FileNotFoundError(f"Whisper model '{self.model_size}' not found. Please download it first.")
                
            # Force empty CUDA cache if using GPU
            if self.has_gpu:
                torch.cuda.empty_cache()
                
            # Load model with explicit device placement
            try:
                self.model = whisper.load_model(self.model_size, device=self.device)
            except Exception as e:
                # If loading fails with GPU, fall back to CPU
                if self.has_gpu:
                    if callback:
                        callback(-1, f"Failed to load model on GPU: {str(e)}. Falling back to CPU.")
                    else:
                        print(f"Failed to load model on GPU: {str(e)}. Falling back to CPU.")
                    self.device = "cpu"
                    self.has_gpu = False
                    self.model = whisper.load_model(self.model_size, device="cpu")
                else:
                    # Re-raise if already trying CPU
                    raise
            
            if callback:
                callback(-1, "Model loaded successfully.")
            else:
                print("Model loaded successfully.")
                
        return self.model
        
    def transcribe_audio(self, audio_path, language='en', 
                        mixed_language=True, confidence_threshold=0.5,
                        callback=None):
        """
        Transcribe audio using Whisper
        
        Args:
            audio_path: Path to the audio file
            language: Language code (en, hi, or None for auto-detection)
            mixed_language: Whether to handle mixed language (Hindi-English)
            confidence_threshold: Threshold for confidence scores
            callback: Progress callback function
            
        Returns:
            dict with text, segments with timestamps, and confidence scores
        """
        # Load model if not already loaded
        model = self.load_model(callback)
        
        # Set up initial prompt for mixed language romanization
        initial_prompt = None
        
        # Setup options specifically for Hindi transcription
        if language == 'hi' or (language is None and mixed_language):
            if callback:
                callback(-1, "Using Hindi-English mixed mode with Romanization...")
            
            # Use English language model for Hindi romanization
            # This works better than using 'hi' and trying to romanize the output
            actual_language = 'en'
            
            # Better prompting for Hindi Romanization - IMPORTANT: don't make it part of transcript
            initial_prompt = "Transcribe Hindi speech using Roman script (not Devanagari). Transcribe English normally."
        else:
            # Use the specified language
            actual_language = language
        
        # Advanced options for GPU
        fp16 = self.has_gpu
        
        # Set task options - always use 'transcribe' for accurate timestamps
        task = "transcribe"
        
        # Set beam search parameters for better quality
        beam_size = 5
        best_of = 5
        
        # Perform transcription
        if callback:
            callback(-1, f"Transcribing audio using language mode: {actual_language}...")
            
        # Note: using verbose=False to avoid printing progress to console
        result = model.transcribe(
            audio_path,
            language=actual_language,
            task=task,
            initial_prompt=initial_prompt,
            beam_size=beam_size,
            best_of=best_of,
            word_timestamps=True,  # Enable word-level timestamps
            fp16=fp16,  # Use FP16 for GPU acceleration
            verbose=False  # Don't print progress to console
        )
        
        if callback:
            callback(-1, "Transcription completed!")
        
        # Process the transcription result
        # When using Hindi mode, check if the result contains the prompt as part of the output
        full_text = result["text"].strip()
        
        # Post-processing to remove any instances of the prompt leaking into the transcript
        if language == 'hi' or (language is None and mixed_language):
            # List of possible prompt leakage patterns to remove
            patterns_to_remove = [
                "Transcribe Hindi speech using Roman script not Devanagari",
                "Transcribe Hindi speech using Roman script",
                "Transcribe Hindi using Roman script",
                "Hindi in Roman script:",
                "Roman script:",
                "(in Roman script)",
                "Transcribe in Roman script",
                "Transcribe Hindi in Roman script"
            ]
            
            # Remove these patterns from the beginning of the text
            for pattern in patterns_to_remove:
                if full_text.startswith(pattern):
                    full_text = full_text[len(pattern):].strip()
                # Also check for case-insensitive matches
                elif full_text.lower().startswith(pattern.lower()):
                    full_text = full_text[len(pattern):].strip()
                # Check for patterns with punctuation
                for punct in [":", "."]:
                    if full_text.startswith(pattern + punct):
                        full_text = full_text[len(pattern) + 1:].strip()
            
            # Also clean up individual segments
            for segment in result["segments"]:
                segment_text = segment["text"].strip()
                for pattern in patterns_to_remove:
                    if segment_text.startswith(pattern):
                        segment_text = segment_text[len(pattern):].strip()
                    # Also check for case-insensitive matches
                    elif segment_text.lower().startswith(pattern.lower()):
                        segment_text = segment_text[len(pattern):].strip()
                    # Check for patterns with punctuation
                    for punct in [":", "."]:
                        if segment_text.startswith(pattern + punct):
                            segment_text = segment_text[len(pattern) + 1:].strip()
                
                segment["text"] = segment_text
        
        # Replace the full text with cleaned version
        result["text"] = full_text
        
        # Extract segments with confidence scores
        segments_with_confidence = []
        for segment in result["segments"]:
            # Calculate average confidence for words in segment
            words_confidence = [word.get("confidence", 0.0) for word in segment.get("words", [])]
            avg_confidence = np.mean(words_confidence) if words_confidence else 0.0
            
            # Mark words with low confidence
            marked_text = segment["text"]
            if avg_confidence < confidence_threshold:
                # The UI will handle the highlighting
                marked_text = f"<low_confidence>{marked_text}</low_confidence>"
            
            segments_with_confidence.append({
                "text": segment["text"],
                "marked_text": marked_text,
                "start": segment["start"],
                "end": segment["end"],
                "confidence": avg_confidence
            })
        
        return {
            "text": result["text"],
            "segments": segments_with_confidence,
            "language": result.get("language", "unknown")
        }
    
    def transcribe_segment(self, audio_path, start_time, duration, callback=None, **kwargs):
        """Transcribe a specific segment of audio"""
        # Create a temporary file for the extracted segment
        temp_file = tempfile.mktemp(suffix=".wav")
        
        try:
            # Extract the segment
            cmd = [
                "ffmpeg", "-ss", str(start_time),
                "-i", audio_path,
                "-t", str(duration),
                "-c:a", "pcm_s16le",
                "-ar", "16000",  # Whisper expects 16kHz audio
                "-ac", "1",      # Mono channel
                "-y", temp_file
            ]
            
            # Run FFmpeg to extract segment
            if callback:
                callback(-1, "Extracting audio segment...")
                
            subprocess.run(cmd, check=True, 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE)
            
            if callback:
                callback(-1, "Audio segment extracted. Transcribing...")
            
            # Transcribe the extracted segment
            result = self.transcribe_audio(temp_file, callback=callback, **kwargs)
            
            # Adjust timestamps to be relative to the original audio
            for segment in result["segments"]:
                segment["start"] += start_time
                segment["end"] += start_time
                
            return result
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def get_available_models(self):
        """Return a list of available Whisper model sizes"""
        return ["tiny", "base", "small", "medium", "large-v3"]
        
    def get_model_size_description(self):
        """Get descriptions for available models with approximate sizes"""
        return {
            "tiny": "Tiny (39M parameters, ~75MB)",
            "base": "Base (74M parameters, ~142MB)",
            "small": "Small (244M parameters, ~466MB)",
            "medium": "Medium (769M parameters, ~1.5GB)",
            "large-v3": "Large v3 (1550M parameters, ~3GB)"
        }

# Example usage:
# transcriber = WhisperTranscriber(model_size="small")
# result = transcriber.transcribe_segment("audio.mp3", start_time=10.0, duration=5.0)
# print(result["text"]) 