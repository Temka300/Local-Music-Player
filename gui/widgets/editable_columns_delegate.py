"""
Custom Editable Columns Delegate
"""

from PyQt5.QtWidgets import QItemDelegate, QLineEdit
from PyQt5.QtCore import Qt


class EditableColumnsDelegate(QItemDelegate):
    """Custom delegate that only allows editing of specific columns"""
    
    def __init__(self, editable_columns, parent=None):
        super().__init__(parent)
        self.editable_columns = editable_columns
    
    def createEditor(self, parent, option, index):
        """Create editor only for allowed columns"""
        if index.column() in self.editable_columns:
            editor = QLineEdit(parent)
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #282828;
                    color: #FFFFFF;
                    border: 2px solid #1DB954;
                    border-radius: 4px;
                    padding: 4px;
                    font-size: 12px;
                }
            """)
            return editor
        return None
    
    def setEditorData(self, editor, index):
        """Set the data to be edited"""
        if isinstance(editor, QLineEdit):
            editor.setText(index.model().data(index, Qt.DisplayRole))
    
    def setModelData(self, editor, model, index):
        """Set the edited data back to the model"""
        if isinstance(editor, QLineEdit):
            model.setData(index, editor.text(), Qt.EditRole)
