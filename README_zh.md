[English](README.md) | **简体中文** | [繁體中文](README_zh_TW.md)

# MarkItDown GUI 封装

这是一个基于 `PySide6` 和官方 Qt Quick Controls/QML 的 `MarkItDown` 桌面 GUI。
它面向快速、多文件转换到 Markdown，并提供接近原生桌面的界面体验。

![当前界面截图](image.png)

更多截图：

| 设置 | 帮助与更新 |
|------|------------|
| ![设置截图](docs/screenshots/settings.png) | ![帮助与更新截图](docs/screenshots/help.png) |

## 功能

- 基于队列的文件流程，支持拖放。
- 粘贴网站 URL，并通过托管的 Defuddle API 转换文章内容。
- 批量转换，支持开始、暂停/恢复、取消和进度反馈。
- 结果页支持按文件选择和 Markdown 预览。
- 预览模式支持渲染 Markdown 和原始 Markdown。
- 保存模式支持合并为一个文件或分别保存。
- 常用操作：复制 Markdown、保存输出、重试失败转换、返回队列、重新开始。
- 可选 OCR，支持扫描版 PDF 和图片文件，可选择 `Azure + Tesseract`、`GLM-OCR` 和通用 `HTTP OCR` 提供方。
- 设置项包括输出目录、保存模式、保存到源文件夹、批处理大小、OCR、更新、语言和主题模式（浅色/深色/跟随系统）。
- 帮助页包含项目链接、OCR 参考、转换参考、诊断信息和键盘快捷键。

## 安装

你可以从 [Releases](https://github.com/imadreamerboy/markitdown-gui/releases) 下载预编译版本，或从源码运行。

### Release 制品

- Windows：普通用户使用 `MarkItDown-Windows-Setup-<version>.exe` 安装器；需要便携版时使用 `MarkItDown-Windows-<version>.zip`。
- Linux：普通用户使用 `MarkItDown-Linux-<version>.AppImage` 单文件应用；需要便携目录时使用 `MarkItDown-Linux-<version>.zip`。
- macOS：使用 `MarkItDown-macOS-<version>.dmg`，并把应用拖入 Applications。

### 更新

- 打包版桌面应用从 GitHub Releases 更新。应用内更新检查会读取最新 release，显示简短说明，并优先选择当前系统对应的制品。
- Windows 和 Linux 打包版在首选制品为 `.zip` 时可启动应用内安装：下载、校验 SHA256（如 release 元数据可用）、准备外部 helper、关闭应用、替换应用目录、重启，并在替换失败时回滚。下一次启动后，帮助页诊断会显示上次更新结果和回滚备份目录。
- macOS 打包版会下载、校验并打开 `.dmg`，用户再手动拖入 Applications。
- Windows 安装器和 Linux AppImage 是额外的首次安装下载选项；应用内自更新会继续优先使用便携 `.zip` 制品。
- Release 会发布 `markitdown-release-manifest.json`，包含平台、大小和 SHA256 元数据。
- 源码 checkout 可以在帮助页运行 `Run source update`，也可以在终端运行：

```sh
python -m markitdowngui.utils.source_updater
```

源码更新器会先确认没有已跟踪的本地修改，然后执行 `git pull --ff-only`，并优先用 `uv`、否则用 `pip` 重新安装 editable 环境。完成后帮助页会显示重启操作。

### 支持包

帮助页会显示 OCR、打包更新、源码更新、更新检查和日志的简短就绪状态。复制诊断会包含该状态，并会隐藏用户主目录和明显 secret。支持包会导出诊断报告、已清理的设置和截断后的最近日志；原始最近文件路径、输出路径和明显 secret 会被排除或脱敏。

### 设置配置文件

设置页可以导入或导出便携 JSON 配置文件，覆盖 OCR、更新、转换、主题、语言和保存模式偏好。配置文件会包含提供方端点和环境变量名，但不会包含最近文件、最近输出、窗口状态或默认输出目录。

### 前置要求

- Python `3.10+`
- 推荐使用 `uv`

安装依赖：

```sh
uv sync
```

也可以：

```sh
pip install -e .[dev]
```

### OCR 说明

- OCR 是可选功能，默认关闭。
- `Azure + Tesseract` 在配置后优先使用 Azure Document Intelligence，然后使用 Tesseract 作为本地回退。
- `GLM-OCR` 是独立 OCR 提供方，适用于 PDF 和图片。可在设置中选择另一个已配置提供方作为回退。
- `HTTP OCR` 是给本地或自托管 OCR 服务使用的通用接入点。应用会发送带 `file` part 的 multipart `POST`，可附带 `model` 字段，并可从配置的环境变量读取 Bearer token。JSON 响应可使用 `markdown`、`text`、`result`、`content` 或 `output`；纯文本响应会直接使用。
- 保留 PDF 图片时会继续使用现有图片保留管线。`Azure + Tesseract` 会在该 helper 内运行 OCR；`GLM-OCR` 或 `HTTP OCR` 会先保留图片，再追加所选提供方的 OCR 文本。
- 设置页提供常见本地方案的一键 OCR 预设，以及打开文档或复制安全设置片段的提供方操作。**Validate OCR** 会在批处理开始前检查必填字段，**Test connection** 会在不上传用户文档的情况下检查提供方连通性。
- GLM-OCR 在设置页中提供三种模式：
  - `Official API`：最省事的零配置方式，从环境变量读取 `ZHIPU_API_KEY` 或 `GLMOCR_API_KEY`。
  - `Ollama`：最简单的本地路径。GUI 直接调用 Ollama 原生 `/api/generate` 端点，默认 `127.0.0.1:11434` 和 `glm-ocr:latest`。
  - `SDK Server (vLLM / SGLang)`：更强的自托管路径。把应用指向现有 `/glmocr/parse` 端点即可。默认值为 `http://127.0.0.1:5002/glmocr/parse`。
- 打包版桌面应用不会内置 GLM-OCR 自托管运行时栈；`torch`、`transformers`、`vLLM`、`SGLang` 和相关 server/runtime 组件仍然在应用外部部署。
- 项目依赖 `glmocr==0.1.4`，用于客户端侧 Official API 和 SDK Server 连接。Ollama 通过 HTTP 直接调用。
- 本地 OCR 需要系统安装 `tesseract`。可从 [Tesseract 官方项目](https://github.com/tesseract-ocr/tesseract) 安装。如果它不在 `PATH` 中，可以在设置页指定可执行文件路径。
- Azure OCR 需要在设置页填写 Azure Document Intelligence endpoint。
- Azure Document Intelligence 价格页面在本文写作时包含 [每月 500 页免费额度](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing)。
- API key 认证请设置 `AZURE_OCR_API_KEY`。
- 如果未设置 `AZURE_OCR_API_KEY`，Azure OCR 会回退到 `DefaultAzureCredential` 支持的 Azure 身份凭据。
- GLM-OCR 项目参考：[zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR)

### 推荐的本地托管方式

普通本地使用建议选择 Ollama。更强的自托管部署可使用 GLM-OCR SDK Server，并搭配 vLLM 或 SGLang。

### Ollama

1. 安装 Ollama。
2. 拉取模型：

```sh
ollama pull glm-ocr:latest
```

3. 如果服务没有自动启动，运行：

```sh
ollama serve
```

4. 在本应用中选择 `GLM-OCR` -> `Ollama`。
5. 除非你改过本地配置，否则保留默认值：
   - host: `127.0.0.1`
   - port: `11434`
   - model: `glm-ocr:latest`

### SDK Server

1. 为 GLM-OCR 创建单独的 Python 环境。
2. 在该环境中安装 `glmocr[selfhosted,server]`。
3. 为 `zai-org/GLM-OCR` 启动本地 `vLLM` 或 `SGLang` 后端。
4. 启动 SDK server：

```sh
python -m glmocr.server --config config.yaml
```

5. 在本应用中选择 `GLM-OCR` -> `SDK Server (vLLM / SGLang)`，并使用 `http://127.0.0.1:5002/glmocr/parse`。

最小 server 侧 `config.yaml`：

```yaml
pipeline:
  maas:
    enabled: false
  ocr_api:
    api_host: 127.0.0.1
    api_port: 8080
```

官方 GLM-OCR 文档包含完整的 Ollama、`vLLM` 和 `SGLang` 设置命令：

- [官方 Ollama 部署指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md)
- [Self-hosted SDK Server + Client 指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/self-host/README.md)
- [GLM-OCR README](https://github.com/zai-org/GLM-OCR)

### 网站 URL 说明

- 网站转换使用托管的 [Defuddle](https://defuddle.md/) API。
- 应用会把粘贴的 `http://` 或 `https://` URL 发送到 `https://defuddle.md/<url>`，并把返回的 Markdown 存到结果页。
- Defuddle 响应通常会在可用时包含 YAML frontmatter 元数据。
- 根据 [Defuddle Terms](https://defuddle.md/terms)，未认证请求截至 2026 年 3 月 14 日限制为每个 IP 每月 `1,000` 次。
- 请求直接从桌面应用发出，因此该免费额度限制适用于用户自己的网络 IP。
- 网站转换需要网络连接，并依赖外部 Defuddle 服务可用。

## 运行应用

```sh
uv run python -m markitdowngui.main
```

## 键盘快捷键

- `Ctrl+O`: 打开文件
- `Ctrl+S`: 保存输出
- `Ctrl+C`: 复制输出
- `Ctrl+R`: 重试失败转换
- `Ctrl+P`: 暂停/恢复
- `Ctrl+B`: 开始转换
- `Ctrl+L`: 清空队列
- `Ctrl+K`: 显示快捷键
- `Esc`: 取消转换

## 构建独立可执行文件

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

默认 spec 会在 `dist/MarkItDown/` 生成 `onedir` 应用。macOS 还会生成 `dist/MarkItDown.app`。
Release workflow 会把 Windows 和 Linux build 打包为平台专属 `.zip`，额外生成 Windows Inno Setup `.exe` 安装器和 Linux `.AppImage`，并把 macOS `.app` bundle 打包为拖入 Applications 的 `.dmg`。如果配置了 `MACOS_CODESIGN_IDENTITY`，macOS bundle 会使用该身份签名，否则使用 ad-hoc signing。每个 release 还会包含 `markitdown-release-manifest.json`，用于更新元数据和校验和。
该构建会刻意排除 GLM-OCR 自托管运行时栈；本地托管仍在 GUI 外部完成。

## 许可证

本项目采用 **MIT License**。

应用使用 `PySide6`/Qt，需遵守 Qt 的 LGPL/商业许可模式。此前的 `PySide6-Fluent-Widgets` 依赖已移除。

## 贡献

1. Fork 仓库并创建分支。
2. 安装开发依赖：

```sh
uv pip install -e .[dev]
```

3. 提交代码修改。
4. 运行测试：

```sh
uv run pytest -q
```

5. 提交 PR，并清楚说明变更内容。

## 鸣谢

- MarkItDown ([MIT License](https://opensource.org/licenses/MIT))
- PySide6 ([LGPLv3 License](https://www.gnu.org/licenses/lgpl-3.0.html))
- Qt Quick Controls ([Qt documentation](https://doc.qt.io/qt-6/qtquickcontrols-index.html))
