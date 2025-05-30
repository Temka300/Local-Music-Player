#!/usr/bin/env python3
"""
🎵 Local Spotify Qt - Music Player for Local Files
A comprehensive music player with modern PyQt interface for local music libraries
"""

import sys
import os
import json
import threading
import time
import random
from pathlib import Path
import sqlite3
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
import shutil
import tempfile

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# Import YouTube downloader
try:
    from youtube_downloader import YouTubeDownloader, YouTubeDownloadThread
    YOUTUBE_AVAILABLE = True
    print("✅ YouTube downloader available")
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("⚠️ YouTube downloader not available")
    # Create dummy classes to avoid errors
    class YouTubeDownloader:
        pass
    class YouTubeDownloadThread:
        pass

# Import pydub for M4A conversion (optional dependency)
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("✅ pydub available - M4A conversion supported")
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub not available - M4A files may have playback issues")
    print("💡 Install with: pip install pydub")

# Import VLC for better audio playback
try:
    import vlc
    VLC_AVAILABLE = True
    print("✅ python-vlc available - Enhanced audio playback")
except ImportError:
    VLC_AVAILABLE = False
    print("⚠️ python-vlc not available - Install with: pip install python-vlc")
    print("💡 Falling back to Qt multimedia (may have codec issues)")


# Custom delegate to control which columns are editable
class EditableColumnsDelegate(QItemDelegate):
    """Custom delegate that only allows editing of specific columns"""
    
    def __init__(self, editable_columns, parent=None):
        super().__init__(parent)
        self.editable_columns = editable_columns
    
    def createEditor(self, parent, option, index):
        """Create editor only for allowed columns"""
        if index.column() in self.editable_columns:
            editor = QLineEdit(parent)
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #282828;
                    color: #FFFFFF;
                    border: 2px solid #1DB954;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }
            """)
            return editor
        return None
    
    def setEditorData(self, editor, index):
        """Set the data to be edited"""
        if isinstance(editor, QLineEdit):
            editor.setText(index.model().data(index, Qt.DisplayRole))
    
    def setModelData(self, editor, model, index):
        """Set the edited data back to the model"""
        if isinstance(editor, QLineEdit):
            model.setData(index, editor.text(), Qt.EditRole)


class MusicDatabase:
    """Database manager for music library"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Create database in the same folder as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(script_dir, "music_library.db")
        else:
            self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Songs table with all required columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                artist TEXT,
                album TEXT,
                year TEXT,
                genre TEXT,
                duration REAL,
                file_path TEXT UNIQUE,
                album_art BLOB,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'local',
                youtube_url TEXT,
                youtube_id TEXT
            )
        ''')
        
        # Check if the new columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(songs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'source' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN source TEXT DEFAULT "local"')
            print("✅ Added 'source' column to songs table")
        
        if 'youtube_url' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN youtube_url TEXT')
            print("✅ Added 'youtube_url' column to songs table")
        
        if 'youtube_id' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN youtube_id TEXT')
            print("✅ Added 'youtube_id' column to songs table")
        
        # Playlists table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Playlist songs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id INTEGER,
                song_id INTEGER,
                position INTEGER,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id),
                FOREIGN KEY (song_id) REFERENCES songs (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_song(self, song_data):
        """Add a song to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Handle both old format (8 fields) and new format (11 fields)
            if len(song_data) == 8:
                # Old format: title, artist, album, year, genre, duration, file_path, album_art
                cursor.execute('''
                    INSERT OR REPLACE INTO songs 
                    (title, artist, album, year, genre, duration, file_path, album_art, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'local')
                ''', song_data)
                print(f"✅ Added local song: {song_data[0]} by {song_data[1]}")
            elif len(song_data) == 11:
                # New format: title, artist, album, year, genre, duration, file_path, album_art, source, youtube_url, youtube_id
                cursor.execute('''
                    INSERT OR REPLACE INTO songs 
                    (title, artist, album, year, genre, duration, file_path, album_art, source, youtube_url, youtube_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', song_data)
                print(f"✅ Added YouTube song: {song_data[0]} by {song_data[1]}")
            else:
                print(f"❌ Invalid song_data length: {len(song_data)}")
                print(f"❌ Song data: {song_data}")
                return None
            
            conn.commit()
            return cursor.lastrowid
        
        except Exception as e:
            print(f"❌ Error adding song to database: {e}")
            print(f"❌ Song data: {song_data}")
            print(f"❌ Song data length: {len(song_data)}")
            return None
        finally:
            conn.close()
    
    def get_all_songs(self):
        """Get all songs from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM songs ORDER BY artist, album, title')
        songs = cursor.fetchall()
        conn.close()
        return songs
    
    def search_songs(self, query):
        """Search for songs by title, artist, or album"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM songs 
            WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?
            ORDER BY artist, album, title
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        songs = cursor.fetchall()
        conn.close()
        return songs
    
    def create_playlist(self, name, description=""):
        """Create a new playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO playlists (name, description) VALUES (?, ?)', 
                         (name, description))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    def get_playlists(self):
        """Get all playlists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM playlists ORDER BY name')
        playlists = cursor.fetchall()
        conn.close()
        return playlists
    
    def add_song_to_playlist(self, playlist_id, song_id):
        """Add a song to a playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get next position
        cursor.execute('SELECT MAX(position) FROM playlist_songs WHERE playlist_id = ?', 
                      (playlist_id,))
        result = cursor.fetchone()
        position = (result[0] or 0) + 1
        
        cursor.execute('''
            INSERT INTO playlist_songs (playlist_id, song_id, position)
            VALUES (?, ?, ?)
        ''', (playlist_id, song_id, position))
        
        conn.commit()
        conn.close()
    
    def get_playlist_songs(self, playlist_id):
        """Get all songs in a playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.* FROM songs s
            JOIN playlist_songs ps ON s.id = ps.song_id
            WHERE ps.playlist_id = ?
            ORDER BY ps.position
        ''', (playlist_id,))
        
        songs = cursor.fetchall()
        conn.close()
        return songs
    
    def remove_song(self, song_id):
        """Remove a song from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Remove song from playlists first
            cursor.execute('DELETE FROM playlist_songs WHERE song_id = ?', (song_id,))
            # Remove the song itself
            cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing song {song_id}: {e}")
            return False
        finally:
            conn.close()
    
    def update_song_metadata(self, song_id, field, value):
        """Update a specific field of a song in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Validate field name to prevent SQL injection
            allowed_fields = ['title', 'artist', 'album', 'year', 'genre']
            if field not in allowed_fields:
                print(f"Error: Field '{field}' is not allowed for update")
                return False
            
            # Update the field
            query = f'UPDATE songs SET {field} = ? WHERE id = ?'
            cursor.execute(query, (value, song_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating song {song_id} field {field}: {e}")
            return False
        finally:
            conn.close()
    
    def cleanup_missing_files(self, musics_folder_path):
        """Remove songs from database if their files no longer exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, file_path FROM songs')
        all_songs = cursor.fetchall()
        
        removed_count = 0
        for song_id, file_path in all_songs:
            if not os.path.exists(file_path):
                print(f"🗑️ Removing missing file from database: {os.path.basename(file_path)}")
                # Remove from playlists first
                cursor.execute('DELETE FROM playlist_songs WHERE song_id = ?', (song_id,))
                # Remove the song
                cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
                removed_count += 1
        
        if removed_count > 0:
            conn.commit()
            print(f"✅ Cleaned up {removed_count} missing files from database")
        
        conn.close()
        return removed_count


class MusicLibraryOrganizer:
    """Handles file organization and management for music library"""
    
    def __init__(self, base_path):
        self.base_path = base_path
        self.musics_folder = os.path.join(base_path, "musics")
        self.settings_file = os.path.join(base_path, "library_settings.json")
        self.settings = self.load_settings()
        
        # Ensure musics directory exists
        os.makedirs(self.musics_folder, exist_ok=True)
        print(f"📁 Music library folder: {self.musics_folder}")
    
    def load_settings(self):
        """Load library settings"""
        default_settings = {
            "organize_files": True,  # Always organize files in musics folder
            "copy_files": True,      # Always copy files to ensure availability
            "folder_structure": "artist/album",  # or "artist/year/album", "album", etc.
            "musics_folder": "musics"
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save library settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        # Remove extra spaces and dots
        filename = filename.strip('. ')
        return filename if filename else "Unknown"
    
    def organize_file(self, metadata, original_path):
        """Organize a music file based on metadata and copy to musics folder"""
        # Sanitize metadata
        artist = self.sanitize_filename(metadata.get('artist', 'Unknown Artist'))
        album = self.sanitize_filename(metadata.get('album', 'Unknown Album'))
        title = self.sanitize_filename(metadata.get('title', os.path.basename(original_path)))
        year = metadata.get('year', '')
        
        # Determine folder structure
        structure = self.settings.get("folder_structure", "artist/album")
        
        if structure == "artist/album":
            folder_path = os.path.join(self.musics_folder, artist, album)
        elif structure == "artist/year/album":
            year_str = str(year) if year else "Unknown Year"
            folder_path = os.path.join(self.musics_folder, artist, year_str, album)
        elif structure == "album":
            folder_path = os.path.join(self.musics_folder, album)
        else:
            folder_path = os.path.join(self.musics_folder, artist, album)
        
        # Create folder structure
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        # FIX: Always use the original file's extension, not the processed file
        # Get the extension from the ORIGINAL file path stored in metadata
        if 'original_file_path' in metadata:
            original_ext = os.path.splitext(metadata['original_file_path'])[1]
        else:
            # Fallback: use the file_path from metadata, but handle temp files
            file_path = metadata.get('file_path', original_path)
            if 'temp_audio_' in file_path:
                # This is a temporary converted file, use original_path instead
                original_ext = os.path.splitext(original_path)[1]
            else:
                original_ext = os.path.splitext(file_path)[1]
        
        # Ensure we have an extension
        if not original_ext:
            original_ext = os.path.splitext(original_path)[1]
        
        # Create the new filename with correct extension
        new_filename = f"{title}{original_ext}"
        new_path = os.path.join(folder_path, new_filename)
        
        # Handle duplicate filenames
        counter = 1
        base_path = new_path
        while os.path.exists(new_path):
            name, ext = os.path.splitext(base_path)
            new_path = f"{name} ({counter}){ext}"
            counter += 1
        
        # Always copy file to musics folder to ensure availability
        try:
            if original_path != new_path:
                shutil.copy2(original_path, new_path)
                print(f"📁 Copied to library: {os.path.basename(original_path)} → {os.path.relpath(new_path, self.base_path)}")
                return new_path
            else:
                return new_path
        except Exception as e:
            print(f"❌ Failed to copy file {original_path}: {e}")
            return original_path



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
    

class FileImportThread(QThread):
    """Thread for importing files without blocking the UI"""
    
    progress = pyqtSignal(str)  # filename being processed
    finished = pyqtSignal(int)   # number of files imported
    
    def __init__(self, file_paths, organizer, db, extract_metadata_func):
        super().__init__()
        self.file_paths = file_paths
        self.organizer = organizer
        self.db = db
        self.extract_metadata_func = extract_metadata_func
    
    def run(self):
        """Import files in background"""
        added_count = 0
        supported_formats = ('.mp3', '.flac', '.m4a', '.wav', '.ogg')
        
        for file_path in self.file_paths:
            if file_path.lower().endswith(supported_formats):
                self.progress.emit(os.path.basename(file_path))
                
                metadata = self.extract_metadata_func(file_path)
                if metadata:
                    # Organize file to musics folder
                    organized_path = self.organizer.organize_file(metadata, file_path)
                    
                    song_data = (
                        metadata['title'],
                        metadata['artist'],
                        metadata['album'],
                        metadata['year'],
                        metadata['genre'],
                        metadata['duration'],
                        organized_path,
                        metadata['album_art']
                    )
                    
                    if self.db.add_song(song_data):
                        added_count += 1
        
        self.finished.emit(added_count)


class FolderScanThread(QThread):
    """Thread for scanning folders without blocking the UI"""
    
    progress = pyqtSignal(str)  # filename being processed
    finished = pyqtSignal(int)   # number of files imported
    
    def __init__(self, folder_path, organizer, db, extract_metadata_func):
        super().__init__()
        self.folder_path = folder_path
        self.organizer = organizer
        self.db = db
        self.extract_metadata_func = extract_metadata_func
    
    def run(self):
        """Scan folder in background"""
        supported_formats = ('.mp3', '.flac', '.m4a', '.wav', '.ogg')
        added_count = 0
        
        try:
            for root, dirs, files in os.walk(self.folder_path):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        file_path = os.path.join(root, file)
                        self.progress.emit(file)
                        
                        metadata = self.extract_metadata_func(file_path)
                        if metadata:
                            # Organize file to musics folder
                            organized_path = self.organizer.organize_file(metadata, file_path)
                            
                            song_data = (
                                metadata['title'],
                                metadata['artist'],
                                metadata['album'],
                                metadata['year'],
                                metadata['genre'],
                                metadata['duration'],
                                organized_path,
                                metadata['album_art']
                            )
                            
                            if self.db.add_song(song_data):
                                added_count += 1
        except Exception as e:
            print(f"Error scanning folder: {e}")
        
        self.finished.emit(added_count)


class LocalSpotifyQt(QMainWindow):
    """Main music player application using PyQt"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Local Spotify Qt - Music Player")
        self.setGeometry(100, 100, 1200, 800)
        
        # Check VLC availability
        if not VLC_AVAILABLE:
            print("⚠️ VLC not available - some audio formats may not play correctly")
    
        # Initialize components
        self.db = MusicDatabase()
        self.player = AudioPlayer()

        # Initialize file organizer
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.organizer = MusicLibraryOrganizer(script_dir)
        
        # Application state (initialize before UI setup)
        self.current_playlist = []
        self.current_index = 0
        self.shuffle_mode = False
        self.repeat_mode = "off"  # off, one, all
        self.current_song_data = None
        self.slider_pressed = False
        self.original_playlist_order = []  # Store original order for shuffle toggle
        self.shuffled_playlist_order = []  # Store shuffled order
        
        # Setup UI FIRST
        self.setup_ui()
        self.setup_connections()
        self.apply_dark_theme()
        
        # THEN do cleanup and data loading (after UI exists)
        self.cleanup_missing_files()
        self.fix_double_extensions()
        
        # Load initial data
        self.refresh_library()
        self.refresh_playlists()
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Left sidebar
        self.create_sidebar(main_layout)
        
        # Right content area
        self.create_content_area(main_layout)
        
        # Bottom player controls
        self.create_player_controls()
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_sidebar(self, parent_layout):
        """Create the left sidebar"""
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(sidebar)
        
        # Title
        title_label = QLabel("🎵 Local Spotify Qt")
        title_label.setObjectName("title")
        sidebar_layout.addWidget(title_label)
          # Import section
        import_group = QGroupBox("📁 Import Music")
        import_layout = QVBoxLayout(import_group)
        
        self.add_folder_btn = QPushButton("📂 Add Folder")
        self.add_files_btn = QPushButton("📄 Add Files")
        self.youtube_btn = QPushButton("🎵 Download from YouTube")
        
        import_layout.addWidget(self.add_folder_btn)
        import_layout.addWidget(self.add_files_btn)
        import_layout.addWidget(self.youtube_btn)
        sidebar_layout.addWidget(import_group)
        
        # Search
        search_group = QGroupBox("🔍 Search Music")
        search_layout = QVBoxLayout(search_group)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search for songs, artists, albums...")
        search_layout.addWidget(self.search_edit)
        sidebar_layout.addWidget(search_group)
        
        # Navigation
        nav_group = QGroupBox("📚 Navigation")
        nav_layout = QVBoxLayout(nav_group)
        
        self.library_btn = QPushButton("📚 Library")
        self.create_playlist_btn = QPushButton("➕ Create Playlist")
        
        nav_layout.addWidget(self.library_btn)
        nav_layout.addWidget(self.create_playlist_btn)
        sidebar_layout.addWidget(nav_group)
        
        # Playlists
        playlist_group = QGroupBox("📝 Playlists")
        playlist_layout = QVBoxLayout(playlist_group)
        
        self.playlist_list = QListWidget()
        playlist_layout.addWidget(self.playlist_list)
        sidebar_layout.addWidget(playlist_group)
        
        sidebar_layout.addStretch()
        parent_layout.addWidget(sidebar)
    
    def create_content_area(self, parent_layout):
        """Create the main content area"""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Top bar with title and import buttons
        top_bar = QHBoxLayout()
        
        self.view_title = QLabel("Music Library")
        self.view_title.setObjectName("view_title")
        top_bar.addWidget(self.view_title)
        
        top_bar.addStretch()
        
        # Quick import buttons
        quick_folder_btn = QPushButton("📂 Import Folder")
        quick_files_btn = QPushButton("📄 Import Files")
        top_bar.addWidget(quick_files_btn)
        top_bar.addWidget(quick_folder_btn)
        
        content_layout.addLayout(top_bar)
        
        # Music table
        self.music_table = QTableWidget()
        self.music_table.setColumnCount(4)
        self.music_table.setHorizontalHeaderLabels(['Title', 'Artist', 'Album', 'Duration'])
          # Configure table
        header = self.music_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.music_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.music_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.music_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.music_table.setAlternatingRowColors(False)
        
        # Enable column sorting
        self.music_table.setSortingEnabled(True)
        
        # Set context menu policy
        self.music_table.setContextMenuPolicy(Qt.CustomContextMenu)
        
        # Set custom delegate to only allow editing Artist and Album columns
        editable_delegate = EditableColumnsDelegate([1, 2])  # Artist and Album columns
        self.music_table.setItemDelegate(editable_delegate)
        
        content_layout.addWidget(self.music_table)
        
        parent_layout.addWidget(content_widget)
        
        # Connect quick import buttons
        quick_folder_btn.clicked.connect(self.add_folder)
        quick_files_btn.clicked.connect(self.add_files)
    
    def create_player_controls(self):
        """Create the bottom player controls"""
        player_dock = QDockWidget("Player Controls", self)
        player_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        
        player_widget = QWidget()
        player_widget.setFixedHeight(120)
        player_layout = QHBoxLayout(player_widget)
        player_layout.setContentsMargins(20, 10, 20, 10)
        
        # Left: Song info and album art
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignLeft | Qt.AlignCenter)
        
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(64, 64)
        self.album_art_label.setAlignment(Qt.AlignCenter)
        self.album_art_label.setText("♪")
        self.album_art_label.setStyleSheet("""
            QLabel {
                background-color: #404040;
                border-radius: 5px;
                font-size: 24px;
                color: #1DB954;
            }
        """)
        
        song_info_layout = QHBoxLayout()
        song_info_layout.addWidget(self.album_art_label)
        
        # Song text info
        text_info_layout = QVBoxLayout()
        text_info_layout.setContentsMargins(10, 0, 0, 0)
        
        self.current_title_label = QLabel("No song selected")
        self.current_title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.current_artist_label = QLabel("")
        self.current_artist_label.setStyleSheet("font-size: 12px; color: #B0B0B0;")
        
        text_info_layout.addWidget(self.current_title_label)
        text_info_layout.addWidget(self.current_artist_label)
        
        song_info_layout.addLayout(text_info_layout)
        left_layout.addLayout(song_info_layout)
        
        player_layout.addLayout(left_layout)
        
        # Center: Controls and progress (centered and improved)
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setContentsMargins(50, 0, 50, 0)
        
        # Control buttons with improved styling
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        controls_layout.setSpacing(20)
        
        # Shuffle button
        self.shuffle_btn = QPushButton("🔀")
        self.shuffle_btn.setFixedSize(40, 40)
        self.shuffle_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #1DB954;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        # Previous button
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(45, 45)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 22px;
                font-size: 18px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #1DB954;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        # Play/Pause button (larger and prominent)
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setFixedSize(60, 60)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                border: none;
                border-radius: 30px;
                font-size: 24px;
                color: #FFFFFF;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ED760;
                /* Remove this line: transform: scale(1.05); */
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        # Next button
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(45, 45)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 22px;
                font-size: 18px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #1DB954;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        # Repeat button
        self.repeat_btn = QPushButton("🔁")
        self.repeat_btn.setFixedSize(40, 40)
        self.repeat_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 20px;
                font-size: 16px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #1DB954;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        controls_layout.addWidget(self.shuffle_btn)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.repeat_btn)
        
        center_layout.addLayout(controls_layout)
        
        # Progress bar with better styling and functionality
        progress_layout = QHBoxLayout()
        progress_layout.setContentsMargins(10, 15, 10, 0)
        progress_layout.setAlignment(Qt.AlignCenter)
        
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(45)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setStyleSheet("font-size: 11px; color: #B0B0B0;")
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimumWidth(350)
        self.progress_slider.setMaximumHeight(20)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                background: #404040;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: none;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setFixedWidth(45)
        self.duration_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.duration_label.setStyleSheet("font-size: 11px; color: #B0B0B0;")
        
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.duration_label)
        
        center_layout.addLayout(progress_layout)
        player_layout.addLayout(center_layout)
        
        # Right: Volume control (improved positioning)
        volume_layout = QHBoxLayout()
        volume_layout.setAlignment(Qt.AlignRight | Qt.AlignCenter)
        volume_layout.setContentsMargins(10, 0, 0, 0)
        volume_layout.setSpacing(8)
        
        self.volume_label = QLabel("🔊")
        self.volume_label.setFixedSize(24, 24)
        self.volume_label.setAlignment(Qt.AlignCenter)
        self.volume_label.setStyleSheet("font-size: 16px; color: #B0B0B0;")
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.setMaximumHeight(20)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 8px;
                background: #282828;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: 1px solid #1DB954;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
                width: 20px;
                height: 20px;
                margin: -3px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 4px;
            }
        """)
        
        volume_layout.addWidget(self.volume_label)
        volume_layout.addWidget(self.volume_slider)
        
        player_layout.addLayout(volume_layout)
        
        player_dock.setWidget(player_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, player_dock)
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('Add Folder to Library', self.add_folder)
        file_menu.addAction('Add Files to Library', self.add_files)
        file_menu.addSeparator()
        file_menu.addAction('Create Playlist', self.create_playlist_dialog)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
        
        # View menu
        view_menu = menubar.addMenu('View')
        view_menu.addAction('Refresh Library', self.refresh_library)
        # view_menu.addAction('Show Statistics', self.show_statistics)
        # view_menu.addSeparator()
        # view_menu.addAction('Clean Up Missing Files', self.manual_cleanup)
        
        # # Settings menu
        # settings_menu = menubar.addMenu('Settings')
        # settings_menu.addAction('Library Organization...', self.show_library_settings)
        
        # # Help menu
        # help_menu = menubar.addMenu('Help')
        # help_menu.addAction('About', self.show_about)
        # help_menu.addAction('Keyboard Shortcuts', self.show_shortcuts)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Import buttons
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.add_files_btn.clicked.connect(self.add_files)
        
        # Always connect YouTube button - let the dialog handle availability check
        self.youtube_btn.clicked.connect(self.youtube_download_dialog)
        
        # Navigation
        self.library_btn.clicked.connect(self.show_library)
        self.create_playlist_btn.clicked.connect(self.create_playlist_dialog)
        
        # Search
        self.search_edit.textChanged.connect(self.on_search)
        
        # Music table
        self.music_table.cellDoubleClicked.connect(self.on_song_double_click)
        self.music_table.customContextMenuRequested.connect(self.show_context_menu)
        self.music_table.itemChanged.connect(self.on_table_item_changed)

        # Player controls
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.prev_btn.clicked.connect(self.previous_song)
        self.next_btn.clicked.connect(self.next_song)
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        self.repeat_btn.clicked.connect(self.toggle_repeat)
        
        # Volume
        self.volume_slider.valueChanged.connect(self.player.set_volume)
        
        # Player signals
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.on_player_state_changed)
        self.progress_slider.sliderMoved.connect(self.on_progress_slider_moved)
        self.progress_slider.sliderPressed.connect(self.on_progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_progress_slider_released)
        
        # Playlist selection
        self.playlist_list.itemDoubleClicked.connect(self.on_playlist_select)
    
    def apply_dark_theme(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #191414;
                color: #FFFFFF;
            }
            QWidget {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel#title {
                font-size: 16px;
                font-weight: bold;
                margin: 10px;
            }
            QLabel#view_title {
                font-size: 18px;
                font-weight: bold;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #404040;
                border-radius: 5px;
                margin: 5px 0px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #1DB954;
                color: #FFFFFF;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
            QLineEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                selection-background-color: #1DB954;
            }
            QTableWidget {
                background-color: #282828;
                color: #FFFFFF;
                gridline-color: #404040;
                selection-background-color: #1DB954;
            }
            QHeaderView::section {
                background-color: #404040;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #191414;
            }
            QSlider::groove:horizontal {
                border: 1px solid #404040;
                height: 8px;
                background: #282828;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: 1px solid #1DB954;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
                width: 20px;
                height: 20px;
                margin: -3px 0;
                border-radius: 10px;
            }
            QMenuBar {
                background-color: #191414;
                color: #FFFFFF;
            }
            QMenuBar::item:selected {
                background-color: #1DB954;
            }
            QMenu {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
            }
            QMenu::item:selected {
                background-color: #1DB954;
            }
        """)
    
    def extract_metadata(self, file_path):
        """Extract metadata from audio file"""
        try:
            audio_file = File(file_path)
            if audio_file is None:
                return None
            
            # Default values
            title = os.path.basename(file_path)
            artist = "Unknown Artist"
            album = "Unknown Album"
            year = ""
            genre = ""
            duration = 0
            album_art = None
            
            # Extract metadata based on file type
            if isinstance(audio_file, MP3):
                title = str(audio_file.get('TIT2', [title])[0])
                artist = str(audio_file.get('TPE1', [artist])[0])
                album = str(audio_file.get('TALB', [album])[0])
                year = str(audio_file.get('TDRC', [year])[0])
                genre = str(audio_file.get('TCON', [genre])[0])
                duration = audio_file.info.length
                
                # Extract album art
                for tag in audio_file.tags.values():
                    if hasattr(tag, 'type') and tag.type == 3:
                        album_art = tag.data
                        break
            
            elif isinstance(audio_file, FLAC):
                title = audio_file.get('TITLE', [title])[0]
                artist = audio_file.get('ARTIST', [artist])[0]
                album = audio_file.get('ALBUM', [album])[0]
                year = audio_file.get('DATE', [year])[0] if 'DATE' in audio_file else ""
                genre = audio_file.get('GENRE', [genre])[0] if 'GENRE' in audio_file else ""
                duration = audio_file.info.length
                
                # Extract album art from FLAC
                if audio_file.pictures:
                    album_art = audio_file.pictures[0].data
            
            elif isinstance(audio_file, MP4):
                title = audio_file.get('\xa9nam', [title])[0]
                artist = audio_file.get('\xa9ART', [artist])[0]
                album = audio_file.get('\xa9alb', [album])[0]
                year = str(audio_file.get('\xa9day', [year])[0]) if '\xa9day' in audio_file else ""
                genre = audio_file.get('\xa9gen', [genre])[0] if '\xa9gen' in audio_file else ""
                duration = audio_file.info.length
                
                # Extract album art from MP4
                if 'covr' in audio_file:
                    album_art = bytes(audio_file['covr'][0])
            
            return {
                'title': title,
                'artist': artist,
                'album': album,
                'year': year,
                'genre': genre,
                'duration': duration,
                'file_path': file_path,
                'original_file_path': file_path,  # ADD THIS LINE
                'album_art': album_art
            }
            
        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")
            return None
    
    # Add this method to LocalSpotifyQt class around line 1600
    def fix_double_extensions(self):
        """Fix files with double extensions like .m4a.m4a"""
        import glob
        
        double_ext_pattern = os.path.join(self.organizer.musics_folder, "**", "*.m4a.m4a")
        double_ext_files = glob.glob(double_ext_pattern, recursive=True)
        
        if not double_ext_files:
            print("✅ No files with double extensions found")
            return 0
        
        fixed_count = 0
        for old_path in double_ext_files:
            # Remove the extra .m4a extension
            new_path = old_path.replace('.m4a.m4a', '.m4a')
            try:
                os.rename(old_path, new_path)
                print(f"🔧 Fixed: {os.path.basename(old_path)} → {os.path.basename(new_path)}")
                
                # Update database path
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('UPDATE songs SET file_path = ? WHERE file_path = ?', 
                            (new_path, old_path))
                conn.commit()
                conn.close()
                
                fixed_count += 1
                
            except Exception as e:
                print(f"❌ Failed to fix {old_path}: {e}")
        
        if fixed_count > 0:
            print(f"✅ Fixed {fixed_count} files with double extensions")
            self.refresh_library()
        
        return fixed_count

    def add_folder(self):
        """Add a folder of music files to the library"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if not folder_path:
            return
        
        # Create progress dialog
        progress_dialog = QProgressDialog("Scanning music files...", "Cancel", 0, 0, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()
        
        # Start scanning thread
        self.scan_thread = FolderScanThread(folder_path, self.organizer, self.db, self.extract_metadata)
        self.scan_thread.progress.connect(lambda filename: progress_dialog.setLabelText(f"Processing: {filename}"))
        self.scan_thread.finished.connect(lambda count: self.on_import_finished(count, progress_dialog))
        self.scan_thread.start()
    
    def add_files(self):
        """Add individual music files to the library"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Music Files",
            "",
            "Audio Files (*.mp3 *.flac *.m4a *.wav *.ogg);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        if len(file_paths) > 5:
            # Create progress dialog for multiple files
            progress_dialog = QProgressDialog("Adding music files...", "Cancel", 0, 0, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()
            
            # Start import thread
            self.import_thread = FileImportThread(file_paths, self.organizer, self.db, self.extract_metadata)
            self.import_thread.progress.connect(lambda filename: progress_dialog.setLabelText(f"Processing: {filename}"))
            self.import_thread.finished.connect(lambda count: self.on_import_finished(count, progress_dialog))
            self.import_thread.start()
        else:
            # Process few files directly
            added_count = 0
            for file_path in file_paths:
                metadata = self.extract_metadata(file_path)
                if metadata:
                    organized_path = self.organizer.organize_file(metadata, file_path)
                    song_data = (
                        metadata['title'], metadata['artist'], metadata['album'],
                        metadata['year'], metadata['genre'], metadata['duration'],
                        organized_path, metadata['album_art']
                    )
                    if self.db.add_song(song_data):
                        added_count += 1
            
            self.refresh_library()
            QMessageBox.information(self, "Import Complete", f"Successfully imported {added_count} songs!")
    
    def on_import_finished(self, count, progress_dialog):
        """Handle import completion"""
        progress_dialog.close()
        self.refresh_library()
        QMessageBox.information(self, "Import Complete", f"Successfully imported {count} songs!")
    
    def youtube_download_dialog(self):
        """Show dialog to download from YouTube"""
        if not YOUTUBE_AVAILABLE:
            QMessageBox.warning(self, "YouTube Download", 
                              "YouTube downloader is not available. Please install yt-dlp:\n\n"
                              "pip install yt-dlp requests")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Download from YouTube")
        dialog.setFixedSize(500, 250)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1DB954;
            }
            QPushButton {
                background-color: #1DB954;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton#cancelButton {
                background-color: #404040;
            }
            QPushButton#cancelButton:hover {
                background-color: #606060;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title_label = QLabel("🎵 Download Audio from YouTube")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # URL input
        layout.addWidget(QLabel("YouTube URL:"))
        url_edit = QLineEdit()
        url_edit.setPlaceholderText("Paste YouTube video or playlist URL here...")
        layout.addWidget(url_edit)
        
        # Info label
        info_label = QLabel("• Supports individual videos and playlists\n"
                           "• Audio will be downloaded as MP3 (192kbps)\n"
                           "• Channel name will be used as artist")
        info_label.setStyleSheet("color: #B3B3B3; font-size: 10px; font-weight: normal; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Warning label
        warning_label = QLabel("⚠️ Please respect copyright and only download content you have permission to use.")
        warning_label.setStyleSheet("color: #FF6B6B; font-size: 9px; font-weight: normal;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        download_btn = QPushButton("🎵 Download")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        
        button_layout.addWidget(download_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        def start_download():
            url = url_edit.text().strip()
            if not url:
                QMessageBox.warning(dialog, "Error", "Please enter a YouTube URL")
                return
            
            if not ("youtube.com" in url or "youtu.be" in url):
                QMessageBox.warning(dialog, "Error", "Please enter a valid YouTube URL")
                return
            
            # Show what will be downloaded
            if 'list=' in url and 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
                clean_url = f"https://www.youtube.com/watch?v={video_id}"
                
                reply = QMessageBox.question(dialog, "Playlist URL Detected", 
                                           f"You entered a playlist URL, but only the individual video will be downloaded.\n\n"
                                           f"Video ID: {video_id}\n"
                                           f"Clean URL: {clean_url}\n\n"
                                           f"Do you want to continue with downloading just this video?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return
            
            dialog.accept()
            self.start_youtube_download(url)
        
        download_btn.clicked.connect(start_download)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Focus on URL input and enable Enter key
        url_edit.setFocus()
        url_edit.returnPressed.connect(start_download)
        
        dialog.exec_()

    def start_youtube_download(self, url):
        """Start YouTube download with progress dialog"""
        progress_dialog = QProgressDialog("Preparing download...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("YouTube Download")
        progress_dialog.setAutoClose(False)  # Don't auto-close on completion
        progress_dialog.show()
        
        # Create download thread
        self.download_thread = YouTubeDownloadThread(url, self.organizer.musics_folder)
        
        # Connect signals directly to thread
        self.download_thread.progress.connect(
            lambda status, percent: self._update_download_progress(progress_dialog, status, percent)
        )
        self.download_thread.finished.connect(
            lambda file_path, metadata: self.on_youtube_download_finished(file_path, metadata, progress_dialog)
        )
        self.download_thread.error.connect(
            lambda error: self.on_youtube_download_error(error, progress_dialog)
        )
        
        # Handle cancel
        def on_cancel():
            if hasattr(self, 'download_thread') and self.download_thread.isRunning():
                progress_dialog.setLabelText("Cancelling download...")
                self.download_thread.terminate()
                self.download_thread.wait(3000)  # Wait up to 3 seconds
            progress_dialog.close()
        
        progress_dialog.canceled.connect(on_cancel)
        
        # Start download
        self.download_thread.start()

    def _update_download_progress(self, progress_dialog, status, percent):
        """Update the progress dialog with download status"""
        progress_dialog.setLabelText(status)
        progress_dialog.setValue(percent)
        
        # Process events to ensure UI updates
        QApplication.processEvents()

    # Update the on_youtube_download_finished method around line 1620

    def on_youtube_download_finished(self, file_path, metadata, progress_dialog):
        """Handle YouTube download completion"""
        progress_dialog.setLabelText("Adding to library...")
        progress_dialog.setValue(100)
        QApplication.processEvents()
        
        try:
            # Verify the file actually exists and is accessible
            if not os.path.exists(file_path):
                raise Exception(f"Downloaded file not found: {file_path}")
            
            # Check if file is empty or too small
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # Less than 1KB
                raise Exception(f"Downloaded file is too small ({file_size} bytes)")
            
            # Add to database with YouTube metadata
            song_data = (
                metadata['title'],
                metadata['artist'],
                metadata['album'],
                metadata['year'],
                metadata['genre'],
                metadata['duration'],
                file_path,
                metadata['album_art'],
                metadata['source'],  # 'youtube'
                metadata.get('youtube_url', ''),
                metadata.get('youtube_id', '')
            )
            
            if self.db.add_song(song_data):
                progress_dialog.close()
                self.refresh_library()
                
                # Show success message with file info
                file_size_mb = file_size / (1024 * 1024)
                QMessageBox.information(self, "Download Complete", 
                                    f"Successfully downloaded: {metadata['title']}\n"
                                    f"By: {metadata['artist']}\n"
                                    f"File size: {file_size_mb:.1f} MB\n"
                                    f"Location: {os.path.relpath(file_path, self.organizer.base_path)}\n\n"
                                    f"Added to library under 'YouTube Downloads'")
            else:
                progress_dialog.close()
                QMessageBox.warning(self, "Error", "Failed to add downloaded song to library")
                
        except Exception as e:
            progress_dialog.close()
            error_msg = f"Error processing downloaded file: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Show detailed error with troubleshooting tips
            QMessageBox.critical(self, "Download Processing Error", 
                            f"{error_msg}\n\n"
                            f"Troubleshooting:\n"
                            f"• Check if the file exists in the YouTube Downloads folder\n"
                            f"• Verify the file isn't corrupted or empty\n"
                            f"• Try downloading the video again\n"
                            f"• Check available disk space")

    def on_youtube_download_error(self, error, progress_dialog):
        """Handle YouTube download error"""
        progress_dialog.close()
        QMessageBox.critical(self, "Download Failed", 
                       f"YouTube download failed:\n\n{error}\n\n"
                       f"Common issues:\n"
                       f"• Video may be private or unavailable\n"
                       f"• Network connection problems\n"
                       f"• Geographic restrictions\n"
                       f"• yt-dlp needs to be updated")

    def create_playlist_dialog(self):
        """Show dialog to create a new playlist"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Playlist")
        dialog.setFixedSize(400, 200)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit, QTextEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #1DB954;
            }
            QPushButton {
                background-color: #1DB954;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton#cancelButton {
                background-color: #404040;
            }
            QPushButton#cancelButton:hover {
                background-color: #606060;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Title
        title_label = QLabel("📝 Create New Playlist")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Playlist name
        layout.addWidget(QLabel("Playlist Name:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter playlist name...")
        layout.addWidget(name_edit)
        
        # Description
        layout.addWidget(QLabel("Description (optional):"))
        desc_edit = QTextEdit()
        desc_edit.setMaximumHeight(60)
        desc_edit.setPlaceholderText("Enter playlist description...")
        layout.addWidget(desc_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("📝 Create Playlist")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        
        button_layout.addWidget(create_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        def create_playlist():
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dialog, "Error", "Please enter a playlist name")
                return
            
            description = desc_edit.toPlainText().strip()
            
            playlist_id = self.db.create_playlist(name, description)
            if playlist_id:
                dialog.accept()
                self.refresh_playlists()
                QMessageBox.information(self, "Success", f"Playlist '{name}' created successfully!")
            else:
                QMessageBox.warning(dialog, "Error", "Playlist name already exists")
    
        create_btn.clicked.connect(create_playlist)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Focus on name input
        name_edit.setFocus()
        name_edit.returnPressed.connect(create_playlist)
        
        dialog.exec_()

    def refresh_library(self):
        """Refresh the music library display"""
        songs = self.db.get_all_songs()
        self.music_table.setRowCount(len(songs))
    
        for row, song in enumerate(songs):
            # Handle both old format (10 fields) and new format (13 fields)
            if len(song) >= 13:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added, source, youtube_url, youtube_id = song[:13]
            else:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song[:10]
                source = 'local'
            
            # Create table items
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Add visual indicators for YouTube downloads
            if source == 'youtube' or 'YouTube' in album:
                title_item.setText(f"🎵 {title}")
                title_item.setToolTip("Downloaded from YouTube")
                artist_item.setToolTip(f"YouTube Channel: {artist}")
            
            # Store song ID in the first item
            title_item.setData(Qt.UserRole, song_id)
            
            # Set items in table
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)
        
        # Update status
        self.statusBar().showMessage(f"Library: {len(songs)} songs")

    def refresh_playlists(self):
        """Refresh the playlists display"""
        self.playlist_list.clear()
        playlists = self.db.get_playlists()
        
        for playlist in playlists:
            playlist_id, name, description, created_date = playlist
            item = QListWidgetItem(f"📝 {name}")
            item.setData(Qt.UserRole, playlist_id)
            item.setToolTip(description if description else f"Playlist: {name}")
            self.playlist_list.addItem(item)

    def show_library(self):
        """Show the main library view"""
        self.view_title.setText("Music Library")
        # Clear current playlist to show all songs
        self.current_playlist = []
        self.refresh_library()

    def on_search(self, query):
        """Handle search input"""
        if not query.strip():
            self.refresh_library()
            return
        
        songs = self.db.search_songs(query)
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            # Handle both old format (10 fields) and new format (13 fields)
            if len(song) >= 13:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added, source, youtube_url, youtube_id = song[:13]
            else:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song[:10]
                source = 'local'
            
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Add visual indicators for YouTube downloads
            if source == 'youtube' or 'YouTube' in album:
                title_item.setText(f"🎵 {title}")
                title_item.setToolTip("Downloaded from YouTube")
            
            title_item.setData(Qt.UserRole, song_id)
            
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)

    def on_song_double_click(self, row, column):
        """Handle double-clicking on a song"""
        if row < self.music_table.rowCount():
            song_id = self.music_table.item(row, 0).data(Qt.UserRole)
            # Find the song data
            songs = self.db.get_all_songs()
            for song in songs:
                if song[0] == song_id:
                    self.play_song(song)
                    break

    def play_song(self, song_data):
        """Play a specific song"""
        try:
            # Handle both old format (10 fields) and new format (13 fields)
            if len(song_data) >= 13:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added, source, youtube_url, youtube_id = song_data[:13]
            else:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song_data[:10]
            
            # Check if file exists
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", 
                                  f"The file '{os.path.basename(file_path)}' could not be found.\n"
                                  f"It may have been moved or deleted.")
                return
            
            # Load and play the song
            if self.player.load_song(file_path):
                self.player.play()
                self.current_song_data = song_data
                
                # Update UI
                self.current_title_label.setText(title)
                self.current_artist_label.setText(artist)
                self.play_pause_btn.setText("⏸")
                
                # Load album art if available
                if album_art:
                    pixmap = QPixmap()
                    pixmap.loadFromData(album_art)
                    scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.album_art_label.setPixmap(scaled_pixmap)
                else:
                    self.album_art_label.setText("♪")
                    self.album_art_label.setPixmap(QPixmap())
                
                self.statusBar().showMessage(f"Playing: {title} - {artist}")
            else:
                QMessageBox.warning(self, "Playback Error", "Could not load the audio file.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error playing song: {str(e)}")

    def format_duration(self, duration):
        """Format duration in seconds to MM:SS format"""
        if duration is None or duration == 0:
            return "0:00"
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"

    def cleanup_missing_files(self):
        """Clean up database entries for missing files"""
        if hasattr(self.organizer, 'musics_folder'):

            removed_count = self.db.cleanup_missing_files(self.organizer.musics_folder)
            if removed_count > 0:
                print(f"🧹 Cleaned up {removed_count} missing files from database")

    def show_context_menu(self, position):
        """Show context menu for music table"""
        if self.music_table.itemAt(position) is None:
            return
        
        menu = QMenu(self)
        
        # Add actions
        play_action = menu.addAction("▶ Play")
        menu.addSeparator()
        edit_action = menu.addAction("✏️ Edit Metadata")
        menu.addSeparator()
        remove_action = menu.addAction("🗑️ Remove from Library")
        
        # Execute menu
        action = menu.exec_(self.music_table.mapToGlobal(position))
        
        if action == play_action:
            row = self.music_table.currentRow()
            self.on_song_double_click(row, 0)
        elif action == remove_action:
            self.remove_selected_song()

    def remove_selected_song(self):
        """Remove selected song from library"""
        current_row = self.music_table.currentRow()
        if current_row < 0:
            return
        
        song_id = self.music_table.item(current_row, 0).data(Qt.UserRole)
        title = self.music_table.item(current_row, 0).text()
        
        reply = QMessageBox.question(self, "Remove Song", 
                                    f"Are you sure you want to remove '{title}' from the library?\n\n"
                                    f"This will not delete the actual file.")
        
        if reply == QMessageBox.Yes:
            if self.db.remove_song(song_id):
                self.refresh_library()
                self.statusBar().showMessage(f"Removed: {title}")
            else:
                QMessageBox.warning(self, "Error", "Failed to remove song from library")

    def on_table_item_changed(self, item):
        """Handle table item changes (metadata editing)"""
        if item.column() not in [1, 2]:  # Only allow editing Artist and Album
            return
        
        song_id = self.music_table.item(item.row(), 0).data(Qt.UserRole)
        new_value = item.text()
        
        # Determine field name
        field_map = {1: 'artist', 2: 'album'}
        field = field_map.get(item.column())
        
        if field and self.db.update_song_metadata(song_id, field, new_value):
            self.statusBar().showMessage(f"Updated {field}: {new_value}")
        else:
            QMessageBox.warning(self, "Error", f"Failed to update {field}")

    def on_playlist_select(self, item):
        """Handle playlist selection"""
        playlist_id = item.data(Qt.UserRole)
        playlist_name = item.text().replace("📝 ", "")
        
        # Load playlist songs
        songs = self.db.get_playlist_songs(playlist_id)
        self.view_title.setText(f"Playlist: {playlist_name}")
        
        # Display songs
        self.music_table.setRowCount(len(songs))
        for row, song in enumerate(songs):
            # Handle both old format and new format
            if len(song) >= 13:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added, source, youtube_url, youtube_id = song[:13]
            else:
                song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song[:10]
                source = 'local'
            
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Add visual indicators for YouTube downloads
            if source == 'youtube' or 'YouTube' in album:
                title_item.setText(f"🎵 {title}")
                title_item.setToolTip("Downloaded from YouTube")
            
            title_item.setData(Qt.UserRole, song_id)
            
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)

    # Player control methods (note the proper indentation - these are part of the LocalSpotifyQt class)
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.setText("▶")
        elif self.player.is_paused():
            self.player.play()
            self.play_pause_btn.setText("⏸")
        else:
            # No song loaded, play first song in library if available
            if self.music_table.rowCount() > 0:
                self.on_song_double_click(0, 0)

    def next_song(self):
        """Play next song"""
        # Implementation for next song
        pass

    def previous_song(self):
        """Play previous song"""
        # Implementation for previous song
        pass

    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_mode = not self.shuffle_mode
        if self.shuffle_mode:
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet().replace("#404040", "#1DB954"))
        else:
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet().replace("#1DB954", "#404040"))

    def toggle_repeat(self):
        """Toggle repeat mode"""
        modes = ["off", "one", "all"]
        current_index = modes.index(self.repeat_mode)
        self.repeat_mode = modes[(current_index + 1) % len(modes)]
        
        if self.repeat_mode == "off":
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("#1DB954", "#404040"))
        elif self.repeat_mode == "one":
            self.repeat_btn.setText("🔂")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("#404040", "#1DB954"))
        else:  # all
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("#404040", "#1DB954"))

    def update_position(self, position):
        """Update position display"""
        if not self.slider_pressed:
            self.progress_slider.setValue(position)
        self.time_label.setText(self.format_duration(position / 1000))

    def update_duration(self, duration):
        """Update duration display"""
        self.progress_slider.setRange(0, duration)
        self.duration_label.setText(self.format_duration(duration / 1000))

    def on_player_state_changed(self, state):
        """Handle player state changes (VLC version)"""
        if VLC_AVAILABLE:
            # VLC states: 0=Stopped, 1=Playing, 2=Paused
            if state == 1:  # Playing
                self.play_pause_btn.setText("⏸")
            else:  # Stopped or Paused
                self.play_pause_btn.setText("▶")
        else:
            # Qt MediaPlayer states (fallback)
            if state == QMediaPlayer.PlayingState:
                self.play_pause_btn.setText("⏸")
            else:
                self.play_pause_btn.setText("▶")

    def on_progress_slider_moved(self, position):
        """Handle progress slider movement"""
        self.player.set_position(position)

    def on_progress_slider_pressed(self):
        """Handle progress slider press"""
        self.slider_pressed = True

    def on_progress_slider_released(self):
        """Handle progress slider release"""
        self.slider_pressed = False


# Main execution block (this should be at the very end, OUTSIDE the class - no indentation)
if __name__ == "__main__":
    import sys
    
    # Create the QApplication
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Local Spotify Qt")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Local Music Player")
    
    try:
        # Create and show the main window
        window = LocalSpotifyQt()
        window.show()
        
        # Start the application event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        QMessageBox.critical(None, "Application Error", 
                           f"Failed to start the application:\n{str(e)}")
        sys.exit(1)