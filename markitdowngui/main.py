import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QFileDialog, QCheckBox, QLineEdit, QLabel, QTextEdit
)
from PySide6.QtCore import Qt
from markitdown import MarkItDown

class DropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.listWidget = QListWidget()
        layout = QVBoxLayout(self)
        label = QLabel("Drag and drop files here")
        label.setToolTip("Drag files you want to convert into Markdown and drop them here.")
        layout.addWidget(label)
        layout.addWidget(self.listWidget)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            self.listWidget.addItem(filepath)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MarkItDown GUI Wrapper")
        self.setMinimumSize(600, 500)
        
        # Drop area for files
        self.dropWidget = DropWidget()
        
        # Clear list button
        self.clearListButton = QPushButton("Clear List")
        self.clearListButton.setToolTip("Clear the list of files")
        self.clearListButton.clicked.connect(self.clearFileList)
        fileListLayout = QHBoxLayout()
        fileListLayout.addWidget(self.clearListButton)
        
        # Settings: Plugins and Document Intelligence Endpoint
        self.enablePluginsCheck = QCheckBox("Enable Plugins")
        self.enablePluginsCheck.setToolTip("Enable third-party plugins for additional conversion features")
        self.docIntelLine = QLineEdit()
        self.docIntelLine.setPlaceholderText("Document Intelligence Endpoint (optional)")
        self.docIntelLine.setToolTip("Enter your Azure Document Intelligence endpoint if you want to use it")
        settingsLayout = QHBoxLayout()
        settingsLayout.addWidget(self.enablePluginsCheck)
        settingsLayout.addWidget(self.docIntelLine)
        
        # Output path selection controls
        self.outputPathLine = QLineEdit()
        self.outputPathLine.setPlaceholderText("Select output file or folder")
        self.outputPathLine.setToolTip("Specify a file (for single output) or folder (for separate outputs)")
        self.browseOutputButton = QPushButton("Browse")
        self.browseOutputButton.setToolTip("Browse to select output file/folder")
        self.browseOutputButton.clicked.connect(self.browseOutputPath)
        outputPathLayout = QHBoxLayout()
        outputPathLayout.addWidget(self.outputPathLine)
        outputPathLayout.addWidget(self.browseOutputButton)
        
        # New option: Save as Separate Files
        self.separateFilesCheck = QCheckBox("Save as Separate Files")
        self.separateFilesCheck.setToolTip("If checked, each input file will be saved as an individual Markdown file.")
        
        # Conversion button
        self.convertButton = QPushButton("Convert Files")
        self.convertButton.setToolTip("Convert the selected files to Markdown")
        self.convertButton.clicked.connect(self.convertFiles)
        
        # Additional action buttons: Copy output and Save output
        self.copyButton = QPushButton("Copy Output")
        self.copyButton.setToolTip("Copy the Markdown output to clipboard")
        self.copyButton.clicked.connect(self.copyOutput)
        self.saveButton = QPushButton("Save Output")
        self.saveButton.setToolTip("Save the Markdown output to file(s)")
        self.saveButton.clicked.connect(self.saveOutput)
        actionsLayout = QHBoxLayout()
        actionsLayout.addWidget(self.copyButton)
        actionsLayout.addWidget(self.saveButton)
        
        # Output text area
        self.outputText = QTextEdit()
        self.outputText.setReadOnly(True)
        self.outputText.setToolTip("Markdown output will be displayed here")
        
        # Main layout assembly
        layout = QVBoxLayout(self)
        layout.addWidget(self.dropWidget)
        layout.addLayout(fileListLayout)
        layout.addWidget(QLabel("Settings:"))
        layout.addLayout(settingsLayout)
        layout.addWidget(QLabel("Output Path (file for single, folder for separate outputs):"))
        layout.addLayout(outputPathLayout)
        layout.addWidget(self.separateFilesCheck)
        layout.addWidget(self.convertButton)
        layout.addLayout(actionsLayout)
        layout.addWidget(self.outputText)
    
    def clearFileList(self):
        self.dropWidget.listWidget.clear()
    
    def browseOutputPath(self):
        if self.separateFilesCheck.isChecked():
            # Browse for a folder
            folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
            if folder:
                self.outputPathLine.setText(folder)
        else:
            # Browse for a single file
            file_path, _ = QFileDialog.getSaveFileName(self, "Select Output File", "", "Markdown Files (*.md);;All Files (*)")
            if file_path:
                self.outputPathLine.setText(file_path)
    
    def convertFiles(self):
        files = [self.dropWidget.listWidget.item(i).text() for i in range(self.dropWidget.listWidget.count())]
        if not files:
            self.outputText.setPlainText("No files to convert. Please drag and drop files.")
            return
        settings = {}
        if self.enablePluginsCheck.isChecked():
            settings["enable_plugins"] = True
        endpoint = self.docIntelLine.text().strip()
        if endpoint:
            settings["docintel_endpoint"] = endpoint
        md = MarkItDown(**settings)
        
        # If saving separately, build a dict mapping each file to its conversion output
        self.conversionResults = {}
        combined_output = ""
        for file in files:
            try:
                result = md.convert(file)
                self.conversionResults[file] = result.text_content
                combined_output += f"File: {file}\n" + result.text_content + "\n\n"
            except Exception as e:
                error_msg = f"Error converting {file}: {str(e)}\n\n"
                self.conversionResults[file] = error_msg
                combined_output += error_msg
        self.outputText.setPlainText(combined_output)
    
    def copyOutput(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.outputText.toPlainText())
    
    def saveOutput(self):
        output_path = self.outputPathLine.text().strip()
        if not output_path:
            # Prompt user if no output path is specified.
            if self.separateFilesCheck.isChecked():
                output_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")
            else:
                output_path, _ = QFileDialog.getSaveFileName(self, "Save Markdown Output", "", "Markdown Files (*.md);;All Files (*)")
            if not output_path:
                return
        
        if self.separateFilesCheck.isChecked():
            # Save each file's output separately
            for infile, md_text in self.conversionResults.items():
                base_name = os.path.splitext(os.path.basename(infile))[0]
                out_file = os.path.join(output_path, base_name + ".md")
                try:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(md_text)
                    self.outputText.append(f"Saved {out_file}")
                except Exception as e:
                    self.outputText.append(f"Error saving {out_file}: {str(e)}")
        else:
            # Save combined output
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(self.outputText.toPlainText())
                self.outputText.append(f"\nCombined output saved to {output_path}")
            except Exception as e:
                self.outputText.append(f"\nError saving output: {str(e)}")
            
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
