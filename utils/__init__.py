"""
Utility functions for Local Music Player
"""

try:
    from .themes import apply_dark_theme
    from .constants import YOUTUBE_AVAILABLE, YouTubeDownloadThread
    
    __all__ = ['apply_dark_theme', 'YOUTUBE_AVAILABLE', 'YouTubeDownloadThread']
except ImportError:
    # Fallback if modules don't exist yet
    __all__ = []