[English](README.md) | [简体中文](README_zh.md) | **繁體中文**

---

# MarkItDown GUI 轉換工具

基於 `PySide6` 和官方 Qt Quick Controls/QML 的桌面 GUI，讓你用接近原生桌面體驗的介面，把 PDF、Word、圖片、網頁 URL 等格式批次轉換為 Markdown。

![目前介面截圖](image.png)

---

## 功能一覽

| 功能 | 說明 |
|------|------|
| 拖放轉換 | 直接拖放檔案到視窗，支援批次處理 |
| 網頁轉換 | 貼上網址，自動擷取文章內容轉為 Markdown |
| 批次控制 | 開始、暫停／繼續、取消，附進度回報 |
| 預覽模式 | 渲染檢視 / 原始 Markdown 雙模式切換 |
| 儲存模式 | 合併單一檔案 或 分別儲存 |
| OCR | 掃描版 PDF 和圖片的文字辨識（選填） |
| 設定 | 輸出目錄、儲存模式、批次大小、OCR、淺色／深色／系統主題 |
| 說明 | 專案連結、OCR 參考、轉換參考和鍵盤快捷鍵 |

---

## 支援的輸入格式

`docx` `pptx` `xlsx` `xls` `pdf` `epub` `html` `txt` `csv` `json` `xml` `圖片` `zip` `網頁 URL`

---

## 安裝

### 方式一：下載預先編譯版本（推薦）

前往 [Releases](https://github.com/imadreamerboy/markitdown-gui/releases) 下載對應平台的壓縮檔，解壓縮後直接執行。

### 方式二：從原始碼執行

**前置需求：** Python `3.10+`，建議搭配 `uv`

```sh
# 安裝相依套件
uv sync

# 啟動應用程式
uv run python markitdowngui/main.py
```

或使用 pip：

```sh
pip install -e .[dev]
python markitdowngui/main.py
```

---

## OCR 設定

OCR 為選填功能，預設關閉。啟用後可辨識掃描版 PDF 和圖片中的文字。

### 提供者說明

**Azure / Tesseract OCR**
- 優先使用 Azure Document Intelligence（需設定端點）
- Azure 失敗時自動備援至本地 Tesseract
- 繁體中文辨識：Tesseract 語言代碼請使用 `chi_tra`
- 使用 API 金鑰請設定環境變數 `AZURE_OCR_API_KEY`

**GLM-OCR**
- 新一代 OCR 提供者，支援三種模式：

| 模式 | 說明 |
|------|------|
| Official API | 零設定，從環境變數讀取 `ZHIPU_API_KEY` 或 `GLMOCR_API_KEY` |
| Ollama | 最簡單的本地方式，呼叫 Ollama 原生 API |
| SDK Server | 進階自架，搭配 vLLM / SGLang |

### Ollama 快速設定

```sh
# 1. 拉取模型
ollama pull glm-ocr:latest

# 2. 啟動服務（若未自動啟動）
ollama serve
```

在應用程式設定中選擇 `GLM-OCR` → `Ollama`，保留預設值（`127.0.0.1:11434`，model `glm-ocr:latest`）即可。

### SDK Server 設定

```sh
# 安裝
pip install glmocr[selfhosted,server]

# 啟動
python -m glmocr.server --config config.yaml
```

最小 `config.yaml`：

```yaml
pipeline:
  maas:
    enabled: false
  ocr_api:
    api_host: 127.0.0.1
    api_port: 8080
```

應用程式指向 `http://127.0.0.1:5002/glmocr/parse`。

---

## 鍵盤快速鍵

| 快速鍵 | 功能 |
|--------|------|
| `Ctrl+O` | 開啟檔案 |
| `Ctrl+S` | 儲存輸出 |
| `Ctrl+C` | 複製輸出 |
| `Ctrl+P` | 暫停／繼續 |
| `Ctrl+B` | 開始轉換 |
| `Ctrl+L` | 清空佇列 |
| `Ctrl+K` | 顯示快速鍵 |
| `Esc` | 取消轉換 |

---

## 建置獨立執行檔

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

輸出目錄：`dist/MarkItDown/`

---

## 貢獻

1. Fork 此儲存庫並建立分支
2. 安裝開發相依套件：`uv pip install -e .[dev]`
3. 提交修改
4. 執行測試：`uv run pytest -q`
5. 開 PR 並說明變更內容

---

## 授權

本專案採用 **GPLv3（僅限非商業用途）**，與 `PySide6-Fluent-Widgets` 的非商業授權要求一致。商業用途請另行洽談授權。

---

## 致謝

- [MarkItDown](https://github.com/microsoft/markitdown)（MIT 授權）
- [PySide6](https://doc.qt.io/qtforpython/)（LGPLv3 授權）
- [PySide6-Fluent-Widgets](https://qfluentwidgets.com)
- [GLM-OCR](https://github.com/zai-org/GLM-OCR)
