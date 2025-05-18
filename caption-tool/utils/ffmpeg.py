import os
import subprocess
import json
import tempfile
from pathlib import Path

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
    
    def generate_drawtext_filter(self, caption, preset, start=None, end=None, fade_duration=0.5):
        """Generate FFmpeg drawtext filter for a caption with specified preset"""
        text_esc = caption["text"].replace("'", "'\\\\''")
        
        # Base drawtext filter
        filter_text = (
            f"drawtext=text='{text_esc}':"
            f"fontfile={preset['font']}:"
            f"fontsize={preset['size']}:"
            f"fontcolor={preset['color']}:"
            f"x={preset['x']}:y={preset['y']}"
        )
        
        # Add fade-in and fade-out if start and end times are specified
        if start is not None and end is not None:
            fade_in_start = caption["start"]
            fade_in_end = caption["start"] + fade_duration
            fade_out_start = caption["end"] - fade_duration
            fade_out_end = caption["end"]
            
            if preset["animation"] == "fadeInBottom":
                filter_text += (
                    f":alpha='if(lt(t,{fade_in_start}),0,"
                    f"if(lt(t,{fade_in_end}),(t-{fade_in_start})/{fade_duration},"
                    f"if(lt(t,{fade_out_start}),1,"
                    f"if(lt(t,{fade_out_end}),1-(t-{fade_out_start})/{fade_duration},0))))"
                    f"':y='if(lt(t,{fade_in_end}),h-50-(t-{fade_in_start})/{fade_duration}*50,{preset['y']})'"
                )
            elif preset["animation"] == "slideFromTop":
                filter_text += (
                    f":alpha='if(lt(t,{fade_in_start}),0,"
                    f"if(lt(t,{fade_in_end}),(t-{fade_in_start})/{fade_duration},"
                    f"if(lt(t,{fade_out_start}),1,"
                    f"if(lt(t,{fade_out_end}),1-(t-{fade_out_start})/{fade_duration},0))))"
                    f"':y='if(lt(t,{fade_in_end}),50+(t-{fade_in_start})/{fade_duration}*({preset['y']}-50),{preset['y']})'"
                )
            else:  # Default fade
                filter_text += (
                    f":alpha='if(lt(t,{fade_in_start}),0,"
                    f"if(lt(t,{fade_in_end}),(t-{fade_in_start})/{fade_duration},"
                    f"if(lt(t,{fade_out_start}),1,"
                    f"if(lt(t,{fade_out_end}),1-(t-{fade_out_start})/{fade_duration},0))))'"
                )
                
        return filter_text
    
    def create_short_preview(self, video_path, caption, preset, output_path=None):
        """Create a short preview with a single caption"""
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp4")
            
        start_time = caption["start"]
        end_time = caption["end"]
        duration = end_time - start_time
        
        # Generate drawtext filter
        drawtext = self.generate_drawtext_filter(caption, preset, start_time, end_time)
        
        cmd = [
            "ffmpeg", "-ss", str(start_time), 
            "-i", video_path, 
            "-t", str(duration),
            "-vf", drawtext,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k",
            "-y", output_path
        ]
        
        subprocess.run(cmd, check=True)
        return output_path
    
    def render_final_video(self, video_path, captions, presets, output_path=None, callback=None):
        """Render the final video with all captions"""
        if output_path is None:
            output_path = os.path.splitext(video_path)[0] + "_captioned.mp4"
            
        # Create complex filter with all captions
        filter_complex = []
        
        for i, caption in enumerate(captions):
            preset = presets[caption["preset"]]
            filter_text = self.generate_drawtext_filter(caption, preset, 
                                                       caption["start"], 
                                                       caption["end"])
            filter_complex.append(filter_text)
            
        if not filter_complex:
            raise ValueError("No captions to render")
            
        filter_arg = ",".join(filter_complex)
        
        # Check for hardware acceleration support
        has_gpu = self.check_gpu_support()
        
        # Base command
        cmd = ["ffmpeg", "-i", video_path, "-vf", filter_arg]
        
        # Add video codec options - use hw acceleration if available
        if has_gpu and self.check_encoder_available("h264_nvenc"):  # NVIDIA
            cmd.extend(["-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19"])
        elif has_gpu and self.check_encoder_available("h264_amf"):  # AMD
            cmd.extend(["-c:v", "h264_amf", "-quality", "quality", "-qp_i", "18", "-qp_p", "20"])
        elif has_gpu and self.check_encoder_available("h264_qsv"):  # Intel
            cmd.extend(["-c:v", "h264_qsv", "-preset", "veryslow", "-global_quality", "18"])
        else:  # Software encoding fallback
            cmd.extend(["-c:v", "libx264", "-crf", "18", "-preset", "fast"])
        
        # Always use AAC audio
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        
        # Add output path
        cmd.extend(["-y", output_path])
        
        # Run the process with progress reporting
        if callback:
            # We will parse output for progress reporting
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Get video duration for progress calculation
            duration = self.get_video_info(video_path)["duration"]
            
            for line in process.stdout:
                # Parse FFmpeg progress information
                if "time=" in line:
                    try:
                        # Extract time in format HH:MM:SS.MS
                        time_str = line.split("time=")[1].split()[0].strip()
                        # Convert to seconds
                        h, m, s = map(float, time_str.split(':'))
                        current_time = h * 3600 + m * 60 + s
                        # Calculate progress percentage
                        progress = min(100, int(current_time / duration * 100))
                        callback(progress, line)
                    except Exception:
                        pass
                else:
                    # Report other info
                    callback(-1, line)
            
            process.wait()
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd)
        else:
            # Simple subprocess call without progress reporting
            subprocess.run(cmd, check=True)
            
        return output_path
        
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