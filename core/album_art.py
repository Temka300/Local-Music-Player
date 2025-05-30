"""
Album art extraction and management utilities
"""

import os
import base64
from io import BytesIO
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QPen
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QLabel

try:
    from mutagen import File
    from mutagen.id3 import ID3, APIC
    from mutagen.mp4 import MP4Cover
    from mutagen.flac import Picture
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


class AlbumArtExtractor:
    """Extract and manage album art from audio files and database"""
    
    @staticmethod
    def extract_album_art_from_file(file_path):
        """Extract album art from audio file"""
        if not MUTAGEN_AVAILABLE:
            return None
            
        try:
            audio_file = File(file_path)
            if audio_file is None:
                return None
            
            album_art_data = None
            
            # MP3 files (ID3 tags)
            if hasattr(audio_file, 'tags') and audio_file.tags:
                if 'APIC:' in audio_file.tags:
                    album_art_data = audio_file.tags['APIC:'].data
                elif 'APIC::' in audio_file.tags:
                    album_art_data = audio_file.tags['APIC::'].data
                else:
                    # Check for any APIC frame
                    for key in audio_file.tags:
                        if key.startswith('APIC'):
                            album_art_data = audio_file.tags[key].data
                            break
            
            # MP4/M4A files
            elif hasattr(audio_file, 'tags') and 'covr' in audio_file.tags:
                covers = audio_file.tags['covr']
                if covers:
                    album_art_data = bytes(covers[0])
            
            # FLAC files
            elif hasattr(audio_file, 'pictures') and audio_file.pictures:
                album_art_data = audio_file.pictures[0].data
            
            return album_art_data
            
        except Exception as e:
            print(f"❌ Error extracting album art from {file_path}: {e}")
            return None
    
    @staticmethod
    def get_album_art_from_database(song_data):
        """Get album art from song database record"""
        try:
            # song_data is a tuple: (id, title, artist, album, year, genre, duration, file_path, album_art, ...)
            if len(song_data) > 8 and song_data[8]:
                return song_data[8]  # album_art is at index 8
            return None
        except Exception as e:
            print(f"❌ Error getting album art from database: {e}")
            return None
    
    @staticmethod
    def create_pixmap_from_data(album_art_data, size=(80, 80)):
        """Create QPixmap from album art data"""
        if not album_art_data:
            return None
            
        try:
            pixmap = QPixmap()
            if pixmap.loadFromData(album_art_data):
                # Scale to desired size while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    size[0], size[1], 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                return scaled_pixmap
            return None
            
        except Exception as e:
            print(f"❌ Error creating pixmap from album art: {e}")
            return None
    
    @staticmethod
    def create_default_album_art(size=(80, 80)):
        """Create default album art when none is available"""
        try:
            pixmap = QPixmap(size[0], size[1])
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw rounded rectangle background
            painter.setBrush(QBrush(Qt.gray))
            painter.setPen(QPen(Qt.darkGray, 1))
            painter.drawRoundedRect(QRect(0, 0, size[0], size[1]), 8, 8)
            
            # Draw music note symbol
            painter.setPen(QPen(Qt.white, 2))
            font = painter.font()
            font.setPixelSize(int(size[0] * 0.4))
            font.setBold(True)
            painter.setFont(font)
            
            painter.drawText(QRect(0, 0, size[0], size[1]), Qt.AlignCenter, "♪")
            
            painter.end()
            return pixmap
            
        except Exception as e:
            print(f"❌ Error creating default album art: {e}")
            return None


class AlbumArtLabel(QLabel):
    """Custom QLabel for displaying album art with rounded corners"""
    
    def __init__(self, size=(80, 80), parent=None):
        super().__init__(parent)
        self.art_size = size
        self.setFixedSize(size[0], size[1])
        self.setAlignment(Qt.AlignCenter)
        self.current_pixmap = None
        self.setStyleSheet("""
            QLabel {
                background-color: #404040;
                border-radius: 8px;
            }
        """)
        
        # Set default album art
        self.set_default_art()
    
    def set_album_art_from_song_data(self, song_data):
        """Set album art from song database record"""
        # First try to get from database (this includes YouTube thumbnails)
        album_art_data = AlbumArtExtractor.get_album_art_from_database(song_data)
        
        if album_art_data:
            pixmap = AlbumArtExtractor.create_pixmap_from_data(album_art_data, self.art_size)
            if pixmap:
                self.current_pixmap = pixmap
                self.setPixmap(pixmap)
                return True
        
        # Fallback: try to extract from file
        if len(song_data) > 7:
            file_path = song_data[7]
            if file_path and os.path.exists(file_path):
                album_art_data = AlbumArtExtractor.extract_album_art_from_file(file_path)
                if album_art_data:
                    pixmap = AlbumArtExtractor.create_pixmap_from_data(album_art_data, self.art_size)
                    if pixmap:
                        self.current_pixmap = pixmap
                        self.setPixmap(pixmap)
                        return True
        
        # No art found, use default
        self.set_default_art()
        return False
    
    def set_default_art(self):
        """Set default album art"""
        default_pixmap = AlbumArtExtractor.create_default_album_art(self.art_size)
        if default_pixmap:
            self.current_pixmap = default_pixmap
            self.setPixmap(default_pixmap)
        else:
            # Fallback text
            self.setText("♪")
            self.setStyleSheet(self.styleSheet() + """
                QLabel {
                    color: #1DB954;
                    font-size: 32px;
                    font-weight: bold;
                }
            """)
    
    def clear_art(self):
        """Clear current album art and show default"""
        self.set_default_art()