"""
GUI components for Local Music Player
"""

try:
    from .main_window import LocalSpotifyQt
    __all__ = ['LocalSpotifyQt']
except ImportError:
    __all__ = []