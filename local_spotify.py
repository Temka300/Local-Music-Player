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

# Import pydub for M4A conversion (optional dependency)
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("✅ pydub available - M4A conversion supported")
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub not available - M4A files may have playback issues")
    print("💡 Install with: pip install pydub")


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
        
        # Songs table
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
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
            cursor.execute('''
                INSERT OR REPLACE INTO songs 
                (title, artist, album, year, genre, duration, file_path, album_art)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', song_data)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error adding song: {e}")
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
    """Enhanced audio playback manager using Qt"""
    
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(QMediaPlayer.State)
    
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.current_song = None
        self.volume = 70
        self._temp_audio_file = None
        
        # Connect signals
        self.player.positionChanged.connect(self.positionChanged.emit)
        self.player.durationChanged.connect(self.durationChanged.emit)
        self.player.stateChanged.connect(self.stateChanged.emit)
        
        # Set initial volume
        self.player.setVolume(self.volume)
    
    def load_song(self, file_path):
        """Load a song file with enhanced error handling and M4A conversion"""
        try:
            # Clean up previous temp file
            self._cleanup_temp_files()
            
            # Check if file is M4A and needs conversion
            if file_path.lower().endswith('.m4a') and PYDUB_AVAILABLE:
                converted_path = self._convert_and_load_m4a(file_path)
                if converted_path:
                    file_path = converted_path
            
            # Load the file
            url = QUrl.fromLocalFile(file_path)
            content = QMediaContent(url)
            self.player.setMedia(content)
            self.current_song = file_path
            
            return True
            
        except Exception as e:
            print(f"Error loading song {file_path}: {e}")
            return False
    
    def _convert_and_load_m4a(self, file_path):
        """Convert M4A to WAV for better compatibility"""
        try:
            # Create temporary WAV file
            temp_dir = tempfile.gettempdir()
            temp_filename = f"temp_audio_{int(time.time())}.wav"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Convert M4A to WAV
            audio = AudioSegment.from_file(file_path, format="m4a")
            audio.export(temp_path, format="wav")
            
            # Store temp file path for cleanup
            self._temp_audio_file = temp_path
            
            print(f"🔄 Converted M4A to WAV: {os.path.basename(file_path)}")
            return temp_path
            
        except Exception as e:
            print(f"❌ Failed to convert M4A file {file_path}: {e}")
            return None
    
    def play(self):
        """Play the current song"""
        self.player.play()
    
    def pause(self):
        """Pause playback"""
        self.player.pause()
    
    def stop(self):
        """Stop playback and cleanup temporary files"""
        self.player.stop()
        self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Clean up temporary audio files"""
        if self._temp_audio_file and os.path.exists(self._temp_audio_file):
            try:
                os.remove(self._temp_audio_file)
                print(f"🧹 Cleaned up temp file: {self._temp_audio_file}")
            except Exception as e:
                print(f"Error cleaning temp file: {e}")
            finally:
                self._temp_audio_file = None
    
    def set_volume(self, volume):
        """Set playback volume (0-100)"""
        self.volume = volume
        self.player.setVolume(volume)
    
    def set_position(self, position):
        """Set playback position"""
        self.player.setPosition(position)
    
    def is_playing(self):
        """Check if music is currently playing"""
        return self.player.state() == QMediaPlayer.PlayingState

    def is_paused(self):
        """Check if music is paused"""
        return self.player.state() == QMediaPlayer.PausedState


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
        
        import_layout.addWidget(self.add_folder_btn)
        import_layout.addWidget(self.add_files_btn)
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
    
    def refresh_library(self):
        """Refresh the music library display"""
        # Clean up missing files first
        self.cleanup_missing_files()
        
        # Clear and reload table
        songs = self.db.get_all_songs()
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song
            
            # Create table items
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Set item flags - only Artist and Album are editable
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            artist_item.setFlags(artist_item.flags() | Qt.ItemIsEditable)
            album_item.setFlags(album_item.flags() | Qt.ItemIsEditable)
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemIsEditable)
            
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)
            
            # Store song ID for later use
            self.music_table.item(row, 0).setData(Qt.UserRole, song_id)
        
        self.view_title.setText(f"Music Library ({len(songs)} songs)")

    def refresh_playlists(self):
        """Refresh the playlists display"""
        self.playlist_list.clear()
        playlists = self.db.get_playlists()
        
        for playlist in playlists:
            playlist_id, name, description, created_date = playlist
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, playlist_id)
            self.playlist_list.addItem(item)
    
    def cleanup_missing_files(self):
        """Check for and remove missing files from the database"""
        try:
            removed_count = self.db.cleanup_missing_files(self.organizer.musics_folder)
            if removed_count > 0:
                print(f"🧹 Database cleanup: Removed {removed_count} missing files")
        except Exception as e:
            print(f"Error during database cleanup: {e}")
    
    def manual_cleanup(self):
        """Manually trigger cleanup of missing files with user feedback"""
        try:
            removed_count = self.db.cleanup_missing_files(self.organizer.musics_folder)
            if removed_count > 0:
                QMessageBox.information(
                    self, "Cleanup Complete",
                    f"Removed {removed_count} missing files from database.\n"
                    "The library has been updated."
                )
                self.refresh_library()
            else:
                QMessageBox.information(
                    self, "Cleanup Complete",
                    "No missing files found. Your library is up to date!"
                )
        except Exception as e:
            QMessageBox.critical(self, "Cleanup Error", f"Error during cleanup: {e}")
    
    def on_search(self, query):
        """Handle search input"""
        if len(query) >= 2:
            self.search_music(query)
        elif len(query) == 0:
            self.refresh_library()
    
    def search_music(self, query):
        """Search for music in the library"""
        songs = self.db.search_songs(query)
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song
            
            # Create table items
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Set item flags - only Artist and Album are editable
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            artist_item.setFlags(artist_item.flags() | Qt.ItemIsEditable)
            album_item.setFlags(album_item.flags() | Qt.ItemIsEditable)
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemIsEditable)
            
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)
            
            # Store song ID for later use
            self.music_table.item(row, 0).setData(Qt.UserRole, song_id)
        
        self.view_title.setText(f"Search Results ({len(songs)} songs)")
    
    def show_library(self):
        """Show the full music library"""
        self.search_edit.clear()
        self.refresh_library()
    
    def on_song_double_click(self, row, column):
        """Handle double-click on a song"""
        # Only play song if not clicking on editable columns (Artist/Album)
        if column not in [1, 2]:  # Columns 1 and 2 are Artist and Album
            self.play_selected_song(row)

    def on_table_item_changed(self, item):
        """Handle changes to table items (for editing artist/album)"""
        if item is None:
            return
        
        row = item.row()
        column = item.column()
        new_value = item.text().strip()
        
        # Only allow editing of Artist (column 1) and Album (column 2)
        if column not in [1, 2]:
            return
        
        # Get the song ID
        song_id_item = self.music_table.item(row, 0)
        if song_id_item is None:
            return
        
        song_id = song_id_item.data(Qt.UserRole)
        if song_id is None:
            return
        
        # Map column to database field
        field_map = {1: 'artist', 2: 'album'}
        field = field_map[column]
        
        # Update database
        if self.db.update_song_metadata(song_id, field, new_value):
            print(f"✅ Updated {field} to '{new_value}' for song ID {song_id}")
            # Update the current song data if it's the currently playing song
            if hasattr(self, 'current_song_data') and self.current_song_data and self.current_song_data[0] == song_id:
                # Update the current song data tuple
                song_list = list(self.current_song_data)
                if field == 'artist':
                    song_list[2] = new_value  # Artist is at index 2
                elif field == 'album':
                    song_list[3] = new_value  # Album is at index 3
                self.current_song_data = tuple(song_list)
                self.update_current_song_display()
        else:
            print(f"❌ Failed to update {field} for song ID {song_id}")
            # Revert the change in the UI
            songs = self.db.get_all_songs()
            for song in songs:
                if song[0] == song_id:
                    if field == 'artist':
                        item.setText(song[2])  # Artist is at index 2
                    elif field == 'album':
                        item.setText(song[3])  # Album is at index 3
                    break

    def show_context_menu(self, position):
        """Show context menu for the music table"""
        item = self.music_table.itemAt(position)
        if item is None:
            return
        
        row = item.row()
        self.music_table.selectRow(row)
        
        # Create context menu
        context_menu = QMenu(self)
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 2px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #1DB954;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 2px 0px;
            }
        """)
        
        # Add menu actions
        play_action = context_menu.addAction("▶ Play")
        context_menu.addSeparator()
        
        add_to_playlist_action = context_menu.addAction("📝 Add to Playlist...")
        context_menu.addSeparator()
        
        show_location_action = context_menu.addAction("📂 Show File Location")
        edit_metadata_action = context_menu.addAction("✏️ Edit Metadata")
        
        # Connect actions
        play_action.triggered.connect(lambda: self.play_selected_song(row))
        add_to_playlist_action.triggered.connect(self.add_to_playlist_dialog)
        show_location_action.triggered.connect(lambda: self.show_file_location(row))
        edit_metadata_action.triggered.connect(lambda: self.edit_metadata_dialog(row))
        
        # Show menu
        context_menu.exec_(self.music_table.mapToGlobal(position))

    def show_file_location(self, row):
        """Show the file location of the selected song"""
        song_id = self.music_table.item(row, 0).data(Qt.UserRole)
        songs = self.db.get_all_songs()
        
        for song in songs:
            if song[0] == song_id:
                file_path = song[7]  # file_path is at index 7
                if os.path.exists(file_path):
                    # Open file explorer and select the file
                    if sys.platform == "win32":
                        os.system(f'explorer /select,"{file_path}"')
                    elif sys.platform == "darwin":  # macOS
                        os.system(f'open -R "{file_path}"')
                    else:  # Linux
                        folder_path = os.path.dirname(file_path)
                        os.system(f'xdg-open "{folder_path}"')
                else:
                    QMessageBox.warning(self, "File Not Found", f"The file no longer exists:\n{file_path}")
                break

    def edit_metadata_dialog(self, row):
        """Show dialog to edit song metadata"""
        song_id = self.music_table.item(row, 0).data(Qt.UserRole)
        songs = self.db.get_all_songs()
        
        current_song = None
        for song in songs:
            if song[0] == song_id:
                current_song = song
                break
        
        if not current_song:
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Metadata")
        dialog.setFixedSize(400, 300)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
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
            QPushButton:pressed {
                background-color: #1aa34a;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        
        # Title field
        layout.addWidget(QLabel("Title:"))
        title_edit = QLineEdit(current_song[1])
        layout.addWidget(title_edit)
        
        # Artist field
        layout.addWidget(QLabel("Artist:"))
        artist_edit = QLineEdit(current_song[2])
        layout.addWidget(artist_edit)
        
        # Album field
        layout.addWidget(QLabel("Album:"))
        album_edit = QLineEdit(current_song[3])
        layout.addWidget(album_edit)
        
        # Year field
        layout.addWidget(QLabel("Year:"))
        year_edit = QLineEdit(current_song[4])
        layout.addWidget(year_edit)
        
        # Genre field
        layout.addWidget(QLabel("Genre:"))
        genre_edit = QLineEdit(current_song[5])
        layout.addWidget(genre_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect buttons
        def save_changes():
            # Update all fields
            updates = [
                ('title', title_edit.text().strip()),
                ('artist', artist_edit.text().strip()),
                ('album', album_edit.text().strip()),
                ('year', year_edit.text().strip()),
                ('genre', genre_edit.text().strip())
            ]
            
            success = True
            for field, value in updates:
                if not self.db.update_song_metadata(song_id, field, value):
                    success = False
                    break
            
            if success:
                # Refresh the library to show changes
                self.refresh_library()
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", "Failed to save changes to database.")
        
        save_btn.clicked.connect(save_changes)
        cancel_btn.clicked.connect(dialog.reject)        
        dialog.exec_()

    def create_playlist_dialog(self):
        """Show dialog to create a new playlist"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Playlist")
        dialog.setFixedSize(400, 250)
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
                min-width: 80px;
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
        
        # Name entry
        layout.addWidget(QLabel("Playlist Name:"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Enter playlist name...")
        layout.addWidget(name_edit)
        
        # Description entry
        layout.addWidget(QLabel("Description (optional):"))
        desc_edit = QTextEdit()
        desc_edit.setPlaceholderText("Enter playlist description...")
        desc_edit.setMaximumHeight(80)
        layout.addWidget(desc_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
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
            
            if self.db.create_playlist(name, description):
                self.refresh_playlists()
                QMessageBox.information(dialog, "Success", f"Playlist '{name}' created successfully!")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", "Playlist name already exists")
        
        create_btn.clicked.connect(create_playlist)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Focus on name entry
        name_edit.setFocus()
        
        dialog.exec_()

    def add_to_playlist_dialog(self):
        """Show dialog to add song to playlist"""
        current_row = self.music_table.currentRow()
        if current_row < 0:
            return
        
        song_id = self.music_table.item(current_row, 0).data(Qt.UserRole)
        playlists = self.db.get_playlists()
        
        if not playlists:
            reply = QMessageBox.question(self, "No Playlists", 
                                       "No playlists found. Would you like to create one?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.create_playlist_dialog()
            return
        
        # Create playlist selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add to Playlist")
        dialog.setFixedSize(300, 200)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
            }
            QListWidget {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
                border-radius: 2px;
            }
            QListWidget::item:selected {
                background-color: #1DB954;
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
        """)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select playlist:"))
        
        playlist_list = QListWidget()
        for playlist in playlists:
            playlist_list.addItem(playlist[1])  # playlist name
        layout.addWidget(playlist_list)
        
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        cancel_btn = QPushButton("Cancel")
        button_layout.addWidget(add_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        def add_to_selected_playlist():
            current_item = playlist_list.currentItem()
            if current_item:
                playlist_name = current_item.text()
                # Find playlist ID
                for playlist in playlists:
                    if playlist[1] == playlist_name:
                        playlist_id = playlist[0]
                        if self.db.add_song_to_playlist(playlist_id, song_id):
                            QMessageBox.information(dialog, "Success", 
                                                  f"Song added to '{playlist_name}' playlist!")
                            dialog.accept()
                        else:
                            QMessageBox.warning(dialog, "Error", 
                                              "Failed to add song to playlist.")
                        break
        
        add_btn.clicked.connect(add_to_selected_playlist)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()
    
    def toggle_play_pause(self):
        """Toggle between play and pause"""
        current_state = self.player.player.state()
        
        if current_state == QMediaPlayer.PlayingState:
            # Currently playing, so pause
            self.player.pause()
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("Play")
            print("⏸️ Paused playback")
            
        elif current_state == QMediaPlayer.PausedState:
            # Currently paused, so resume
            self.player.play()
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("Pause")
            print("▶️ Resumed playback")
            
        else:
            # Not playing anything, start playback
            if self.current_song_data:
                # Resume current song
                self.player.play()
                self.play_pause_btn.setText("⏸")
                self.play_pause_btn.setToolTip("Pause")
                print("▶️ Started playback")
            else:
                # No song selected, play first song if available
                if self.music_table.rowCount() > 0:
                    self.music_table.selectRow(0)
                    self.play_selected_song(0)

    def previous_song(self):
        """Play the previous song"""
        if self.music_table.rowCount() == 0:
            return
        
        if self.shuffle_mode and self.shuffled_playlist_order:
            # Find current song in shuffled order
            current_song_id = None
            if self.current_song_data:
                current_song_id = self.current_song_data[0]
            
            current_shuffle_index = -1
            for i, (row, song_id) in enumerate(self.shuffled_playlist_order):
                if song_id == current_song_id:
                    current_shuffle_index = i
                    break
            
            if current_shuffle_index > 0:
                prev_row, prev_song_id = self.shuffled_playlist_order[current_shuffle_index - 1]
                self.music_table.selectRow(prev_row)
                self.play_selected_song()
            elif self.repeat_mode == "all":
                # Go to last song in shuffle order
                last_row, last_song_id = self.shuffled_playlist_order[-1]
                self.music_table.selectRow(last_row)
                self.play_selected_song()
        else:
            # Normal sequential mode
            current_row = self.music_table.currentRow()
            if current_row > 0:
                self.music_table.selectRow(current_row - 1)
                self.play_selected_song()
            elif self.repeat_mode == "all":
                # Go to last song
                self.music_table.selectRow(self.music_table.rowCount() - 1)
                self.play_selected_song()
    
    def next_song(self):
        """Play the next song"""
        if self.music_table.rowCount() == 0:
            return
        
        if self.shuffle_mode and self.shuffled_playlist_order:
            # Find current song in shuffled order
            current_song_id = None
            if self.current_song_data:
                current_song_id = self.current_song_data[0]
            
            current_shuffle_index = -1
            for i, (row, song_id) in enumerate(self.shuffled_playlist_order):
                if song_id == current_song_id:
                    current_shuffle_index = i
                    break
            
            if current_shuffle_index >= 0 and current_shuffle_index < len(self.shuffled_playlist_order) - 1:
                next_row, next_song_id = self.shuffled_playlist_order[current_shuffle_index + 1]
                self.music_table.selectRow(next_row)
                self.play_selected_song()
            elif self.repeat_mode == "all":
                # Go to first song in shuffle order
                first_row, first_song_id = self.shuffled_playlist_order[0]
                self.music_table.selectRow(first_row)
                self.play_selected_song()
        else:
            # Normal sequential mode
            current_row = self.music_table.currentRow()
            if current_row < self.music_table.rowCount() - 1:
                self.music_table.selectRow(current_row + 1)
                self.play_selected_song()
            elif self.repeat_mode == "all":                # Go to first song
                self.music_table.selectRow(0)
                self.play_selected_song()
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            # Enable shuffle mode
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet().replace("#404040", "#1DB954"))
            self.shuffle_btn.setToolTip("Shuffle: ON - Songs will play in random order")
            print("🔀 Shuffle mode enabled")
            
            # Create shuffled playlist order if we have songs
            if self.music_table.rowCount() > 0:
                self.create_shuffled_playlist()
        else:
            # Disable shuffle mode
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet().replace("#1DB954", "#404040"))
            self.shuffle_btn.setToolTip("Shuffle: OFF - Songs will play in order")
            print("📄 Shuffle mode disabled")
            
            # Clear shuffled playlist
            self.shuffled_playlist_order = []
    
    def create_shuffled_playlist(self):
        """Create a shuffled order of current playlist"""
        # Get all song IDs from the current table
        song_ids = []
        for row in range(self.music_table.rowCount()):
            song_id = self.music_table.item(row, 0).data(Qt.UserRole)
            if song_id:
                song_ids.append((row, song_id))
          # Shuffle the list while keeping track of original positions
        self.shuffled_playlist_order = song_ids.copy()
        random.shuffle(self.shuffled_playlist_order)
        print(f"🎲 Created shuffled playlist with {len(self.shuffled_playlist_order)} songs")
    
    def toggle_repeat(self):
        """Toggle repeat mode"""
        if self.repeat_mode == "off":
            self.repeat_mode = "all"
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("#404040", "#1DB954"))
            self.repeat_btn.setToolTip("Repeat: ALL - Will repeat entire playlist")
            print("🔁 Repeat all enabled")
        elif self.repeat_mode == "all":
            self.repeat_mode = "one"
            self.repeat_btn.setText("🔂")
            self.repeat_btn.setToolTip("Repeat: ONE - Will repeat current song")
            print("🔂 Repeat one enabled")
        else:
            self.repeat_mode = "off"
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("#1DB954", "#404040"))
            self.repeat_btn.setToolTip("Repeat: OFF")
            print("⏹️ Repeat disabled")
    
    def format_duration(self, duration):
        """Format duration in seconds to mm:ss format"""
        if duration is None or duration <= 0:
            return "0:00"
        
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        return f"{minutes}:{seconds:02d}"
    
    def update_position(self, position):
        """Update playback position"""
        if not self.slider_pressed:
            # Convert milliseconds to seconds for slider
            seconds = position // 1000
            self.progress_slider.setValue(seconds)
            self.time_label.setText(self.format_duration(seconds))

    def update_duration(self, duration):
        """Update song duration"""
        seconds = duration // 1000
        self.progress_slider.setMaximum(seconds)
        self.duration_label.setText(self.format_duration(seconds))

    def update_current_song_display(self):
        """Update the current song display"""
        if self.current_song_data:
            title = self.current_song_data[1] or "Unknown Title"
            artist = self.current_song_data[2] or "Unknown Artist"
            
            self.current_title_label.setText(title)
            self.current_artist_label.setText(artist)
            # Remove this line - current_song_label doesn't exist:
            # self.current_song_label.setText(f"♪ {title} - {artist}")

    def play_selected_song(self, row=None):
        """Play the currently selected song"""
        if row is None:
            current_row = self.music_table.currentRow()
        else:
            current_row = row
            # Select the row in the table
            self.music_table.selectRow(current_row)
        
        if current_row < 0:
            return
        
        # Get song ID from the table
        song_id = self.music_table.item(current_row, 0).data(Qt.UserRole)
        
        # Get full song data from database
        songs = self.db.get_all_songs()
        for song in songs:
            if song[0] == song_id:
                self.current_song_data = song
                break
        
        if self.current_song_data:
            file_path = self.current_song_data[7]  # file_path is at index 7
            
            if os.path.exists(file_path):
                if self.player.load_song(file_path):
                    self.player.play()
                    self.update_current_song_display()
                    # Button will be updated by the state change signal
                    print(f"🎵 Now playing: {self.current_song_data[1]} - {self.current_song_data[2]}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to load song")
            else:
                QMessageBox.critical(self, "Error", "Song file not found")
    
    def on_player_state_changed(self, state):
        """Handle player state changes"""
        # Update play button based on state
        self.update_play_button(state)
        
        if state == QMediaPlayer.StoppedState:
            # Check if it's an error or natural end
            if self.player.player.error() != QMediaPlayer.NoError:
                error_string = self.player.player.errorString()
                print(f"⚠️ Playback error: {error_string}")
                # Try next song on error
                self.next_song()
                return
            
            # Song finished naturally, handle repeat/next
            if self.repeat_mode == "one":
                self.play_selected_song()
            elif self.repeat_mode == "all":
                self.next_song()
            # If repeat is off, just stop (button already updated above)
    
    def on_progress_slider_moved(self, position):
        """Handle progress slider movement"""
        self.player.player.setPosition(position * 1000)
    
    def on_progress_slider_pressed(self):
        """Handle progress slider press - pause updates to avoid conflicts"""
        self.slider_pressed = True
    
    def on_progress_slider_released(self):
        """Handle progress slider release - resume updates"""
        self.slider_pressed = False
        position = self.progress_slider.value()
        self.player.player.setPosition(position * 1000)
    
    def update_play_button(self, state):
        """Update play button based on player state"""
        if state == QMediaPlayer.PlayingState:
            self.play_pause_btn.setText("⏸")
            self.play_pause_btn.setToolTip("Pause")
        elif state == QMediaPlayer.PausedState:
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("Play")
        else:  # StoppedState
            self.play_pause_btn.setText("▶")
            self.play_pause_btn.setToolTip("Play")
    
    def on_playlist_select(self, item):
        """Handle playlist selection"""
        playlist_name = item.text()
        try:
            # Get playlist ID from name
            playlists = self.db.get_playlists()
            playlist_id = None
            for pid, name, desc in playlists:
                if name == playlist_name:
                    playlist_id = pid
                    break
            
            if playlist_id:
                songs = self.db.get_playlist_songs(playlist_id)
                self.load_songs_to_table(songs)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load playlist: {e}")
    
    def load_songs_to_table(self, songs):
        """Load songs into the music table"""
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            song_id, title, artist, album, year, genre, duration, file_path, album_art, date_added = song
            
            # Create table items
            title_item = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            album_item = QTableWidgetItem(album)
            duration_item = QTableWidgetItem(self.format_duration(duration))
            
            # Set item flags - only Artist and Album are editable
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            artist_item.setFlags(artist_item.flags() | Qt.ItemIsEditable)
            album_item.setFlags(album_item.flags() | Qt.ItemIsEditable)
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemIsEditable)
            
            self.music_table.setItem(row, 0, title_item)
            self.music_table.setItem(row, 1, artist_item)
            self.music_table.setItem(row, 2, album_item)
            self.music_table.setItem(row, 3, duration_item)
            
            # Store song ID for later use
            title_item.setData(Qt.UserRole, song_id)

    # ...existing code...


def main():
    """Main function to run the music player"""
    app = QApplication(sys.argv)
    app.setApplicationName("Local Spotify Qt")
    app.setOrganizationName("Local Music Player")
    
    # Set application icon (if available)
    # app.setWindowIcon(QIcon('icon.png'))
    
    try:
        player = LocalSpotifyQt()
        player.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {e}")
        QMessageBox.critical(None, "Error", f"Failed to start application: {e}")


if __name__ == "__main__":
    main()


