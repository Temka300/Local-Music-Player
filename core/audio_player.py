"""
Audio Player Module - Enhanced audio playback manager using VLC
"""

import sys
import os
import tempfile
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl

# Add parent directory to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import VLC for better audio playback
try:
    import vlc
    VLC_AVAILABLE = True
    print("✅ python-vlc available - Enhanced audio playback")
except ImportError:
    VLC_AVAILABLE = False
    print("⚠️ python-vlc not available - Install with: pip install python-vlc")
    print("💡 Falling back to Qt multimedia (may have codec issues)")

# Import pydub for M4A conversion (optional dependency)
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("✅ pydub available - M4A conversion supported")
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub not available - M4A files may have playback issues")
    print("💡 Install with: pip install pydub")

from PyQt5.QtMultimedia import QMediaPlayer


class AudioPlayer(QObject):
    """Enhanced audio playback manager using VLC"""
    
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)  # VLC uses different state values
    
    def __init__(self):
        super().__init__()
        
        try:
            if VLC_AVAILABLE:
                # Create VLC instance and player
                self.vlc_instance = vlc.Instance('--no-xlib')  # Disable X11 for better compatibility
                self.player = self.vlc_instance.media_player_new()
                self.using_vlc = True
                print("✅ VLC audio player initialized")
            else:
                # Fallback to Qt MediaPlayer
                self.player = QMediaPlayer()
                self.using_vlc = False
                print("✅ Qt MediaPlayer initialized (fallback)")
                
        except Exception as e:
            print(f"❌ Error initializing VLC, falling back to Qt MediaPlayer: {e}")
            self.player = QMediaPlayer()
            self.using_vlc = False
        
        self.current_song = None
        self.volume = 70
        self._temp_audio_file = None
        self.duration = 0
        
        # Set up position tracking timer
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(100)  # Update every 100ms
        
        # Set initial volume
        self.player.audio_set_volume(self.volume)
    
    def load_song(self, file_path):
        """Load a song file with VLC"""
        try:
            # Clean up previous temp file
            self._cleanup_temp_files()
            
            # Store original file path
            self.current_song = file_path
            
            # Check if file needs conversion for better compatibility
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Convert problematic formats if pydub is available
            if file_ext in ['.m4a', '.ogg', '.flac'] and PYDUB_AVAILABLE:
                print(f"🔄 Converting {file_ext} file for better compatibility...")
                converted_path = self._convert_audio_file(file_path)
                if converted_path:
                    file_path = converted_path
            
            # Create VLC media object
            media = self.vlc_instance.media_new(file_path)
            if media is None:
                raise Exception("Failed to create VLC media object")
            
            # Set media to player
            self.player.set_media(media)
            
            # Get duration (may take a moment to be available)
            QTimer.singleShot(500, self._get_duration)
            
            print(f"✅ Loaded song with VLC: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading song {file_path}: {e}")
            return False
    
    def _convert_audio_file(self, file_path):
        """Convert audio file to WAV for better compatibility"""
        if not PYDUB_AVAILABLE:
            return None
            
        try:
            # Create temporary WAV file
            temp_dir = tempfile.gettempdir()
            temp_filename = f"temp_audio_{int(time.time())}.wav"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Determine input format
            file_ext = os.path.splitext(file_path)[1].lower()
            format_map = {
                '.mp3': 'mp3',
                '.m4a': 'mp4',
                '.ogg': 'ogg',
                '.flac': 'flac',
                '.wav': 'wav'
            }
            
            input_format = format_map.get(file_ext, 'mp3')
            
            # Convert to WAV with VLC-compatible settings
            audio = AudioSegment.from_file(file_path, format=input_format)
            
            # Ensure compatible audio format
            audio = audio.set_frame_rate(44100)  # Standard sample rate
            audio = audio.set_channels(2)        # Stereo
            audio = audio.set_sample_width(2)    # 16-bit
            
            audio.export(temp_path, format="wav")
            
            # Store temp file path for cleanup
            self._temp_audio_file = temp_path
            
            print(f"✅ Converted {file_ext} to WAV: {os.path.basename(file_path)}")
            return temp_path
            
        except Exception as e:
            print(f"❌ Failed to convert audio file {file_path}: {e}")
            return None
    
    def play(self):
        """Play the current song"""
        if self.player.get_media() is not None:
            result = self.player.play()
            if result == 0:  # VLC returns 0 on success
                self.stateChanged.emit(1)  # Playing state
                print("▶️ Playing")
            else:
                print("❌ Failed to start playback")
    
    def pause(self):
        """Pause playback"""
        self.player.pause()
        self.stateChanged.emit(2)  # Paused state
        print("⏸️ Paused")
    
    def stop(self):
        """Stop playback and cleanup temporary files"""
        self.player.stop()
        self.stateChanged.emit(0)  # Stopped state
        self._cleanup_temp_files()
        print("⏹️ Stopped")
    
    def _cleanup_temp_files(self):
        """Clean up temporary audio files"""
        if self._temp_audio_file and os.path.exists(self._temp_audio_file):
            try:
                os.remove(self._temp_audio_file)
                print(f"🧹 Cleaned up temp file: {os.path.basename(self._temp_audio_file)}")
            except Exception as e:
                print(f"Error cleaning temp file: {e}")
            finally:
                self._temp_audio_file = None
    
    def set_volume(self, volume):
        """Set playback volume (0-100)"""
        self.volume = volume
        self.player.audio_set_volume(volume)
    
    def set_position(self, position):
        """Set playback position (in milliseconds)"""
        if self.duration > 0:
            # Convert position to percentage (0.0 - 1.0)
            pos_percent = position / self.duration
            self.player.set_position(pos_percent)
    
    def _update_position(self):
        """Update position and emit signals"""
        try:
            if self.player.get_media() is not None:
                # Get current position as percentage (0.0 - 1.0)
                pos_percent = self.player.get_position()
                
                if self.duration > 0 and pos_percent >= 0:
                    current_pos = int(pos_percent * self.duration)
                    self.positionChanged.emit(current_pos)
                
                # Check if song has ended
                state = self.player.get_state()
                if state == vlc.State.Ended:
                    self.stateChanged.emit(0)  # Stopped state
                    print("🏁 Song ended")
                    
        except Exception as e:
            # Silently handle VLC state query errors
            pass
    
    def _get_duration(self):
        """Get and emit duration"""
        try:
            duration_ms = self.player.get_length()
            if duration_ms > 0:
                self.duration = duration_ms
                self.durationChanged.emit(duration_ms)
                print(f"⏱️ Duration: {self.format_duration(duration_ms / 1000)}")
            else:
                # Try again in a moment if duration not available yet
                QTimer.singleShot(500, self._get_duration)
        except Exception as e:
            print(f"Error getting duration: {e}")
    
    def format_duration(self, duration_seconds):
        """Format duration in seconds to MM:SS format"""
        if duration_seconds is None or duration_seconds <= 0:
            return "0:00"
        
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def is_playing(self):
        """Check if music is currently playing"""
        try:
            state = self.player.get_state()
            return state == vlc.State.Playing
        except:
            return False

    def is_paused(self):
        """Check if music is paused"""
        try:
            state = self.player.get_state()
            return state == vlc.State.Paused
        except:
            return False
    
    def get_state_string(self):
        """Get current state as string for debugging"""
        try:
            state = self.player.get_state()
            state_map = {
                vlc.State.NothingSpecial: "Nothing Special",
                vlc.State.Opening: "Opening",
                vlc.State.Buffering: "Buffering", 
                vlc.State.Playing: "Playing",
                vlc.State.Paused: "Paused",
                vlc.State.Stopped: "Stopped",
                vlc.State.Ended: "Ended",
                vlc.State.Error: "Error"
            }
            return state_map.get(state, f"Unknown({state})")
        except:
            return "Unknown"
