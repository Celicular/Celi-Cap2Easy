import os
import json
import shutil
from pathlib import Path

class PresetManager:
    def __init__(self, presets_file=None):
        """Initialize the preset manager"""
        if presets_file is None:
            # Default presets file path
            base_dir = Path(__file__).parent.parent
            presets_file = base_dir / "presets" / "presets.json"
            
        self.presets_file = presets_file
        
        # Setup fonts directory
        self.base_dir = Path(presets_file).parent
        self.fonts_dir = self.base_dir / "fonts"
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        # Track custom fonts
        self.custom_fonts = {}
        self.load_custom_fonts()
        
        self.presets = self.load_presets()
        
    def load_presets(self):
        """Load presets from JSON file"""
        if not os.path.exists(self.presets_file):
            return self.create_default_presets()
            
        try:
            with open(self.presets_file, 'r') as f:
                presets = json.load(f)
                return presets
        except Exception as e:
            print(f"Error loading presets: {e}")
            return self.create_default_presets()
            
    def load_custom_fonts(self):
        """Load custom font information"""
        fonts_info_file = self.fonts_dir / "fonts_info.json"
        
        if os.path.exists(fonts_info_file):
            try:
                with open(fonts_info_file, 'r') as f:
                    self.custom_fonts = json.load(f)
            except Exception as e:
                print(f"Error loading custom fonts info: {e}")
                self.custom_fonts = {}
        else:
            self.custom_fonts = {}
    
    def save_custom_fonts(self):
        """Save custom font information"""
        fonts_info_file = self.fonts_dir / "fonts_info.json"
        
        try:
            with open(fonts_info_file, 'w') as f:
                json.dump(self.custom_fonts, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving custom fonts info: {e}")
            return False
    
    def add_custom_font(self, font_path, font_name=None):
        """
        Add a custom TTF font file to the fonts directory
        
        Args:
            font_path: Path to the TTF file
            font_name: Optional custom name for the font (default: filename)
            
        Returns:
            str: Font name if successful, None if failed
        """
        try:
            # Get font filename
            font_file = Path(font_path).name
            
            # Use filename as font name if not provided
            if not font_name:
                font_name = Path(font_file).stem
                
            # Copy font file to fonts directory
            dest_path = self.fonts_dir / font_file
            shutil.copy2(font_path, dest_path)
            
            # Add font info to custom_fonts
            self.custom_fonts[font_name] = {
                "file": font_file,
                "path": str(dest_path)
            }
            
            # Save updated custom fonts info
            self.save_custom_fonts()
            
            return font_name
            
        except Exception as e:
            print(f"Error adding custom font: {e}")
            return None
    
    def remove_custom_font(self, font_name):
        """Remove a custom font"""
        if font_name not in self.custom_fonts:
            return False
            
        try:
            # Get font file path
            font_info = self.custom_fonts[font_name]
            font_path = self.fonts_dir / font_info["file"]
            
            # Delete the font file if it exists
            if os.path.exists(font_path):
                os.remove(font_path)
                
            # Remove from custom_fonts dictionary
            del self.custom_fonts[font_name]
            
            # Save updated custom fonts info
            self.save_custom_fonts()
            
            return True
            
        except Exception as e:
            print(f"Error removing custom font: {e}")
            return False
            
    def get_custom_font_path(self, font_name):
        """Get the path to a custom font file"""
        if font_name in self.custom_fonts:
            return self.custom_fonts[font_name]["path"]
        return None
    
    def create_default_presets(self):
        """Create and save default presets"""
        default_presets = {
            "fadeBottom": {
                "font": "Arial",
                "size": 36,
                "color": "white",
                "animation": "fadeInBottom",
                "x": "(w-text_w)/2",
                "y": "h-100"
            },
            "topSlide": {
                "font": "Verdana",
                "size": 24,
                "color": "yellow",
                "animation": "slideFromTop",
                "x": "(w-text_w)/2",
                "y": "50"
            },
            "centerBold": {
                "font": "Arial",
                "size": 42,
                "color": "#ffffff",
                "animation": "appear",
                "x": "(w-text_w)/2",
                "y": "(h-text_h)/2"
            }
        }
        
        self.save_presets(default_presets)
        return default_presets
    
    def save_presets(self, presets=None):
        """Save presets to JSON file"""
        if presets is None:
            presets = self.presets
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.presets_file), exist_ok=True)
        
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(presets, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving presets: {e}")
            return False
    
    def get_preset(self, preset_id):
        """Get a specific preset by ID"""
        return self.presets.get(preset_id)
    
    def add_preset(self, preset_id, preset_data):
        """Add a new preset"""
        if preset_id in self.presets:
            return False
        
        # Normalize font name if present
        if 'font' in preset_data:
            preset_data['font'] = self.normalize_font_name(preset_data['font'])
            
        self.presets[preset_id] = preset_data
        return self.save_presets()
    
    def update_preset(self, preset_id, preset_data):
        """Update an existing preset"""
        if preset_id not in self.presets:
            return False
        
        # Normalize font name if present
        if 'font' in preset_data:
            preset_data['font'] = self.normalize_font_name(preset_data['font'])
            
        self.presets[preset_id] = preset_data
        return self.save_presets()
    
    def delete_preset(self, preset_id):
        """Delete a preset"""
        if preset_id not in self.presets:
            return False
            
        del self.presets[preset_id]
        return self.save_presets()
    
    def get_preset_list(self):
        """Get a list of preset names (IDs)"""
        return list(self.presets.keys())
        
    def get_animation_types(self):
        """Return a list of available animation types"""
        return ["appear", "fadeInBottom", "slideFromTop", "fadeIn"]
        
    def get_standard_fonts(self):
        """Return a list of standard fonts that should work with FFmpeg"""
        return [
            "Arial",
            "Verdana",
            "Times New Roman",
            "Courier New",
            "Georgia",
            "Tahoma",
            "Trebuchet MS",
            "Impact",
            "Comic Sans MS",
            "Consolas",
            "Calibri"
        ]
        
    def get_all_fonts(self):
        """Return a list of all available fonts (standard + custom)"""
        all_fonts = self.get_standard_fonts()
        custom_fonts = list(self.custom_fonts.keys())
        return all_fonts + custom_fonts
        
    def is_custom_font(self, font_name):
        """Check if a font is a custom font"""
        return font_name in self.custom_fonts
        
    def normalize_font_name(self, font_name):
        """Convert a font name to a standard one that will work with FFmpeg"""
        # Check if it's a custom font first
        if self.is_custom_font(font_name):
            return font_name
            
        # Map of common non-standard font names to standard ones
        font_map = {
            "Arial Black": "Arial",
            "Arial Bold": "Arial",
            "Arial Narrow": "Arial",
            "Helvetica": "Arial",
            "Sans-Serif": "Arial",
            "Times": "Times New Roman",
            "Courier": "Courier New",
            "Monospace": "Consolas",
            "Sans": "Arial",
            "Serif": "Times New Roman"
        }
        
        # Check if we need to normalize
        if font_name in font_map:
            return font_map[font_name]
        
        # Check if it's already a standard font
        standard_fonts = self.get_standard_fonts()
        if font_name in standard_fonts:
            return font_name
            
        # Default to Arial if not found
        return "Arial" 