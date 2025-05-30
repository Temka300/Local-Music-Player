"""
Music Library Organizer - Handles file organization and management
"""

import os
import json
import shutil


class MusicLibraryOrganizer:
    """Handles file organization and management for music library"""
    
    def __init__(self, base_path):
        self.base_path = base_path
        self.musics_folder = os.path.join(base_path, "musics")
        self.settings_file = os.path.join(base_path, "library_settings.json")
        self.settings = self.load_settings()
        
        # Ensure musics directory exists
        os.makedirs(self.musics_folder, exist_ok=True)
        print(f"📁 Music library folder: {self.musics_folder}")
    
    def load_settings(self):
        """Load library settings"""
        default_settings = {
            "organize_files": True,  # Always organize files in musics folder
            "copy_files": True,      # Always copy files to ensure availability
            "folder_structure": "artist/album",  # or "artist/year/album", "album", etc.
            "musics_folder": "musics"
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save library settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem compatibility"""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        # Remove extra spaces and dots
        filename = filename.strip('. ')
        return filename if filename else "Unknown"
    
    def organize_file(self, metadata, original_path):
        """Organize a music file based on metadata and copy to musics folder"""
        # Sanitize metadata
        artist = self.sanitize_filename(metadata.get('artist', 'Unknown Artist'))
        album = self.sanitize_filename(metadata.get('album', 'Unknown Album'))
        title = self.sanitize_filename(metadata.get('title', os.path.basename(original_path)))
        year = metadata.get('year', '')
        
        # Determine folder structure
        structure = self.settings.get("folder_structure", "artist/album")
        
        if structure == "artist/album":
            folder_path = os.path.join(self.musics_folder, artist, album)
        elif structure == "artist/year/album":
            year_str = str(year) if year else "Unknown Year"
            folder_path = os.path.join(self.musics_folder, artist, year_str, album)
        elif structure == "album":
            folder_path = os.path.join(self.musics_folder, album)
        else:
            folder_path = os.path.join(self.musics_folder, artist, album)
        
        # Create folder structure
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        # FIX: Always use the original file's extension, not the processed file
        # Get the extension from the ORIGINAL file path stored in metadata
        if 'original_file_path' in metadata:
            original_ext = os.path.splitext(metadata['original_file_path'])[1]
        else:
            # Fallback: use the file_path from metadata, but handle temp files
            file_path = metadata.get('file_path', original_path)
            if 'temp_audio_' in file_path:
                # This is a temporary converted file, use original_path instead
                original_ext = os.path.splitext(original_path)[1]
            else:
                original_ext = os.path.splitext(file_path)[1]
        
        # Ensure we have an extension
        if not original_ext:
            original_ext = os.path.splitext(original_path)[1]
        
        # Create the new filename with correct extension
        new_filename = f"{title}{original_ext}"
        new_path = os.path.join(folder_path, new_filename)
        
        # Handle duplicate filenames
        counter = 1
        base_path = new_path
        while os.path.exists(new_path):
            name, ext = os.path.splitext(base_path)
            new_path = f"{name} ({counter}){ext}"
            counter += 1
        
        # Always copy file to musics folder to ensure availability
        try:
            if original_path != new_path:
                shutil.copy2(original_path, new_path)
                print(f"📁 Copied to library: {os.path.basename(original_path)} → {os.path.relpath(new_path, self.base_path)}")
                return new_path
            else:
                return new_path
        except Exception as e:
            print(f"❌ Failed to copy file {original_path}: {e}")
            return original_path
