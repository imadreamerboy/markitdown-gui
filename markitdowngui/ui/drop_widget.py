from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QComboBox, QPushButton, QFileDialog, QAbstractItemView, QMenu
from PySide6.QtCore import Qt, Signal, QPoint
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
        # Predeclare to satisfy type checkers
        self.clearAllHeaderButton = None
        
        # Add file type filter
        filterLayout = QHBoxLayout()
        self.filterLabel = QLabel() # Initialize, text set in retranslate_ui
        self.filterCombo = QComboBox()
        # Convert dict_keys to a list for type checkers and Qt API
        self.filterCombo.addItems(list(FileManager.SUPPORTED_TYPES.keys()))  # Keys are not translated
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
        # Context menu for removing selected or clearing all
        self.listWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self._show_context_menu)
        self.listWidget.keyPressEvent = self._wrap_keypress(self.listWidget.keyPressEvent)
        self.dropLabel = QLabel() # Initialize, text set in retranslate_ui

        # Add Clear All on the right of the header row
        self.clearAllHeaderButton = QPushButton(self.translate("clear_all_button"))
        self.clearAllHeaderButton.setObjectName("clear_all_button_header")
        self.clearAllHeaderButton.clicked.connect(self.listWidget.clear)
        filterLayout.addWidget(self.clearAllHeaderButton)
        
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
        btn = getattr(self, "clearAllHeaderButton", None)
        if btn is not None:
            btn.setText(self.translate("clear_all_button"))
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
                # Notify parent of new file if method exists (runtime check; ignore static type warning)
                parent = self.parent()
                if parent is not None and hasattr(parent, 'handleNewFile'):
                    getattr(parent, 'handleNewFile')(filepath)
    
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.translate("select_files_title"), "", self.translate("all_files_filter"))
        if files:
            for file in files:
                if self.isAcceptedFile(file):
                    self.listWidget.addItem(file)
            self.filesAdded.emit(files)
    
    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        remove_selected = menu.addAction(self.translate("remove_selected_action") if hasattr(self, "translate") else "Remove Selected")
        clear_all = menu.addAction(self.translate("clear_list_action") if hasattr(self, "translate") else "Clear List")
        action = menu.exec(self.listWidget.mapToGlobal(pos))
        if action == remove_selected:
            self._remove_selected_items()
        elif action == clear_all:
            self.listWidget.clear()
    
    def _remove_selected_items(self):
        # Remove from bottom to top to keep indices valid
        for item in sorted(self.listWidget.selectedItems(), key=lambda it: self.listWidget.row(it), reverse=True):
            row = self.listWidget.row(item)
            self.listWidget.takeItem(row)
    
    def _wrap_keypress(self, original_handler):
        def handler(event):
            # Delete or Backspace removes selected
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self._remove_selected_items()
                return
            return original_handler(event)
        return handler
