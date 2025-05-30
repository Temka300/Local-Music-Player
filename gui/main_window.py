"""
Main window for the Local Spotify Qt application
"""

import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Add parent directory to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from core.database import MusicDatabase
from core.audio_player import AudioPlayer
from core.organizer import MusicLibraryOrganizer
from core.metadata import extract_metadata
from utils.themes import apply_dark_theme
from utils.constants import YOUTUBE_AVAILABLE, YouTubeDownloadThread
from workers.file_import_thread import FileImportThread, FolderScanThread
from gui.widgets.editable_columns_delegate import EditableColumnsDelegate
from gui.dialogs.create_playlist_dialog import CreatePlaylistDialog
from gui.dialogs.youtube_download_dialog import YouTubeDownloadDialog


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
        self.setup_keyboard_shortcuts()
        apply_dark_theme(self)
        
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
        self.current_artist_label.setStyleSheet("color: #B3B3B3; font-size: 12px;")
        
        text_info_layout.addWidget(self.current_title_label)
        text_info_layout.addWidget(self.current_artist_label)
        
        song_info_layout.addLayout(text_info_layout)
        left_layout.addLayout(song_info_layout)
        
        player_layout.addLayout(left_layout)
        
        # Center: Player controls
        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignCenter)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        
        self.shuffle_btn = QPushButton("🔀")
        self.previous_btn = QPushButton("⏮")
        self.play_pause_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.repeat_btn = QPushButton("🔁")
        
        # Style buttons
        for btn in [self.shuffle_btn, self.previous_btn, self.play_pause_btn, self.next_btn, self.repeat_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 20px;
                    background-color: #404040;
                    color: white;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #303030;
                }
            """)
        
        # Make play button larger and green
        self.play_pause_btn.setFixedSize(50, 50)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 25px;
                background-color: #1DB954;
                color: white;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)
        
        controls_layout.addWidget(self.shuffle_btn)
        controls_layout.addWidget(self.previous_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.repeat_btn)
        
        center_layout.addLayout(controls_layout)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("color: #B3B3B3; font-size: 11px;")
        self.time_label.setFixedWidth(35)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #404040;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)
        
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet("color: #B3B3B3; font-size: 11px;")
        self.duration_label.setFixedWidth(35)
        
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.duration_label)
        
        center_layout.addLayout(progress_layout)
        player_layout.addLayout(center_layout)
        
        # Right: Volume controls
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignCenter)
        
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(30, 30)
        self.mute_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 16px;
                color: #B3B3B3;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #404040;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)
        
        right_layout.addWidget(self.mute_btn)
        right_layout.addWidget(self.volume_slider)
        
        player_layout.addLayout(right_layout)
        
        player_dock.setWidget(player_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, player_dock)

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        import_folder_action = QAction('Import Folder...', self)
        import_folder_action.setShortcut('Ctrl+O')
        import_folder_action.triggered.connect(self.add_folder)
        file_menu.addAction(import_folder_action)
        
        import_files_action = QAction('Import Files...', self)
        import_files_action.setShortcut('Ctrl+Shift+O')
        import_files_action.triggered.connect(self.add_files)
        file_menu.addAction(import_files_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        library_action = QAction('Library', self)
        library_action.setShortcut('Ctrl+1')
        library_action.triggered.connect(self.show_library)
        view_menu.addAction(library_action)
        
        # Playback menu
        playback_menu = menubar.addMenu('Playback')
        
        play_pause_action = QAction('Play/Pause', self)
        play_pause_action.setShortcut('Space')
        play_pause_action.triggered.connect(self.toggle_play_pause)
        playback_menu.addAction(play_pause_action)
        
        next_action = QAction('Next', self)
        next_action.setShortcut('Ctrl+Right')
        next_action.triggered.connect(self.next_song)
        playback_menu.addAction(next_action)
        
        previous_action = QAction('Previous', self)
        previous_action.setShortcut('Ctrl+Left')
        previous_action.triggered.connect(self.previous_song)
        playback_menu.addAction(previous_action)
        
        playback_menu.addSeparator()
        
        shuffle_action = QAction('Shuffle', self)
        shuffle_action.setShortcut('Ctrl+S')
        shuffle_action.triggered.connect(self.toggle_shuffle)
        playback_menu.addAction(shuffle_action)
        
        repeat_action = QAction('Repeat', self)
        repeat_action.setShortcut('Ctrl+R')
        repeat_action.triggered.connect(self.toggle_repeat)
        playback_menu.addAction(repeat_action)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Sidebar connections
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.add_files_btn.clicked.connect(self.add_files)
        if YOUTUBE_AVAILABLE:
            self.youtube_btn.clicked.connect(self.youtube_download_dialog)
        else:
            self.youtube_btn.setEnabled(False)
            self.youtube_btn.setToolTip("YouTube downloader not available")
        
        self.library_btn.clicked.connect(self.show_library)
        self.create_playlist_btn.clicked.connect(self.create_playlist_dialog)
        self.search_edit.textChanged.connect(self.on_search)
        self.playlist_list.itemClicked.connect(self.on_playlist_select)
        
        # Table connections
        self.music_table.cellDoubleClicked.connect(self.on_song_double_click)
        self.music_table.customContextMenuRequested.connect(self.show_context_menu)
        self.music_table.itemChanged.connect(self.on_table_item_changed)
        
        # Player connections
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.next_song)
        self.previous_btn.clicked.connect(self.previous_song)
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        self.repeat_btn.clicked.connect(self.toggle_repeat)
        
        # Volume connections
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.volume_slider.sliderPressed.connect(self.on_volume_slider_pressed)
        self.volume_slider.sliderReleased.connect(self.on_volume_slider_released)
        self.mute_btn.clicked.connect(self.toggle_mute)
        
        # Progress connections
        self.progress_slider.sliderMoved.connect(self.on_progress_slider_moved)
        self.progress_slider.sliderPressed.connect(self.on_progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_progress_slider_released)
        
        # Audio player connections
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.on_player_state_changed)
    
    # Import and file management methods
    def add_folder(self):
        """Add all music files from a selected folder"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if folder_path:
            # Create progress dialog
            progress_dialog = QProgressDialog("Scanning folder...", "Cancel", 0, 0, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setWindowTitle("Importing Music")
            progress_dialog.setAutoClose(False)
            progress_dialog.show()
            
            # Start folder scan thread
            self.scan_thread = FolderScanThread(folder_path, self.organizer, self.db, extract_metadata)
            self.scan_thread.progress.connect(lambda filename: progress_dialog.setLabelText(f"Processing: {os.path.basename(filename)}"))
            self.scan_thread.finished.connect(lambda count: self.on_import_finished(count, progress_dialog))
            self.scan_thread.start()
    
    def add_files(self):
        """Add selected music files"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Music Files",
            "",
            "Audio Files (*.mp3 *.m4a *.flac *.wav *.ogg *.aac);;All Files (*)"
        )
        
        if file_paths:
            # Create progress dialog
            progress_dialog = QProgressDialog("Importing files...", "Cancel", 0, len(file_paths), self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setWindowTitle("Importing Music")
            progress_dialog.setAutoClose(False)
            progress_dialog.show()
            
            # Start import thread
            self.import_thread = FileImportThread(file_paths, self.organizer, self.db, extract_metadata)
            self.import_thread.progress.connect(lambda filename: progress_dialog.setLabelText(f"Processing: {os.path.basename(filename)}"))
            self.import_thread.finished.connect(lambda count: self.on_import_finished(count, progress_dialog))
            self.import_thread.start()
    
    def on_import_finished(self, count, progress_dialog):
        """Handle import completion"""
        progress_dialog.close()
        if count > 0:
            QMessageBox.information(self, "Import Complete", f"Successfully imported {count} songs!")
            self.refresh_library()
        else:
            QMessageBox.warning(self, "Import Warning", "No new songs were imported.")
    
    # YouTube download methods
    def youtube_download_dialog(self):
        """Show YouTube download dialog"""
        if not YOUTUBE_AVAILABLE:
            QMessageBox.warning(self, "YouTube Unavailable", "YouTube downloader is not available.")
            return
        
        url, ok = QInputDialog.getText(self, "Download from YouTube", "Enter YouTube URL:")
        if ok and url:
            self.start_youtube_download(url)
    
    def start_youtube_download(self, url):
        """Start YouTube download in background thread"""
        # Create progress dialog
        progress_dialog = QProgressDialog("Downloading from YouTube...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("YouTube Download")
        progress_dialog.setAutoClose(False)
        progress_dialog.show()
        
        # Start download thread
        self.download_thread = YouTubeDownloadThread(url, self.organizer.musics_folder)
        self.download_thread.progress.connect(lambda status, percent: self._update_download_progress(progress_dialog, status, percent))
        self.download_thread.finished.connect(lambda file_path, metadata: self.on_youtube_download_finished(file_path, metadata, progress_dialog))
        self.download_thread.error.connect(lambda error: self.on_youtube_download_error(error, progress_dialog))
        self.download_thread.start()
    
    def _update_download_progress(self, progress_dialog, status, percent):
        """Update download progress"""
        progress_dialog.setLabelText(status)
        progress_dialog.setValue(int(percent))
    
    def on_youtube_download_finished(self, file_path, metadata, progress_dialog):
        """Handle YouTube download completion"""
        progress_dialog.close()
        if file_path and os.path.exists(file_path):
            # Add to database
            try:
                song_data = extract_metadata(file_path)
                if song_data:
                    self.db.add_song(song_data)
                    QMessageBox.information(self, "Download Complete", f"Successfully downloaded: {song_data['title'] if song_data['title'] else 'Unknown'}")
                    self.refresh_library()
                else:
                    QMessageBox.warning(self, "Download Warning", "File downloaded but metadata extraction failed.")
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to add song to database: {str(e)}")
        else:
            QMessageBox.critical(self, "Download Failed", "Download failed or file not found.")
    
    def on_youtube_download_error(self, error, progress_dialog):
        """Handle YouTube download error"""
        progress_dialog.close()
        QMessageBox.critical(self, "Download Error", f"Download failed: {error}")
    
    # Playlist management
    def create_playlist_dialog(self):
        """Show create playlist dialog"""
        name, ok = QInputDialog.getText(self, "Create Playlist", "Enter playlist name:")
        if ok and name:
            description, ok = QInputDialog.getText(self, "Create Playlist", "Enter playlist description (optional):")
            if ok:
                try:
                    self.db.create_playlist(name, description or "")
                    self.refresh_playlists()
                    QMessageBox.information(self, "Playlist Created", f"Playlist '{name}' created successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create playlist: {str(e)}")
    
    def refresh_library(self):
        """Refresh the music library display"""
        try:
            songs = self.db.get_all_songs()
            self.populate_music_table(songs)
            print(f"✅ Loaded {len(songs)} songs")
        except Exception as e:
            print(f"❌ Error refreshing library: {e}")
   
    def populate_music_table(self, songs):
        """Populate the music table with song data"""
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            try:
                # song is a tuple from database: (id, title, artist, album, year, genre, duration, file_path, ...)
                # Access by index, not by key
                song_id = song[0] if len(song) > 0 else 0
                title = str(song[1]) if len(song) > 1 else "Unknown"
                artist = str(song[2]) if len(song) > 2 else "Unknown Artist"
                album = str(song[3]) if len(song) > 3 else "Unknown Album"
                duration = song[6] if len(song) > 6 else 0
                
                # Format duration
                if duration and duration > 0:
                    try:
                        duration_float = float(duration)
                        minutes = int(duration_float // 60)
                        seconds = int(duration_float % 60)
                        duration_str = f"{minutes}:{seconds:02d}"
                    except (ValueError, TypeError):
                        duration_str = ""
                else:
                    duration_str = ""
                
                # Create table items
                title_item = QTableWidgetItem(title)
                artist_item = QTableWidgetItem(artist)
                album_item = QTableWidgetItem(album)
                duration_item = QTableWidgetItem(duration_str)
                
                # Store the complete song data in the title item for later access
                title_item.setData(Qt.UserRole, song)
                
                # Set items in table
                self.music_table.setItem(row, 0, title_item)
                self.music_table.setItem(row, 1, artist_item)
                self.music_table.setItem(row, 2, album_item)
                self.music_table.setItem(row, 3, duration_item)
                
            except Exception as e:
                print(f"❌ Error populating row {row}: {e}")
                # Set error values for failed rows
                self.music_table.setItem(row, 0, QTableWidgetItem("Error"))
                self.music_table.setItem(row, 1, QTableWidgetItem("Unknown"))
                self.music_table.setItem(row, 2, QTableWidgetItem("Unknown"))
                self.music_table.setItem(row, 3, QTableWidgetItem(""))

    def refresh_playlists(self):
        """Refresh the playlists display"""
        try:
            playlists = self.db.get_playlists()
            self.playlist_list.clear()
            for playlist in playlists:
                # playlist is a tuple: (id, name, description, created_date)
                # Access by index, not by key
                playlist_id = playlist[0] if len(playlist) > 0 else 0
                playlist_name = str(playlist[1]) if len(playlist) > 1 else "Unknown Playlist"
                playlist_description = str(playlist[2]) if len(playlist) > 2 else ""
                
                item = QListWidgetItem(playlist_name)
                item.setData(Qt.UserRole, playlist_id)
                item.setToolTip(playlist_description if playlist_description else f"Playlist: {playlist_name}")
                self.playlist_list.addItem(item)
            print(f"✅ Loaded {len(playlists)} playlists")
        except Exception as e:
            print(f"❌ Error refreshing playlists: {e}")
    
    def show_library(self):
        """Show the main library view"""
        self.view_title.setText("Music Library")
        self.refresh_library()
    def on_search(self, query):
        """Handle search query"""
        if query.strip():
            songs = self.db.search_songs(query)
            self.view_title.setText(f"Search Results for '{query}'")
        else:
            songs = self.db.get_all_songs()
            self.view_title.setText("Music Library")
        
        self.music_table.setRowCount(len(songs))
        
        for row, song in enumerate(songs):
            # song is a tuple: (id, title, artist, album, year, genre, duration, file_path, ...)
            title = song[1] if len(song) > 1 and song[1] else 'Unknown'
            artist = song[2] if len(song) > 2 and song[2] else 'Unknown'
            album = song[3] if len(song) > 3 and song[3] else 'Unknown'
            duration = song[6] if len(song) > 6 and song[6] else 0
            
            title_item = QTableWidgetItem(title)
            title_item.setData(Qt.UserRole, song)
            self.music_table.setItem(row, 0, title_item)
            
            self.music_table.setItem(row, 1, QTableWidgetItem(artist))
            self.music_table.setItem(row, 2, QTableWidgetItem(album))
            self.music_table.setItem(row, 3, QTableWidgetItem(self.format_duration(duration)))
    
    def on_song_double_click(self, row, column):
        """Handle song double click to play"""
        title_item = self.music_table.item(row, 0)
        if title_item:
            song_data = title_item.data(Qt.UserRole)
            if song_data:
                self.play_song(song_data)
    def play_song(self, song_data):
        """Play a song"""
        # song_data is a tuple: (id, title, artist, album, year, genre, duration, file_path, ...)
        # Access file_path by index (index 7)
        file_path = song_data[7] if len(song_data) > 7 else None
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The file was not found.")
            return
        
        self.current_song_data = song_data
        
        # Update UI - access tuple elements by index
        title = str(song_data[1]) if len(song_data) > 1 else "Unknown"
        artist = str(song_data[2]) if len(song_data) > 2 else "Unknown Artist"
        
        self.current_title_label.setText(title)
        self.current_artist_label.setText(artist)
        
        # Load and play
        self.player.load_song(file_path)
        self.player.play()
        
        # Update play button
        self.play_pause_btn.setText("⏸")
        
        # Update current playlist if not already set
        if not self.current_playlist:
            self.current_playlist = self.get_current_song_list()
            self.current_index = self.find_current_song_index(self.current_playlist)
            if self.shuffle_mode:
                self.create_shuffled_playlist()
        
        self.statusBar().showMessage(f"Playing: {title} - {artist}")
    
    def format_duration(self, duration):
        """Format duration in seconds to mm:ss"""
        if not duration or duration == 0:
            return "0:00"
        
        try:
            duration = int(float(duration))
            minutes = duration // 60
            seconds = duration % 60
            return f"{minutes}:{seconds:02d}"
        except (ValueError, TypeError):
            return "0:00"
    
    # Context menu and table editing
    def show_context_menu(self, position):
        """Show context menu for table items"""
        item = self.music_table.itemAt(position)
        if item:
            menu = QMenu(self)
            
            play_action = QAction("Play", self)
            play_action.triggered.connect(lambda: self.on_song_double_click(item.row(), 0))
            menu.addAction(play_action)
            
            menu.addSeparator()
            
            remove_action = QAction("Remove from Library", self)
            remove_action.triggered.connect(self.remove_selected_song)
            menu.addAction(remove_action)
            
            menu.exec_(self.music_table.mapToGlobal(position))
    def remove_selected_song(self):
        """Remove selected song from library"""
        current_row = self.music_table.currentRow()
        if current_row >= 0:
            title_item = self.music_table.item(current_row, 0)
            if title_item:
                song_data = title_item.data(Qt.UserRole)
                if song_data:
                    # song_data is a tuple: (id, title, artist, album, ...)
                    # Access by index, not by key
                    song_id = song_data[0] if len(song_data) > 0 else 0
                    title = str(song_data[1]) if len(song_data) > 1 else "Unknown"
                    
                    reply = QMessageBox.question(
                        self, 
                        "Remove Song", 
                        f"Are you sure you want to remove '{title}' from the library?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        try:
                            self.db.remove_song(song_id)
                            self.refresh_library()
                            QMessageBox.information(self, "Song Removed", "Song removed from library successfully!")
                        except Exception as e:
                            QMessageBox.critical(self, "Error", f"Failed to remove song: {str(e)}")
    
    def on_table_item_changed(self, item):
        """Handle table item changes for inline editing"""
        try:
            # Get the song data from the first column of this row
            title_item = self.music_table.item(item.row(), 0)
            if not title_item:
                return
            
            song_data = title_item.data(Qt.UserRole)
            if not song_data:
                return
            
            # Get the field being edited
            column = item.column()
            if column == 0:
                field = 'title'
                field_index = 1
            elif column == 1:
                field = 'artist'
                field_index = 2
            elif column == 2:
                field = 'album'
                field_index = 3
            else:
                return  # Only allow editing title, artist, album
            
            new_value = item.text().strip()
            
            # Handle both tuple and dictionary access
            if isinstance(song_data, (list, tuple)):
                song_id = song_data[0]  # ID is at index 0
                old_value = song_data[field_index] if len(song_data) > field_index else ''
            else:
                song_id = song_data['id']
                old_value = song_data[field] if song_data[field] else ''
            
            # Only update if value actually changed
            if new_value != old_value:
                success = self.db.update_song_metadata(song_id, field, new_value)
                if success:
                    # Update the stored song data in the item
                    if isinstance(song_data, (list, tuple)):
                        # Convert to list, update, convert back to tuple
                        song_list = list(song_data)
                        if len(song_list) > field_index:
                            song_list[field_index] = new_value
                        updated_song_data = tuple(song_list)
                    else:
                        song_data[field] = new_value
                        updated_song_data = song_data
                    
                    title_item.setData(Qt.UserRole, updated_song_data)
                    self.statusBar().showMessage(f"Updated {field} successfully", 2000)
                else:
                    # Revert the change
                    if isinstance(song_data, (list, tuple)):
                        item.setText(old_value)
                    else:
                        item.setText(song_data[field] if song_data[field] else '')
                    
        except Exception as e:
            print(f"❌ Error updating song metadata: {e}")
            # Revert the change on error
            try:
                if isinstance(song_data, (list, tuple)):
                    old_value = song_data[field_index] if len(song_data) > field_index else ''
                    item.setText(old_value)
                else:
                    item.setText(song_data[field] if song_data[field] else '')
            except:
                item.setText('')
    def on_playlist_select(self, item):
        """Handle playlist selection"""
        playlist_id = item.data(Qt.UserRole)
        if playlist_id:
            playlist_name = item.text()
            self.view_title.setText(f"Playlist: {playlist_name}")
            songs = self.db.get_playlist_songs(playlist_id)
            
            self.music_table.setRowCount(len(songs))
            for row, song in enumerate(songs):
                # song is a tuple: (id, title, artist, album, year, genre, duration, file_path, ...)
                title = str(song[1]) if len(song) > 1 else "Unknown"
                artist = str(song[2]) if len(song) > 2 else "Unknown Artist"
                album = str(song[3]) if len(song) > 3 else "Unknown Album"
                duration = song[6] if len(song) > 6 else 0
                
                title_item = QTableWidgetItem(title)
                title_item.setData(Qt.UserRole, song)
                self.music_table.setItem(row, 0, title_item)
                
                self.music_table.setItem(row, 1, QTableWidgetItem(artist))
                self.music_table.setItem(row, 2, QTableWidgetItem(album))
                self.music_table.setItem(row, 3, QTableWidgetItem(self.format_duration(duration)))
    
    # Player control methods
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.current_song_data:
            if self.player.is_playing():
                self.player.pause()
                self.play_pause_btn.setText("▶")
            else:
                self.player.play()
                self.play_pause_btn.setText("⏸")
        else:
            # If no song is loaded, play first song in current view
            if self.music_table.rowCount() > 0:
                self.on_song_double_click(0, 0)
    
    def next_song(self):
        """Play next song"""
        if not self.current_playlist:
            return
        
        if self.shuffle_mode and self.shuffled_playlist_order:
            current_shuffled_index = self.shuffled_playlist_order.index(self.current_index)
            if current_shuffled_index < len(self.shuffled_playlist_order) - 1:
                self.current_index = self.shuffled_playlist_order[current_shuffled_index + 1]
            elif self.repeat_mode == "all":
                self.current_index = self.shuffled_playlist_order[0]
            else:
                return
        else:
            if self.current_index < len(self.current_playlist) - 1:
                self.current_index += 1
            elif self.repeat_mode == "all":
                self.current_index = 0
            else:
                return
        
        song_data = self.current_playlist[self.current_index]
        self.play_song(song_data)
        self.update_table_selection(self.current_index)
    
    def previous_song(self):
        """Play previous song"""
        if not self.current_playlist:
            return
        
        if self.shuffle_mode and self.shuffled_playlist_order:
            current_shuffled_index = self.shuffled_playlist_order.index(self.current_index)
            if current_shuffled_index > 0:
                self.current_index = self.shuffled_playlist_order[current_shuffled_index - 1]
            elif self.repeat_mode == "all":
                self.current_index = self.shuffled_playlist_order[-1]
            else:
                return
        else:
            if self.current_index > 0:
                self.current_index -= 1
            elif self.repeat_mode == "all":
                self.current_index = len(self.current_playlist) - 1
            else:
                return
        
        song_data = self.current_playlist[self.current_index]
        self.play_song(song_data)
        self.update_table_selection(self.current_index)
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet() + "color: #1DB954;")
            if self.current_playlist:
                self.create_shuffled_playlist()
        else:
            self.shuffle_btn.setStyleSheet(self.shuffle_btn.styleSheet().replace("color: #1DB954;", ""))
            self.shuffled_playlist_order = []
        
        self.statusBar().showMessage(f"Shuffle {'ON' if self.shuffle_mode else 'OFF'}", 2000)
    
    def toggle_repeat(self):
        """Toggle repeat mode (off -> one -> all -> off)"""
        if self.repeat_mode == "off":
            self.repeat_mode = "one"
            self.repeat_btn.setText("🔂")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet() + "color: #1DB954;")
            status = "Repeat ONE"
        elif self.repeat_mode == "one":
            self.repeat_mode = "all"
            self.repeat_btn.setText("🔁")
            status = "Repeat ALL"
        else:
            self.repeat_mode = "off"
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setStyleSheet(self.repeat_btn.styleSheet().replace("color: #1DB954;", ""))
            status = "Repeat OFF"
        
        self.statusBar().showMessage(status, 2000)
    
    # Helper methods
    def get_current_song_list(self):
        """Get list of songs currently displayed in table"""
        songs = []
        for row in range(self.music_table.rowCount()):
            title_item = self.music_table.item(row, 0)
            if title_item:
                song_data = title_item.data(Qt.UserRole)
                if song_data:
                    songs.append(song_data)
        return songs
    def find_current_song_index(self, song_list):
        """Find index of current song in the given list"""
        if not self.current_song_data:
            return 0
        
        # current_song_data is a tuple: (id, title, artist, ...)
        current_song_id = self.current_song_data[0] if len(self.current_song_data) > 0 else 0
        
        for i, song in enumerate(song_list):
            # song is also a tuple: (id, title, artist, ...)
            song_id = song[0] if len(song) > 0 else 0
            if song_id == current_song_id:
                return i
        return 0
    
    def update_table_selection(self, index):
        """Update table selection to match current playing song"""
        if 0 <= index < self.music_table.rowCount():
            self.music_table.selectRow(index)
    
    def create_shuffled_playlist(self):
        """Create shuffled order for current playlist"""
        import random
        if self.current_playlist:
            self.shuffled_playlist_order = list(range(len(self.current_playlist)))
            random.shuffle(self.shuffled_playlist_order)
            # Ensure current song stays current
            if self.current_index in self.shuffled_playlist_order:
                current_shuffled_pos = self.shuffled_playlist_order.index(self.current_index)
                self.shuffled_playlist_order[0], self.shuffled_playlist_order[current_shuffled_pos] = \
                    self.shuffled_playlist_order[current_shuffled_pos], self.shuffled_playlist_order[0]
    
    def on_song_end(self):
        """Handle when song ends"""
        if self.repeat_mode == "one":
            self.player.set_position(0)
            self.player.play()
        else:
            self.next_song()
    
    # Keyboard shortcuts
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Volume shortcuts
        QShortcut(QKeySequence("Ctrl+Up"), self, lambda: self.increase_volume(10))
        QShortcut(QKeySequence("Ctrl+Down"), self, lambda: self.decrease_volume(10))
        QShortcut(QKeySequence("M"), self, self.toggle_mute)
        
        # Quick volume sets
        for i in range(10):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda vol=i*10: self.set_volume_shortcut(vol))
    
    # Volume control methods
    def on_volume_changed(self, value):
        """Handle volume slider change"""
        self.player.set_volume(value)
        
        # Update mute button icon
        if value == 0:
            self.mute_btn.setText("🔇")
        elif value < 30:
            self.mute_btn.setText("🔈")
        elif value < 70:
            self.mute_btn.setText("🔉")
        else:
            self.mute_btn.setText("🔊")
    
    def on_volume_slider_pressed(self):
        """Handle volume slider press"""
        pass
    
    def on_volume_slider_released(self):
        """Handle volume slider release"""
        pass
    
    def toggle_mute(self):
        """Toggle mute"""
        if not hasattr(self, '_previous_volume'):
            self._previous_volume = 70
        
        if self.volume_slider.value() == 0:
            self.volume_slider.setValue(self._previous_volume)
        else:
            self._previous_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
    
    def set_volume_shortcut(self, volume):
        """Set volume via keyboard shortcut"""
        self.volume_slider.setValue(volume)
    
    def increase_volume(self, amount=5):
        """Increase volume"""
        current = self.volume_slider.value()
        new_volume = min(100, current + amount)
        self.volume_slider.setValue(new_volume)
    
    def decrease_volume(self, amount=5):
        """Decrease volume"""
        current = self.volume_slider.value()
        new_volume = max(0, current - amount)
        self.volume_slider.setValue(new_volume)
    
    # Progress and position methods
    def update_position(self, position):
        """Update playback position"""
        if not self.slider_pressed:
            self.progress_slider.setValue(position)
            self.time_label.setText(self.player.format_duration(position // 1000))
    
    def update_duration(self, duration):
        """Update track duration"""
        self.progress_slider.setRange(0, duration)
        self.duration_label.setText(self.player.format_duration(duration // 1000))
    
    def on_player_state_changed(self, state):
        """Handle player state changes"""
        if state == 6:  # VLC Ended state
            self.on_song_end()
    
    def on_progress_slider_moved(self, position):
        """Handle progress slider movement"""
        if self.slider_pressed:
            self.player.set_position(position)
    
    def on_progress_slider_pressed(self):
        """Handle progress slider press"""
        self.slider_pressed = True
    
    def on_progress_slider_released(self):
        """Handle progress slider release"""
        self.slider_pressed = False
    
    # Cleanup methods
    def cleanup_missing_files(self):
        """Remove references to missing files from database"""
        try:
            musics_folder = self.organizer.musics_folder
            removed_count = self.db.cleanup_missing_files(musics_folder)
            if removed_count > 0:
                print(f"🧹 Removed {removed_count} missing files from database")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
    
    def fix_double_extensions(self):
        """Fix files with double extensions"""
        try:
            musics_folder = self.organizer.musics_folder
            if not os.path.exists(musics_folder):
                return
            
            fixed_count = 0
            for root, dirs, files in os.walk(musics_folder):
                for filename in files:
                    # Check for double extensions like .mp3.mp3, .m4a.m4a, etc.
                    if any(filename.endswith(f'.{ext}.{ext}') for ext in ['mp3', 'm4a', 'flac', 'wav', 'ogg', 'aac']):
                        old_path = os.path.join(root, filename)
                        # Remove the duplicate extension
                        new_filename = filename
                        for ext in ['mp3', 'm4a', 'flac', 'wav', 'ogg', 'aac']:
                            if filename.endswith(f'.{ext}.{ext}'):
                                new_filename = filename[:-len(f'.{ext}')]
                                break
                        
                        new_path = os.path.join(root, new_filename)
                        
                        if old_path != new_path and not os.path.exists(new_path):
                            try:
                                os.rename(old_path, new_path)
                                # Update database path if the file exists in database
                                songs = self.db.get_all_songs()
                                for song in songs:
                                    if song['file_path'] == old_path:
                                        self.db.update_song_metadata(song['id'], 'file_path', new_path)
                                        break
                                
                                fixed_count += 1
                                print(f"🔧 Fixed double extension: {filename} -> {new_filename}")
                                
                            except OSError as e:
                                print(f"❌ Failed to rename {filename}: {e}")
            
            if fixed_count > 0:
                print(f"🔧 Fixed {fixed_count} files with double extensions")
                
        except Exception as e:
            print(f"❌ Error during double extension fix: {e}")
