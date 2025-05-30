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
    """Enhanced audio playback manager with VLC and Qt MediaPlayer support"""
    
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    mediaLoaded = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        
        # Initialize both players for hybrid support
        self.vlc_player = None
        self.qt_player = None
        self.using_vlc = False
        
        # Initialize VLC if available
        try:
            if VLC_AVAILABLE:
                self.vlc_instance = vlc.Instance('--no-xlib')  # Disable X11 for better compatibility
                self.vlc_player = self.vlc_instance.media_player_new()
                self.using_vlc = True
                print("✅ VLC audio player initialized")
        except Exception as e:
            print(f"❌ Error initializing VLC: {e}")
            self.vlc_player = None
        
        # Always initialize Qt MediaPlayer as fallback
        try:
            self.qt_player = QMediaPlayer()
            self.qt_player.stateChanged.connect(self._qt_state_changed)
            self.qt_player.positionChanged.connect(self._qt_position_changed)
            self.qt_player.durationChanged.connect(self._qt_duration_changed)
            self.qt_player.mediaStatusChanged.connect(self._qt_media_status_changed)
            if not self.using_vlc:
                print("✅ Qt MediaPlayer initialized (primary)")
            else:
                print("✅ Qt MediaPlayer initialized (fallback)")
        except Exception as e:
            print(f"❌ Error initializing Qt MediaPlayer: {e}")
            self.qt_player = None
        
        # Player state
        self.current_song = None
        self.volume = 70
        self._temp_audio_file = None
        self.duration = 0
        self._is_muted = False
        self._volume_before_mute = 70
        
        # Set up position tracking timer for VLC
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(100)  # Update every 100ms
        
        # Set initial volume
        self.set_volume(self.volume)
    def load_song(self, file_path):
        """Load a song file with automatic engine selection"""
        try:
            # Clean up previous temp file
            self._cleanup_temp_files()
            
            # Store original file path
            self.current_song = file_path
            
            # Check file existence
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Try VLC first if available
            if self.using_vlc and self.vlc_player:
                if self._load_with_vlc(file_path):
                    print(f"✅ Loaded with VLC: {os.path.basename(file_path)}")
                    self.mediaLoaded.emit(True)
                    return True
                else:
                    print("⚠️ VLC failed, trying Qt MediaPlayer...")
            
            # Try Qt MediaPlayer
            if self.qt_player:
                if self._load_with_qt(file_path):
                    print(f"✅ Loaded with Qt MediaPlayer: {os.path.basename(file_path)}")
                    self.using_vlc = False  # Switch to Qt for this file
                    self.mediaLoaded.emit(True)
                    return True
            
            # If both fail, try converting problematic formats
            if file_ext in ['.m4a', '.ogg', '.flac'] and PYDUB_AVAILABLE:
                print(f"🔄 Converting {file_ext} file for better compatibility...")
                converted_path = self._convert_audio_file(file_path)
                if converted_path:
                    # Try loading converted file
                    if self.qt_player:
                        if self._load_with_qt(converted_path):
                            print(f"✅ Loaded converted file with Qt MediaPlayer")
                            self.using_vlc = False
                            self.mediaLoaded.emit(True)
                            return True
            
            raise Exception("Failed to load with any available player")
            
        except Exception as e:
            print(f"❌ Error loading song {file_path}: {e}")
            self.mediaLoaded.emit(False)
            return False
    
    def _load_with_vlc(self, file_path):
        """Load file with VLC player"""
        try:
            if not self.vlc_player:
                return False
                
            # Create VLC media object
            media = self.vlc_instance.media_new(file_path)
            if media is None:
                return False
            
            # Set media to player
            self.vlc_player.set_media(media)
            
            # Get duration (may take a moment to be available)
            QTimer.singleShot(500, self._get_duration)
            
            return True
            
        except Exception as e:
            print(f"VLC load error: {e}")
            return False
    
    def _load_with_qt(self, file_path):
        """Load file with Qt MediaPlayer"""
        try:
            if not self.qt_player:
                return False
                
            # Create media content
            url = QUrl.fromLocalFile(file_path)
            media_content = QMediaContent(url)
            
            # Set media to player
            self.qt_player.setMedia(media_content)
            
            return True
            
        except Exception as e:
            print(f"Qt MediaPlayer load error: {e}")
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
        try:
            if self.using_vlc and self.vlc_player:
                if self.vlc_player.get_media() is not None:
                    result = self.vlc_player.play()
                    if result == 0:  # VLC returns 0 on success
                        self.stateChanged.emit(1)  # Playing state
                        print("▶️ Playing (VLC)")
                        return True
            elif self.qt_player:
                if self.qt_player.media().canonicalUrl().isValid():
                    self.qt_player.play()
                    print("▶️ Playing (Qt)")
                    return True
            
            print("❌ Failed to start playback")
            return False
        except Exception as e:
            print(f"❌ Play error: {e}")
            return False
    
    def pause(self):
        """Pause playback"""
        try:
            if self.using_vlc and self.vlc_player:
                self.vlc_player.pause()
                self.stateChanged.emit(2)  # Paused state
                print("⏸️ Paused (VLC)")
            elif self.qt_player:
                self.qt_player.pause()
                print("⏸️ Paused (Qt)")
        except Exception as e:
            print(f"❌ Pause error: {e}")
    
    def stop(self):
        """Stop playback and cleanup temporary files"""
        try:
            if self.using_vlc and self.vlc_player:
                self.vlc_player.stop()
                self.stateChanged.emit(0)  # Stopped state
                print("⏹️ Stopped (VLC)")
            elif self.qt_player:
                self.qt_player.stop()
                print("⏹️ Stopped (Qt)")
            
            self._cleanup_temp_files()
        except Exception as e:
            print(f"❌ Stop error: {e}")
    
    def set_volume(self, volume):
        """Set playback volume (0-100)"""
        try:
            self.volume = max(0, min(100, volume))  # Clamp to 0-100
            
            if not self._is_muted:
                if self.using_vlc and self.vlc_player:
                    self.vlc_player.audio_set_volume(self.volume)
                elif self.qt_player:
                    # Qt MediaPlayer uses 0-100 range
                    self.qt_player.setVolume(self.volume)
        except Exception as e:
            print(f"❌ Volume error: {e}")
    
    def get_volume(self):
        """Get current volume"""
        return self.volume
    
    def mute(self):
        """Mute audio"""
        if not self._is_muted:
            self._volume_before_mute = self.volume
            self._is_muted = True
            try:
                if self.using_vlc and self.vlc_player:
                    self.vlc_player.audio_set_volume(0)
                elif self.qt_player:
                    self.qt_player.setVolume(0)
                print("🔇 Muted")
            except Exception as e:
                print(f"❌ Mute error: {e}")
    
    def unmute(self):
        """Unmute audio"""
        if self._is_muted:
            self._is_muted = False
            self.set_volume(self._volume_before_mute)
            print("🔊 Unmuted")
    
    def toggle_mute(self):
        """Toggle mute state"""
        if self._is_muted:
            self.unmute()
        else:
            self.mute()
    
    def is_muted(self):
        """Check if audio is muted"""
        return self._is_muted
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
    
    def set_position(self, position):
        """Set playback position (in milliseconds)"""
        try:
            if self.using_vlc and self.vlc_player and self.duration > 0:
                # Convert position to percentage (0.0 - 1.0)
                pos_percent = position / self.duration
                self.vlc_player.set_position(pos_percent)
            elif self.qt_player and self.duration > 0:
                # Qt MediaPlayer uses milliseconds
                self.qt_player.setPosition(position)
        except Exception as e:
            print(f"❌ Position error: {e}")
    
    def get_position(self):
        """Get current position in milliseconds"""
        try:
            if self.using_vlc and self.vlc_player:
                pos_percent = self.vlc_player.get_position()
                if self.duration > 0 and pos_percent >= 0:
                    return int(pos_percent * self.duration)
            elif self.qt_player:
                return self.qt_player.position()
        except Exception as e:
            pass
        return 0
    
    def get_duration(self):
        """Get duration in milliseconds"""
        return self.duration
    def _update_position(self):
        """Update position and emit signals (for VLC only, Qt uses its own signals)"""
        try:
            if self.using_vlc and self.vlc_player and self.vlc_player.get_media() is not None:
                # Get current position as percentage (0.0 - 1.0)
                pos_percent = self.vlc_player.get_position()
                
                if self.duration > 0 and pos_percent >= 0:
                    current_pos = int(pos_percent * self.duration)
                    self.positionChanged.emit(current_pos)
                
                # Check if song has ended
                state = self.vlc_player.get_state()
                if state == vlc.State.Ended:
                    self.stateChanged.emit(0)  # Stopped state
                    print("🏁 Song ended (VLC)")
                elif state == vlc.State.Playing:
                    self.stateChanged.emit(1)  # Playing state
                elif state == vlc.State.Paused:
                    self.stateChanged.emit(2)  # Paused state
                    
        except Exception as e:
            # Silently handle VLC state query errors
            pass
    
    def _get_duration(self):
        """Get and emit duration (for VLC)"""
        try:
            if self.using_vlc and self.vlc_player:
                duration_ms = self.vlc_player.get_length()
                if duration_ms > 0:
                    self.duration = duration_ms
                    self.durationChanged.emit(duration_ms)
                    print(f"⏱️ Duration: {self.format_duration(duration_ms / 1000)} (VLC)")
                else:
                    # Try again in a moment if duration not available yet
                    QTimer.singleShot(500, self._get_duration)
        except Exception as e:
            print(f"Error getting duration: {e}")
    
    # Qt MediaPlayer signal handlers
    def _qt_state_changed(self, state):
        """Handle Qt MediaPlayer state changes"""
        if not self.using_vlc:
            state_map = {
                QMediaPlayer.StoppedState: 0,
                QMediaPlayer.PlayingState: 1,
                QMediaPlayer.PausedState: 2
            }
            mapped_state = state_map.get(state, 0)
            self.stateChanged.emit(mapped_state)
            
            if state == QMediaPlayer.StoppedState:
                print("🏁 Song ended (Qt)")
    
    def _qt_position_changed(self, position):
        """Handle Qt MediaPlayer position changes"""
        if not self.using_vlc:
            self.positionChanged.emit(position)
    
    def _qt_duration_changed(self, duration):
        """Handle Qt MediaPlayer duration changes"""
        if not self.using_vlc and duration > 0:
            self.duration = duration
            self.durationChanged.emit(duration)
            print(f"⏱️ Duration: {self.format_duration(duration / 1000)} (Qt)")
    
    def _qt_media_status_changed(self, status):
        """Handle Qt MediaPlayer media status changes"""
        if not self.using_vlc:
            if status == QMediaPlayer.LoadedMedia:
                print("✅ Media loaded (Qt)")
            elif status == QMediaPlayer.InvalidMedia:
                print("❌ Invalid media (Qt)")
                self.mediaLoaded.emit(False)
    
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
            if self.using_vlc and self.vlc_player:
                state = self.vlc_player.get_state()
                return state == vlc.State.Playing
            elif self.qt_player:
                return self.qt_player.state() == QMediaPlayer.PlayingState
        except:
            pass
        return False

    def is_paused(self):
        """Check if music is paused"""
        try:
            if self.using_vlc and self.vlc_player:
                state = self.vlc_player.get_state()
                return state == vlc.State.Paused
            elif self.qt_player:
                return self.qt_player.state() == QMediaPlayer.PausedState
        except:
            pass
        return False
    
    def is_stopped(self):
        """Check if music is stopped"""
        try:
            if self.using_vlc and self.vlc_player:
                state = self.vlc_player.get_state()
                return state in [vlc.State.Stopped, vlc.State.Ended, vlc.State.NothingSpecial]
            elif self.qt_player:
                return self.qt_player.state() == QMediaPlayer.StoppedState
        except:
            pass
        return True
    
    def get_state_string(self):
        """Get current state as string for debugging"""
        try:
            if self.using_vlc and self.vlc_player:
                state = self.vlc_player.get_state()
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
                return f"{state_map.get(state, f'Unknown({state})')} (VLC)"
            elif self.qt_player:
                state = self.qt_player.state()
                state_map = {
                    QMediaPlayer.StoppedState: "Stopped",
                    QMediaPlayer.PlayingState: "Playing",
                    QMediaPlayer.PausedState: "Paused"
                }
                return f"{state_map.get(state, f'Unknown({state})')} (Qt)"
        except:
            pass
        return "Unknown"
    
    def get_engine_info(self):
        """Get information about the current audio engine"""
        engine = "VLC" if self.using_vlc else "Qt MediaPlayer"
        vlc_available = "Yes" if VLC_AVAILABLE else "No"
        pydub_available = "Yes" if PYDUB_AVAILABLE else "No"
        
        return {
            "current_engine": engine,
            "vlc_available": vlc_available,
            "pydub_available": pydub_available,
            "current_song": self.current_song,
            "volume": self.volume,
            "is_muted": self._is_muted
        }
