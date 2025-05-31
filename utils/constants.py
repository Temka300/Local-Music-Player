"""Application constants and configuration"""

import os

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = [
    '.mp3', '.m4a', '.flac', '.wav', '.ogg', '.aac'
]

# Audio format filter for file dialogs
AUDIO_FILE_FILTER = "Audio Files (*.mp3 *.m4a *.flac *.wav *.ogg *.aac);;All Files (*)"

# Default database name
DEFAULT_DATABASE_NAME = "music_library.db"

# Default musics folder name
DEFAULT_MUSICS_FOLDER = "musics"

# Player states (VLC states)
VLC_STATE_NOTHING_SPECIAL = 0
VLC_STATE_OPENING = 1
VLC_STATE_BUFFERING = 2
VLC_STATE_PLAYING = 3
VLC_STATE_PAUSED = 4
VLC_STATE_STOPPED = 5
VLC_STATE_ENDED = 6
VLC_STATE_ERROR = 7

# Repeat modes
REPEAT_OFF = "off"
REPEAT_ONE = "one"
REPEAT_ALL = "all"

# Application info
APP_NAME = "Local Spotify"
APP_VERSION = "0.21"

# Default settings
DEFAULT_SETTINGS = {
    'auto_organize': True,
    'folder_structure': '{artist}/{album}',
    'filename_pattern': '{track:02d} - {title}',
    'last_import_folder': '',
    'volume': 70,
    'shuffle_mode': False,
    'repeat_mode': REPEAT_OFF,
}

# Database schema
DB_SCHEMA = {
    'songs_table': '''
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
    ''',
    'playlists_table': '''
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''',    'playlist_songs_table': '''
        CREATE TABLE IF NOT EXISTS playlist_songs (
            playlist_id INTEGER,
            song_id INTEGER,
            position INTEGER,
            FOREIGN KEY (playlist_id) REFERENCES playlists (id),
            FOREIGN KEY (song_id) REFERENCES songs (id),
            PRIMARY KEY (playlist_id, song_id)
        )
    '''
}

# App directories
def get_app_dirs():
    """Get application directories"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return {
        'base': script_dir,
        'musics': os.path.join(script_dir, 'musics'),
        'database': os.path.join(script_dir, 'music_library.db'),
        'settings': os.path.join(script_dir, 'library_settings.json')
    }

# YouTube availability check
try:
    from core.youtube_downloader import YouTubeDownloader, YouTubeDownloadThread
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

# VLC availability check
try:
    import vlc
    VLC_AVAILABLE = True
    print("✅ python-vlc available - Enhanced audio playback")
except ImportError:
    VLC_AVAILABLE = False
    print("⚠️ python-vlc not available - Install with: pip install python-vlc")
    print("💡 Falling back to Qt multimedia (may have codec issues)")

# pydub availability check  
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
    print("✅ pydub available - M4A conversion supported")
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub not available - M4A files may have playback issues")
    print("💡 Install with: pip install pydub")
