"""Scrolling text label for long song titles"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter

class ScrollingLabel(QLabel):
    """Label that automatically scrolls text if it's too long to display"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Scrolling properties
        self.scrolling = False
        self.scroll_position = 0
        self.scroll_direction = 1   # 1 = right to left
        self.scroll_speed = 2       # Pixels per step
        self.pause_at_edges = 30    # Frames to pause at edges
        self.pause_counter = 0
        
        # Text properties 
        self._full_text = ""
        self._text_width = 0
        self._label_width = 0
        
        # Setup timer for animation
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.update_scroll_position)
        self.scroll_timer.setInterval(50)  # 20 FPS scrolling
        
    def setText(self, text):
        """Set text and check if scrolling is needed"""
        self._full_text = text
        super().setText(text)
        
        # Get text metrics after a short delay to ensure font is loaded
        QTimer.singleShot(10, self.check_scrolling_needed)
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self._label_width = self.width()
        QTimer.singleShot(10, self.check_scrolling_needed)
    
    def check_scrolling_needed(self):
        """Check if text needs to scroll"""
        if not self._full_text:
            return
            
        # Get text metrics
        font_metrics = self.fontMetrics()
        self._text_width = font_metrics.horizontalAdvance(self._full_text)
        self._label_width = self.width()
        
        print(f"📏 Text width: {self._text_width}, Label width: {self._label_width}")
        
        if self._text_width > self._label_width - 10:  # Account for padding
            if not self.scrolling:
                print("🔄 Starting scroll animation")
                self.scrolling = True
                self.scroll_timer.start()
                self.scroll_position = 0
                self.scroll_direction = 1
                self.pause_counter = self.pause_at_edges
        else:
            if self.scrolling:
                print("⏹️ Stopping scroll animation")
                self.scrolling = False
                self.scroll_timer.stop()
                self.scroll_position = 0
                self.update()
    
    def update_scroll_position(self):
        """Update scroll position for animation"""
        if not self.scrolling or not self._full_text:
            return
        
        # Handle pausing at edges
        if self.pause_counter > 0:
            self.pause_counter -= 1
            return
            
        # Update position
        self.scroll_position += (self.scroll_speed * self.scroll_direction)
        max_scroll = self._text_width - self._label_width + 20
        
        # Change direction if we hit an edge
        if self.scroll_position <= 0:
            self.scroll_position = 0
            self.scroll_direction = 1
            self.pause_counter = self.pause_at_edges
        elif self.scroll_position >= max_scroll:
            self.scroll_position = max_scroll
            self.scroll_direction = -1
            self.pause_counter = self.pause_at_edges
            
        # Request redraw
        self.update()
    
    def paintEvent(self, event):
        """Custom paint to handle text scrolling"""
        if not self.scrolling or not self._full_text:
            # Normal rendering for short text
            super().paintEvent(event)
            return
            
        # Custom rendering for scrolling text
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        
        # Calculate text position
        x_pos = -self.scroll_position
        y_pos = (self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) // 2
        
        # Draw the scrolling text
        text_rect = QRect(x_pos, 0, self._text_width, self.height())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self._full_text)