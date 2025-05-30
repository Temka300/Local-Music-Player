#!/usr/bin/env python3
"""
Simple launcher for the modular Local Spotify Qt application
"""

import sys
import os
from main import main
# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    print("🎵 Starting Local Spotify Qt (Modular Version)...")
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
