"""
Dialog for downloading music from YouTube
"""

import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

try:
    from core.youtube_downloader import YouTubeDownloadThread
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    class YouTubeDownloadThread:
        pass


class YouTubeDownloadDialog(QDialog):
    """Dialog for downloading from YouTube"""
    
    def __init__(self, parent=None, download_folder=""):
        super().__init__(parent)
        self.download_folder = download_folder
        self.setWindowTitle("Download from YouTube")
        self.setFixedSize(500, 250)
        self.download_thread = None
        self.setup_ui()
        self.apply_styling()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("🎵 Download Audio from YouTube")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # URL input
        layout.addWidget(QLabel("YouTube URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste YouTube video or playlist URL here...")
        layout.addWidget(self.url_edit)
        
        # Info label
        info_label = QLabel("• Supports individual videos and playlists\n"
                           "• Audio will be downloaded as MP3 (192kbps)\n"
                           "• Channel name will be used as artist")
        info_label.setStyleSheet("color: #B3B3B3; font-size: 10px; font-weight: normal; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Warning label
        warning_label = QLabel("⚠️ Please respect copyright and only download content you have permission to use.")
        warning_label.setStyleSheet("color: #FF6B6B; font-size: 9px; font-weight: normal;")
        layout.addWidget(warning_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.download_btn = QPushButton("🎵 Download")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelButton")
        
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn.clicked.connect(self.reject)
        self.url_edit.returnPressed.connect(self.start_download)
        
        # Focus on URL input
        self.url_edit.setFocus()
    
    def apply_styling(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #191414;
                color: #FFFFFF;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1DB954;
            }
            QPushButton {
                background-color: #1DB954;
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton#cancelButton {
                background-color: #404040;
            }
            QPushButton#cancelButton:hover {
                background-color: #606060;
            }
        """)
    
    def start_download(self):
        """Start the download process"""
        if not YOUTUBE_AVAILABLE:
            QMessageBox.warning(self, "Error", "YouTube downloader is not available")
            return
        
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return
        
        if not ("youtube.com" in url or "youtu.be" in url):
            QMessageBox.warning(self, "Error", "Please enter a valid YouTube URL")
            return
        
        # Show what will be downloaded
        if 'list=' in url and 'v=' in url:
            video_id = url.split('v=')[1].split('&')[0]
            clean_url = f"https://www.youtube.com/watch?v={video_id}"
            
            reply = QMessageBox.question(self, "Playlist URL Detected", 
                                       f"You entered a playlist URL, but only the individual video will be downloaded.\n\n"
                                       f"Video ID: {video_id}\n"
                                       f"Clean URL: {clean_url}\n\n"
                                       f"Do you want to continue with downloading just this video?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        
        self.accept()
        self.start_youtube_download(url)
    
    def start_youtube_download(self, url):
        """Start YouTube download with progress dialog"""
        progress_dialog = QProgressDialog("Preparing download...", "Cancel", 0, 100, self.parent())
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("YouTube Download")
        progress_dialog.setAutoClose(False)
        progress_dialog.show()
        
        # Create download thread
        self.download_thread = YouTubeDownloadThread(url, self.download_folder)
        
        # Connect signals
        self.download_thread.progress.connect(
            lambda status, percent: self._update_download_progress(progress_dialog, status, percent)
        )
        self.download_thread.finished.connect(
            lambda file_path, metadata: self.on_download_finished(file_path, metadata, progress_dialog)
        )
        self.download_thread.error.connect(
            lambda error: self.on_download_error(error, progress_dialog)
        )
        
        # Handle cancel
        def on_cancel():
            if self.download_thread and self.download_thread.isRunning():
                progress_dialog.setLabelText("Cancelling download...")
                self.download_thread.terminate()
                self.download_thread.wait(3000)
            progress_dialog.close()
        
        progress_dialog.canceled.connect(on_cancel)
        
        # Start download
        self.download_thread.start()
    
    def _update_download_progress(self, progress_dialog, status, percent):
        """Update the progress dialog"""
        progress_dialog.setLabelText(status)
        progress_dialog.setValue(percent)
        QApplication.processEvents()
    
    def on_download_finished(self, file_path, metadata, progress_dialog):
        """Handle download completion"""
        progress_dialog.close()
        
        # Verify file exists
        if not os.path.exists(file_path):
            QMessageBox.critical(self.parent(), "Error", f"Downloaded file not found: {file_path}")
            return
        
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        QMessageBox.information(self.parent(), "Download Complete", 
                              f"Successfully downloaded: {metadata['title']}\n"
                              f"By: {metadata['artist']}\n"
                              f"File size: {file_size:.1f} MB")
    
    def on_download_error(self, error, progress_dialog):
        """Handle download error"""
        progress_dialog.close()
        QMessageBox.critical(self.parent(), "Download Failed", 
                           f"YouTube download failed:\n\n{error}\n\n"
                           f"Common issues:\n"
                           f"• Video may be private or unavailable\n"
                           f"• Network connection problems\n"
                           f"• yt-dlp needs to be updated")
