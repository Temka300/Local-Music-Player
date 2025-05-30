"""
Core functionality for Local Music Player
"""

try:
    from .database import MusicDatabase
    from .audio_player import AudioPlayer
    from .organizer import MusicLibraryOrganizer
    from .metadata import extract_metadata
    
    __all__ = ['MusicDatabase', 'AudioPlayer', 'MusicLibraryOrganizer', 'extract_metadata']
except ImportError:
    # Fallback if modules don't exist yet
    __all__ = []