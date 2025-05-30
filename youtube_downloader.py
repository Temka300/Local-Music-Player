#!/usr/bin/env python3
"""
YouTube Downloader for Local Music Player
Downloads audio from YouTube and extracts metadata
"""

import os
import sys
import subprocess
import json
import requests
from PyQt5.QtCore import QObject, QThread, pyqtSignal
import tempfile
import re

# Configuration option - set to False to disable verbose output
VERBOSE_DOWNLOAD = True  # Change this to False to disable verbose output


class YouTubeDownloader(QObject):
    """Handles YouTube audio downloads with metadata"""
    
    progress = pyqtSignal(str, int)  # status, percentage
    finished = pyqtSignal(str, dict)  # file_path, metadata
    error = pyqtSignal(str)
    
    def __init__(self, musics_folder):
        super().__init__()
        self.musics_folder = musics_folder
        self.youtube_folder = os.path.join(musics_folder, "YouTube Downloads")
        os.makedirs(self.youtube_folder, exist_ok=True)

    def download_audio(self, url):
        """Download audio from YouTube URL"""
        try:
            self.progress.emit("Verifying video...", 3)
            
            # Clean the URL to get just the video ID for single video downloads
            clean_url = self._clean_youtube_url(url)
            
            # Verify video exists and get basic info
            video_info = self._verify_video_info(clean_url)
            
            self.progress.emit("Extracting video information...", 5)
            
            # Use a custom output template with filename sanitization
            output_template = os.path.join(self.youtube_folder, '%(uploader)s', '%(title)s.%(ext)s')
            
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                '--format', 'bestaudio/best',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '192',
                '--output', output_template,
                '--write-thumbnail',
                '--write-info-json',
                '--no-playlist',
                '--embed-metadata',
                '--ignore-errors',
                '--restrict-filenames'  # This forces ASCII-only filenames
            ]
            
            # Add quiet mode if verbose is disabled
            if not VERBOSE_DOWNLOAD:
                cmd.append('--quiet')
            
            cmd.append(clean_url)
            
            if VERBOSE_DOWNLOAD:
                print(f"🎵 Downloading from URL: {clean_url}")
                print(f"📁 Output folder: {self.youtube_folder}")
            
            self.progress.emit("Starting download...", 10)
            
            # Run yt-dlp with real-time output processing
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True, 
                universal_newlines=True,
                cwd=self.musics_folder
            )
            
            # Monitor output for progress
            self._monitor_download_progress(process)
            
            # Wait for completion
            return_code = process.wait()
            
            if return_code != 0:
                raise Exception(f"yt-dlp failed with code {return_code}")
            
            self.progress.emit("Processing downloaded files...", 90)
            
            # Find the downloaded files
            info_file, mp3_file, thumbnail_file = self._find_downloaded_files(clean_url)
            
            # If we still didn't find the MP3, use the absolute newest MP3 method
            if not mp3_file or not os.path.exists(mp3_file):
                if VERBOSE_DOWNLOAD:
                    print("🔍 Using fallback method to find newest MP3...")
                mp3_file = self._find_newest_mp3()
                if not mp3_file:
                    raise Exception("Downloaded MP3 file not found")
            
            # Extract metadata
            metadata = self._extract_metadata_from_files(info_file, mp3_file, thumbnail_file, clean_url)
            
            self.progress.emit("Download complete!", 100)
            self.finished.emit(mp3_file, metadata)
            
        except Exception as e:
            print(f"YouTube download error: {e}")
            self.error.emit(str(e))
    
    def _clean_youtube_url(self, url):
        """Clean YouTube URL to get just the video without playlist info"""
        try:
            if 'youtube.com/watch' in url and 'v=' in url:
                # Extract just the video ID
                video_id = url.split('v=')[1].split('&')[0]
                clean_url = f"https://www.youtube.com/watch?v={video_id}"
                if VERBOSE_DOWNLOAD:
                    print(f"🧹 Cleaned URL: {url} -> {clean_url}")
                return clean_url
            elif 'youtu.be/' in url:
                # Already a clean short URL, but remove any parameters
                video_id = url.split('youtu.be/')[1].split('?')[0]
                clean_url = f"https://www.youtube.com/watch?v={video_id}"
                if VERBOSE_DOWNLOAD:
                    print(f"🧹 Cleaned URL: {url} -> {clean_url}")
                return clean_url
            else:
                # Return as-is if we can't parse it
                return url
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Error cleaning URL: {e}")
            return url
    
    def _monitor_download_progress(self, process):
        """Monitor download progress from yt-dlp output"""
        try:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if VERBOSE_DOWNLOAD:
                        print(line)  # Print to console if verbose is enabled
                    
                    # Parse progress from yt-dlp output
                    if '[download]' in line:
                        # Look for percentage in download lines
                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', line)
                        if percent_match:
                            percent = float(percent_match.group(1))
                            # Scale to our progress range (10-85)
                            scaled_percent = int(10 + (percent * 0.75))
                            
                            if 'Destination:' in line:
                                filename = line.split('Destination: ')[-1].split('\\')[-1]
                                self.progress.emit(f"Downloading: {filename}", scaled_percent)
                            else:
                                self.progress.emit(f"Downloading... {percent:.1f}%", scaled_percent)
                    
                    elif '[ExtractAudio]' in line:
                        self.progress.emit("Converting to MP3...", 85)
                    
                    elif 'Deleting original file' in line:
                        self.progress.emit("Cleaning up temporary files...", 88)
                    
                    elif '[info]' in line and 'Downloading' in line:
                        if 'video thumbnail' in line:
                            self.progress.emit("Downloading thumbnail...", 15)
                        elif 'format(s):' in line:
                            self.progress.emit("Starting audio download...", 20)
                    
                    elif line.startswith('[youtube]') and 'Downloading' in line:
                        if 'webpage' in line:
                            self.progress.emit("Extracting video information...", 8)
                        elif 'player' in line:
                            self.progress.emit("Getting audio streams...", 12)
        
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Error monitoring progress: {e}")
    
    def _find_newest_mp3(self):
        """Find the newest MP3 file in the YouTube folder"""
        try:
            newest_file = None
            newest_time = 0
            
            # Get current time for reference
            import time
            current_time = time.time()
            
            if VERBOSE_DOWNLOAD:
                print("🔍 Searching for newest MP3 file...")
            
            for root, dirs, files in os.walk(self.youtube_folder):
                for file in files:
                    if file.endswith('.mp3'):
                        file_path = os.path.join(root, file)
                        try:
                            file_time = os.path.getmtime(file_path)
                            
                            # Only consider files modified in the last 10 minutes
                            if (current_time - file_time) > 600:
                                continue
                            
                            if file_time > newest_time:
                                newest_time = file_time
                                newest_file = file_path
                                if VERBOSE_DOWNLOAD:
                                    print(f"🎵 Found newer MP3: {file} (modified {int(current_time - file_time)} seconds ago)")
                        except OSError:
                            # File might be in use or have permission issues
                            continue
            
            if newest_file and VERBOSE_DOWNLOAD:
                print(f"✅ Selected newest MP3: {os.path.basename(newest_file)}")
            elif VERBOSE_DOWNLOAD:
                print("❌ No recent MP3 files found")
            
            return newest_file
            
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Error finding newest MP3: {e}")
            return None
    # Add this method to the YouTubeDownloader class

    def _sanitize_filename(self, filename):
        """Sanitize filename by removing problematic characters"""
        # Characters that yt-dlp replaces and we want to remove entirely
        problematic_chars = [
            '⧸',  # Fraction slash (replaces /)
            '∶',  # Ratio (replaces :)
            '⦂',  # Two dot punctuation (replaces :)
            '❘',  # Light vertical bar (replaces |)
            '⧵',  # Reverse solidus (replaces \)
            '？', # Full-width question mark (replaces ?)
            '＊', # Full-width asterisk (replaces *)
            '‹',  # Single left angle quotation (replaces <)
            '›',  # Single right angle quotation (replaces >)
            '″',  # Double prime (replaces ")
            '/',  # Forward slash
            '\\', # Backslash
            ':',  # Colon
            '*',  # Asterisk
            '?',  # Question mark
            '"',  # Quote
            '<',  # Less than
            '>',  # Greater than
            '|'   # Pipe
        ]
        
        # Remove all problematic characters
        sanitized = filename
        for char in problematic_chars:
            sanitized = sanitized.replace(char, '')
        
        # Replace multiple spaces with single space and trim
        sanitized = ' '.join(sanitized.split())
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip('. ')
        
        return sanitized if sanitized else "Unknown"

    def _find_downloaded_files(self, url):
        """Find the downloaded MP3, info, and thumbnail files"""
        try:
            # Extract video ID from URL
            if 'v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]
            else:
                video_id = url.split('/')[-1]
            
            if VERBOSE_DOWNLOAD:
                print(f"🔍 Looking for files with video ID: {video_id}")
            
            # Get current time for reference
            import time
            current_time = time.time()
            
            # Find the newest info file that matches our video ID
            newest_info_file = None
            newest_time = 0
            
            for root, dirs, files in os.walk(self.youtube_folder):
                for file in files:
                    if file.endswith('.info.json'):
                        file_path = os.path.join(root, file)
                        file_time = os.path.getmtime(file_path)
                        
                        # Only consider files modified in the last 10 minutes
                        if (current_time - file_time) > 600:
                            continue
                        
                        # Check if this info file matches our video ID
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                info = json.load(f)
                                if info.get('id') == video_id and file_time > newest_time:
                                    newest_info_file = file_path
                                    newest_time = file_time
                                    if VERBOSE_DOWNLOAD:
                                        print(f"✅ Found matching info file: {file}")
                        except Exception as e:
                            if VERBOSE_DOWNLOAD:
                                print(f"Error reading info file {file}: {e}")
            
            # Now find the corresponding MP3 and thumbnail files
            newest_mp3_file = None
            newest_thumbnail_file = None
            
            if newest_info_file:
                # Get the base name from the info file (remove .info.json)
                info_base_name = os.path.splitext(newest_info_file)[0]  # Remove .json
                info_base_name = os.path.splitext(info_base_name)[0]  # Remove .info
                
                # Look for MP3 and thumbnail files with the same base name
                folder_path = os.path.dirname(newest_info_file)
                
                if VERBOSE_DOWNLOAD:
                    print(f"🔍 Looking for files matching base: {os.path.basename(info_base_name)}")
                
                # Search for files in the same directory
                for file in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file)
                    file_base = os.path.splitext(file_path)[0]
                    
                    # Direct match first
                    if file_base == info_base_name:
                        if file.endswith('.mp3'):
                            newest_mp3_file = file_path
                            if VERBOSE_DOWNLOAD:
                                print(f"✅ Found matching MP3 file: {file}")
                        elif file.endswith(('.webp', '.jpg', '.png')):
                            newest_thumbnail_file = file_path
                            if VERBOSE_DOWNLOAD:
                                print(f"✅ Found matching thumbnail: {file}")
            
            # If we still didn't find the MP3, search for the newest MP3 file in the entire folder
            if newest_mp3_file is None:
                if VERBOSE_DOWNLOAD:
                    print("🔍 MP3 not found via info file, searching for newest MP3...")
                
                newest_mp3_time = 0
                for root, dirs, files in os.walk(self.youtube_folder):
                    for file in files:
                        if file.endswith('.mp3'):
                            file_path = os.path.join(root, file)
                            file_time = os.path.getmtime(file_path)
                            
                            # Only consider files modified in the last 5 minutes
                            if (current_time - file_time) > 300:
                                continue
                            
                            if file_time > newest_mp3_time:
                                newest_mp3_file = file_path
                                newest_mp3_time = file_time
                                if VERBOSE_DOWNLOAD:
                                    print(f"✅ Found recent MP3 file: {file}")
            
            if VERBOSE_DOWNLOAD:
                print(f"📄 Info file: {newest_info_file}")
                print(f"🎵 MP3 file: {newest_mp3_file}")
                print(f"🖼️ Thumbnail: {newest_thumbnail_file}")
            
            return newest_info_file, newest_mp3_file, newest_thumbnail_file
            
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Error finding downloaded files: {e}")
            return None, None, None


    def _extract_metadata_from_files(self, info_file, mp3_file, thumbnail_file, url):
        """Extract metadata from downloaded files"""
        try:
            # Default metadata
            metadata = {
                'title': 'Unknown Title',
                'artist': 'Unknown Channel',
                'album': 'YouTube Downloads',
                'year': '',
                'genre': 'YouTube Download',
                'duration': 0,
                'album_art': None,
                'youtube_url': url,
                'youtube_id': '',
                'source': 'youtube'
            }
            
            # Extract from info.json if available
            if info_file and os.path.exists(info_file):
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    
                    title = info.get('title', 'Unknown Title')
                    artist = info.get('uploader', 'Unknown Channel')
                    
                    if VERBOSE_DOWNLOAD:
                        print(f"📋 Extracted metadata from info.json:")
                        print(f"   Title: {title}")
                        print(f"   Artist: {artist}")
                        print(f"   Video ID: {info.get('id', 'Unknown')}")
                    
                    metadata.update({
                        'title': title,
                        'artist': artist,
                        'album': f"YouTube - {artist}",
                        'year': str(info.get('upload_date', '')[:4]) if info.get('upload_date') else '',
                        'duration': info.get('duration', 0),
                        'youtube_url': info.get('webpage_url', url),
                        'youtube_id': info.get('id', ''),
                    })
                except Exception as e:
                    if VERBOSE_DOWNLOAD:
                        print(f"Error reading info.json: {e}")
            else:
                if VERBOSE_DOWNLOAD:
                    print("⚠️ No info.json file found, using filename for metadata")
                # Try to extract basic info from filename
                if mp3_file:
                    filename = os.path.basename(mp3_file)
                    # Remove .mp3 extension
                    filename = filename.replace('.mp3', '')
                    metadata['title'] = filename
                    
                    # Try to get channel name from folder
                    folder_name = os.path.basename(os.path.dirname(mp3_file))
                    if folder_name != "YouTube Downloads":
                        metadata['artist'] = folder_name
                        metadata['album'] = f"YouTube - {folder_name}"
            
            # Extract thumbnail as album art
            if thumbnail_file and os.path.exists(thumbnail_file):
                try:
                    with open(thumbnail_file, 'rb') as f:
                        metadata['album_art'] = f.read()
                    if VERBOSE_DOWNLOAD:
                        print("🖼️ Extracted album art from thumbnail")
                except Exception as e:
                    if VERBOSE_DOWNLOAD:
                        print(f"Error reading thumbnail: {e}")
            
            # Get duration from MP3 if not available
            if metadata['duration'] == 0 and mp3_file:
                try:
                    from mutagen.mp3 import MP3
                    audio = MP3(mp3_file)
                    metadata['duration'] = audio.info.length
                    if VERBOSE_DOWNLOAD:
                        print(f"⏱️ Extracted duration from MP3: {metadata['duration']} seconds")
                except:
                    pass
            
            if VERBOSE_DOWNLOAD:
                print(f"🎯 Final metadata: {metadata['title']} by {metadata['artist']}")
            
            return metadata
            
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Error extracting metadata: {e}")
            return metadata
        
    def _verify_video_info(self, url):
        """Verify video information before downloading"""
        try:
            cmd = [
                sys.executable, '-m', 'yt_dlp',
                '--dump-json',
                '--no-playlist',
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                if VERBOSE_DOWNLOAD:
                    print(f"📺 Video Title: {info.get('title', 'Unknown')}")
                    print(f"👤 Channel: {info.get('uploader', 'Unknown')}")
                    print(f"⏱️ Duration: {info.get('duration', 0)} seconds")
                return info
            else:
                raise Exception(f"Failed to get video info: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Timeout while getting video information")
        except json.JSONDecodeError:
            raise Exception("Invalid response from YouTube")
        except Exception as e:
            raise Exception(f"Error verifying video: {str(e)}")


class YouTubeDownloadThread(QThread):
    """Thread wrapper for YouTube downloads"""
    
    progress = pyqtSignal(str, int)  # Forward progress signals
    finished = pyqtSignal(str, dict)  # Forward finished signals
    error = pyqtSignal(str)  # Forward error signals
    
    def __init__(self, url, musics_folder):
        super().__init__()
        self.url = url
        self.musics_folder = musics_folder
        self.downloader = None
    
    def run(self):
        """Run the download in a separate thread"""
        try:
            self.downloader = YouTubeDownloader(self.musics_folder)
            
            # Connect downloader signals to thread signals
            self.downloader.progress.connect(self.progress.emit)
            self.downloader.finished.connect(self.finished.emit)
            self.downloader.error.connect(self.error.emit)
            
            # Start the download
            self.downloader.download_audio(self.url)
            
        except Exception as e:
            if VERBOSE_DOWNLOAD:
                print(f"Download thread error: {e}")
            self.error.emit(str(e))
    
    def get_downloader(self):
        """Get the downloader instance for signal connections"""
        return self.downloader
