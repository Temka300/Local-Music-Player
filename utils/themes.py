"""Application themes and styling"""

def apply_dark_theme(widget):
    """Apply dark theme styling to a widget"""
    widget.setStyleSheet("""
        QMainWindow {
            background-color: #191414;
            color: #FFFFFF;
        }
        QWidget {
            background-color: #191414;
            color: #FFFFFF;
        }
        QLabel#title {
            font-size: 16px;
            font-weight: bold;
            margin: 10px;
        }
        QLabel#view_title {
            font-size: 18px;
            font-weight: bold;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #404040;
            border-radius: 5px;
            margin: 5px 0px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #1DB954;
            color: #FFFFFF;
            border: none;
            padding: 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1ED760;
        }
        QPushButton:pressed {
            background-color: #169C46;
        }
        QLineEdit {
            background-color: #282828;
            color: #FFFFFF;
            border: 1px solid #404040;
            padding: 5px;
            border-radius: 3px;
        }
        QListWidget {
            background-color: #282828;
            color: #FFFFFF;
            border: 1px solid #404040;
            selection-background-color: #1DB954;
        }
        QTableWidget {
            background-color: #282828;
            color: #FFFFFF;
            gridline-color: #404040;
            selection-background-color: #1DB954;
        }
        QHeaderView::section {
            background-color: #404040;
            color: #FFFFFF;
            padding: 5px;
            border: 1px solid #191414;
        }
        QSlider::groove:horizontal {
            border: 1px solid #404040;
            height: 8px;
            background: #282828;
            margin: 2px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #1DB954;
            border: 1px solid #1DB954;
            width: 18px;
            margin: -2px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: #1ED760;
            width: 20px;
            height: 20px;
            margin: -3px 0;
            border-radius: 10px;
        }
        QMenuBar {
            background-color: #191414;
            color: #FFFFFF;
        }
        QMenuBar::item:selected {
            background-color: #1DB954;
        }
        QMenu {
            background-color: #282828;
            color: #FFFFFF;
            border: 1px solid #404040;
        }
        QMenu::item:selected {
            background-color: #1DB954;
        }
    """)
