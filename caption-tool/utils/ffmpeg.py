import os
import subprocess
import json
import tempfile
from pathlib import Path
import time
import re

class FFmpegHandler:
    def __init__(self):
        self.check_ffmpeg()
        
    def check_ffmpeg(self):
        """Check if FFmpeg is installed and accessible"""
        try:
            subprocess.run(["ffmpeg", "-version"], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE, 
                          check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and make sure it's in your PATH.")
    
    def extract_audio(self, video_path, output_path=None):
        """Extract audio from video file"""
        if output_path is None:
            output_path = os.path.splitext(video_path)[0] + ".wav"
            
        cmd = [
            "ffmpeg", "-i", video_path, 
            "-vn", "-acodec", "pcm_s16le", 
            "-ar", "44100", "-ac", "2", 
            "-y", output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def get_video_info(self, video_path):
        """Get video information like duration, resolution, etc."""
        cmd = [
            "ffprobe", "-v", "error", 
            "-show_entries", "format=duration:stream=width,height", 
            "-of", "json", video_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)
        info = json.loads(result.stdout)
        
        duration = float(info["format"]["duration"])
        
        # Find video stream
        width = height = None
        for stream in info["streams"]:
            if "width" in stream and "height" in stream:
                width = stream["width"]
                height = stream["height"]
                break
                
        return {
            "duration": duration,
            "width": width,
            "height": height
        }
    
    def extract_frame(self, video_path, time_sec, output_path=None):
        """Extract a single frame from video at specified time"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".jpg")
            
        cmd = [
            "ffmpeg", "-ss", str(time_sec), 
            "-i", video_path, 
            "-vframes", "1", "-q:v", "2", 
            "-y", output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def escape_ffmpeg_text(self, text):
        """Escape special characters for FFmpeg drawtext filter"""
        # Replace backslashes first
        text = text.replace('\\', '\\\\')
        # Escape quotes
        text = text.replace('"', '\\"')
        # Escape colons
        text = text.replace(':', '\\:')
        # Escape single quotes
        text = text.replace("'", "\\'")
        # Escape asterisks
        text = text.replace('*', '\\*')
        return text

    def generate_drawtext_filter(self, caption, preset, preset_manager=None):
        """Generate FFmpeg drawtext filter for a caption"""
        # Escape the caption text
        text = self.escape_ffmpeg_text(caption['text'])
        
        # Get preset values with defaults
        font = preset.get('font', 'Arial')
        size = preset.get('size', 24)
        color = preset.get('color', 'white')
        x_pos = preset.get('x', '(w-text_w)/2')
        y_pos = preset.get('y', 'h-100')
        
        # Handle custom fonts if a preset manager is provided
        font_path = None
        if preset_manager and preset_manager.is_custom_font(font):
            font_path = preset_manager.get_custom_font_path(font)
            # Ensure path is valid and properly escaped
            if font_path:
                # Convert path to raw string and normalize slashes
                font_path = font_path.replace('\\', '/')
        
        # Calculate timing
        start_time = caption['start']
        end_time = caption['end']
        
        # Generate alpha expression for fade in/out
        alpha_expr = f"if(lt(t,{start_time+0.5}),(t-{start_time})/0.5,if(lt(t,{end_time-0.5}),1,if(lt(t,{end_time}),1-(t-{end_time-0.5})/0.5,0)))"
        
        # Build the drawtext filter
        filter_parts = [
            f"drawtext=text='{text}'"
        ]
        
        # Use font file path for custom fonts
        if font_path:
            # Properly escape the font path
            font_path = self.escape_ffmpeg_text(font_path)
            filter_parts.append(f"fontfile='{font_path}'")
        else:
            filter_parts.append(f"font='{font}'")
            
        filter_parts.extend([
            f"fontsize={size}",
            f"fontcolor={color}",
            f"x={x_pos}",
            f"y={y_pos}",
            "box=1:boxcolor=black@0.5:boxborderw=5",
            f"alpha='{alpha_expr}'"
        ])
        
        filter_string = ':'.join(filter_parts)
        
        # Validate the filter
        is_valid, error = self.check_filter_valid(filter_string)
        if not is_valid:
            # Try simplified version if validation fails
            print(f"Warning: Filter validation failed: {error}")
            return self.create_fallback_filter(text, font, size, color, x_pos, y_pos)
        
        return filter_string
        
    def create_fallback_filter(self, text, font, size, color, x_pos, y_pos):
        """Create a simplified fallback filter if the main one fails"""
        filter_parts = [
            f"drawtext=text='{text}'",
            f"font='Arial'",  # Always use Arial as fallback
            f"fontsize={size}",
            f"fontcolor={color}",
            f"x={x_pos}",
            f"y={y_pos}"
        ]
        return ':'.join(filter_parts)
    
    def create_short_preview(self, video_path, caption, preset, output_path=None):
        """Create a short preview with a single caption"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp4")
            
        start_time = caption["start"]
        end_time = caption["end"]
        duration = end_time - start_time
        
        # Generate drawtext filter
        drawtext = self.generate_drawtext_filter(caption, preset)
        
        # Validate and sanitize the filter if needed
        is_valid, error = self.check_filter_valid(drawtext)
        if not is_valid:
            drawtext = self.sanitize_filter(drawtext)
        
        # Use filter_complex instead of -vf for consistency and to handle more complex filters
        filter_complex = f"[0:v]{drawtext}[out]"
        
        cmd = [
            "ffmpeg", "-ss", str(start_time), 
            "-i", video_path, 
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", "[out]", "-map", "0:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def render_final_video(self, input_path, captions, presets, output_path, progress_callback=None, aspect_ratio=None, scale_mode='contain', preset_manager=None):
        """Render the final video with captions"""
        try:
            # Build filter chain
            filter_parts = []
            current_input = "0:v"  # Start with the video input
            
            # Add scale filter if aspect ratio is specified
            if aspect_ratio:
                if scale_mode == 'contain':
                    filter_parts.append(f"[{current_input}]scale={aspect_ratio}:force_original_aspect_ratio=decrease,pad={aspect_ratio}:(ow-ih)/2:(oh-iw)/2:black[v0]")
                else:  # cover
                    filter_parts.append(f"[{current_input}]scale={aspect_ratio}:force_original_aspect_ratio=increase,crop={aspect_ratio}[v0]")
                current_input = "v0"
            
            # Add drawtext filters for each caption
            for i, caption in enumerate(captions):
                preset = presets.get(caption['preset'], {})
                drawtext_filter = self.generate_drawtext_filter(caption, preset, preset_manager)
                output_label = f"v{i+1}"
                filter_parts.append(f"[{current_input}]{drawtext_filter}[{output_label}]")
                current_input = output_label
            
            # Combine all filters
            filter_complex = ';'.join(filter_parts)
            
            # Build FFmpeg command
            command = [
                'ffmpeg',
                '-i', input_path,
                '-filter_complex', filter_complex,
                '-map', f'[{current_input}]',  # Use the last output label
                '-map', '0:a',
            ]
            
            # Use appropriate encoder based on availability
            if self.check_encoder_available('h264_nvenc'):
                command.extend([
                    '-c:v', 'h264_nvenc',
                    '-preset', 'p7',
                    '-cq', '19',
                ])
            else:
                # Fallback to libx264 if NVENC not available
                command.extend([
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                ])
                
            # Add audio codec and output file
            command.extend([
                '-c:a', 'aac',
                '-b:a', '192k',
                '-y',
                output_path
            ])
            
            # Print the command for debugging
            command_str = ' '.join(command)
            print(f"Running FFmpeg command: {command_str}")
            
            if progress_callback:
                progress_callback(-1, f"Starting render with command: {command_str}")
                
            # Execute command with progress monitoring
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            duration = self.get_video_info(input_path)["duration"]
            stderr_output = []
            
            while True:
                output = process.stderr.readline()
                stderr_output.append(output)
                
                if output == '' and process.poll() is not None:
                    break
                    
                if output:
                    if progress_callback:
                        # Extract time from FFmpeg output
                        time_match = re.search(r'time=(\d+:\d+:\d+.\d+)', output)
                        if time_match:
                            current_time = self.parse_time(time_match.group(1))
                            progress = min(100, int((current_time / duration) * 100))
                            progress_callback(progress, output.strip())
            
            # Check for errors
            if process.returncode != 0:
                error_output = '\n'.join(stderr_output)
                raise Exception(f"FFmpeg error: {error_output}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Render error: {error_msg}")
            
            # Try to diagnose the issue
            if "No such file or directory" in error_msg and "fontfile" in error_msg:
                raise Exception("Font file not found. Please ensure custom fonts are properly installed.")
            elif "Error initializing filter" in error_msg and "drawtext" in error_msg:
                raise Exception("Error in drawtext filter. There may be special characters or font issues. Try a different font or text.")
            else:
                raise Exception(f"Error rendering video: {error_msg}")
        
    def parse_time(self, time_str):
        """Parse FFmpeg time string to seconds"""
        h, m, s = time_str.split(':')
        return float(h) * 3600 + float(m) * 60 + float(s)
        
    def check_gpu_support(self):
        """Check if GPU acceleration is available"""
        try:
            # Check for NVIDIA GPU
            result = subprocess.run(
                ["nvidia-smi"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=False
            )
            if result.returncode == 0:
                return True
                
            # Check for AMD GPU
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=False
            )
            if b"h264_amf" in result.stdout:
                return True
                
            # Check for Intel GPU
            if b"h264_qsv" in result.stdout:
                return True
                
            return False
        except Exception:
            return False
            
    def check_encoder_available(self, encoder_name):
        """Check if a specific encoder is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=False
            )
            return encoder_name.encode() in result.stdout
        except Exception:
            return False
            
    def check_filter_valid(self, filter_string):
        """Check if a filter string is valid by testing it with FFmpeg"""
        try:
            # Create a minimal command to test the filter
            cmd = [
                "ffmpeg", 
                "-f", "lavfi", 
                "-i", "color=c=black:s=1280x720:d=0.1", 
                "-vf", filter_string,
                "-f", "null", "-"
            ]
            
            # Run the command and capture output
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                text=True
            )
            
            # If successful, return True
            if result.returncode == 0:
                return True, None
            else:
                # Return the error message for debugging
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
            
    def sanitize_filter(self, filter_text):
        """Attempt to sanitize a filter string to make it valid"""
        # Common issues to fix:
        # 1. Replace fontfile with font
        filter_text = filter_text.replace("fontfile=", "font=")
        
        # 2. Make sure font names have quotes
        if "font=" in filter_text and not "font='" in filter_text:
            filter_text = filter_text.replace("font=", "font='")
            # Add closing quote if needed
            if not "font='Arial'" in filter_text and not "font='Verdana'" in filter_text:
                parts = filter_text.split("font='")
                if len(parts) > 1:
                    subparts = parts[1].split(":")
                    if len(subparts) > 1:
                        filter_text = parts[0] + "font='" + subparts[0] + "':" + ":".join(subparts[1:])
        
        return filter_text
    
    def check_has_audio(self, video_path):
        """Check if a video file has an audio stream"""
        try:
            cmd = [
                "ffprobe", "-v", "error", 
                "-select_streams", "a", 
                "-show_entries", "stream=codec_type", 
                "-of", "json", 
                video_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
            info = json.loads(result.stdout)
            
            # If we have audio streams, there will be entries in the streams array
            return 'streams' in info and len(info['streams']) > 0
        except Exception:
            # If anything goes wrong, assume no audio to be safe
            return False 