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
    
    # Signals
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    mediaLoaded = pyqtSignal(bool)
    songEnded = pyqtSignal()  # MAKE SURE THIS SIGNAL EXISTS

    # ========================================
    # CONFIGURABLE CONTROL VARIABLES
    # ========================================
    
    # Engine Selection
    PREFER_VLC = True  # Set to False to prefer Qt MediaPlayer over VLC
    ALLOW_ENGINE_FALLBACK = True  # Allow fallback between engines on failure
    
    # VLC Settings
    VLC_QUIET_MODE = True  # Reduce VLC console output
    VLC_NO_VIDEO = True  # Disable video output for VLC
    VLC_AUDIO_OUTPUT = "directsound"  # Windows: directsound, Linux: pulse, macOS: auhal
    VLC_CACHE_SIZE = 1000  # VLC network cache in ms (default: 1000)
    
    # Rate Limiting & Performance
    MAX_SEEKS_PER_SECOND = 10  # Maximum position seeks per second to prevent buffer overflow
    POSITION_UPDATE_INTERVAL = 100  # Position update timer interval in ms
    STATE_CHECK_INTERVAL = 50  # VLC state monitoring interval in ms
    
    # File Conversion Settings
    ENABLE_M4A_CONVERSION = True  # Convert M4A files to temporary WAV for better compatibility
    TEMP_FILE_CLEANUP = True  # Auto-cleanup temporary converted files
    CONVERSION_SAMPLE_RATE = 44100  # Sample rate for converted files
    CONVERSION_CHANNELS = 2  # Number of channels for converted files (1=mono, 2=stereo)
    
    # Volume & Audio Control
    DEFAULT_VOLUME = 70  # Default volume level (0-100)
    ENABLE_MUTE_MEMORY = True  # Remember volume level when muting/unmuting
    VOLUME_STEP_SIZE = 5  # Volume increment/decrement step size
    
    # Error Handling & Reliability
    MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for media loading
    RETRY_DELAY_MS = 500  # Delay between retry attempts in milliseconds
    ENABLE_DETAILED_LOGGING = False  # Enable detailed debug logging
    AUTO_RECOVER_ON_ERROR = True  # Attempt to recover from playback errors
    
    # State Management
    EMIT_REDUNDANT_STATES = False  # Emit state changes even if state hasn't changed
    TRACK_SEEK_STATE = True  # Track seeking state to prevent conflicts
    ENABLE_SMOOTH_SEEKING = True  # Use smooth seeking to reduce audio glitches
    
    # Qt MediaPlayer Fallback Settings
    QT_BUFFER_SIZE = 5000  # Qt MediaPlayer buffer size hint in ms
    QT_NOTIFICATION_INTERVAL = 100  # Qt position notification interval in ms
    
    # ========================================
    
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(int)
    mediaLoaded = pyqtSignal(bool)
    songEnded = pyqtSignal()  # NEW: Signal for song end
    def __init__(self):
        super().__init__()
        
        # Initialize both players for hybrid support
        self.vlc_player = None
        self.qt_player = None
        self.using_vlc = False
        
        # Initialize VLC if available and preferred with configurable options
        try:
            if VLC_AVAILABLE and self.PREFER_VLC:
                # Build VLC options from configuration
                vlc_options = ['--no-xlib']  # Base compatibility option
                
                if self.VLC_QUIET_MODE:
                    vlc_options.append('--quiet')
                
                if self.VLC_NO_VIDEO:
                    vlc_options.append('--no-video')
                
                if self.VLC_AUDIO_OUTPUT:
                    vlc_options.append(f'--aout={self.VLC_AUDIO_OUTPUT}')
                
                vlc_options.extend([
                    '--input-repeat=0',  # Disable input repeat
                    f'--network-caching={self.VLC_CACHE_SIZE}'
                ])
                
                self.vlc_instance = vlc.Instance(vlc_options)
                self.vlc_player = self.vlc_instance.media_player_new()
                self.using_vlc = True
                
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"✅ VLC audio player initialized with options: {vlc_options}")
                else:
                    print("✅ VLC audio player initialized")
        except Exception as e:
            if self.ENABLE_DETAILED_LOGGING:
                print(f"❌ Error initializing VLC: {e}")
            if self.ALLOW_ENGINE_FALLBACK:
                print("🔄 Falling back to Qt MediaPlayer")
            self.vlc_player = None
        
        # Initialize Qt MediaPlayer as fallback or primary (if VLC not preferred)
        try:
            self.qt_player = QMediaPlayer()
            
            # Configure Qt MediaPlayer with configurable settings
            if hasattr(self.qt_player, 'setBufferSize'):
                self.qt_player.setBufferSize(self.QT_BUFFER_SIZE)
            
            self.qt_player.setNotifyInterval(self.QT_NOTIFICATION_INTERVAL)
            
            # Connect Qt MediaPlayer signals
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
        
        # Player state with configurable defaults
        self.current_song = None
        self.volume = self.DEFAULT_VOLUME
        self._temp_audio_file = None
        self.duration = 0
        self._is_muted = False
        self._volume_before_mute = self.DEFAULT_VOLUME
        self._song_ended = False
        self._is_seeking = False if self.TRACK_SEEK_STATE else None
        self._last_seek_time = 0
        self._last_vlc_state = None  # Track last VLC state to prevent redundant emissions
        self._retry_count = 0  # Track retry attempts
        
        # Set up position tracking timer for VLC with configurable interval
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(self.POSITION_UPDATE_INTERVAL)
        
        # Set up VLC state monitoring timer with configurable interval
        # In the __init__ method, replace the state timer section with:
        # Set up VLC state monitoring timer with configurable interval (optional)
        if self.using_vlc and hasattr(self, 'STATE_CHECK_INTERVAL') and self.STATE_CHECK_INTERVAL > 0:
            self.state_timer = QTimer()
            self.state_timer.timeout.connect(self._check_vlc_state)
            self.state_timer.start(self.STATE_CHECK_INTERVAL)
            if self.ENABLE_DETAILED_LOGGING:
                print(f"✅ VLC state monitor started ({self.STATE_CHECK_INTERVAL}ms interval)")
        
        # Set initial volume
        self.set_volume(self.volume)

    def load_song(self, file_path):
        """Load a song file with automatic engine selection"""
        try:
            # Clean up previous temp file
            self._cleanup_temp_files()
            
            # Reset song ended flag
            self._song_ended = False
            
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
                    # Restart position timer for new song
                    if not self.position_timer.isActive():
                        self.position_timer.start(100)
                    self.mediaLoaded.emit(True)
                    return True
                else:
                    print("⚠️ VLC failed, trying Qt MediaPlayer...")
            
            # Try Qt MediaPlayer
            if self.qt_player:
                if self._load_with_qt(file_path):
                    print(f"✅ Loaded with Qt MediaPlayer: {os.path.basename(file_path)}")
                    self.using_vlc = False  # Switch to Qt for this file
                    # Stop VLC position timer when using Qt
                    self.position_timer.stop()
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
                            self.position_timer.stop()
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
        """Convert audio file to WAV for better compatibility with configurable settings"""
        if not PYDUB_AVAILABLE or not self.ENABLE_M4A_CONVERSION:
            if self.ENABLE_DETAILED_LOGGING:
                reason = "pydub not available" if not PYDUB_AVAILABLE else "conversion disabled"
                print(f"⚠️ Skipping conversion ({reason})")
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
            
            if self.ENABLE_DETAILED_LOGGING:
                print(f"🔄 Converting {file_ext} file using format '{input_format}'")
            
            # Convert to WAV with configurable settings
            audio = AudioSegment.from_file(file_path, format=input_format)
            
            # Apply configurable audio format settings
            audio = audio.set_frame_rate(self.CONVERSION_SAMPLE_RATE)
            audio = audio.set_channels(self.CONVERSION_CHANNELS)
            audio = audio.set_sample_width(2)  # 16-bit (fixed for compatibility)
            
            audio.export(temp_path, format="wav")
            
            # Store temp file path for cleanup (if cleanup is enabled)
            if self.TEMP_FILE_CLEANUP:
                self._temp_audio_file = temp_path
            
            if self.ENABLE_DETAILED_LOGGING:
                print(f"✅ Converted {file_ext} to WAV with {self.CONVERSION_SAMPLE_RATE}Hz, {self.CONVERSION_CHANNELS}ch: {os.path.basename(file_path)}")
            else:
                print(f"✅ Converted {file_ext} to WAV: {os.path.basename(file_path)}")
            return temp_path
            
        except Exception as e:
            if self.ENABLE_DETAILED_LOGGING:
                print(f"❌ Failed to convert audio file {file_path}: {e}")
            else:
                print(f"❌ Conversion failed: {os.path.basename(file_path)}")
            return None
        
    def play(self):
        """Play the current song"""
        try:
            if self.using_vlc and self.vlc_player:
                if self.vlc_player.get_media() is not None:
                    # Reset song ended flag when playing
                    self._song_ended = False
                    
                    # Only print play message if not already playing
                    current_state = self.vlc_player.get_state()
                    if current_state != vlc.State.Playing:
                        # Restart position timer
                        if not self.position_timer.isActive():
                            self.position_timer.start(100)
                        
                        result = self.vlc_player.play()
                        if result == 0:  # VLC returns 0 on success
                            self.stateChanged.emit(1)  # Playing state
                            print("▶️ Playing (VLC)")
                            return True
                    else:
                        print("ℹ️ Already playing")
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

    def _check_vlc_state(self):
        """Check VLC state periodically for better state management"""
        try:
            if self.using_vlc and self.vlc_player and self.vlc_player.get_media() is not None:
                state = self.vlc_player.get_state()
                
                # Handle state changes based on configuration
                if not hasattr(self, '_last_vlc_state'):
                    self._last_vlc_state = None
                    
                should_emit = (state != self._last_vlc_state) or self.EMIT_REDUNDANT_STATES
                
                if should_emit:
                    self._last_vlc_state = state
                    
                    if state == vlc.State.Ended:
                        if not self._song_ended:
                            self._song_ended = True
                            self.stateChanged.emit(0)  # Stopped state
                            self.songEnded.emit()  # Emit signal for repeat/next functionality
                            if self.ENABLE_DETAILED_LOGGING:
                                print("🏁 Song ended (VLC) - state check")
                            else:
                                print("🏁 Song ended (VLC)")
                            # Stop the state timer when song ends
                            if hasattr(self, 'state_timer'):
                                self.state_timer.stop()
                    elif state == vlc.State.Playing:
                        self._song_ended = False
                        self.stateChanged.emit(1)  # Playing state
                        if self.ENABLE_DETAILED_LOGGING:
                            print("▶️ State: Playing (VLC) - state check")
                    elif state == vlc.State.Paused:
                        self.stateChanged.emit(2)  # Paused state
                        if self.ENABLE_DETAILED_LOGGING:
                            print("⏸️ State: Paused (VLC) - state check")
                    elif state == vlc.State.Stopped:
                        self.stateChanged.emit(0)  # Stopped state
                        if self.ENABLE_DETAILED_LOGGING:
                            print("⏹️ State: Stopped (VLC) - state check")
                    elif state == vlc.State.Error:
                        if self.AUTO_RECOVER_ON_ERROR and self.current_song:
                            print("🔄 VLC error detected - attempting recovery")
                            self._attempt_recovery()
                        else:
                            print("❌ VLC error state detected")
                            
        except Exception as e:
            # Silently handle VLC state query errors unless detailed logging is enabled
            if self.ENABLE_DETAILED_LOGGING:
                print(f"❌ VLC state check error: {e}")
            pass

    def _attempt_recovery(self):
        """Attempt to recover from VLC errors with configurable retry logic"""
        try:
            if self._retry_count < self.MAX_RETRY_ATTEMPTS:
                self._retry_count += 1
                
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"🔄 Recovery attempt {self._retry_count}/{self.MAX_RETRY_ATTEMPTS}")
                else:
                    print(f"🔄 Recovery attempt {self._retry_count}")
                
                # Stop current playback
                if self.vlc_player:
                    self.vlc_player.stop()
                
                # Wait a bit before retrying
                QTimer.singleShot(self.RETRY_DELAY_MS, self._retry_load_current_song)
            else:
                print(f"❌ Recovery failed after {self.MAX_RETRY_ATTEMPTS} attempts")
                self._retry_count = 0
                
                # Try fallback to Qt MediaPlayer if available
                if self.ALLOW_ENGINE_FALLBACK and self.qt_player and self.current_song:
                    print("🔄 Falling back to Qt MediaPlayer")
                    self.using_vlc = False
                    if self._load_with_qt(self.current_song):
                        print("✅ Fallback to Qt successful")
                        self.mediaLoaded.emit(True)
                    else:
                        print("❌ Fallback to Qt failed")
                        self.mediaLoaded.emit(False)
                        
        except Exception as e:
            if self.ENABLE_DETAILED_LOGGING:
                print(f"❌ Recovery error: {e}")
            self._retry_count = 0

    def _retry_load_current_song(self):
        """Retry loading the current song"""
        try:
            if self.current_song and os.path.exists(self.current_song):
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"🔄 Retrying load: {os.path.basename(self.current_song)}")
                
                if self._load_with_vlc(self.current_song):
                    print("✅ Recovery successful")
                    self._retry_count = 0  # Reset retry count on success
                    self.mediaLoaded.emit(True)
                else:
                    # If this retry failed, attempt recovery again
                    self._attempt_recovery()
            else:
                print("❌ Current song no longer exists for retry")
                self._retry_count = 0
                
        except Exception as e:
            if self.ENABLE_DETAILED_LOGGING:
                print(f"❌ Retry load error: {e}")
            self._attempt_recovery()

    def set_volume(self, volume):
        """Set playback volume (0-100) with configurable constraints"""
        try:
            self.volume = max(0, min(100, volume))  # Clamp to 0-100
            
            # Only update volume if not muted (or mute memory is disabled)
            if not self._is_muted or not self.ENABLE_MUTE_MEMORY:
                if self.using_vlc and self.vlc_player:
                    self.vlc_player.audio_set_volume(self.volume)
                elif self.qt_player:
                    # Qt MediaPlayer uses 0-100 range
                    self.qt_player.setVolume(self.volume)
                    
            if self.ENABLE_DETAILED_LOGGING:
                print(f"🔊 Volume set to {self.volume}% (muted: {self._is_muted})")
        except Exception as e:
            print(f"❌ Volume error: {e}")

    def get_volume(self):
        """Get current volume"""
        return self.volume

    def mute(self):
        """Mute audio with configurable memory"""
        if not self._is_muted:
            if self.ENABLE_MUTE_MEMORY:
                self._volume_before_mute = self.volume
            else:
                self._volume_before_mute = self.DEFAULT_VOLUME
                
            self._is_muted = True
            try:
                if self.using_vlc and self.vlc_player:
                    self.vlc_player.audio_set_volume(0)
                elif self.qt_player:
                    self.qt_player.setVolume(0)
                    
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"🔇 Muted (saved volume: {self._volume_before_mute})")
                else:
                    print("🔇 Muted")
            except Exception as e:
                print(f"❌ Mute error: {e}")

    def unmute(self):
        """Unmute audio with configurable memory"""
        if self._is_muted:
            self._is_muted = False
            restore_volume = self._volume_before_mute if self.ENABLE_MUTE_MEMORY else self.DEFAULT_VOLUME
            self.set_volume(restore_volume)
            
            if self.ENABLE_DETAILED_LOGGING:
                print(f"🔊 Unmuted (restored volume: {restore_volume})")
            else:
                print("🔊 Unmuted")

    def toggle_mute(self):
        """Toggle mute state"""
        if self._is_muted:
            self.unmute()
        else:
            self.mute()
            
    def increase_volume(self, amount=None):
        """Increase volume by configurable amount"""
        step = amount if amount is not None else self.VOLUME_STEP_SIZE
        new_volume = min(100, self.volume + step)
        self.set_volume(new_volume)
        return new_volume
        
    def decrease_volume(self, amount=None):
        """Decrease volume by configurable amount"""
        step = amount if amount is not None else self.VOLUME_STEP_SIZE
        new_volume = max(0, self.volume - step)
        self.set_volume(new_volume)
        return new_volume
    
    def is_muted(self):
        """Check if audio is muted"""
        return self._is_muted

    def _cleanup_temp_files(self):
        """Clean up temporary audio files with configurable cleanup"""
        if self.TEMP_FILE_CLEANUP and self._temp_audio_file and os.path.exists(self._temp_audio_file):
            try:
                os.remove(self._temp_audio_file)
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"🧹 Cleaned up temp file: {os.path.basename(self._temp_audio_file)}")
                else:
                    print(f"🧹 Cleaned up temp file")
            except Exception as e:
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"❌ Error cleaning temp file: {e}")
                else:
                    print("❌ Error cleaning temp file")
            finally:
                self._temp_audio_file = None
        elif self.ENABLE_DETAILED_LOGGING:
            print("🧹 No temp files to clean or cleanup disabled")
    def set_position(self, position):
        """Set playback position (in milliseconds) with configurable rate limiting"""
        try:
            import time
            current_time = time.time()
            
            # Rate limit seeking to prevent VLC fifo overflow (configurable)
            min_seek_interval = 1.0 / self.MAX_SEEKS_PER_SECOND
            if current_time - self._last_seek_time < min_seek_interval:
                if self.ENABLE_DETAILED_LOGGING:
                    print(f"🚫 Seek rate limited (max {self.MAX_SEEKS_PER_SECOND}/s)")
                return
            
            self._last_seek_time = current_time
            
            # Set seeking state if tracking is enabled
            if self.TRACK_SEEK_STATE:
                self._is_seeking = True
            
            if self.using_vlc and self.vlc_player and self.duration > 0:
                # Reset song ended flag when seeking
                self._song_ended = False
                
                # Convert position to percentage (0.0 - 1.0)
                pos_percent = max(0.0, min(1.0, position / self.duration))
                
                # Set position
                self.vlc_player.set_position(pos_percent)
                
                # If we're seeking after song ended, restart playback
                current_state = self.vlc_player.get_state()
                if current_state == vlc.State.Ended:
                    self.vlc_player.pause()
                    QTimer.singleShot(100, lambda: self.vlc_player.play())
                    print(f"🔄 Seeking after end - restarting playback at {position/1000:.1f}s")
                
                # Restart position timer if it was stopped
                if not self.position_timer.isActive():
                    self.position_timer.start(100)
                    
            elif self.qt_player and self.duration > 0:
                # Qt MediaPlayer uses milliseconds
                self.qt_player.setPosition(int(position))
              # Reset seeking flag after a short delay (only if tracking is enabled)
            if self.TRACK_SEEK_STATE:
                QTimer.singleShot(200, lambda: setattr(self, '_is_seeking', False))
                
        except Exception as e:
            print(f"❌ Position error: {e}")
            if self.TRACK_SEEK_STATE:
                self._is_seeking = False
    
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
                
                # Check state changes only (not every update)
                state = self.vlc_player.get_state()
                
                # Only handle state changes to avoid spam
                if not hasattr(self, '_last_vlc_state'):
                    self._last_vlc_state = None
                    
                if state != self._last_vlc_state:
                    self._last_vlc_state = state
                    
                    if state == vlc.State.Ended:
                        if not self._song_ended:
                            self._song_ended = True
                            self.stateChanged.emit(0)  # Stopped state
                            self.songEnded.emit()  # EMIT THIS SIGNAL FOR REPEAT FUNCTIONALITY
                            print("🏁 Song ended (VLC)")
                            # Don't stop timer here - let repeat logic handle it
                    elif state == vlc.State.Playing:
                        self._song_ended = False
                        self.stateChanged.emit(1)  # Playing state
                    elif state == vlc.State.Paused:
                        self.stateChanged.emit(2)  # Paused state
                    elif state == vlc.State.Stopped:
                        self.stateChanged.emit(0)  # Stopped state
                        
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
