"""
Dialog windows for the GUI
"""

try:
    from .create_playlist_dialog import CreatePlaylistDialog
    from .youtube_download_dialog import YouTubeDownloadDialog
    
    __all__ = ['CreatePlaylistDialog', 'YouTubeDownloadDialog']
except ImportError:
    # Fallback if modules don't exist yet
    __all__ = []