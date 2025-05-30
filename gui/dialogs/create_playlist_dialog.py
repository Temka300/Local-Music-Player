"""
Dialog for creating new playlists
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class CreatePlaylistDialog(QDialog):
    """Dialog for creating a new playlist"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Playlist")
        self.setFixedSize(400, 200)
        self.setup_ui()
        self.apply_styling()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("📝 Create New Playlist")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Playlist name
        layout.addWidget(QLabel("Playlist Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter playlist name...")
        layout.addWidget(self.name_edit)
        
        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)
        self.desc_edit.setPlaceholderText("Enter playlist description...")
        layout.addWidget(self.desc_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.create_btn = QPushButton("📝 Create Playlist")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancelButton")
        
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.create_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)
        self.name_edit.returnPressed.connect(self.validate_and_accept)
        
        # Focus on name input
        self.name_edit.setFocus()
    
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
            QLineEdit, QTextEdit {
                background-color: #282828;
                color: #FFFFFF;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
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
    
    def validate_and_accept(self):
        """Validate input and accept dialog"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a playlist name")
            return
        
        self.accept()
    
    def get_playlist_data(self):
        """Get the playlist name and description"""
        name = self.name_edit.text().strip()
        description = self.desc_edit.toPlainText().strip()
        return name, description
