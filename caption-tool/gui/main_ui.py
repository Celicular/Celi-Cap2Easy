import os
import sys
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout,                             QHBoxLayout, QPushButton, QLabel, QFileDialog,                             QTextEdit, QComboBox, QSpinBox, QLineEdit,                             QScrollArea, QGroupBox, QTabWidget, QDialog,                             QColorDialog, QMessageBox, QSplitter, QProgressBar,                            QPlainTextEdit, QCheckBox, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QColor, QPalette, QFont, QTextCharFormat, QTextCursor
import torch
import subprocess

# Import our custom utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ffmpeg import FFmpegHandler
from utils.audio_player import AudioPlayer
from utils.preset_manager import PresetManager
from utils.whisper_transcriber import WhisperTranscriber
from gui.preset_editor import PresetEditorDialog
from gui.caption_preview import CaptionPreviewWidget

# Thread class for model download
class ModelDownloadThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, transcriber, model_size):
        super().__init__()
        self.transcriber = transcriber
        self.model_size = model_size
        
    def run(self):
        try:
            self.transcriber.model_size = self.model_size
            success = self.transcriber.download_model(
                callback=lambda progress, message: self.progress_signal.emit(progress, message)
            )
            self.finished_signal.emit(True, "Model downloaded successfully")
        except Exception as e:
            self.finished_signal.emit(False, str(e))

# Thread class for CUDA installation
class CudaInstallThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def run(self):
        try:
            # Command to install PyTorch with CUDA support
            command = [
                sys.executable, "-m", "pip", "install", "--force-reinstall",
                "torch", "torchvision", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cu118"
            ]
            
            self.output_signal.emit("Starting PyTorch installation with CUDA support...")
            self.output_signal.emit(f"Command: {' '.join(command)}")
            
            # Run pip install command with real-time output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                self.output_signal.emit(line.strip())
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode == 0:
                self.output_signal.emit("PyTorch installation completed successfully!")
                self.finished_signal.emit(True, "PyTorch with CUDA installed successfully")
            else:
                self.output_signal.emit(f"Installation failed with return code: {process.returncode}")
                self.finished_signal.emit(False, f"Installation failed with return code: {process.returncode}")
                
        except Exception as e:
            self.output_signal.emit(f"Error during installation: {str(e)}")
            self.finished_signal.emit(False, str(e))

# Thread class for transcription to keep UI responsive
class TranscriptionThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(dict, str)
    
    def __init__(self, transcriber, audio_path, start_time, duration, language, mixed_language):
        super().__init__()
        self.transcriber = transcriber
        self.audio_path = audio_path
        self.start_time = start_time
        self.duration = duration
        self.language = language
        self.mixed_language = mixed_language
        
    def run(self):
        try:
            result = self.transcriber.transcribe_segment(
                self.audio_path, 
                self.start_time, 
                self.duration,
                language=self.language,
                mixed_language=self.mixed_language,
                callback=lambda progress, message: self.progress_signal.emit(progress, message)
            )
            self.finished_signal.emit(result, "Transcription completed")
        except Exception as e:
            self.finished_signal.emit({}, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # App version
        self.app_version = "1.0.0"
        
        # Check for forced GPU mode from previous run
        force_gpu = os.environ.get("FORCE_GPU", "").lower() in ("1", "true", "yes")
        if force_gpu:
            # Production mode - no debug prints
            pass
        
        # Initialize utilities
        try:
            self.ffmpeg = FFmpegHandler()
            self.audio_player = AudioPlayer()
            self.preset_manager = PresetManager()
            self.transcriber = WhisperTranscriber(model_size="small")
            
            # Connect audio player signal explicitly
            self.audio_player.playback_finished.connect(self.on_playback_finished)
        except Exception as e:
            self.show_critical_error(f"Failed to initialize components: {e}")
        
        # Initialize app state
        self.current_video_path = None
        self.current_audio_path = None
        self.current_time = 0.0
        self.segment_duration = 5.0
        self.video_duration = 0.0
        self.captions = []
        self.captions_file = None
        self.auto_transcribe_next = False
        self.is_segment_playing = False  # Track playback state
        
        # Initialize navigation timer
        self.navigation_timer = QTimer()
        self.navigation_timer.setSingleShot(True)
        
        # Set default captions file path
        base_dir = Path(__file__).parent.parent
        self.captions_file = base_dir / "data" / "captions.json"
        
        # Ensure data directory exists
        try:
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
        except Exception as e:
            self.show_critical_error(f"Failed to create data directory: {e}")
        
        # Reset captions file on startup
        self.reset_captions_file()
        
        # Set up UI
        self.init_ui()
        
        # Load captions if exist
        self.load_captions()
        
    def show_critical_error(self, message):
        """Show critical error and exit if necessary"""
        QMessageBox.critical(self, "Critical Error", message)
        # For truly fatal errors, we might want to exit
        # sys.exit(1)
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Video Captioning Tool")
        self.setMinimumSize(1600, 1000)  # Increased minimum size for better preview
        
        # Initialize all UI elements first
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        
        self.edit_presets_btn = QPushButton("Edit Presets")
        self.edit_presets_btn.setMinimumWidth(100)
        
        self.save_caption_btn = QPushButton("💾 Save Caption")
        self.save_caption_btn.setMinimumWidth(120)
        
        self.preview_caption_btn = QPushButton("👁 Preview Caption")
        self.preview_caption_btn.setMinimumWidth(120)
        
        # Update preset combo after initialization
        self.update_preset_combo()
        
        # Set application style with dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
                border-color: #3d3d3d;
            }
            QGroupBox {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 16px;
                margin-top: 16px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #00a8ff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox, QTextEdit, QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
                color: #ffffff;
            }
            QComboBox:hover, QTextEdit:hover, QLineEdit:hover {
                border-color: #00a8ff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QLabel {
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #00a8ff;
                border-radius: 3px;
            }
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                background-color: #2d2d2d;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                border-bottom: 2px solid #00a8ff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3d3d3d;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #00a8ff;
                border-color: #00a8ff;
            }
            QCheckBox::indicator:hover {
                border-color: #00a8ff;
            }
        """)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Create splitter for top and bottom sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Video and controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setSpacing(16)
        
        # Video preview container with fixed aspect ratio
        preview_container = QWidget()
        preview_container.setMinimumHeight(350)  # Further reduced height
        preview_container.setMaximumHeight(450)  # Reduced maximum height
        preview_container.setStyleSheet("""
            QWidget {
                background-color: black;
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        # Video preview widget
        self.preview_widget = CaptionPreviewWidget()
        self.preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_widget.setMinimumHeight(350)  # Reduced height
        self.preview_widget.setMaximumHeight(450)  # Reduced height
        preview_layout.addWidget(self.preview_widget)
        
        top_layout.addWidget(preview_container)
        
        # Video controls in a horizontal layout
        controls_layout = QHBoxLayout()
        
        # Left side controls
        left_controls = QHBoxLayout()
        self.load_btn = QPushButton("📂 Load Video")
        self.load_btn.setIconSize(QSize(20, 20))
        left_controls.addWidget(self.load_btn)
        
        self.video_label = QLabel("No video loaded")
        self.video_label.setStyleSheet("font-weight: bold;")
        left_controls.addWidget(self.video_label)
        left_controls.addStretch()
        
        # Right side controls
        right_controls = QHBoxLayout()
        self.current_time_label = QLabel("Time: 0.0s")
        right_controls.addWidget(self.current_time_label)
        
        self.duration_label = QLabel("Duration: 0.0s")
        right_controls.addWidget(self.duration_label)
        
        # Combine left and right controls
        controls_layout.addLayout(left_controls)
        controls_layout.addLayout(right_controls)
        top_layout.addLayout(controls_layout)
        
        # Playback controls in a horizontal layout
        playback_layout = QHBoxLayout()
        playback_layout.setSpacing(8)
        
        self.prev_segment_btn = QPushButton("⏮ Previous 5s")
        self.prev_segment_btn.setIconSize(QSize(20, 20))
        playback_layout.addWidget(self.prev_segment_btn)
        
        self.play_segment_btn = QPushButton("▶ Play 5s")
        self.play_segment_btn.setIconSize(QSize(20, 20))
        playback_layout.addWidget(self.play_segment_btn)
        
        self.next_segment_btn = QPushButton("Next 5s ⏭")
        self.next_segment_btn.setIconSize(QSize(20, 20))
        playback_layout.addWidget(self.next_segment_btn)
        
        playback_layout.addStretch()
        
        # Aspect ratio and scaling controls
        self.aspect_ratio_combo = QComboBox()
        self.aspect_ratio_combo.addItems(["Original", "16:9", "9:16", "4:3", "1:1"])
        self.aspect_ratio_combo.setMinimumWidth(100)
        playback_layout.addWidget(QLabel("Aspect Ratio:"))
        playback_layout.addWidget(self.aspect_ratio_combo)
        
        self.scale_mode_combo = QComboBox()
        self.scale_mode_combo.addItems(["Contain", "Cover"])
        self.scale_mode_combo.setMinimumWidth(100)
        playback_layout.addWidget(QLabel("Scale Mode:"))
        playback_layout.addWidget(self.scale_mode_combo)
        
        top_layout.addLayout(playback_layout)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Captions and presets
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(16)
        
        # Create tabs for better organization
        tabs = QTabWidget()
        
        # Caption Input Tab
        caption_tab = QWidget()
        caption_layout = QVBoxLayout(caption_tab)
        caption_layout.setSpacing(16)
        
        # Transcription controls
        transcription_group = QGroupBox("AI Transcription")
        transcription_layout = QVBoxLayout(transcription_group)
        
        # Top row of transcription controls
        transcription_top = QHBoxLayout()
        
        self.auto_transcribe_btn = QPushButton("🧠 Auto-Transcribe")
        transcription_top.addWidget(self.auto_transcribe_btn)
        
        transcription_top.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Hindi (Romanized)", "hi")
        self.language_combo.addItem("Mixed (Hindi+English)", None)
        transcription_top.addWidget(self.language_combo)
        
        transcription_top.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        model_descriptions = self.transcriber.get_model_size_description()
        for model_name in self.transcriber.get_available_models():
            self.model_combo.addItem(model_descriptions[model_name], model_name)
        transcription_top.addWidget(self.model_combo)
        
        self.download_model_btn = QPushButton("Download Model")
        transcription_top.addWidget(self.download_model_btn)
        
        transcription_layout.addLayout(transcription_top)
        
        # GPU status row
        gpu_layout = QHBoxLayout()
        gpu_status_label = QLabel("GPU Status:")
        gpu_layout.addWidget(gpu_status_label)
        
        self.gpu_indicator = QLabel()
        gpu_info = self.transcriber.get_gpu_info()
        hardware_gpu = gpu_info.get("hardware_gpu", {})
        
        if gpu_info["has_gpu"]:
            gpu_name = gpu_info.get("gpu_name", "Unknown")
            self.gpu_indicator.setText(f"GPU Enabled ✓ ({gpu_name})")
            self.gpu_indicator.setStyleSheet("color: green; font-weight: bold;")
        elif hardware_gpu and hardware_gpu.get("hardware_detected", False):
            gpu_name = hardware_gpu.get("gpu_name", "Unknown")
            self.gpu_indicator.setText(f"GPU Detected but Inactive: {gpu_name} ⚠")
            self.gpu_indicator.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.gpu_indicator.setText("CPU Mode (slower) ⚠")
            self.gpu_indicator.setStyleSheet("color: orange;")
        
        gpu_layout.addWidget(self.gpu_indicator)
        
        self.gpu_diagnostics_btn = QPushButton("GPU Diagnostics")
        gpu_layout.addWidget(self.gpu_diagnostics_btn)
        
        if hardware_gpu and hardware_gpu.get("hardware_detected", False) and not gpu_info["has_gpu"]:
            self.force_gpu_btn = QPushButton("Force GPU")
            self.force_gpu_btn.setStyleSheet("background-color: #4CAF50;")
            gpu_layout.addWidget(self.force_gpu_btn)
        
        gpu_layout.addStretch()
        transcription_layout.addLayout(gpu_layout)
        
        # Auto-transcribe checkbox
        self.auto_transcribe_checkbox = QCheckBox("Auto-transcribe next segment")
        transcription_layout.addWidget(self.auto_transcribe_checkbox)
        
        caption_layout.addWidget(transcription_group)
        
        # Caption input
        caption_input_group = QGroupBox("Caption Input")
        caption_input_layout = QVBoxLayout(caption_input_group)
        caption_input_layout.setSpacing(16)  # Add more spacing between elements
        
        # Caption text input
        self.caption_text = QTextEdit()
        self.caption_text.setPlaceholderText("Enter caption text here or use auto-transcribe...")
        self.caption_text.setMinimumHeight(150)  # Increased height
        caption_input_layout.addWidget(self.caption_text)
        
        # Preset selection
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)  # Add spacing between preset elements
        preset_layout.addWidget(QLabel("Style Preset:"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.edit_presets_btn)
        preset_layout.addStretch()
        
        # Action buttons layout
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)  # Add spacing between buttons
        action_layout.addLayout(preset_layout)
        action_layout.addStretch()
        action_layout.addWidget(self.save_caption_btn)
        action_layout.addWidget(self.preview_caption_btn)
        
        # Add action layout to caption input layout
        caption_input_layout.addLayout(action_layout)
        
        caption_layout.addWidget(caption_input_group)
        
        # Captions List Tab
        captions_tab = QWidget()
        captions_layout = QVBoxLayout(captions_tab)
        
        # Captions list with search
        captions_group = QGroupBox("Captions")
        captions_group_layout = QVBoxLayout(captions_group)
        
        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search captions...")
        search_layout.addWidget(search_input)
        captions_group_layout.addLayout(search_layout)
        
        # Captions list
        self.captions_scroll = QScrollArea()
        self.captions_scroll.setWidgetResizable(True)
        self.captions_widget = QWidget()
        self.captions_layout = QVBoxLayout(self.captions_widget)
        self.captions_scroll.setWidget(self.captions_widget)
        captions_group_layout.addWidget(self.captions_scroll)
        
        # Action buttons
        captions_actions = QHBoxLayout()
        self.render_btn = QPushButton("🎥 Render Video")
        captions_actions.addWidget(self.render_btn)
        
        self.save_captions_btn = QPushButton("💾 Save Captions")
        captions_actions.addWidget(self.save_captions_btn)
        
        captions_group_layout.addLayout(captions_actions)
        
        captions_layout.addWidget(captions_group)
        
        # Add tabs
        tabs.addTab(caption_tab, "Caption Input")
        tabs.addTab(captions_tab, "Captions List")
        
        bottom_layout.addWidget(tabs)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set splitter proportions (50% for preview, 50% for controls)
        splitter.setSizes([int(self.height() * 0.5), int(self.height() * 0.5)])
        
        # Connect signals
        self.load_btn.clicked.connect(self.on_load_video)
        self.prev_segment_btn.clicked.connect(self.on_prev_segment)
        self.play_segment_btn.clicked.connect(self.on_play_segment)
        self.next_segment_btn.clicked.connect(self.on_next_segment)
        self.save_caption_btn.clicked.connect(self.on_save_caption)
        self.preview_caption_btn.clicked.connect(self.on_preview_caption)
        self.edit_presets_btn.clicked.connect(self.on_edit_presets)
        self.render_btn.clicked.connect(self.on_render_video)
        self.save_captions_btn.clicked.connect(self.on_save_captions)
        self.auto_transcribe_btn.clicked.connect(self.on_auto_transcribe)
        self.download_model_btn.clicked.connect(self.on_download_model)
        self.gpu_diagnostics_btn.clicked.connect(self.show_gpu_diagnostics)
        self.aspect_ratio_combo.currentTextChanged.connect(self.update_preview)
        self.scale_mode_combo.currentTextChanged.connect(self.update_preview)
        
        # Enable/disable UI elements
        self.update_ui_state()
        
        # Check model status immediately
        self.check_model_status()
        
    def check_model_status(self):
        """Check if the current model is downloaded and update UI"""
        current_model = self.model_combo.currentData()
        self.transcriber.model_size = current_model
        
        model_exists = self.transcriber.check_model()
        self.download_model_btn.setEnabled(not model_exists)
        self.download_model_btn.setText("Download Model" if not model_exists else "Model Downloaded ✓")
        
        # Update auto-transcribe button status
        self.auto_transcribe_btn.setEnabled(self.current_video_path is not None and model_exists)
        
        if not model_exists:
            self.auto_transcribe_btn.setToolTip("You need to download the model first")
        else:
            self.auto_transcribe_btn.setToolTip("Auto-transcribe the current segment")
            
    def on_download_model(self):
        """Download the selected Whisper model"""
        current_model = self.model_combo.currentData()
        
        # Create progress dialog
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Downloading Model")
        progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress_dialog.setMinimumWidth(400)
        
        dialog_layout = QVBoxLayout(progress_dialog)
        
        progress_label = QLabel(f"Downloading {current_model} model...")
        dialog_layout.addWidget(progress_label)
        
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        dialog_layout.addWidget(progress_bar)
        
        details_text = QPlainTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(100)
        details_text.setPlaceholderText("Download details will appear here...")
        dialog_layout.addWidget(details_text)
        
        # Create download thread
        self.download_thread = ModelDownloadThread(self.transcriber, current_model)
        
        # Connect signals
        self.download_thread.progress_signal.connect(
            lambda progress, message: self.update_download_progress(
                progress, message, progress_bar, details_text, progress_label
            )
        )
        
        self.download_thread.finished_signal.connect(
            lambda success, message: self.on_download_finished(
                success, message, progress_dialog
            )
        )
        
        # Start download
        self.download_thread.start()
        
        # Show dialog
        progress_dialog.exec()
        
    def update_download_progress(self, progress, message, progress_bar, details_text, label):
        """Update download progress UI"""
        if progress >= 0:
            progress_bar.setValue(progress)
            label.setText(f"Downloading: {progress}% complete")
        
        details_text.appendPlainText(message)
        details_text.ensureCursorVisible()
        
    def on_download_finished(self, success, message, dialog):
        """Handle download completion"""
        dialog.accept()
        
        if success:
            QMessageBox.information(self, "Download Complete", 
                                   "Model downloaded successfully!")
            # Update UI state
            self.check_model_status()
        else:
            QMessageBox.critical(self, "Download Error", 
                                f"Failed to download model: {message}")
        
    def update_ui_state(self):
        """Update enabled/disabled state of UI elements based on app state"""
        has_video = self.current_video_path is not None
        has_caption = len(self.caption_text.toPlainText()) > 0
        has_captions = len(self.captions) > 0
        
        # Double-check if audio is actually playing (belt and suspenders approach)
        currently_playing = getattr(self, 'is_segment_playing', False)
        if currently_playing and hasattr(self.audio_player, 'is_playing'):
            # Override our state if the player says it's not playing
            if not self.audio_player.is_playing():
                self.is_segment_playing = False
                currently_playing = False
        
        # Handle navigation buttons based on playback status
        if currently_playing:
            # Disable navigation during playback
            self.prev_segment_btn.setEnabled(False)
            self.next_segment_btn.setEnabled(False)
            self.play_segment_btn.setEnabled(False)
        else:
            # Normal state when not playing
            self.play_segment_btn.setEnabled(has_video)
            self.prev_segment_btn.setEnabled(has_video and self.current_time > 0)
            self.next_segment_btn.setEnabled(has_video and self.current_time + self.segment_duration < self.video_duration)
        
        # Model needs to be checked separately since it might not be downloaded
        current_model = self.model_combo.currentData()
        self.transcriber.model_size = current_model
        model_exists = self.transcriber.check_model()
        self.auto_transcribe_btn.setEnabled(has_video and model_exists and not currently_playing)
        
        # Disable caption editing during playback
        caption_edit_enabled = has_video and not currently_playing
        self.save_caption_btn.setEnabled(caption_edit_enabled and has_caption)
        self.preview_caption_btn.setEnabled(caption_edit_enabled and has_caption)
        self.caption_text.setEnabled(caption_edit_enabled)
        
        # Always enable these buttons
        self.render_btn.setEnabled(has_video and has_captions)
        self.save_captions_btn.setEnabled(has_captions)
        
    def update_preset_combo(self):
        """Update the preset combo box with current presets"""
        self.preset_combo.clear()
        for preset_id in self.preset_manager.get_preset_list():
            self.preset_combo.addItem(preset_id)
            
    def update_captions_list(self):
        """Update the captions list widget"""
        # Clear the current list
        for i in reversed(range(self.captions_layout.count())):
            widget = self.captions_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
                
        # Add each caption as a widget
        for i, caption in enumerate(self.captions):
            caption_widget = QWidget()
            layout = QHBoxLayout(caption_widget)
            
            time_label = QLabel(f"{caption['start']:.1f}s - {caption['end']:.1f}s")
            layout.addWidget(time_label)
            
            text_label = QLabel(caption['text'])
            text_label.setStyleSheet(f"font-weight: bold;")
            layout.addWidget(text_label)
            
            preset_label = QLabel(f"[{caption['preset']}]")
            layout.addWidget(preset_label)
            
            # Add language label if available
            if 'language' in caption:
                lang_label = QLabel(f"({caption['language']})")
                if caption.get('auto_generated', False):
                    lang_label.setStyleSheet("color: #0066CC;")  # Blue for AI-generated
                layout.addWidget(lang_label)
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, idx=i: self.on_edit_caption(idx))
            layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, idx=i: self.on_delete_caption(idx))
            layout.addWidget(delete_btn)
            
            self.captions_layout.addWidget(caption_widget)
        
        self.update_ui_state()
        
    def on_load_video(self):
        """Handler for loading video file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.mov *.mkv *.avi)"
        )
        
        if not file_path:
            return
            
        try:
            # Get video info
            video_info = self.ffmpeg.get_video_info(file_path)
            self.video_duration = video_info["duration"]
            
            # Extract audio
            audio_path = self.ffmpeg.extract_audio(file_path)
            
            # Set current state
            self.current_video_path = file_path
            self.current_audio_path = audio_path
            self.current_time = 0.0
            
            # Load audio into player
            self.audio_player.load_audio(audio_path)
            
            # Update preview
            self.update_preview()
            
            # Update UI
            self.video_label.setText(os.path.basename(file_path))
            self.duration_label.setText(f"Duration: {self.video_duration:.1f}s")
            self.update_ui_state()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load video: {str(e)}")
            
    def update_preview(self):
        """Update the video preview frame"""
        if not self.current_video_path:
            return
            
        try:
            # Extract current frame
            frame_path = self.ffmpeg.extract_frame(
                self.current_video_path, self.current_time
            )
            
            # Update preview widget
            self.preview_widget.set_frame(frame_path)
            
            # Update preview caption if there's one at the current time
            current_caption = self.get_caption_at_time(self.current_time)
            if current_caption:
                preset = self.preset_manager.get_preset(current_caption["preset"])
                if preset:
                    language = current_caption.get("language", None)
                    self.preview_widget.set_caption(current_caption["text"], preset, language)
            else:
                self.preview_widget.clear_caption()
                
            # Update time label
            self.current_time_label.setText(f"Time: {self.current_time:.1f}s")
            
        except Exception as e:
            print(f"Error updating preview: {e}")
            
    def on_play_segment(self):
        """Play the current 5-second segment"""
        if not self.current_audio_path:
            return
            
        try:
            self.is_segment_playing = True
            self.audio_player.play_segment(self.current_time, self.segment_duration)
            self.update_ui_state()
        except Exception as e:
            self.is_segment_playing = False
            QMessageBox.warning(self, "Playback Error", str(e))
            
    def on_prev_segment(self):
        """Go to previous segment"""
        # Don't allow navigation while a segment is playing
        if getattr(self, 'is_segment_playing', False):
            return
            
        # Don't allow navigation if the timer is active
        if hasattr(self, 'navigation_timer') and self.navigation_timer.isActive():
            return
            
        if self.current_time > 0:
            self.current_time = max(0, self.current_time - self.segment_duration)
            self.update_preview()
            self.update_ui_state()
            
            # Start the cooldown timer to prevent rapid clicking
            if hasattr(self, 'navigation_timer'):
                self.navigation_timer.start(1000)  # 1 second cooldown
            
    def on_next_segment(self):
        """Go to next segment and save the current caption if any"""
        # Don't allow navigation while a segment is playing
        if getattr(self, 'is_segment_playing', False):
            return
            
        # Don't allow navigation if the timer is active
        if hasattr(self, 'navigation_timer') and self.navigation_timer.isActive():
            return
            
        # Save current caption if there's text
        text = self.caption_text.toPlainText().strip()
        if text and self.current_video_path:
            preset_id = self.preset_combo.currentText()
            if preset_id:
                language = self.language_combo.currentData()
                language_name = self.language_combo.currentText()
                
                # Create caption object
                caption = {
                    "start": self.current_time,
                    "end": min(self.current_time + self.segment_duration, self.video_duration),
                    "text": text,
                    "preset": preset_id,
                    "language": language_name,
                    "auto_generated": self.auto_transcribe_next
                }
                
                # Check if we're editing an existing caption at this time
                existing_idx = self.get_caption_index_at_time(self.current_time)
                if existing_idx is not None:
                    self.captions[existing_idx] = caption
                else:
                    self.captions.append(caption)
                    
                # Sort captions by start time
                self.captions.sort(key=lambda x: x["start"])
                
                # Update UI
                self.update_captions_list()
                
                # Save captions to file
                self.save_captions()
            
        # Clear caption text for the next segment
        self.caption_text.clear()
        
        # Go to next segment
        next_time = self.current_time + self.segment_duration
        if next_time < self.video_duration:
            self.current_time = next_time
            self.update_preview()
            self.update_ui_state()
            
            # Auto-play the next segment
            if self.current_audio_path:
                self.on_play_segment()
                
                # Auto-transcribe if enabled
                if self.auto_transcribe_next:
                    QTimer.singleShot(500, self.on_auto_transcribe)
            
            # Start the cooldown timer to prevent rapid clicking
            if hasattr(self, 'navigation_timer'):
                self.navigation_timer.start(1000)  # 1 second cooldown
            
    def keyPressEvent(self, event):
        """Handle global keyboard shortcuts"""
        # Spacebar to go to next segment
        if event.key() == Qt.Key.Key_Space:
            self.on_next_segment()
        else:
            # Pass other keys to parent class
            super().keyPressEvent(event)
            
    def on_save_caption(self):
        """Save the current caption"""
        text = self.caption_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter caption text")
            return
            
        preset_id = self.preset_combo.currentText()
        if not preset_id:
            QMessageBox.warning(self, "Warning", "Please select a preset")
            return
        
        language = self.language_combo.currentData()
        language_name = self.language_combo.currentText()
            
        # Create caption object
        caption = {
            "start": self.current_time,
            "end": min(self.current_time + self.segment_duration, self.video_duration),
            "text": text,
            "preset": preset_id,
            "language": language_name,
            "auto_generated": False
        }
        
        # Check if we're editing an existing caption at this time
        existing_idx = self.get_caption_index_at_time(self.current_time)
        if existing_idx is not None:
            self.captions[existing_idx] = caption
        else:
            self.captions.append(caption)
            
        # Sort captions by start time
        self.captions.sort(key=lambda x: x["start"])
        
        # Update UI
        self.update_captions_list()
        self.update_preview()
        self.caption_text.clear()
        
        # Save captions to file
        self.save_captions()
        
    def on_preview_caption(self):
        """Preview the current caption"""
        text = self.caption_text.toPlainText().strip()
        if not text:
            return
            
        preset_id = self.preset_combo.currentText()
        if not preset_id:
            return
            
        preset = self.preset_manager.get_preset(preset_id)
        if preset:
            language_name = self.language_combo.currentText()
            self.preview_widget.set_caption(text, preset, language_name)
            
    def get_caption_at_time(self, time):
        """Get caption at the specified time, if any"""
        for caption in self.captions:
            if caption["start"] <= time < caption["end"]:
                return caption
        return None
        
    def get_caption_index_at_time(self, time):
        """Get index of caption at the specified time, if any"""
        for i, caption in enumerate(self.captions):
            if caption["start"] <= time < caption["end"]:
                return i
        return None
        
    def on_edit_caption(self, index):
        """Edit a caption from the list"""
        if index < 0 or index >= len(self.captions):
            return
            
        caption = self.captions[index]
        
        # Set current time to caption start
        self.current_time = caption["start"]
        
        # Set text and preset
        self.caption_text.setText(caption["text"])
        preset_index = self.preset_combo.findText(caption["preset"])
        if preset_index >= 0:
            self.preset_combo.setCurrentIndex(preset_index)
            
        # Update preview
        self.update_preview()
        self.update_ui_state()
        
    def on_delete_caption(self, index):
        """Delete a caption from the list"""
        if index < 0 or index >= len(self.captions):
            return
            
        # Ask for confirmation
        result = QMessageBox.question(
            self, "Confirm Deletion", 
            "Are you sure you want to delete this caption?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            del self.captions[index]
            self.update_captions_list()
            self.update_preview()
            self.save_captions()
            
    def on_playback_finished(self):
        """Handle when audio playback finished"""
        # Production mode - no debug prints
        self.is_segment_playing = False
        self.update_ui_state()
            
    def open_folder_in_explorer(self, path):
        """Open a folder in Windows Explorer"""
        try:
            folder_path = os.path.dirname(path) if os.path.isfile(path) else path
            if os.path.exists(folder_path):
                subprocess.Popen(['explorer', folder_path])
            else:
                # In production, show a user-friendly message instead of console warning
                QMessageBox.warning(self, "Warning", f"The folder does not exist:\n{folder_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder: {e}")
            
    def on_edit_presets(self):
        """Open the preset editor dialog"""
        dialog = PresetEditorDialog(self.preset_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Refresh presets
            self.update_preset_combo()
            
    def on_render_video(self):
        """Render the final video with captions"""
        if not self.current_video_path or not self.captions:
            return
            
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Captioned Video", "", "MP4 Files (*.mp4)"
        )
        
        if not output_path:
            return
            
        try:
            # Create and show render progress dialog
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Rendering Video")
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.setMinimumWidth(500)
            
            dialog_layout = QVBoxLayout(progress_dialog)
            
            # Add progress info
            progress_label = QLabel("Rendering video with captions...")
            dialog_layout.addWidget(progress_label)
            
            # Add progress bar
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(0)
            dialog_layout.addWidget(progress_bar)
            
            # Add details text area
            details_text = QPlainTextEdit()
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            details_text.setPlaceholderText("Rendering details will appear here...")
            dialog_layout.addWidget(details_text)
            
            progress_dialog.show()
            QApplication.processEvents()
            
            # Progress callback function
            def progress_callback(progress, info):
                if progress >= 0:
                    progress_bar.setValue(progress)
                    progress_label.setText(f"Rendering... {progress}% complete")
                if info:
                    details_text.appendPlainText(info.strip())
                QApplication.processEvents()
            
            # Get aspect ratio and scale mode
            aspect_ratio = None
            if self.aspect_ratio_combo.currentText() != "Original":
                aspect_ratio = self.aspect_ratio_combo.currentText()
            
            scale_mode = self.scale_mode_combo.currentText().lower()
            
            # Render the video with progress reporting
            self.ffmpeg.render_final_video(
                self.current_video_path, 
                self.captions, 
                self.preset_manager.presets,
                output_path,
                progress_callback,
                aspect_ratio,
                scale_mode,
                preset_manager=self.preset_manager
            )
            
            progress_dialog.close()
            
            # Create success dialog with open folder button
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle("Render Complete")
            success_dialog.setMinimumWidth(400)
            
            dialog_layout = QVBoxLayout(success_dialog)
            
            success_label = QLabel(f"Video rendered successfully to:\n{output_path}")
            success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            success_label.setWordWrap(True)
            dialog_layout.addWidget(success_label)
            
            button_layout = QHBoxLayout()
            
            open_folder_btn = QPushButton("📂 Open Folder")
            open_folder_btn.clicked.connect(lambda: self.open_folder_in_explorer(output_path))
            
            ok_btn = QPushButton("✓ OK")
            ok_btn.clicked.connect(success_dialog.accept)
            
            button_layout.addWidget(open_folder_btn)
            button_layout.addWidget(ok_btn)
            
            dialog_layout.addLayout(button_layout)
            
            success_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Render Error", str(e))
            
    def on_save_captions(self):
        """Save captions to a JSON file (export)"""
        if not self.captions:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Captions", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w') as f:
                json.dump(self.captions, f, indent=2)
                
            QMessageBox.information(
                self, "Success", 
                f"Captions saved to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))
            
    def save_captions(self):
        """Save captions to the default file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
            
            with open(self.captions_file, 'w') as f:
                json.dump(self.captions, f, indent=2)
                
        except Exception as e:
            print(f"Error saving captions: {e}")
            
    def load_captions(self):
        """Load captions from the default file if it exists"""
        if not os.path.exists(self.captions_file):
            return
            
        try:
            with open(self.captions_file, 'r') as f:
                self.captions = json.load(f)
                
            self.update_captions_list()
            
        except Exception as e:
            print(f"Error loading captions: {e}")
            # If there's an error, ensure we have an empty captions array
            self.captions = []
            
    def closeEvent(self, event):
        """Handle window close event"""
        # Save captions before closing
        self.save_captions()
        
        # Clean up temporary files
        self.audio_player.cleanup()
        
        event.accept()
        
    def reset_captions_file(self):
        """Reset the captions file by deleting it or creating an empty one"""
        if self.captions_file is None:
            # Default captions file path
            base_dir = Path(__file__).parent.parent
            self.captions_file = base_dir / "data" / "captions.json"
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
            
        try:
            # Write an empty array to the file
            with open(self.captions_file, 'w') as f:
                json.dump([], f)
                
            # Reset captions in memory
            self.captions = []
                
        except Exception as e:
            print(f"Error resetting captions file: {e}")
            
    def on_auto_transcribe(self):
        """Automatically transcribe the current segment"""
        if not self.current_audio_path:
            QMessageBox.warning(self, "Warning", "No audio loaded")
            return
            
        # Check if model is downloaded
        current_model = self.model_combo.currentData()
        self.transcriber.model_size = current_model
        
        if not self.transcriber.check_model():
            result = QMessageBox.question(
                self, "Model Not Downloaded", 
                f"The {current_model} model needs to be downloaded first. Download now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                self.on_download_model()
            return
            
        try:
            # Get selected language
            language = self.language_combo.currentData()
            language_name = self.language_combo.currentText()
            mixed_language = language is None or language == 'hi'
            
            # Create progress dialog
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Transcribing Audio")
            progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            progress_dialog.setMinimumWidth(400)
            dialog_layout = QVBoxLayout(progress_dialog)
            
            # Add language mode information
            if language == 'hi':
                lang_info = QLabel("🇮🇳 Hindi Mode - Transcribing to Roman script")
                lang_info.setStyleSheet("font-weight: bold; color: #FF5722;")
                dialog_layout.addWidget(lang_info)
            elif language is None:
                lang_info = QLabel("🔄 Mixed Hindi-English Mode - Transcribing Hindi to Roman script")
                lang_info.setStyleSheet("font-weight: bold; color: #3F51B5;")
                dialog_layout.addWidget(lang_info)
            
            progress_label = QLabel(f"Transcribing audio segment in {language_name} mode...")
            dialog_layout.addWidget(progress_label)
            
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(0)
            progress_bar.setFormat("Processing... %p%")
            dialog_layout.addWidget(progress_bar)
            
            details_text = QPlainTextEdit()
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(100)
            details_text.setPlaceholderText("Transcription details will appear here...")
            dialog_layout.addWidget(details_text)
            
            # Create transcription thread
            self.transcription_thread = TranscriptionThread(
                self.transcriber,
                self.current_audio_path,
                self.current_time,
                self.segment_duration,
                language,
                mixed_language
            )
            
            # Connect signals
            self.transcription_thread.progress_signal.connect(
                lambda progress, message: self.update_transcription_progress(
                    progress, message, progress_bar, details_text, progress_label
                )
            )
            
            self.transcription_thread.finished_signal.connect(
                lambda result, message: self.on_transcription_finished(
                    result, message, progress_dialog
                )
            )
            
            # Start transcription
            self.transcription_thread.start()
            
            # Show dialog
            progress_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Transcription Error", str(e))
    
    def update_transcription_progress(self, progress, message, progress_bar, details_text, label):
        """Update transcription progress UI"""
        if progress >= 0:
            progress_bar.setValue(progress)
        
        details_text.appendPlainText(message)
        details_text.ensureCursorVisible()
        
    def on_transcription_finished(self, result, message, dialog):
        """Handle transcription completion"""
        dialog.accept()
        
        if not result:
            QMessageBox.critical(self, "Transcription Error", message)
            return
            
        # Clear existing text
        self.caption_text.clear()
        
        # Format the text - highlight low confidence parts
        cursor = self.caption_text.textCursor()
        format_default = QTextCharFormat()
        format_low_confidence = QTextCharFormat()
        format_low_confidence.setBackground(QColor(255, 165, 0))  # Orange background
        
        # Insert each segment with appropriate formatting
        for segment in result["segments"]:
            text = segment["text"].strip()
            if "<low_confidence>" in segment.get("marked_text", ""):
                cursor.insertText(text, format_low_confidence)
            else:
                cursor.insertText(text, format_default)
            cursor.insertText(" ")
        
        # Update UI
        self.update_ui_state()
    
    def toggle_auto_transcribe(self, state):
        """Toggle auto-transcribe mode"""
        self.auto_transcribe_next = (state == Qt.CheckState.Checked.value)
        
    def show_gpu_diagnostics(self):
        """Show GPU diagnostics dialog"""
        gpu_info = self.transcriber.get_gpu_info()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("GPU Diagnostics")
        dialog.setMinimumWidth(500)
        dialog_layout = QVBoxLayout(dialog)
        
        # GPU Status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("GPU Status:"))
        
        status_value = "Active ✓" if gpu_info["has_gpu"] else "Inactive ✗"
        status_color = "green" if gpu_info["has_gpu"] else "red"
        status_label = QLabel(status_value)
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        dialog_layout.addLayout(status_layout)
        
        # Hardware Detection
        hardware_gpu = gpu_info.get("hardware_gpu", {})
        if hardware_gpu and hardware_gpu.get("hardware_detected", False):
            # GPU hardware is detected, but not being used!
            if not gpu_info["has_gpu"]:
                hardware_msg = QLabel(f"⚠️ NVIDIA GPU detected but not being used: {hardware_gpu.get('gpu_name', 'Unknown')}")
                hardware_msg.setStyleSheet("color: orange; font-weight: bold;")
                dialog_layout.addWidget(hardware_msg)
                
                # Add Force GPU Mode button - prominent placement
                force_gpu_btn = QPushButton("⚡ FORCE GPU MODE (Recommended) ⚡")
                force_gpu_btn.setMinimumHeight(40)
                force_gpu_btn.setStyleSheet(
                    "background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px;"
                )
                force_gpu_btn.clicked.connect(self.force_gpu_mode)
                dialog_layout.addWidget(force_gpu_btn)
            else:
                hardware_msg = QLabel(f"✅ Using detected GPU: {hardware_gpu.get('gpu_name', 'Unknown')}")
                hardware_msg.setStyleSheet("color: green;")
                dialog_layout.addWidget(hardware_msg)
        
        # Show detailed info in a text view
        details = QPlainTextEdit()
        details.setReadOnly(True)
        details.setMinimumHeight(300)
        
        # Format GPU info
        details_text = "===== GPU DIAGNOSTIC INFORMATION =====\n\n"
        
        if gpu_info["has_gpu"]:
            details_text += f"✅ GPU ACTIVE: {gpu_info.get('gpu_name', 'Unknown')}\n"
            details_text += f"CUDA Version: {gpu_info.get('cuda_version', 'Unknown')}\n"
            details_text += f"Device: {gpu_info.get('device', 'Unknown')}\n"
            details_text += f"Device Count: {gpu_info.get('device_count', 0)}\n"
        else:
            details_text += "❌ GPU NOT ACTIVE\n"
            details_text += f"Reason: {gpu_info.get('reason', 'Unknown')}\n"
            details_text += f"CUDA Available: {gpu_info.get('cuda_available', False)}\n"
            details_text += f"Device Count: {gpu_info.get('device_count', 0)}\n"
        
        # Add hardware GPU info section
        details_text += "\n===== HARDWARE GPU DETECTION =====\n\n"
        if hardware_gpu and hardware_gpu.get("hardware_detected", False):
            details_text += f"✅ HARDWARE GPU DETECTED: {hardware_gpu.get('gpu_name', 'Unknown')}\n"
            details_text += f"Driver Version: {hardware_gpu.get('driver_version', 'Unknown')}\n"
            details_text += f"VRAM: {hardware_gpu.get('vram_total', 'Unknown')}\n"
            details_text += f"Detection Method: {hardware_gpu.get('detection_method', 'Unknown')}\n"
        else:
            details_text += "❌ NO HARDWARE GPU DETECTED\n"
            
        details_text += "\n===== PyTorch INFORMATION =====\n\n"
        details_text += f"PyTorch Version: {torch.__version__}\n"
        details_text += f"CUDA Available: {torch.cuda.is_available()}\n"
        if torch.cuda.is_available():
            details_text += f"CUDA Version: {torch.version.cuda}\n"
            details_text += f"Device Count: {torch.cuda.device_count()}\n"
            details_text += f"Current Device: {torch.cuda.current_device()}\n"
            try:
                details_text += f"Device Name: {torch.cuda.get_device_name(0)}\n"
                details_text += f"Device Properties:\n"
                prop = torch.cuda.get_device_properties(0)
                details_text += f"  Name: {prop.name}\n"
                details_text += f"  Compute Capability: {prop.major}.{prop.minor}\n"
                details_text += f"  Total Memory: {prop.total_memory / 1024 / 1024 / 1024:.2f} GB\n"
            except Exception as e:
                details_text += f"Error getting device info: {str(e)}\n"
        
        # Add a section about possible issues and solutions
        details_text += "\n===== TROUBLESHOOTING =====\n\n"
        if not gpu_info["has_gpu"]:
            details_text += "Possible issues:\n"
            details_text += "1. CUDA drivers not installed or outdated\n"
            details_text += "2. PyTorch installed without CUDA support\n"
            details_text += "3. GPU is being used by another application\n"
            details_text += "4. Insufficient GPU memory\n"
            details_text += "\nPossible solutions:\n"
            details_text += "1. Update NVIDIA drivers\n"
            details_text += "2. Reinstall PyTorch with CUDA support:\n"
            details_text += "   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118\n"
            details_text += "3. Close other GPU-intensive applications\n"
            details_text += "4. Try a smaller Whisper model (tiny or base)\n"
            details_text += "5. Try forcing GPU mode with the button above\n"
        
        details.setPlainText(details_text)
        dialog_layout.addWidget(details)
        
        # Add buttons row
        buttons_layout = QHBoxLayout()
        
        # Add copy to clipboard button
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(details_text))
        buttons_layout.addWidget(copy_btn)
        
        # Add manual CUDA test button
        test_btn = QPushButton("Force GPU Test (Reload)")
        test_btn.clicked.connect(self.force_gpu_test)
        buttons_layout.addWidget(test_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(close_btn)
        
        dialog_layout.addLayout(buttons_layout)
        
        dialog.exec()
        
    def force_gpu_mode(self):
        """Force GPU mode by setting environment variable"""
        try:
            success = self.transcriber.force_gpu_mode()
            
            if success:
                QMessageBox.information(
                    self, "GPU Mode Forced", 
                    "Successfully forced GPU mode! The application will now use your GPU for transcription.\n\n"
                    "Note: Please restart the application if you experience any issues."
                )
                
                # Update the GPU indicator
                gpu_info = self.transcriber.get_gpu_info()
                hardware_gpu = gpu_info.get("hardware_gpu", {})
                gpu_name = hardware_gpu.get("gpu_name", "Unknown")
                self.gpu_indicator.setText(f"GPU Enabled ✓ ({gpu_name})")
                self.gpu_indicator.setStyleSheet("color: green; font-weight: bold;")
                
                # Show the diagnostics again with updated info
                self.show_gpu_diagnostics()
            else:
                QMessageBox.warning(
                    self, "Force GPU Failed", 
                    "Failed to force GPU mode. See the diagnostics for more information."
                )
        except Exception as e:
            QMessageBox.critical(self, "Force GPU Error", str(e))
        
    def force_gpu_test(self):
        """Force a GPU test by reinitializing the transcriber"""
        try:
            # Reinitialize the transcriber object
            current_model = self.model_combo.currentData()
            self.transcriber = WhisperTranscriber(model_size=current_model)
            
            # Show the diagnostics again with updated info
            self.show_gpu_diagnostics()
            
            # Update the GPU indicator
            gpu_info = self.transcriber.get_gpu_info()
            if self.transcriber.has_gpu:
                gpu_name = gpu_info.get("gpu_name", "Unknown")
                cuda_version = gpu_info.get("cuda_version", "Unknown")
                self.gpu_indicator.setText(f"GPU Enabled ✓ ({gpu_name})")
                self.gpu_indicator.setStyleSheet("color: green; font-weight: bold;")
            else:
                reason = gpu_info.get("reason", "Unknown reason")
                self.gpu_indicator.setText(f"CPU Mode (slower) ⚠")
                self.gpu_indicator.setStyleSheet("color: orange;")
                
        except Exception as e:
            QMessageBox.critical(self, "GPU Test Error", str(e))

    def on_language_changed(self):
        """Handle language change event"""
        current_lang = self.language_combo.currentData()
        lang_name = self.language_combo.currentText()
        
        # If the language is set to Hindi or Mixed, show a tooltip about Romanization
        if current_lang == 'hi' or current_lang is None:
            # Create a temporary status message
            temp_label = QLabel(f"Language mode: {lang_name} - Hindi will be transcribed in Roman script")
            
            # Create a non-modal dialog that auto-dismisses
            info_dialog = QDialog(self)
            info_dialog.setWindowTitle("Language Mode Changed")
            layout = QVBoxLayout(info_dialog)
            
            # Add an icon or flag
            if current_lang == 'hi':
                msg = "Hindi mode selected. All speech will be transcribed in Roman script (not Devanagari)."
                icon = "🇮🇳"  # India flag
            else:  # Mixed mode
                msg = "Mixed Hindi-English mode selected. Speech will be auto-detected, and Hindi will be transcribed in Roman script."
                icon = "🔄"  # Auto-detect symbol
                
            layout.addWidget(QLabel(f"{icon} {msg}"))
            
            # Add OK button
            ok_btn = QPushButton("OK")
            ok_btn.clicked.connect(info_dialog.accept)
            layout.addWidget(ok_btn)
            
            # Show non-modal dialog that won't block the UI
            info_dialog.setModal(False)
            info_dialog.show()
            
            # Auto-dismiss after 5 seconds
            QTimer.singleShot(5000, info_dialog.accept) 