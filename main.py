#!/usr/bin/env python3
"""
🎵 Local Spotify Qt - Music Player for Local Files
Main application entry point
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# Add the current directory to Python path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import from the gui package
from gui.main_window import LocalSpotifyQt

def main():
    """Main application entry point"""
    try:
        # Create QApplication instance
        app = QApplication(sys.argv)
        app.setApplicationName("Local Spotify")
        app.setApplicationVersion("1.10")
        
        # Create and show main window
        window = LocalSpotifyQt()
        window.show()
        
        # Start the application event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        QMessageBox.critical(None, "Application Error", 
                           f"Failed to start the application:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()