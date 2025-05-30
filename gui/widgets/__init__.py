"""
Custom widgets for the GUI
"""

try:
    from .editable_columns_delegate import EditableColumnsDelegate
    
    __all__ = ['EditableColumnsDelegate']
except ImportError:
    # Fallback if modules don't exist yet
    __all__ = []