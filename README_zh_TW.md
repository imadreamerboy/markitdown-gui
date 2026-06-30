[English](README.md) | [简体中文](README_zh.md) | **繁體中文**

# MarkItDown GUI 轉換工具

這是一個基於 `PySide6` 和官方 Qt Quick Controls/QML 的 `MarkItDown` 桌面 GUI。
它專注於快速將多個檔案轉換為 Markdown，並提供接近原生桌面的操作體驗。

![目前介面截圖](image.png)

更多截圖：

| 設定 | 說明與更新 |
|------|------------|
| ![設定截圖](docs/screenshots/settings.png) | ![說明與更新截圖](docs/screenshots/help.png) |

## 功能

- 以佇列為核心的檔案流程，支援拖放。
- 貼上網站 URL，並透過託管的 Defuddle API 將文章內容轉為 Markdown。
- 批次轉換，支援開始、暫停/繼續、取消和進度回報。
- 結果頁支援逐檔選取和 Markdown 預覽。
- 預覽模式支援渲染後 Markdown 和原始 Markdown。
- 儲存模式支援合併為單一檔案或分別儲存。
- 常用操作：複製 Markdown、儲存輸出、重試失敗轉換、返回佇列、重新開始。
- 可選 OCR，支援掃描版 PDF 和圖片檔案，可選擇 `Azure + Tesseract`、`GLM-OCR` 和通用 `HTTP OCR` 提供者。
- 設定項包含輸出資料夾、儲存模式、儲存到來源資料夾、批次大小、OCR、更新、語言和主題模式（淺色/深色/跟隨系統）。
- 說明頁包含專案連結、OCR 參考、轉換參考、診斷資訊和鍵盤快速鍵。

## 安裝

你可以從 [Releases](https://github.com/imadreamerboy/markitdown-gui/releases) 下載預先編譯版本，或從原始碼執行。

### Release 制品

- Windows：一般使用者使用 `MarkItDown-Windows-Setup-<version>.exe` 安裝器；需要可攜版時使用 `MarkItDown-Windows-<version>.zip`。
- Linux：一般使用者使用 `MarkItDown-Linux-<version>.AppImage` 單檔應用；需要可攜資料夾時使用 `MarkItDown-Linux-<version>.zip`。
- macOS：使用 `MarkItDown-macOS-<version>.dmg`，並把應用拖入 Applications。

### 更新

- 打包版桌面應用程式從 GitHub Releases 更新。應用內更新檢查會讀取最新 release，顯示簡短說明，並優先選擇目前作業系統對應的制品。
- Windows 和 Linux 打包版在首選制品為 `.zip` 時可啟動應用內安裝：下載、驗證 SHA256（如 release metadata 可用）、準備外部 helper、關閉應用、替換應用資料夾、重新啟動，並在替換失敗時回滾。下一次啟動後，說明頁診斷會顯示上次更新結果和回滾備份資料夾。
- macOS 打包版會下載、驗證並開啟 `.dmg`，使用者再手動拖入 Applications。
- Windows 安裝器和 Linux AppImage 是額外的首次安裝下載選項；應用內自動更新會繼續優先使用可攜 `.zip` 制品。
- Release 會發布 `markitdown-release-manifest.json`，包含平台、大小和 SHA256 metadata。
- 原始碼 checkout 可以在說明頁執行 `Run source update`，也可以在終端機執行：

```sh
python -m markitdowngui.utils.source_updater
```

原始碼更新器會先確認沒有已追蹤的本機修改，接著執行 `git pull --ff-only`，並優先用 `uv`、否則用 `pip` 重新安裝 editable 環境。完成後說明頁會顯示重新啟動操作。

### 支援包

說明頁會顯示 OCR、打包更新、原始碼更新、更新檢查和日誌的簡短就緒狀態。複製診斷會包含該狀態，並會隱藏使用者家目錄和明顯 secret。支援包會匯出診斷報告、已清理的設定和截斷後的最近日誌；原始最近檔案路徑、輸出路徑和明顯 secret 會被排除或脫敏。

### 設定設定檔

設定頁可以匯入或匯出可攜 JSON 設定檔，覆蓋 OCR、更新、轉換、主題、語言和儲存模式偏好。設定檔會包含提供者端點和環境變數名稱，但不會包含最近檔案、最近輸出、視窗狀態或預設輸出資料夾。

### 前置需求

- Python `3.10+`
- 建議使用 `uv`

安裝相依套件：

```sh
uv sync
```

也可以：

```sh
pip install -e .[dev]
```

### OCR 說明

- OCR 是可選功能，預設關閉。
- `Azure + Tesseract` 在設定後會優先使用 Azure Document Intelligence，然後使用 Tesseract 作為本機回退。
- `GLM-OCR` 是獨立 OCR 提供者，適用於 PDF 和圖片。可在設定中選擇另一個已設定提供者作為回退。
- `HTTP OCR` 是給本機或自架 OCR 服務使用的通用接入點。應用會傳送帶有 `file` part 的 multipart `POST`，可附帶 `model` 欄位，並可從設定的環境變數讀取 Bearer token。JSON 回應可使用 `markdown`、`text`、`result`、`content` 或 `output`；純文字回應會直接使用。
- 保留 PDF 圖片時會繼續使用既有圖片保留管線。`Azure + Tesseract` 會在該 helper 內執行 OCR；`GLM-OCR` 或 `HTTP OCR` 會先保留圖片，再追加所選提供者的 OCR 文字。
- 設定頁提供常見本機方案的一鍵 OCR presets，以及開啟文件或複製安全設定片段的提供者操作。**Validate OCR** 會在批次開始前檢查必填欄位，**Test connection** 會在不上传使用者文件的情況下檢查提供者連線。
- GLM-OCR 在設定頁中提供三種模式：
  - `Official API`：最簡單的零設定方式，從環境變數讀取 `ZHIPU_API_KEY` 或 `GLMOCR_API_KEY`。
  - `Ollama`：最簡單的本機路徑。GUI 直接呼叫 Ollama 原生 `/api/generate` 端點，預設 `127.0.0.1:11434` 和 `glm-ocr:latest`。
  - `SDK Server (vLLM / SGLang)`：更強的自架路徑。把應用指向現有 `/glmocr/parse` 端點即可。預設值為 `http://127.0.0.1:5002/glmocr/parse`。
- 打包版桌面應用不會內建 GLM-OCR 自架執行環境；`torch`、`transformers`、`vLLM`、`SGLang` 和相關 server/runtime 元件仍需在應用外部部署。
- 專案依賴 `glmocr==0.1.4`，用於客戶端 Official API 和 SDK Server 連線。Ollama 透過 HTTP 直接呼叫。
- 本機 OCR 需要系統安裝 `tesseract`。可從 [Tesseract 官方專案](https://github.com/tesseract-ocr/tesseract) 安裝。如果它不在 `PATH` 中，可以在設定頁指定可執行檔路徑。
- Azure OCR 需要在設定頁填寫 Azure Document Intelligence endpoint。
- Azure Document Intelligence 價格頁面在本文撰寫時包含 [每月 500 頁免費額度](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing)。
- API key 認證請設定 `AZURE_OCR_API_KEY`。
- 如果未設定 `AZURE_OCR_API_KEY`，Azure OCR 會回退到 `DefaultAzureCredential` 支援的 Azure 身分憑證。
- GLM-OCR 專案參考：[zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR)

### 建議的本機託管方式

一般本機使用建議選擇 Ollama。更強的自架部署可使用 GLM-OCR SDK Server，並搭配 vLLM 或 SGLang。

### Ollama

1. 安裝 Ollama。
2. 拉取模型：

```sh
ollama pull glm-ocr:latest
```

3. 如果服務沒有自動啟動，執行：

```sh
ollama serve
```

4. 在本應用中選擇 `GLM-OCR` -> `Ollama`。
5. 除非你改過本機設定，否則保留預設值：
   - host: `127.0.0.1`
   - port: `11434`
   - model: `glm-ocr:latest`

### SDK Server

1. 為 GLM-OCR 建立單獨的 Python 環境。
2. 在該環境中安裝 `glmocr[selfhosted,server]`。
3. 為 `zai-org/GLM-OCR` 啟動本機 `vLLM` 或 `SGLang` 後端。
4. 啟動 SDK server：

```sh
python -m glmocr.server --config config.yaml
```

5. 在本應用中選擇 `GLM-OCR` -> `SDK Server (vLLM / SGLang)`，並使用 `http://127.0.0.1:5002/glmocr/parse`。

最小 server 端 `config.yaml`：

```yaml
pipeline:
  maas:
    enabled: false
  ocr_api:
    api_host: 127.0.0.1
    api_port: 8080
```

官方 GLM-OCR 文件包含完整的 Ollama、`vLLM` 和 `SGLang` 設定命令：

- [官方 Ollama 部署指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md)
- [Self-hosted SDK Server + Client 指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/self-host/README.md)
- [GLM-OCR README](https://github.com/zai-org/GLM-OCR)

### 網站 URL 說明

- 網站轉換使用託管的 [Defuddle](https://defuddle.md/) API。
- 應用會把貼上的 `http://` 或 `https://` URL 傳送到 `https://defuddle.md/<url>`，並把返回的 Markdown 存到結果頁。
- Defuddle 回應通常會在可用時包含 YAML frontmatter metadata。
- 根據 [Defuddle Terms](https://defuddle.md/terms)，未認證請求截至 2026 年 3 月 14 日限制為每個 IP 每月 `1,000` 次。
- 請求直接從桌面應用發出，因此該免費額度限制適用於使用者自己的網路 IP。
- 網站轉換需要網路連線，並依賴外部 Defuddle 服務可用。

## 執行應用

```sh
uv run python -m markitdowngui.main
```

## 鍵盤快速鍵

- `Ctrl+O`: 開啟檔案
- `Ctrl+S`: 儲存輸出
- `Ctrl+C`: 複製輸出
- `Ctrl+R`: 重試失敗轉換
- `Ctrl+P`: 暫停/繼續
- `Ctrl+B`: 開始轉換
- `Ctrl+L`: 清空佇列
- `Ctrl+K`: 顯示快速鍵
- `Esc`: 取消轉換

## 建置獨立執行檔

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

預設 spec 會在 `dist/MarkItDown/` 產生 `onedir` 應用。macOS 也會產生 `dist/MarkItDown.app`。
Release workflow 會把 Windows 和 Linux build 打包成平台專屬 `.zip`，額外產生 Windows Inno Setup `.exe` 安裝器和 Linux `.AppImage`，並把 macOS `.app` bundle 打包成拖入 Applications 的 `.dmg`。如果設定了 `MACOS_CODESIGN_IDENTITY`，macOS bundle 會使用該身份簽名，否則使用 ad-hoc signing。每個 release 也會包含 `markitdown-release-manifest.json`，用於更新 metadata 和 checksum。
該 build 會刻意排除 GLM-OCR 自架執行環境；本機託管仍在 GUI 外部完成。

## 授權

本專案採用 **MIT License**。

應用使用 `PySide6`/Qt，需遵守 Qt 的 LGPL/商業授權模式。此前的 `PySide6-Fluent-Widgets` 相依套件已移除。

## 貢獻

1. Fork 此儲存庫並建立分支。
2. 安裝開發相依套件：

```sh
uv pip install -e .[dev]
```

3. 提交程式碼修改。
4. 執行測試：

```sh
uv run pytest -q
```

5. 開 PR 並清楚說明變更內容。

## 致謝

- MarkItDown ([MIT License](https://opensource.org/licenses/MIT))
- PySide6 ([LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html))
- Qt Quick Controls ([Qt documentation](https://doc.qt.io/qt-6/qtquickcontrols-index.html))
