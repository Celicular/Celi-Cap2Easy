import os
import sys
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout,                             QHBoxLayout, QPushButton, QLabel, QFileDialog,                             QTextEdit, QComboBox, QSpinBox, QLineEdit,                             QScrollArea, QGroupBox, QTabWidget, QDialog,                             QColorDialog, QMessageBox, QSplitter, QProgressBar,                            QPlainTextEdit)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QColor, QPalette, QFont

# Import our custom utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.ffmpeg import FFmpegHandler
from utils.audio_player import AudioPlayer
from utils.preset_manager import PresetManager
from gui.preset_editor import PresetEditorDialog
from gui.caption_preview import CaptionPreviewWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize utilities
        self.ffmpeg = FFmpegHandler()
        self.audio_player = AudioPlayer()
        self.preset_manager = PresetManager()
        
        # Initialize app state
        self.current_video_path = None
        self.current_audio_path = None
        self.current_time = 0.0
        self.segment_duration = 5.0
        self.video_duration = 0.0
        self.captions = []
        self.captions_file = None
        
        # Set up UI
        self.init_ui()
        
        # Load captions if exist
        self.load_captions()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Video Captioning Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for top and bottom sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Video and controls
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Video toolbar
        video_toolbar = QHBoxLayout()
        self.load_btn = QPushButton("Load Video")
        self.load_btn.clicked.connect(self.on_load_video)
        video_toolbar.addWidget(self.load_btn)
        
        self.video_label = QLabel("No video loaded")
        video_toolbar.addWidget(self.video_label)
        
        self.current_time_label = QLabel("Time: 0.0s")
        video_toolbar.addWidget(self.current_time_label)
        
        self.duration_label = QLabel("Duration: 0.0s")
        video_toolbar.addWidget(self.duration_label)
        
        top_layout.addLayout(video_toolbar)
        
        # Video preview area
        self.preview_widget = CaptionPreviewWidget()
        top_layout.addWidget(self.preview_widget)
        
        # Playback controls
        playback_layout = QHBoxLayout()
        
        self.prev_segment_btn = QPushButton("◀ Previous 5s")
        self.prev_segment_btn.clicked.connect(self.on_prev_segment)
        playback_layout.addWidget(self.prev_segment_btn)
        
        self.play_segment_btn = QPushButton("▶ Play 5s")
        self.play_segment_btn.clicked.connect(self.on_play_segment)
        playback_layout.addWidget(self.play_segment_btn)
        
        self.next_segment_btn = QPushButton("Next 5s ▶")
        self.next_segment_btn.clicked.connect(self.on_next_segment)
        playback_layout.addWidget(self.next_segment_btn)
        
        top_layout.addLayout(playback_layout)
        
        # Add top widget to splitter
        splitter.addWidget(top_widget)
        
        # Bottom section - Captions and presets
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Caption input
        caption_group = QGroupBox("Caption Input")
        caption_layout = QVBoxLayout(caption_group)
        
        self.caption_text = QTextEdit()
        self.caption_text.setPlaceholderText("Enter caption text here...")
        caption_layout.addWidget(self.caption_text)
        
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Style Preset:"))
        
        self.preset_combo = QComboBox()
        self.update_preset_combo()
        preset_layout.addWidget(self.preset_combo)
        
        self.edit_presets_btn = QPushButton("Edit Presets")
        self.edit_presets_btn.clicked.connect(self.on_edit_presets)
        preset_layout.addWidget(self.edit_presets_btn)
        
        caption_layout.addLayout(preset_layout)
        
        save_layout = QHBoxLayout()
        self.save_caption_btn = QPushButton("Save Caption")
        self.save_caption_btn.clicked.connect(self.on_save_caption)
        save_layout.addWidget(self.save_caption_btn)
        
        self.preview_caption_btn = QPushButton("Preview Caption")
        self.preview_caption_btn.clicked.connect(self.on_preview_caption)
        save_layout.addWidget(self.preview_caption_btn)
        
        caption_layout.addLayout(save_layout)
        
        bottom_layout.addWidget(caption_group)
        
        # Captions list
        captions_group = QGroupBox("Captions")
        captions_layout = QVBoxLayout(captions_group)
        
        # Add caption list here
        self.captions_scroll = QScrollArea()
        self.captions_scroll.setWidgetResizable(True)
        self.captions_widget = QWidget()
        self.captions_layout = QVBoxLayout(self.captions_widget)
        self.captions_scroll.setWidget(self.captions_widget)
        captions_layout.addWidget(self.captions_scroll)
        
        # Render button
        render_layout = QHBoxLayout()
        
        self.render_btn = QPushButton("Render Video with Captions")
        self.render_btn.clicked.connect(self.on_render_video)
        render_layout.addWidget(self.render_btn)
        
        self.save_captions_btn = QPushButton("Save Captions to File")
        self.save_captions_btn.clicked.connect(self.on_save_captions)
        render_layout.addWidget(self.save_captions_btn)
        
        captions_layout.addLayout(render_layout)
        
        bottom_layout.addWidget(captions_group)
        
        # Add bottom widget to splitter
        splitter.addWidget(bottom_widget)
        
        # Set splitter proportions
        splitter.setSizes([int(self.height() * 0.6), int(self.height() * 0.4)])
        
        # Enable/disable UI elements
        self.update_ui_state()
        
    def update_ui_state(self):
        """Update enabled/disabled state of UI elements based on app state"""
        has_video = self.current_video_path is not None
        has_caption = len(self.caption_text.toPlainText()) > 0
        has_captions = len(self.captions) > 0
        
        self.play_segment_btn.setEnabled(has_video)
        self.prev_segment_btn.setEnabled(has_video and self.current_time > 0)
        self.next_segment_btn.setEnabled(has_video and self.current_time + self.segment_duration < self.video_duration)
        
        self.save_caption_btn.setEnabled(has_video and has_caption)
        self.preview_caption_btn.setEnabled(has_video and has_caption)
        
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
                    self.preview_widget.set_caption(current_caption["text"], preset)
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
            self.audio_player.play_segment(self.current_time, self.segment_duration)
        except Exception as e:
            QMessageBox.warning(self, "Playback Error", str(e))
            
    def on_prev_segment(self):
        """Go to previous segment"""
        if self.current_time > 0:
            self.current_time = max(0, self.current_time - self.segment_duration)
            self.update_preview()
            self.update_ui_state()
            
    def on_next_segment(self):
        """Go to next segment and save the current caption if any"""
        # Save current caption if there's text
        text = self.caption_text.toPlainText().strip()
        if text and self.current_video_path:
            preset_id = self.preset_combo.currentText()
            if preset_id:
                # Create caption object
                caption = {
                    "start": self.current_time,
                    "end": min(self.current_time + self.segment_duration, self.video_duration),
                    "text": text,
                    "preset": preset_id
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
                self.audio_player.play_segment(self.current_time, self.segment_duration)
                
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
            
        # Create caption object
        caption = {
            "start": self.current_time,
            "end": min(self.current_time + self.segment_duration, self.video_duration),
            "text": text,
            "preset": preset_id
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
            self.preview_widget.set_caption(text, preset)
            
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
            
            # Render the video with progress reporting
            self.ffmpeg.render_final_video(
                self.current_video_path, 
                self.captions, 
                self.preset_manager.presets,
                output_path,
                progress_callback
            )
            
            progress_dialog.close()
            
            QMessageBox.information(
                self, "Success", 
                f"Video rendered successfully to:\n{output_path}"
            )
            
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
            
    def load_captions(self):
        """Load captions from the default file if it exists"""
        if self.captions_file is None:
            # Default captions file path
            base_dir = Path(__file__).parent.parent
            self.captions_file = base_dir / "data" / "captions.json"
            
        if not os.path.exists(self.captions_file):
            return
            
        try:
            with open(self.captions_file, 'r') as f:
                self.captions = json.load(f)
                
            self.update_captions_list()
            
        except Exception as e:
            print(f"Error loading captions: {e}")
            
    def save_captions(self):
        """Save captions to the default file"""
        if self.captions_file is None:
            # Default captions file path
            base_dir = Path(__file__).parent.parent
            self.captions_file = base_dir / "data" / "captions.json"
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.captions_file), exist_ok=True)
            
            with open(self.captions_file, 'w') as f:
                json.dump(self.captions, f, indent=2)
                
        except Exception as e:
            print(f"Error saving captions: {e}")
            
    def closeEvent(self, event):
        """Handle window close event"""
        # Save captions before closing
        self.save_captions()
        
        # Clean up temporary files
        self.audio_player.cleanup()
        
        event.accept() 