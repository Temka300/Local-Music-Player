#!/usr/bin/env python3
"""
🎵 Local Spotify Qt - Music Player for Local Files
Main application entry point with enhanced error handling
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox

# Add the current directory to Python path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import from the gui package and constants
from gui.main_window import LocalSpotifyQt
from utils.constants import APP_NAME, APP_VERSION

def main():
    """Main application entry point"""
    try:
        # Set Windows application ID before creating QApplication
        import ctypes
        try:
            # Set the app user model ID for Windows taskbar/audio mixer
            # Convert spaces to dots for the ID
            app_id = APP_NAME.replace(" ", ".")
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except:
            pass  # Ignore if not on Windows or if it fails
        
        # Create QApplication instance
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        
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
    try:
        print(f"🎵 Starting {APP_NAME}")
        main()
    except KeyboardInterrupt:
        print("\n👋 Application terminated by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        print("\n📝 Full error trace:")
        import traceback
        traceback.print_exc()
        
        # Additional debugging
        print(f"\n🔍 Error type: {type(e)}")
        print(f"🔍 Error args: {e.args}")
        
        input("\nPress Enter to exit...")
        sys.exit(1)