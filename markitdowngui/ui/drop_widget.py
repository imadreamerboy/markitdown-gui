from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QComboBox, QPushButton, QFileDialog, QAbstractItemView
from PySide6.QtCore import Qt, Signal
from markitdowngui.core.file_utils import FileManager

class DropWidget(QWidget):
    filesAdded = Signal(list)  # Signal to notify when files are added
    def __init__(self, translate_func):
        super().__init__()
        self.translate = translate_func
        self.setAcceptDrops(True)
        self.accepted_extensions = ["*.*"]
        self.setup_ui()
        self.retranslate_ui(translate_func) # Initial translation
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add file type filter
        filterLayout = QHBoxLayout()
        self.filterLabel = QLabel() # Initialize, text set in retranslate_ui
        self.filterCombo = QComboBox()
        self.filterCombo.addItems(FileManager.SUPPORTED_TYPES.keys()) # Keys are not translated
        self.filterCombo.currentTextChanged.connect(self.update_filter)
        filterLayout.addWidget(self.filterLabel)
        filterLayout.addWidget(self.filterCombo)
        
        # Browse button
        self.browseButton = QPushButton(self.translate("browse_files_button"))
        self.browseButton.clicked.connect(self.open_file_dialog)
        filterLayout.addWidget(self.browseButton)
        
        # List widget and drop label
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.listWidget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.dropLabel = QLabel() # Initialize, text set in retranslate_ui
        
        layout.addLayout(filterLayout)
        layout.addWidget(self.dropLabel)
        layout.addWidget(self.listWidget)
    
    def retranslate_ui(self, translate_func):
        """Update UI element texts using the translate function."""
        self.translate = translate_func # Update translate function reference if needed
        self.filterLabel.setText(self.translate("drop_widget_file_type_label"))
        self.dropLabel.setText(self.translate("drop_widget_drop_label"))
        self.dropLabel.setToolTip(self.translate("drop_widget_tooltip"))
        self.browseButton.setText(self.translate("browse_files_button"))
        self.browseButton.setToolTip(self.translate("browse_files_tooltip"))
        # Add other elements that need retranslation if any
    
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
    
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.translate("select_files_title"), "", self.translate("all_files_filter"))
        if files:
            for file in files:
                if self.isAcceptedFile(file):
                    self.listWidget.addItem(file)
            self.filesAdded.emit(files)