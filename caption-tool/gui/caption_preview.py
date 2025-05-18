import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QPen

class CaptionPreviewWidget(QWidget):
    """Widget for previewing video frames with caption overlay"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
        
        # State
        self.frame_path = None
        self.caption_text = None
        self.caption_preset = None
        self.pixmap = None
        
    def init_ui(self):
        """Initialize the UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setStyleSheet("background-color: black;")
        
        layout.addWidget(self.preview_label)
        
    def set_frame(self, frame_path):
        """Set the current video frame"""
        if not os.path.exists(frame_path):
            return
            
        self.frame_path = frame_path
        self.update_preview()
        
    def set_caption(self, text, preset):
        """Set the caption text and style to display over the frame"""
        self.caption_text = text
        self.caption_preset = preset
        self.update_preview()
        
    def clear_caption(self):
        """Clear the caption overlay"""
        self.caption_text = None
        self.caption_preset = None
        self.update_preview()
        
    def update_preview(self):
        """Redraw the preview with the current frame and caption"""
        if not self.frame_path:
            return
            
        # Load the image
        pixmap = QPixmap(self.frame_path)
        
        # If we have a caption to overlay
        if self.caption_text and self.caption_preset:
            # Create a copy we can paint on
            self.pixmap = QPixmap(pixmap)
            painter = QPainter(self.pixmap)
            
            # Configure text style
            font_size = self.caption_preset.get("size", 36)
            font_name = self.caption_preset.get("font", "Arial")
            color_name = self.caption_preset.get("color", "white")
            
            font = QFont(font_name)
            font.setPointSize(font_size)
            painter.setFont(font)
            
            try:
                # Handle hex colors or named colors
                if color_name.startswith("#"):
                    color = QColor(color_name)
                else:
                    color = QColor(color_name)
            except:
                color = QColor("white")
                
            painter.setPen(QPen(color))
            
            # Calculate position (simplified from FFmpeg expressions)
            width = self.pixmap.width()
            height = self.pixmap.height()
            
            # Get text bounding rect
            text_rect = painter.boundingRect(
                0, 0, width, height, Qt.AlignmentFlag.AlignLeft, self.caption_text
            )
            text_w = text_rect.width()
            text_h = text_rect.height()
            
            # Evaluate position expressions
            x_expr = self.caption_preset.get("x", "(w-text_w)/2")
            y_expr = self.caption_preset.get("y", "h-100")
            
            try:
                # Basic substitution and eval for expressions
                x_expr = x_expr.replace("w", str(width))
                x_expr = x_expr.replace("text_w", str(text_w))
                
                y_expr = y_expr.replace("h", str(height))
                y_expr = y_expr.replace("text_h", str(text_h))
                
                x = int(eval(x_expr))
                y = int(eval(y_expr))
            except:
                # Default to center bottom if expression fails
                x = (width - text_w) // 2
                y = height - 100
                
            # Draw text with outline for better visibility
            # Draw black outline
            for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
                painter.setPen(QPen(QColor("black")))
                painter.drawText(x + dx, y + dy, self.caption_text)
                
            # Draw text
            painter.setPen(QPen(color))
            painter.drawText(x, y, self.caption_text)
            
            painter.end()
        else:
            self.pixmap = pixmap
            
        # Scale the pixmap to fit the label while maintaining aspect ratio
        scaled_pixmap = self.pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Set the pixmap to the label
        self.preview_label.setPixmap(scaled_pixmap)
        
    def resizeEvent(self, event):
        """Handle widget resize event"""
        super().resizeEvent(event)
        
        # Update preview to ensure it's properly scaled
        if self.pixmap:
            self.update_preview() 