from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                            QPushButton, QListWidget, QComboBox, QSpinBox, QGroupBox,
                            QColorDialog, QMessageBox, QFormLayout, QTabWidget, QWidget,
                            QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
import os
from pathlib import Path

class PresetEditorDialog(QDialog):
    """Dialog for creating, editing, and deleting style presets"""
    
    def __init__(self, preset_manager, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        
        self.init_ui()
        self.load_presets()
        self.load_fonts()
        
    def init_ui(self):
        """Initialize the UI layout"""
        self.setWindowTitle("Caption Style Presets")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Preset list and edit tabs
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Presets list tab
        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        
        # Presets list
        self.presets_list = QListWidget()
        self.presets_list.currentRowChanged.connect(self.on_preset_selected)
        presets_layout.addWidget(self.presets_list)
        
        # Buttons for list actions
        list_buttons_layout = QHBoxLayout()
        
        self.new_preset_btn = QPushButton("New Preset")
        self.new_preset_btn.clicked.connect(self.on_new_preset)
        list_buttons_layout.addWidget(self.new_preset_btn)
        
        self.delete_preset_btn = QPushButton("Delete Preset")
        self.delete_preset_btn.clicked.connect(self.on_delete_preset)
        list_buttons_layout.addWidget(self.delete_preset_btn)
        
        presets_layout.addLayout(list_buttons_layout)
        
        tab_widget.addTab(presets_tab, "Presets")
        
        # Edit tab
        edit_tab = QWidget()
        edit_layout = QVBoxLayout(edit_tab)
        
        # Edit form
        form_layout = QFormLayout()
        
        # Preset ID
        self.preset_id_edit = QLineEdit()
        form_layout.addRow("Preset ID:", self.preset_id_edit)
        
        # Font family with custom font support
        font_layout = QHBoxLayout()
        self.font_combo = QComboBox()
        font_layout.addWidget(self.font_combo, 1)
        
        # Add font upload button
        self.upload_font_btn = QPushButton("Upload TTF...")
        self.upload_font_btn.clicked.connect(self.on_upload_font)
        font_layout.addWidget(self.upload_font_btn)
        
        # Add font management button
        self.manage_fonts_btn = QPushButton("Manage Fonts")
        self.manage_fonts_btn.clicked.connect(self.on_manage_fonts)
        font_layout.addWidget(self.manage_fonts_btn)
        
        form_layout.addRow("Font:", font_layout)
        
        # Font size
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(36)
        form_layout.addRow("Size:", self.size_spin)
        
        # Text color
        color_layout = QHBoxLayout()
        self.color_edit = QLineEdit()
        self.color_edit.setText("white")
        color_layout.addWidget(self.color_edit)
        
        self.color_picker_btn = QPushButton("Pick Color")
        self.color_picker_btn.clicked.connect(self.on_pick_color)
        color_layout.addWidget(self.color_picker_btn)
        
        form_layout.addRow("Color:", color_layout)
        
        # Animation
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(self.preset_manager.get_animation_types())
        form_layout.addRow("Animation:", self.animation_combo)
        
        # Position X
        self.x_pos_edit = QLineEdit()
        self.x_pos_edit.setText("(w-text_w)/2")
        form_layout.addRow("X Position:", self.x_pos_edit)
        
        # Position Y
        self.y_pos_edit = QLineEdit()
        self.y_pos_edit.setText("h-100")
        form_layout.addRow("Y Position:", self.y_pos_edit)
        
        # Position help text
        help_text = QLabel(
            "Position can use these variables:\n"
            "w = video width, h = video height\n"
            "text_w = text width, text_h = text height\n"
            "Example: (w-text_w)/2 centers horizontally"
        )
        help_text.setStyleSheet("color: gray;")
        
        # Font help text
        font_help = QLabel(
            "Note: Custom TTF fonts will be used for rendering. "
            "Standard fonts will be used in preview."
        )
        font_help.setStyleSheet("color: gray;")
        
        edit_layout.addLayout(form_layout)
        edit_layout.addWidget(help_text)
        edit_layout.addWidget(font_help)
        
        # Save button
        save_layout = QHBoxLayout()
        
        self.save_preset_btn = QPushButton("Save Preset")
        self.save_preset_btn.clicked.connect(self.on_save_preset)
        save_layout.addWidget(self.save_preset_btn)
        
        self.cancel_edit_btn = QPushButton("Cancel")
        self.cancel_edit_btn.clicked.connect(self.on_cancel_edit)
        save_layout.addWidget(self.cancel_edit_btn)
        
        edit_layout.addLayout(save_layout)
        
        tab_widget.addTab(edit_tab, "Edit Preset")
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        self.done_btn = QPushButton("Done")
        self.done_btn.clicked.connect(self.accept)
        dialog_buttons.addWidget(self.done_btn)
        
        main_layout.addLayout(dialog_buttons)
        
        # Set initial state
        self.editing_preset_id = None
        self.update_ui_state()
        
    def load_fonts(self):
        """Load fonts into the font combo box"""
        self.font_combo.clear()
        
        # Add standard fonts
        standard_fonts = self.preset_manager.get_standard_fonts()
        self.font_combo.addItems(standard_fonts)
        
        # Add separator if we have custom fonts
        if self.preset_manager.custom_fonts:
            self.font_combo.insertSeparator(len(standard_fonts))
            
            # Add custom fonts with indicator
            for font_name in self.preset_manager.custom_fonts.keys():
                self.font_combo.addItem(f"📝 {font_name} (Custom)")
        
    def load_presets(self):
        """Load presets into the list"""
        self.presets_list.clear()
        
        for preset_id in self.preset_manager.get_preset_list():
            self.presets_list.addItem(preset_id)
            
    def update_ui_state(self):
        """Update enabled/disabled state of UI elements"""
        has_selected = self.presets_list.currentRow() >= 0
        self.delete_preset_btn.setEnabled(has_selected)
        
    def on_preset_selected(self, row):
        """Handle preset selection from list"""
        self.update_ui_state()
        
        if row < 0:
            return
            
        preset_id = self.presets_list.item(row).text()
        preset = self.preset_manager.get_preset(preset_id)
        
        if preset:
            # Load preset data into form
            self.editing_preset_id = preset_id
            self.preset_id_edit.setText(preset_id)
            
            # Handle font selection, check if it's a custom font
            font_name = preset.get("font", "Arial")
            is_custom = self.preset_manager.is_custom_font(font_name)
            
            if is_custom:
                # Find the custom font in combo box
                for i in range(self.font_combo.count()):
                    item_text = self.font_combo.itemText(i)
                    if f"📝 {font_name}" in item_text:
                        self.font_combo.setCurrentIndex(i)
                        break
            else:
                # Standard font
                font_index = self.font_combo.findText(font_name)
                if font_index >= 0:
                    self.font_combo.setCurrentIndex(font_index)
                
            self.size_spin.setValue(preset.get("size", 36))
            self.color_edit.setText(preset.get("color", "white"))
            
            anim_index = self.animation_combo.findText(preset.get("animation", "appear"))
            if anim_index >= 0:
                self.animation_combo.setCurrentIndex(anim_index)
                
            self.x_pos_edit.setText(preset.get("x", "(w-text_w)/2"))
            self.y_pos_edit.setText(preset.get("y", "h-100"))
            
    def on_new_preset(self):
        """Create a new preset"""
        self.editing_preset_id = None
        self.preset_id_edit.setText("new_preset")
        self.font_combo.setCurrentIndex(0)
        self.size_spin.setValue(36)
        self.color_edit.setText("white")
        self.animation_combo.setCurrentIndex(0)
        self.x_pos_edit.setText("(w-text_w)/2")
        self.y_pos_edit.setText("h-100")
        
    def on_delete_preset(self):
        """Delete the selected preset"""
        row = self.presets_list.currentRow()
        if row < 0:
            return
            
        preset_id = self.presets_list.item(row).text()
        
        # Confirm deletion
        result = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the preset '{preset_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            # Delete the preset
            self.preset_manager.delete_preset(preset_id)
            
            # Refresh the list
            self.load_presets()
            self.update_ui_state()
            
    def on_upload_font(self):
        """Upload a custom TTF font file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select TTF Font File", "", "TTF Files (*.ttf);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Ask for a custom name
        font_name, ok = QFileDialog.getSaveFileName(
            self, "Save Font As", "", "Font Name (no extension needed)"
        )
        
        if not ok or not font_name:
            font_name = None  # Use default (filename)
        else:
            # Strip any extension and path
            font_name = Path(font_name).stem
            
        # Add the font
        added_name = self.preset_manager.add_custom_font(file_path, font_name)
        
        if added_name:
            QMessageBox.information(
                self, "Font Added", 
                f"Custom font '{added_name}' added successfully!"
            )
            
            # Reload fonts
            self.load_fonts()
        else:
            QMessageBox.critical(
                self, "Error", 
                "Failed to add custom font. Please check the file is valid."
            )
    
    def on_manage_fonts(self):
        """Open font management dialog"""
        dialog = FontManagerDialog(self.preset_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Reload fonts
            self.load_fonts()
            
    def on_save_preset(self):
        """Save the current preset"""
        preset_id = self.preset_id_edit.text().strip()
        
        if not preset_id:
            QMessageBox.warning(self, "Error", "Preset ID cannot be empty")
            return
            
        # Get font name, handling custom fonts
        font_text = self.font_combo.currentText()
        if "📝" in font_text and "(Custom)" in font_text:
            # Extract custom font name from the display text
            # Format: "📝 FontName (Custom)"
            font_name = font_text.split("📝 ")[1].split(" (Custom)")[0]
        else:
            font_name = font_text
            
        # Create preset data from form
        preset_data = {
            "font": font_name,
            "size": self.size_spin.value(),
            "color": self.color_edit.text(),
            "animation": self.animation_combo.currentText(),
            "x": self.x_pos_edit.text(),
            "y": self.y_pos_edit.text()
        }
        
        # Add or update the preset
        if self.editing_preset_id and preset_id != self.editing_preset_id:
            # Delete old preset if ID changed
            self.preset_manager.delete_preset(self.editing_preset_id)
            
        # Add/update the preset
        if preset_id in self.preset_manager.get_preset_list():
            self.preset_manager.update_preset(preset_id, preset_data)
        else:
            self.preset_manager.add_preset(preset_id, preset_data)
            
        # Refresh the list
        self.load_presets()
        
        # Switch to presets tab
        self.parent().findChild(QTabWidget).setCurrentIndex(0)
        
        QMessageBox.information(self, "Success", f"Preset '{preset_id}' saved successfully")
        
    def on_cancel_edit(self):
        """Cancel preset editing"""
        # Reset to the current preset data, if any
        row = self.presets_list.currentRow()
        if row >= 0:
            self.on_preset_selected(row)
        else:
            self.on_new_preset()
            
    def on_pick_color(self):
        """Open color picker dialog"""
        # Try to parse current color
        try:
            current_color = QColor(self.color_edit.text())
        except:
            current_color = QColor("white")
            
        # Open color dialog
        color = QColorDialog.getColor(current_color, self, "Select Text Color")
        
        if color.isValid():
            # Use hex format for color
            self.color_edit.setText(color.name())

class FontManagerDialog(QDialog):
    """Dialog for managing custom fonts"""
    
    def __init__(self, preset_manager, parent=None):
        super().__init__(parent)
        self.preset_manager = preset_manager
        
        self.init_ui()
        self.load_fonts()
        
    def init_ui(self):
        """Initialize the UI layout"""
        self.setWindowTitle("Custom Font Manager")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Font list
        self.font_list = QListWidget()
        self.font_list.currentRowChanged.connect(self.on_font_selected)
        main_layout.addWidget(self.font_list)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.add_font_btn = QPushButton("Add Font")
        self.add_font_btn.clicked.connect(self.on_add_font)
        buttons_layout.addWidget(self.add_font_btn)
        
        self.delete_font_btn = QPushButton("Delete Font")
        self.delete_font_btn.clicked.connect(self.on_delete_font)
        buttons_layout.addWidget(self.delete_font_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        close_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(close_layout)
        
        # Initial UI state
        self.update_ui_state()
        
    def load_fonts(self):
        """Load custom fonts into the list"""
        self.font_list.clear()
        
        for font_name, font_info in self.preset_manager.custom_fonts.items():
            self.font_list.addItem(f"📝 {font_name} ({font_info['file']})")
            
    def update_ui_state(self):
        """Update enabled/disabled state of UI elements"""
        has_selected = self.font_list.currentRow() >= 0
        self.delete_font_btn.setEnabled(has_selected)
        
    def on_font_selected(self, row):
        """Handle font selection"""
        self.update_ui_state()
        
    def on_add_font(self):
        """Add a new custom font"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select TTF Font File", "", "TTF Files (*.ttf);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        # Ask for a custom name
        font_name, ok = QFileDialog.getSaveFileName(
            self, "Save Font As", "", "Font Name (no extension needed)"
        )
        
        if not ok or not font_name:
            font_name = None  # Use default (filename)
        else:
            # Strip any extension and path
            font_name = Path(font_name).stem
            
        # Add the font
        added_name = self.preset_manager.add_custom_font(file_path, font_name)
        
        if added_name:
            QMessageBox.information(
                self, "Font Added", 
                f"Custom font '{added_name}' added successfully!"
            )
            
            # Reload fonts
            self.load_fonts()
        else:
            QMessageBox.critical(
                self, "Error", 
                "Failed to add custom font. Please check the file is valid."
            )
            
    def on_delete_font(self):
        """Delete the selected custom font"""
        row = self.font_list.currentRow()
        if row < 0:
            return
            
        # Extract font name from the display text
        item_text = self.font_list.item(row).text()
        font_name = item_text.split("📝 ")[1].split(" (")[0]
        
        # Confirm deletion
        result = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the font '{font_name}'?\n\n"
            "Note: This may affect presets using this font.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            success = self.preset_manager.remove_custom_font(font_name)
            
            if success:
                QMessageBox.information(
                    self, "Font Deleted",
                    f"Font '{font_name}' deleted successfully."
                )
                
                # Reload fonts
                self.load_fonts()
            else:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to delete font '{font_name}'."
                )
                
            self.update_ui_state() 