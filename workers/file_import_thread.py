"""
Background worker threads for file operations
"""

import os
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal


class FileImportThread(QThread):
    """Thread for importing files without blocking the UI"""
    
    progress = pyqtSignal(str)  # filename being processed
    finished = pyqtSignal(int)   # number of files imported
    
    def __init__(self, file_paths, organizer, db, extract_metadata_func):
        super().__init__()
        self.file_paths = file_paths
        self.organizer = organizer
        self.db = db
        self.extract_metadata = extract_metadata_func
    
    def run(self):
        """Import files in background"""
        imported_count = 0
        supported_formats = ('.mp3', '.m4a', '.flac', '.wav', '.ogg', '.aac')
        
        for file_path in self.file_paths:
            try:
                self.progress.emit(file_path)
                
                # Check if file has supported extension
                if not file_path.lower().endswith(supported_formats):
                    continue
                
                # Check if file already exists in database
                existing_songs = self.db.get_all_songs()
                file_exists = any(song['file_path'] == file_path for song in existing_songs)
                
                if file_exists:
                    continue
                
                # Extract metadata
                song_data = self.extract_metadata(file_path)
                if song_data:
                    # Organize file if organizer is configured
                    if self.organizer.auto_organize:
                        try:
                            new_path = self.organizer.organize_file(song_data, file_path)
                            if new_path and new_path != file_path:
                                song_data['file_path'] = new_path
                        except Exception as e:
                            print(f"⚠️ Failed to organize file {file_path}: {e}")
                    
                    # Add to database
                    self.db.add_song(song_data)
                    imported_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                continue
        
        self.finished.emit(imported_count)


class FolderScanThread(QThread):
    """Thread for scanning folders without blocking the UI"""
    
    progress = pyqtSignal(str)  # filename being processed
    finished = pyqtSignal(int)   # number of files imported
    
    def __init__(self, folder_path, organizer, db, extract_metadata_func):
        super().__init__()
        self.folder_path = folder_path
        self.organizer = organizer
        self.db = db
        self.extract_metadata = extract_metadata_func
    
    def run(self):
        """Scan folder and import music files"""
        imported_count = 0
        supported_formats = ('.mp3', '.m4a', '.flac', '.wav', '.ogg', '.aac')
        
        # Get all existing files in database to avoid duplicates
        existing_songs = self.db.get_all_songs()
        existing_paths = {song['file_path'] for song in existing_songs}
        
        # Walk through folder and find music files
        for root, dirs, files in os.walk(self.folder_path):
            for file in files:
                try:
                    # Check if file has supported extension
                    if not file.lower().endswith(supported_formats):
                        continue
                    
                    file_path = os.path.join(root, file)
                    self.progress.emit(file_path)
                    
                    # Skip if already in database
                    if file_path in existing_paths:
                        continue
                    
                    # Extract metadata
                    song_data = self.extract_metadata(file_path)
                    if song_data:
                        # Organize file if organizer is configured
                        if self.organizer.auto_organize:
                            try:
                                new_path = self.organizer.organize_file(song_data, file_path)
                                if new_path and new_path != file_path:
                                    song_data['file_path'] = new_path
                                    # Update existing paths set
                                    existing_paths.add(new_path)
                            except Exception as e:
                                print(f"⚠️ Failed to organize file {file_path}: {e}")
                        
                        # Add to database
                        self.db.add_song(song_data)
                        imported_count += 1
                        
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    continue
        
        self.finished.emit(imported_count)
