# Local Spotify Qt

A modern, feature-rich local music player with a sleek dark interface inspired by Spotify. Built with PyQt5 and powered by VLC for high-quality audio playback.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-brightgreen.svg)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-orange.svg)

## ✨ Features

### 🎵 Audio Playback
- **Advanced VLC Engine**: Enhanced audio quality with VLC backend and Qt MediaPlayer fallback
- **Multi-format Support**: MP3, WAV, FLAC, M4A, and more
- **High-Quality Audio**: Professional-grade audio processing
- **Gapless Playback**: Seamless transitions between tracks

### 🎨 Modern Interface
- **Spotify-inspired Design**: Dark theme with modern aesthetics
- **Album Art Display**: Beautiful cover art integration
- **Responsive Layout**: Intuitive and user-friendly interface
- **Real-time Visualization**: Progress tracking and waveform display

### 📚 Library Management
- **SQLite Database**: Fast and reliable music library organization
- **Metadata Extraction**: Automatic title, artist, album, and genre detection
- **Smart Search**: Quick filtering and search capabilities
- **Custom Organization**: Flexible library structure

### 🎵 Playlist Features
- **Custom Playlists**: Create and manage unlimited playlists
- **Shuffle & Repeat**: Multiple playback modes
- **Queue Management**: Dynamic playlist manipulation
- **Smart Recommendations**: AI-powered song suggestions

### 📥 YouTube Integration
- **YouTube Downloader**: Built-in yt-dlp integration for audio downloads
- **Automatic Conversion**: Convert downloaded audio to preferred formats
- **Metadata Preservation**: Maintain track information during download

### 🔧 Advanced Features
- **Audio Conversion**: M4A to MP3 conversion with pydub
- **Volume Control**: Precise audio level management
- **Keyboard Shortcuts**: Efficient navigation and control
- **Cross-platform**: Windows, macOS, and Linux support

## 🚀 Installation

### Prerequisites
- Python 3.7 or higher
- VLC Media Player (for enhanced audio support)

### Quick Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Local-Music-Player.git
   cd Local-Music-Player
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install VLC (recommended)**
   - **Windows**: Download from [VLC website](https://www.videolan.org/vlc/)
   - **macOS**: `brew install vlc` or download from website
   - **Linux**: `sudo apt install vlc` (Ubuntu/Debian) or `sudo dnf install vlc` (Fedora)

4. **Run the application**
   ```bash
   python main.py
   ```

## 📦 Dependencies

### Core Dependencies
- **PyQt5** (≥5.15.0) - Modern GUI framework
- **mutagen** (≥1.47.0) - Audio metadata extraction
- **Pillow** (≥10.0.0) - Image processing for album art
- **pydub** (≥0.25.1) - Audio format conversion

### Optional Dependencies
- **python-vlc** - Enhanced VLC audio engine support
- **yt-dlp** - YouTube audio download functionality
- **requests** - Web-based features and updates

### System Requirements
- **VLC Media Player** - For optimal audio quality (falls back to Qt MediaPlayer)
- **FFmpeg** - For advanced audio processing (optional)

## 🎯 Usage

### Getting Started
1. **Add Music**: Use File → Add Music or drag & drop music files/folders
2. **Create Playlists**: Right-click to create custom playlists
3. **Search Library**: Use the search bar to find specific tracks
4. **Download from YouTube**: Use the built-in downloader for new music

### Keyboard Shortcuts
- `Space` - Play/Pause
- `→` - Next track
- `←` - Previous track
- `↑/↓` - Volume control
- `Ctrl+S` - Shuffle toggle
- `Ctrl+R` - Repeat toggle
- `Ctrl+F` - Focus search

### Supported Formats
- **Audio**: MP3, WAV, FLAC, M4A, AAC, OGG
- **Playlists**: M3U, PLS (import/export)
- **Images**: JPEG, PNG, BMP (album art)

## 📁 Project Structure

```
Local-Music-Player/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
│
├── core/                      # Core functionality
│   ├── __init__.py
│   ├── audio_player.py       # VLC/Qt audio engine
│   ├── database.py           # SQLite music library
│   ├── youtube_downloader.py # yt-dlp integration
│   └── playlist_manager.py   # Playlist operations
│
├── gui/                       # PyQt5 interface components
│   ├── __init__.py
│   ├── main_window.py        # Main application window
│   ├── dialogs/              # Dialog windows
│   │   ├── add_music_dialog.py
│   │   ├── playlist_dialog.py
│   │   └── settings_dialog.py
│   └── widgets/              # Custom widgets
│       ├── player_controls.py
│       ├── library_view.py
│       └── progress_bar.py
│
├── utils/                     # Utility modules
│   ├── __init__.py
│   ├── constants.py          # Application constants
│   ├── file_utils.py         # File management
│   └── metadata_utils.py     # Audio metadata handling
│
├── workers/                   # Background processing
│   ├── __init__.py
│   ├── download_worker.py    # YouTube download threads
│   └── scan_worker.py        # Library scanning threads
│
└── assets/                    # Application resources
    ├── icons/                # UI icons
    ├── styles/               # CSS stylesheets
    └── themes/               # Color themes
```

## 🔧 Configuration

### Settings Location
- **Windows**: `%APPDATA%/Local Spotify Qt/`
- **macOS**: `~/Library/Application Support/Local Spotify Qt/`
- **Linux**: `~/.config/Local Spotify Qt/`

### Database
- SQLite database automatically created at first run
- Stores music metadata, playlists, and user preferences
- Automatic backup and recovery features

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Submit a pull request with a clear description

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

**Audio not playing?**
- Ensure VLC is installed and accessible
- Check if audio files are in supported formats
- Verify system audio drivers

**YouTube downloads failing?**
- Update yt-dlp: `pip install --upgrade yt-dlp`
- Check internet connection
- Some videos may be region-restricted

**Library not updating?**
- Restart the application
- Check file permissions in music directories
- Use "Refresh Library" in the File menu

### Getting Help
- 🐛 [Report bugs](https://github.com/yourusername/Local-Music-Player/issues)
- 💡 [Request features](https://github.com/yourusername/Local-Music-Player/discussions)
- 📖 [Check documentation](https://github.com/yourusername/Local-Music-Player/wiki)

## 🙏 Acknowledgments

- **VLC Media Player** - For excellent audio engine
- **Spotify** - For design inspiration
- **PyQt5** - For robust GUI framework
- **yt-dlp** - For YouTube integration
- **Contributors** - For making this project better

---

⭐ **Star this repository if you find it useful!**
# 🎵 Local Spotify - Music Player for Local Files

A comprehensive, Spotify-like music player for your local music collection. Built with Python and featuring a modern dark theme interface, complete music library management, and robust audio playback with advanced error handling.

## ✨ Features

### 🎨 **Modern Interface**
- **Spotify-inspired Dark Theme**: Professional dark interface with green accents
- **Responsive Layout**: Sidebar navigation with main content area
- **Album Art Display**: Shows album artwork from your music files
- **Real-time Updates**: Live display of currently playing song and progress

### 🎵 **Music Library Management**
- **Automatic Metadata Extraction**: Reads title, artist, album, year, genre from files
- **Album Art Support**: Displays embedded album artwork
- **Smart Organization**: Automatic organization by artist, album, and title
- **Search Functionality**: Real-time search across all metadata fields
- **Supported Formats**: MP3, FLAC, M4A, WAV, OGG

### 📝 **Playlist Management**
- **Create Custom Playlists**: Organize your music into personalized collections
- **Easy Song Management**: Context menu support for adding songs to playlists
- **Playlist Persistence**: All playlists saved in local SQLite database
- **Quick Access**: Sidebar playlist navigation

### 🎮 **Enhanced Playback Controls**
- **Full Transport Controls**: Play, pause, previous, next with visual feedback
- **Shuffle Mode**: Randomize playback order with visual indicator
- **Repeat Modes**: Off, repeat all, repeat one with cycling button
- **Volume Control**: Smooth volume adjustment with visual slider
- **Progress Tracking**: Visual progress bar with time display

### 🔧 **Advanced Audio Engine**
- **ModPlug_Load Error Recovery**: Automatic fallback systems for problematic files
- **Multiple Audio Configurations**: 5 different initialization fallbacks
- **Enhanced Error Handling**: Detailed diagnostics and troubleshooting
- **File Validation**: Checks file existence, size, and format before loading
- **Alternative Loading Methods**: Multiple approaches for maximum compatibility

### 🔍 **Library Features**
- **Folder Scanning**: Add entire music folders with automatic recursive scanning
- **Individual File Import**: Add specific music files via file picker
- **Duplicate Detection**: Prevents duplicate entries in your library
- **Library Statistics**: View collection overview and detailed metrics
- **File Location Access**: Quick access to song files on disk

### ⌨️ **Keyboard Shortcuts**
- **Space**: Play/Pause
- **Ctrl+O**: Add Files
- **Ctrl+Shift+O**: Add Folder
- **Ctrl+N**: Create Playlist
- **Ctrl+F**: Focus Search
- **Ctrl+R**: Refresh Library
- **Esc**: Stop Playback

## 🚀 Quick Start

### Windows (Recommended)
```bash
# Double-click to auto-install and run:
launch.bat

# Or manually:
pip install pygame mutagen pillow
python local_spotify.py
```

### Cross-Platform
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python local_spotify.py
```

## 🎮 How to Use

### 1. **First Launch**
1. **Import Your Music**: Use "📂 Add Folder" or "📄 Add Files" buttons in the sidebar
2. **Supported Formats**: MP3 (recommended), WAV, FLAC, OGG, M4A
3. **Automatic Scanning**: The app will extract metadata and album art automatically

### 2. **Playing Music**
1. **Double-click any song** in the library to start playing
2. **Use transport controls**: Previous (⏮), Play/Pause (▶/⏸), Next (⏭)
3. **Adjust volume**: Use the volume slider in the bottom-right
4. **Track progress**: Click on the progress bar to seek

### 3. **Creating Playlists**
1. **Create**: File → Create Playlist or use the "➕ Create Playlist" button
2. **Add Songs**: Right-click songs → "Add to Playlist"
3. **Access**: Click playlist names in the sidebar to view contents

### 4. **Customizing Playback**
1. **Shuffle Mode**: Click 🔀 to randomize song order
2. **Repeat Modes**: Click 🔁 to cycle through repeat options
3. **Search**: Use the search box to filter your library in real-time

## 📋 Requirements

### System Requirements
- **Python**: 3.7 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 512MB RAM minimum
- **Storage**: 50MB for application + space for music library database

### Python Dependencies
- **pygame**: Audio playback engine
- **mutagen**: Metadata extraction from audio files
- **Pillow**: Image processing for album art
- **sqlite3**: Database for library management (included with Python)

Install all dependencies with:
```bash
pip install -r requirements.txt
```

## 🎨 Interface Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🎵 Local Spotify                                        ♪ Now Playing │
├─────────────┬───────────────────────────────────────────────────────┤
│             │ Music Library (X songs)          📂 Import 📄 Import   │
│ 📁 Import   ├───────────────────────────────────────────────────────┤
│ 📂 Add Folder│ Title    │ Artist   │ Album    │ Duration              │
│ 📄 Add Files │ Song 1   │ Artist 1 │ Album 1  │ 3:45                 │
│             │ Song 2   │ Artist 2 │ Album 2  │ 4:12                 │
│ 🔍 Search   │ Song 3   │ Artist 3 │ Album 3  │ 2:58                 │
│             │          │          │          │                      │
│ 📚 Library  │          │          │          │                      │
│             │          │          │          │                      │
│ 📝 Playlists│          │          │          │                      │
│ • My Favs   │          │          │          │                      │
│ • Rock Mix  │          │          │          │                      │
│ • Chill     │          │          │          │                      │
├─────────────┴───────────────────────────────────────────────────────┤
│ [♪] Song Title - Artist    [⏮][▶][⏭][🔀][🔁]  0:00──●──3:45 🔊──── │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔧 Troubleshooting

### **Common Issues & Solutions**

#### **"ModPlug_Load failed" Error**
✅ **Fixed Automatically**: The enhanced audio player includes automatic error recovery
- Multiple audio initialization fallbacks
- Alternative loading methods for problematic files
- Clear error messages with suggestions

#### **"No module named 'pygame'" Error**
```bash
pip install pygame mutagen pillow
```

#### **Songs Not Playing**
- Verify audio file exists and isn't corrupted
- Try different audio format (MP3 is most compatible)
- Check system audio drivers and volume
- The app will automatically try alternative loading methods

#### **No Album Art Displayed**
- Album art must be embedded in the audio file
- Not all music files have embedded artwork
- The app shows ♪ symbol when no art is available

#### **Slow Library Scanning**
- Large music libraries take time on first scan
- Subsequent launches are faster (metadata cached in database)
- Consider scanning smaller folders incrementally

#### **Search Not Working**
- Make sure you're typing in the search box (🔍 Search Music)
- Search works across title, artist, and album fields
- Search is case-insensitive and supports partial matches

### **Audio Format Compatibility**
- **✅ MP3**: Excellent compatibility (recommended)
- **✅ WAV**: High compatibility
- **✅ OGG**: Good compatibility
- **⚠️ FLAC**: May need conversion for some systems
- **⚠️ M4A**: May need conversion for some systems

## 🏗️ Technical Details

### **Database Schema**
- **Songs Table**: Stores all music metadata and file paths
- **Playlists Table**: Stores playlist information with timestamps
- **Playlist Songs Table**: Links songs to playlists with position ordering

### **Enhanced Audio Engine**
The music player includes an advanced audio system with:
- **5 different audio initialization configurations** with automatic fallbacks
- **Specific ModPlug_Load error detection** and recovery
- **Alternative loading methods** for problematic files
- **File validation** (existence, size, format checking)
- **Detailed error diagnostics** with user-friendly messages

### **Supported Audio Formats**
- **MP3**: Full support including ID3v2 tags and album art
- **FLAC**: Lossless audio with full metadata support
- **M4A/MP4**: iTunes format with full metadata
- **WAV**: Basic support (limited metadata)
- **OGG**: Vorbis format support

## 📊 Library Statistics

Access detailed statistics about your music collection via **View → Show Statistics**:
- **Total Songs**: Number of tracks in your library
- **Artists**: Unique artists in your collection
- **Albums**: Unique albums in your collection
- **Playlists**: Number of custom playlists
- **Total Duration**: Combined length of all music

## 🎨 Customization

### **Themes**
The application uses a Spotify-inspired dark theme with:
- **Background**: Dark gray (#191414)
- **Sidebar**: Darker gray (#282828)  
- **Accent**: Spotify green (#1DB954)
- **Text**: White (#FFFFFF)

## 📁 File Structure

```
music_player/
├── local_spotify.py          # Main application file
├── music_library.db         # SQLite database (auto-created)
├── requirements.txt         # Python dependencies
├── launch.bat              # Windows launcher script
└── README.md               # This documentation
```

## 🎉 Getting Started

1. **Install**: Run `pip install -r requirements.txt`
2. **Launch**: Double-click `launch.bat` (Windows) or run `python local_spotify.py`
3. **Import**: Use the "📂 Add Folder" button to scan your music directory
4. **Enjoy**: Double-click songs to play and create playlists!

---

**🎵 Happy Listening!**  
*Built with Python, pygame, tkinter, and lots of ♪*
