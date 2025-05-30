"""
Metadata Extraction Module - Extract metadata from audio files
"""

import os
from mutagen import File
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4


def extract_metadata(file_path):
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
