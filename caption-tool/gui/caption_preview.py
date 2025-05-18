import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QPen, QImage

class CaptionPreviewWidget(QLabel):
    """Widget for previewing video frames with caption overlay"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: black;
                border-radius: 8px;
            }
        """)
        self.current_frame = None
        self.current_frame_path = None  # Store the original frame path
        self.current_caption = None
        self.current_preset = None
        self.current_language = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
    def set_frame(self, frame_path):
        """Set the current frame image"""
        if isinstance(frame_path, QImage):
            # If we're passed a QImage (like during resizing), use it directly
            image = frame_path
            # We don't update current_frame_path in this case
        else:
            # Normal case: load image from file path
            if not os.path.exists(frame_path):
                return
                
            # Store the original frame path for resizing
            self.current_frame_path = frame_path
                
            # Load the image
            image = QImage(frame_path)
            
        if image.isNull():
            return
            
        # Get the widget size
        widget_size = self.size()
        if widget_size.width() <= 1 or widget_size.height() <= 1:
            # Widget not properly sized yet, use a reasonable default
            widget_size = QSize(640, 360)
        
        # Calculate aspect ratios
        image_ratio = image.width() / image.height()
        widget_ratio = widget_size.width() / widget_size.height()
        
        # Calculate the scaled size while maintaining aspect ratio
        # Use a scaling factor to ensure the entire image is visible
        scaling_factor = 0.8  # Reduced from 0.9 to 0.8 to create more margin
        
        if image_ratio > widget_ratio:
            # Image is wider than widget - fit to width
            scaled_width = int(widget_size.width() * scaling_factor)
            scaled_height = int(scaled_width / image_ratio)
        else:
            # Image is taller than widget - fit to height
            scaled_height = int(widget_size.height() * scaling_factor)
            scaled_width = int(scaled_height * image_ratio)
            
        scaled_size = QSize(scaled_width, scaled_height)
        
        # Scale the image
        scaled_image = image.scaled(
            scaled_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Create a black background image of widget size
        background = QImage(widget_size, QImage.Format.Format_RGB32)
        background.fill(QColor(0, 0, 0))
        
        # Calculate position to center the scaled image
        x = (widget_size.width() - scaled_size.width()) // 2
        y = (widget_size.height() - scaled_size.height()) // 2
        
        # Draw the scaled image on the background
        painter = QPainter(background)
        painter.drawImage(x, y, scaled_image)
        painter.end()
        
        self.current_frame = background
        self.update()
        
    def set_caption(self, text, preset, language=None):
        """Set the current caption text and style"""
        self.current_caption = text
        self.current_preset = preset
        self.current_language = language
        self.update()
        
    def clear_caption(self):
        """Clear the current caption"""
        self.current_caption = None
        self.current_preset = None
        self.current_language = None
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event to draw the frame and caption"""
        super().paintEvent(event)
        
        if not self.current_frame:
            return
            
        painter = QPainter(self)
        
        # Draw the frame
        painter.drawImage(0, 0, self.current_frame)
        
        # Draw caption if available
        if self.current_caption and self.current_preset:
            # Get the widget dimensions
            widget_width = self.width()
            widget_height = self.height()
            
            # Scale factor for text relative to a standard 1080p video
            # This ensures preview text size matches rendered output
            base_height = 1080
            scale_factor = widget_height / base_height
            
            # Set up font with scaled size
            font = QFont(self.current_preset.get('font', 'Arial'))
            original_size = self.current_preset.get('size', 24)
            scaled_size = max(int(original_size * scale_factor), 10)  # Minimum size of 10
            font.setPointSize(scaled_size)
            painter.setFont(font)
            
            # Set up text color
            color = QColor(self.current_preset.get('color', 'white'))
            
            # If we have an outline or shadow setting in the preset, use it
            has_outline = self.current_preset.get('outline', False)
            outline_size = self.current_preset.get('outline_size', 2)
            outline_color = QColor(self.current_preset.get('outline_color', 'black'))
            
            # Get text metrics to properly size the background
            text_metrics = painter.fontMetrics()
            text_width = text_metrics.horizontalAdvance(self.current_caption)
            text_height = text_metrics.height()
            
            # Create text rectangle
            text_rect = self.rect()
            
            # If text is too wide, adjust for word wrapping
            if text_width > text_rect.width() - 40:
                # Estimate number of lines based on text width and available width
                estimated_lines = max(1, int(text_width / (text_rect.width() - 40)))
                text_height = text_height * estimated_lines
                
            # Calculate margin based on scale
            margin = int(30 * scale_factor)  # Scale margin too
            
            # Reposition text rectangle at the BOTTOM of the frame
            caption_height = text_height + margin*2
            
            # This explicitly sets the text rectangle at the bottom portion of the screen
            # Moving the text up by approximately 100 pixels (scaled)
            extra_offset = int(100 * scale_factor)
            text_rect.setTop(text_rect.bottom() - caption_height - margin - extra_offset)
            text_rect.setBottom(text_rect.bottom() - margin - extra_offset)
            
            # Create background rectangle
            bg_rect = text_rect
            
            # Check if background is enabled in preset
            has_bg = self.current_preset.get('background', False)
            bg_color = QColor(self.current_preset.get('bg_color', '#000000'))
            bg_opacity = self.current_preset.get('bg_opacity', 50)  # 0-100
            
            # Draw semi-transparent background if enabled
            if has_bg:
                bg_color.setAlpha(int(bg_opacity * 2.55))  # Convert 0-100 to 0-255
                painter.fillRect(bg_rect, bg_color)
            
            # Draw text shadow/outline for better readability if enabled
            if has_outline:
                shadow_size = max(1, int(outline_size * scale_factor))
                
                # Draw text outline by drawing the text 4 times with small offsets
                painter.setPen(outline_color)
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    offset_rect = text_rect.translated(shadow_size * dx, shadow_size * dy)
                    painter.drawText(
                        offset_rect,
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                        self.current_caption
                    )
            
            # Draw the main text
            painter.setPen(color)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.current_caption
            )
            
    def resizeEvent(self, event):
        """Handle resize events to maintain aspect ratio"""
        super().resizeEvent(event)
        # If we have a current frame path, reload the image to fit the new size
        if self.current_frame_path:
            self.set_frame(self.current_frame_path)
        
    def sizeHint(self):
        """Provide a size hint that maintains aspect ratio"""
        if self.current_frame:
            return QSize(640, 360)  # 16:9 aspect ratio
        return super().sizeHint()
        
    def minimumSizeHint(self):
        """Provide a minimum size hint"""
        return QSize(320, 180)  # Half of the preferred size 