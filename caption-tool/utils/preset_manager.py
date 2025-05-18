import os
import json
from pathlib import Path

class PresetManager:
    def __init__(self, presets_file=None):
        """Initialize the preset manager"""
        if presets_file is None:
            # Default presets file path
            base_dir = Path(__file__).parent.parent
            presets_file = base_dir / "presets" / "presets.json"
            
        self.presets_file = presets_file
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
                "font": "Arial Black",
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
            
        self.presets[preset_id] = preset_data
        return self.save_presets()
    
    def update_preset(self, preset_id, preset_data):
        """Update an existing preset"""
        if preset_id not in self.presets:
            return False
            
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