"""
Main window for the Local Spotify Qt application
"""

import random
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
from core.album_art import AlbumArtExtractor, AlbumArtLabel
from utils.themes import apply_dark_theme
from utils.constants import (
    APP_NAME, APP_VERSION, 
    AUDIO_FILE_FILTER
)

# Import YouTube functionality directly
try:
    from core.youtube_downloader import YouTubeDownloadThread
    YOUTUBE_AVAILABLE = True
    print("✅ YouTube downloader available")
except ImportError:
    YOUTUBE_AVAILABLE = False
    YouTubeDownloadThread = None
    print("⚠️ YouTube downloader not available")
from workers.file_import_thread import FileImportThread, FolderScanThread
from gui.widgets.editable_columns_delegate import EditableColumnsDelegate
from gui.dialogs.create_playlist_dialog import CreatePlaylistDialog
from gui.dialogs.youtube_download_dialog import YouTubeDownloadDialog
from gui.widgets.scrolling_label import ScrollingLabel


class LocalSpotifyQt(QMainWindow):
    """Main music player application using PyQt"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"🎵 {APP_NAME}")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize components
        self.db = MusicDatabase()
        self.player = AudioPlayer()

        # Initialize file organizer
        current_dir = os.path.dirname(os.path.abspath(__file__))  # This is gui/
        parent_dir = os.path.dirname(current_dir)  # This is the main project directory
        self.organizer = MusicLibraryOrganizer(parent_dir)  # Use parent_dir instead of current_dir
        
        # Application state (initialize before UI setup)
        self.current_playlist = []
        self.current_index = 0
        self.shuffle_mode = False
        self.shuffle_index = 0
        self.shuffled_playlist = []  # Keep this one, remove the other
        self.current_song_data = None
        self.slider_pressed = False
        
        # Setup UI FIRST
        self.setup_ui()
        self.setup_connections()  # This already connects all audio player signals
        self.setup_keyboard_shortcuts()
        apply_dark_theme(self)
        
        # THEN do cleanup and data loading (after UI exists)
        self.cleanup_missing_files()
        self.fix_double_extensions()
        
        # Load initial data
        self.refresh_library()
        self.refresh_playlists()
        
        # Initialize repeat mode
        self.repeat_mode = "off"  # Can be "off", "one", "all"
    
    def setup_ui(self):
        """Setup the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout - VERTICAL to stack content and player controls
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Content area layout
        content_layout = QHBoxLayout()
        
        # Left sidebar
        self.create_sidebar(content_layout)
        
        # Right content area
        self.create_content_area(content_layout)
        
        # Create a widget for the content area
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        
        # Bottom player controls
        player_controls = self.create_player_controls()
        
        # Add content and player controls to main layout
        main_layout.addWidget(content_widget)
        main_layout.addWidget(player_controls)  # This was missing!
        
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
        title_label = QLabel(f"🎵 {APP_NAME}")
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
        
        # Configure table header for draggable resizing
        header = self.music_table.horizontalHeader()
        
        # Enable manual resize mode for all columns
        header.setSectionResizeMode(QHeaderView.Interactive)
        
        # Set minimum column widths
        header.setMinimumSectionSize(80)
        
        # Set initial column widths
        header.resizeSection(0, 300)  # Title - wider
        header.resizeSection(1, 150)  # Artist
        header.resizeSection(2, 150)  # Album
        header.resizeSection(3, 80)   # Duration - narrower
        
        # Make the last section (Duration) stretch to fill remaining space
        header.setStretchLastSection(True)
        
        # Enable drag and drop for column reordering (optional)
        header.setSectionsMovable(True)
        
        # Show resize cursor when hovering over column borders
        header.setCursor(Qt.SplitHCursor)
        
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
        """Create the bottom player controls with centered layout"""
        # Main player container
        player_widget = QWidget()
        player_widget.setFixedHeight(120)
        player_widget.setStyleSheet("""
            QWidget {
                background-color: #181818;
            }
        """)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(player_widget)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(20)
        
        # === LEFT SECTION: Album Art + Song Info ===
        left_section = QWidget()
        left_section.setFixedWidth(380)
        left_layout = QHBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Album art
        self.album_art_label = AlbumArtLabel(size=(80, 80))
        left_layout.addWidget(self.album_art_label)
        
        # Song info container
        song_info_container = QWidget()
        song_info_layout = QVBoxLayout(song_info_container)
        song_info_layout.setContentsMargins(0, 0, 0, 0)
        song_info_layout.setSpacing(4)
        
        # Song title - USE SCROLLING LABEL
        self.current_song_label = ScrollingLabel("No song playing")
        self.current_song_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.current_song_label.setMaximumHeight(36)
        self.current_song_label.setMinimumWidth(200)
        
        # Artist info
        self.current_artist_label = QLabel("")
        self.current_artist_label.setStyleSheet("""
            QLabel {
                color: #B3B3B3;
                font-size: 12px;
            }
        """)
        self.current_artist_label.setWordWrap(True)
        
        # Album info
        self.current_album_label = QLabel("")
        self.current_album_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 11px;
            }
        """)
        
        song_info_layout.addWidget(self.current_song_label)
        song_info_layout.addWidget(self.current_artist_label)
        song_info_layout.addWidget(self.current_album_label)
        song_info_layout.addStretch()
        
        left_layout.addWidget(song_info_container)
        left_layout.addStretch()


        # === CENTER SECTION: Controls ===
        center_section = QWidget()
        center_section.setFixedWidth(400)
        center_layout = QVBoxLayout(center_section)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        
        # Control buttons row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(15)
        
        # Create control buttons
        self.shuffle_btn = QPushButton("🔀")
        self.previous_btn = QPushButton("⏮")
        self.play_pause_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.repeat_btn = QPushButton("↪️")
        
        # UNIFIED STYLE - All buttons start grey
        self.apply_grey_button_style(self.shuffle_btn)
        self.apply_grey_button_style(self.previous_btn)
        self.apply_grey_button_style(self.next_btn)
        self.apply_grey_button_style(self.repeat_btn)
        self.apply_grey_button_style(self.play_pause_btn)  # Play button also starts grey
        
        # Add buttons to controls layout
        controls_layout.addStretch()
        controls_layout.addWidget(self.shuffle_btn)
        controls_layout.addWidget(self.previous_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.repeat_btn)
        controls_layout.addStretch()
        
        # Progress bar section
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)
        
        # Current time
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet("color: #B3B3B3; font-size: 11px; font-family: 'Consolas', monospace;")
        
        # Progress slider
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #404040; border-radius: 2px; }
            QSlider::handle:horizontal { background: #FFFFFF; width: 12px; height: 12px; border-radius: 6px; margin: -4px 0; }
            QSlider::handle:horizontal:hover { background: #1DB954; }
            QSlider::sub-page:horizontal { background: #1DB954; border-radius: 2px; }
        """)
        
        # Total time
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #B3B3B3; font-size: 11px; font-family: 'Consolas', monospace;")
        
        progress_layout.addWidget(self.current_time_label)
        progress_layout.addWidget(self.position_slider)
        progress_layout.addWidget(self.total_time_label)
        
        center_layout.addLayout(controls_layout)
        center_layout.addLayout(progress_layout)
        
        # === RIGHT SECTION: Volume ===
        right_section = QWidget()
        right_section.setFixedWidth(150)
        right_layout = QHBoxLayout(right_section)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # Mute button
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(32, 32)
        self.apply_grey_button_style(self.mute_btn)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: #404040; border-radius: 2px; }
            QSlider::handle:horizontal { background: #FFFFFF; width: 12px; height: 12px; border-radius: 6px; margin: -4px 0; }
            QSlider::handle:horizontal:hover { background: #1DB954; }
            QSlider::sub-page:horizontal { background: #FFFFFF; border-radius: 2px; }
        """)
        
        right_layout.addStretch()
        right_layout.addWidget(self.mute_btn)
        right_layout.addWidget(self.volume_slider)
        
        # === ASSEMBLE ===
        main_layout.addWidget(left_section)
        main_layout.addWidget(center_section)
        main_layout.addWidget(right_section)
        
        return player_widget

    def apply_grey_button_style(self, button):
        """Apply consistent grey button style"""
        button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 20px;
                background-color: transparent;
                color: #808080;
                font-size: 16px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: #333333;
            }
            QPushButton:pressed {
                background-color: #1A1A1A;
            }
        """)

    def apply_green_button_style(self, button):
        """Apply consistent green button style for active states"""
        button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 20px;
                background-color: #1DB954;
                color: #000000;
                font-size: 16px;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
            QPushButton:pressed {
                background-color: #169C46;
            }
        """)

    def update_button_states(self, has_song=True):
        """Update button states based on whether a song is loaded"""
        if has_song:
            # Enable previous/next buttons
            self.apply_grey_button_style(self.previous_btn)
            self.apply_grey_button_style(self.next_btn)
            self.previous_btn.setEnabled(True)
            self.next_btn.setEnabled(True)
            
            # Enable play button
            self.play_pause_btn.setEnabled(True)
            
        else:
            # Disable previous/next buttons
            disabled_style = """
                QPushButton {
                    border: none;
                    border-radius: 20px;
                    background-color: transparent;
                    color: #404040;
                    font-size: 16px;
                    min-width: 32px;
                    max-width: 32px;
                    min-height: 32px;
                    max-height: 32px;
                }
            """
            self.previous_btn.setStyleSheet(disabled_style)
            self.next_btn.setStyleSheet(disabled_style)
            self.previous_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            
            # Disable play button
            self.play_pause_btn.setEnabled(False)

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
        
        # Player control connections
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.next_song)
        self.previous_btn.clicked.connect(self.previous_song)
        self.shuffle_btn.clicked.connect(self.toggle_shuffle)
        self.repeat_btn.clicked.connect(self.toggle_repeat)
        
        # Volume connections
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        self.mute_btn.clicked.connect(self.toggle_mute)
        
        # Progress connections
        self.position_slider.sliderMoved.connect(self.on_position_slider_moved)
        self.position_slider.sliderPressed.connect(self.on_position_slider_pressed)
        self.position_slider.sliderReleased.connect(self.on_position_slider_released)
        
        # Audio player connections (only connect once here)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.on_player_state_changed)
        self.player.songEnded.connect(self.on_song_end)
    
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
        """Start YouTube download in background thread"""
        # Create progress dialog
        progress_dialog = QProgressDialog("Preparing download...", "Cancel", 0, 100, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("YouTube Download")
        progress_dialog.setAutoClose(False)  # Don't auto-close on completion
        progress_dialog.show()
        
        # Start download thread
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
        """Update download progress"""
        progress_dialog.setLabelText(status)
        progress_dialog.setValue(int(percent))
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
        self.playlist_list.clear()
        playlists = self.db.get_playlists()
        
        for playlist in playlists:
            # Debug: Check how many values we're getting
            print(f"Playlist data length: {len(playlist)}, data: {playlist}")
            
            # Handle different playlist data formats safely
            if len(playlist) >= 4:
                playlist_id, name, description, created_date = playlist[:4]
            elif len(playlist) >= 2:
                playlist_id, name = playlist[:2]
                description = ""
            else:
                print(f"❌ Invalid playlist data: {playlist}")
                continue
            
            item = QListWidgetItem(f"📝 {name}")
            item.setData(Qt.UserRole, playlist_id)
            item.setToolTip(description if description else f"Playlist: {name}")
            self.playlist_list.addItem(item)
    
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
                # Update shuffle index if in shuffle mode
                if self.shuffle_mode and self.shuffled_playlist:
                    try:
                        self.shuffle_index = self.shuffled_playlist.index(row)
                        print(f"🔀 Updated shuffle index to {self.shuffle_index} for row {row}")
                    except ValueError:
                        # Row not in shuffle list, recreate shuffle
                        self.create_shuffled_playlist()
                
                self.play_song(song_data)

    def play_song(self, song_data):
        """Play a song"""
        file_path = song_data[7] if len(song_data) > 7 else None
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The file was not found.")
            return
        
        self.current_song_data = song_data
        
        # Update UI
        title = str(song_data[1]) if len(song_data) > 1 else "Unknown"
        artist = str(song_data[2]) if len(song_data) > 2 else "Unknown Artist"
        album = str(song_data[3]) if len(song_data) > 3 else "Unknown Album"
        
        # Update text labels - ScrollingLabel will handle long text automatically
        print(f"🎵 Setting title: {title}")
        self.current_song_label.setText(title)
        self.current_artist_label.setText(artist)
        self.current_album_label.setText(album)
        
        # Add tooltips for hover info
        self.current_song_label.setToolTip(title)
        self.current_artist_label.setToolTip(artist)
        self.current_album_label.setToolTip(album)
        
        # Update album art
        self.album_art_label.set_album_art_from_song_data(song_data)
        
        # Enable buttons now that we have a song
        self.update_button_states(has_song=True)
        
        # Load and play
        self.player.load_song(file_path)
        self.player.play()
        
        # Update play button to show pause and make it green
        self.play_pause_btn.setText("⏸")
        self.apply_green_button_style(self.play_pause_btn)
        
        self.statusBar().showMessage(f"Playing: {title} - {artist}")
    
    def clear_current_song_display(self):
        """Clear current song display when stopping"""
        self.current_song_label.setText("No song playing")
        self.current_artist_label.setText("")
        self.current_album_label.setText("")
        self.album_art_label.clear_art()
        self.current_song_data = None

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

    def update_song_info_display(self, song_data):
        """Update the song info display with text wrapping"""
        try:
            if song_data and len(song_data) > 1:
                title = song_data[1] if song_data[1] else "Unknown Title"
                artist = song_data[2] if len(song_data) > 2 and song_data[2] else "Unknown Artist"
                
                # Update labels with truncation for very long texts
                if len(title) > 60:  # Truncate very long titles
                    title = title[:57] + "..."
                
                if len(artist) > 40:  # Truncate very long artist names
                    artist = artist[:37] + "..."
                
                self.current_song_label.setText(title)
                self.current_artist_label.setText(artist)
            else:
                self.current_song_label.setText("No song playing")
                self.current_artist_label.setText("")
                
        except Exception as e:
            print(f"❌ Error updating song info: {e}")
            self.current_song_label.setText("No song playing")
            self.current_artist_label.setText("")

    def on_position_slider_moved(self, position):
        """Handle position slider movement"""
        if self.slider_pressed:
            self.player.set_position(position)

    def on_position_slider_pressed(self):
        """Handle position slider press"""
        self.slider_pressed = True

    def on_position_slider_released(self):
        """Handle position slider release"""
        self.slider_pressed = False

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
    
    
    def next_song(self):
        """Play the next song in the current playlist or library"""
        try:
            total_rows = self.music_table.rowCount()
            
            if total_rows == 0:
                return
            
            next_row = 0
            
            if self.shuffle_mode and self.shuffled_playlist:
                # Use shuffled playlist
                self.shuffle_index += 1
                
                # If we've reached the end of shuffle list
                if self.shuffle_index >= len(self.shuffled_playlist):
                    if self.repeat_mode == "all":
                        # Reshuffle and continue
                        self.create_shuffled_playlist()
                        print("🔀 Reshuffling playlist for repeat all")
                    else:
                        # End of shuffle, stop
                        print("🔀 End of shuffled playlist")
                        return
                
                next_row = self.shuffled_playlist[self.shuffle_index]
                print(f"🔀 Shuffle next: row {next_row} (shuffle index: {self.shuffle_index})")
                
            else:
                # Normal sequential mode
                current_row = self.music_table.currentRow()
                
                # Calculate next row
                if current_row < total_rows - 1:
                    next_row = current_row + 1
                else:
                    # If at the end, loop back to the beginning for "repeat all"
                    if self.repeat_mode == "all":
                        next_row = 0
                    else:
                        print("📜 End of playlist")
                        return
            
            # Select and play the next song
            self.music_table.selectRow(next_row)
            self.on_song_double_click(next_row, 0)
            
        except Exception as e:
            print(f"❌ Error playing next song: {e}")
    
    def previous_song(self):
        """Play the previous song in the current playlist or library"""
        try:
            total_rows = self.music_table.rowCount()
            
            if total_rows == 0:
                return
            
            prev_row = 0
            
            if self.shuffle_mode and self.shuffled_playlist:
                # Use shuffled playlist
                self.shuffle_index -= 1
                
                # If we've gone before the beginning, wrap to end
                if self.shuffle_index < 0:
                    self.shuffle_index = len(self.shuffled_playlist) - 1
                
                prev_row = self.shuffled_playlist[self.shuffle_index]
                print(f"🔀 Shuffle previous: row {prev_row} (shuffle index: {self.shuffle_index})")
                
            else:
                # Normal sequential mode
                current_row = self.music_table.currentRow()
                
                # Calculate previous row
                if current_row > 0:
                    prev_row = current_row - 1
                else:
                    # If at the beginning, wrap to end
                    prev_row = total_rows - 1
            
            # Select and play the previous song
            self.music_table.selectRow(prev_row)
            self.on_song_double_click(prev_row, 0)
            
        except Exception as e:
            print(f"❌ Error playing previous song: {e}")

    def create_shuffled_playlist(self):
        """Create shuffled order for current playlist"""
        import random
        
        # Get all rows from current table view
        total_rows = self.music_table.rowCount()
        if total_rows == 0:
            self.shuffled_playlist = []
            return
        
        # Create list of row indices
        self.shuffled_playlist = list(range(total_rows))
        
        # Shuffle the list
        random.shuffle(self.shuffled_playlist)
        
        # Find current playing song and move it to the front
        current_row = self.music_table.currentRow()
        if current_row >= 0 and current_row in self.shuffled_playlist:
            # Move current song to front of shuffle
            current_pos = self.shuffled_playlist.index(current_row)
            self.shuffled_playlist[0], self.shuffled_playlist[current_pos] = \
                self.shuffled_playlist[current_pos], self.shuffled_playlist[0]
            self.shuffle_index = 0
        else:
            self.shuffle_index = 0
        
        print(f"🔀 Created shuffled playlist with {len(self.shuffled_playlist)} songs")

    def toggle_mute(self):
        """Toggle mute on/off"""
        if self.volume_slider.value() == 0:
            # Currently muted, restore previous volume
            if hasattr(self, 'previous_volume'):
                self.volume_slider.setValue(self.previous_volume)
            else:
                self.volume_slider.setValue(70)  # Default volume
        else:
            # Currently not muted, save current volume and mute
            self.previous_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)

    def toggle_shuffle(self):
        """Toggle shuffle mode on/off"""
        self.shuffle_mode = not self.shuffle_mode
        
        if self.shuffle_mode:
            # Create shuffled playlist from current table
            self.create_shuffled_playlist()
            self.apply_green_button_style(self.shuffle_btn)
            print("🔀 Shuffle: ON")
        else:
            self.shuffled_playlist = []  # Clear shuffle list
            self.shuffle_index = 0
            self.apply_grey_button_style(self.shuffle_btn)
            print("🔀 Shuffle: OFF")

    def toggle_repeat(self):
        """Toggle between repeat modes: off -> one -> all -> off"""
        if self.repeat_mode == "off":
            self.repeat_mode = "one"
            self.repeat_btn.setText("🔂")
            self.apply_green_button_style(self.repeat_btn)
            print("🔂 Repeat: One")
            
        elif self.repeat_mode == "one":
            self.repeat_mode = "all"
            self.repeat_btn.setText("🔁")
            self.apply_green_button_style(self.repeat_btn)
            print("🔁 Repeat: All")
            
        else:  # "all" -> "off"
            self.repeat_mode = "off"
            self.repeat_btn.setText("↪️")
            self.apply_grey_button_style(self.repeat_btn)
            print("↪️ Repeat: Off")
    # Player control methods
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.current_song_data:
            if self.player.is_playing():
                self.player.pause()
                self.play_pause_btn.setText("▶")
                self.apply_grey_button_style(self.play_pause_btn)
            else:
                self.player.play()
                self.play_pause_btn.setText("⏸")
                self.apply_green_button_style(self.play_pause_btn)
        else:
            # If no song is loaded, play first song in current view
            if self.music_table.rowCount() > 0:
                self.on_song_double_click(0, 0)
    
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
    
    def on_song_end(self):
        """Handle when song ends"""
        try:
            if self.repeat_mode == "one":
                # For repeat one, we need to reload the current song
                print("🔁 Repeating current song")
                if self.current_song_data:
                    # Get the file path from current song data
                    file_path = self.current_song_data[7] if len(self.current_song_data) > 7 else None
                    if file_path and os.path.exists(file_path):
                        # Reload and play the same song
                        self.player.load_song(file_path)
                        self.player.play()
                        print(f"🔄 Reloaded and playing: {os.path.basename(file_path)}")
                    else:
                        print("❌ Current song file not found for repeat")
                else:
                    print("❌ No current song data for repeat")
                    
            elif self.repeat_mode == "all":
                # Play next song in playlist/library
                print("🔁 Repeat all - playing next song")
                self.next_song()
                
            else:  # repeat_mode == "off"
                # Stop playback and reset UI
                print("⏹️ Song ended - stopping")
                self.play_pause_btn.setText("▶")
                
        except Exception as e:
            print(f"❌ Error handling song end: {e}")
    
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
            self.position_slider.setValue(position)  # Changed from progress_slider
            self.current_time_label.setText(self.format_duration(position // 1000))

    def update_duration(self, duration):
        """Update track duration"""
        self.position_slider.setRange(0, duration)  # Changed from progress_slider
        self.total_time_label.setText(self.format_duration(duration // 1000))
    
    def on_player_state_changed(self, state):
        """Handle player state changes"""
        if state == 6:  # VLC Ended state
            self.on_song_end()
    
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