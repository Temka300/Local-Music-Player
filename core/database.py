"""
Database management for the Local Music Player
"""

import sys
import os
import sqlite3
from pathlib import Path

# Add parent directory to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from utils.constants import DB_SCHEMA, get_app_dirs
except ImportError:
    # Fallback constants if utils module doesn't exist
    DB_SCHEMA = {
        'songs': '''
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
        'playlists': '''
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''',
        'playlist_songs': '''
            CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id INTEGER,
                song_id INTEGER,
                position INTEGER,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id),
                FOREIGN KEY (song_id) REFERENCES songs (id)
            )
        '''
    }
    
    def get_app_dirs():
        return {
            'data': os.path.dirname(os.path.abspath(__file__)),
            'music': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'musics')
        }

class MusicDatabase:
    """Database manager for music library"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Create database in the same folder as the script
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.db_path = os.path.join(script_dir, "music_library.db")
        else:
            self.db_path = db_path
        self.init_database()
        print(f"📊 Database initialized: {self.db_path}")
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Songs table with all required columns
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
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'local',
                youtube_url TEXT,
                youtube_id TEXT
            )
        ''')
        
        # Check if the new columns exist and add them if they don't
        cursor.execute("PRAGMA table_info(songs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'source' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN source TEXT DEFAULT "local"')
            print("✅ Added 'source' column to songs table")
        
        if 'youtube_url' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN youtube_url TEXT')
            print("✅ Added 'youtube_url' column to songs table")
        
        if 'youtube_id' not in columns:
            cursor.execute('ALTER TABLE songs ADD COLUMN youtube_id TEXT')
            print("✅ Added 'youtube_id' column to songs table")
        
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
            # Handle both old format (8 fields) and new format (11 fields)
            if len(song_data) == 8:
                # Old format: title, artist, album, year, genre, duration, file_path, album_art
                cursor.execute('''
                    INSERT OR REPLACE INTO songs 
                    (title, artist, album, year, genre, duration, file_path, album_art, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'local')
                ''', song_data)
                print(f"✅ Added local song: {song_data[0]} by {song_data[1]}")
            elif len(song_data) == 11:
                # New format: title, artist, album, year, genre, duration, file_path, album_art, source, youtube_url, youtube_id
                cursor.execute('''
                    INSERT OR REPLACE INTO songs 
                    (title, artist, album, year, genre, duration, file_path, album_art, source, youtube_url, youtube_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', song_data)
                print(f"✅ Added YouTube song: {song_data[0]} by {song_data[1]}")
            else:
                print(f"❌ Invalid song_data length: {len(song_data)}")
                print(f"❌ Song data: {song_data}")
                return None
            
            conn.commit()
            return cursor.lastrowid
        
        except Exception as e:
            print(f"❌ Error adding song to database: {e}")
            print(f"❌ Song data: {song_data}")
            print(f"❌ Song data length: {len(song_data)}")
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