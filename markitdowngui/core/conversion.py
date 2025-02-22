from PySide6.QtCore import QThread, Signal

class ConversionWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, args, batch_size):
        super().__init__()
        self.md, self.files, self.settings = args
        self.batch_size = batch_size
        self.is_paused = False
        self.is_cancelled = False

    def run(self):
        results = {}
        
        for i in range(0, len(self.files), self.batch_size):
            if self.is_cancelled:
                break
                
            batch = self.files[i:i + self.batch_size]
            for j, file in enumerate(batch):
                while self.is_paused:
                    if self.is_cancelled:
                        return
                    self.msleep(100)
                    
                try:
                    result = self.md.convert(file)
                    results[file] = result.text_content
                except Exception as e:
                    results[file] = f"Error converting {file}: {str(e)}"
                
                progress = int((i + j + 1) / len(self.files) * 100)
                self.progress.emit(progress, file)
            
        self.finished.emit(results)