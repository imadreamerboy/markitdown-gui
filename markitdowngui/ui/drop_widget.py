from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QComboBox
from PySide6.QtCore import Qt
from ..core.file_utils import FileManager

class DropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.accepted_extensions = ["*.*"]
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add file type filter
        filterLayout = QHBoxLayout()
        filterLabel = QLabel("File Type:")
        self.filterCombo = QComboBox()
        self.filterCombo.addItems(FileManager.SUPPORTED_TYPES.keys())
        self.filterCombo.currentTextChanged.connect(self.update_filter)
        filterLayout.addWidget(filterLabel)
        filterLayout.addWidget(self.filterCombo)
        
        # List widget and drop label
        self.listWidget = QListWidget()
        dropLabel = QLabel("Drag and drop files here")
        dropLabel.setToolTip("Drag files you want to convert into Markdown and drop them here.")
        
        layout.addLayout(filterLayout)
        layout.addWidget(dropLabel)
        layout.addWidget(self.listWidget)
    
    def update_filter(self, filter_name):
        """Update accepted extensions based on selected filter."""
        self.accepted_extensions = [FileManager.SUPPORTED_TYPES[filter_name]]
        
    def setAcceptedExtensions(self, extensions):
        if isinstance(extensions, str):
            extensions = [extensions]
        self.accepted_extensions = extensions
    
    def isAcceptedFile(self, filepath):
        if "*.*" in self.accepted_extensions:
            return True
        return any(filepath.lower().endswith(ext.replace("*", "")) 
                  for ext in self.accepted_extensions)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if all(self.isAcceptedFile(url.toLocalFile()) for url in urls):
                event.acceptProposedAction()
    
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if self.isAcceptedFile(filepath):
                self.listWidget.addItem(filepath)
                # Notify parent of new file
                if hasattr(self.parent(), 'handleNewFile'):
                    self.parent().handleNewFile(filepath)