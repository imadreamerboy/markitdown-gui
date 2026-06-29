# MarkItDown GUI 封装

这是一个基于 `PySide6` 和官方 Qt Quick Controls/QML 的 `MarkItDown` 桌面 GUI。
目标是用现代、接近原生体验的桌面界面完成多文件到 Markdown 的转换。

![当前界面截图](image.png)

## 功能

- 基于队列的文件流程，支持拖放添加文件。
- 粘贴网页 URL，并通过托管的 Defuddle API 转换文章内容。
- 批量转换，支持开始、暂停/恢复、取消和进度反馈。
- 结果页支持按文件查看转换结果。
- 预览模式支持渲染视图和原始 Markdown 视图。
- 保存模式支持合并为单文件或分别保存多个文件。
- 常用操作：复制 Markdown、保存输出、返回队列、重新开始。
- 可选 OCR，支持扫描版 PDF 和图片文件，可在 `Azure/Tesseract OCR` 与 `GLM-OCR` 两种提供方之间切换。
- 设置项包括输出目录、保存模式、保存到源文件夹、批处理大小、OCR 和主题模式（浅色/深色/跟随系统）。
- 帮助页包含项目链接、OCR 参考、转换参考和键盘快捷键。

## 安装

你可以从 [Releases](https://github.com/imadreamerboy/markitdown-gui/releases) 下载预编译版本，或从源码运行。

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

- OCR 为可选功能，默认关闭。
- `Azure/Tesseract OCR` 会在配置后优先使用 Azure Document Intelligence，然后回退到本地 Tesseract。
- `GLM-OCR` 是新的 OCR 提供方，适用于 PDF 和图片。它会先运行，若设置中启用了回退，则失败后会回退到 Azure/Tesseract OCR。
- GLM-OCR 在设置页中提供三种模式：
  - `Official API`：最省事的零配置方式，从环境变量读取 `ZHIPU_API_KEY` 或 `GLMOCR_API_KEY`。
  - `Ollama`：最简单的本地路径。GUI 会直接调用 Ollama 原生 `/api/generate` 接口，默认使用 `127.0.0.1:11434` 和 `glm-ocr:latest`。
  - `SDK Server (vLLM / SGLang)`：更强的自托管路径。把应用指向现成的 `/glmocr/parse` 端点即可。默认值为 `http://127.0.0.1:5002/glmocr/parse`。
- 打包后的桌面应用并不内置 GLM-OCR 的 self-hosted 运行时栈；`torch`、`transformers`、`vLLM`、`SGLang` 等仍然需要在应用外部单独部署。
- 项目默认依赖 `glmocr==0.1.4`，用于客户端侧的 Official API 和 SDK Server 连接。Ollama 通过 HTTP 直接调用。
- 本地 OCR 需要系统已安装 `tesseract`。可从 [Tesseract 官方项目](https://github.com/tesseract-ocr/tesseract) 安装。如果它不在 `PATH` 中，可以在设置页里指定可执行文件路径。
- Azure OCR 需要在设置页里填写 Azure Document Intelligence 终结点。
- Azure Document Intelligence 定价页面目前标注有 [每月 500 页免费额度](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing)。
- 若使用 API Key 认证，请设置 `AZURE_OCR_API_KEY` 环境变量。
- 如果未设置 `AZURE_OCR_API_KEY`，Azure OCR 会回退到 `DefaultAzureCredential` 支持的 Azure 身份凭据。
- GLM-OCR 项目参考： [zai-org/GLM-OCR](https://github.com/zai-org/GLM-OCR)

### 推荐的本地托管方式

对普通本地使用来说，最简单的路径是 Ollama。对更强的自托管部署，再使用 GLM-OCR SDK Server + vLLM / SGLang。

### Ollama

1. 安装 Ollama。
2. 拉取模型：

```sh
ollama pull glm-ocr:latest
```

3. 如果服务没有自动启动，就运行：

```sh
ollama serve
```

4. 在本应用里选择 `GLM-OCR` -> `Ollama`。
5. 除非你改过本地配置，否则保持默认值即可：
   - host：`127.0.0.1`
   - port：`11434`
   - model：`glm-ocr:latest`

### SDK Server

1. 为 GLM-OCR 创建单独的 Python 环境。
2. 在该环境中安装 `glmocr[selfhosted,server]`。
3. 为 `zai-org/GLM-OCR` 启动本地 `vLLM` 或 `SGLang` 后端。
4. 启动 SDK Server：

```sh
python -m glmocr.server --config config.yaml
```

5. 在本应用里选择 `GLM-OCR` -> `SDK Server (vLLM / SGLang)`，并使用 `http://127.0.0.1:5002/glmocr/parse`。

最小 server 侧 `config.yaml`：

```yaml
pipeline:
  maas:
    enabled: false
  ocr_api:
    api_host: 127.0.0.1
    api_port: 8080
```

完整的 Ollama、`vLLM` / `SGLang` 启动方式请参考官方文档：

- [官方 Ollama 部署指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/ollama-deploy/README.md)
- [Self-hosted SDK Server + Client 指南](https://github.com/zai-org/GLM-OCR/blob/main/examples/self-host/README.md)
- [GLM-OCR README](https://github.com/zai-org/GLM-OCR)

## 运行应用

```sh
uv run python -m markitdowngui.main
```

## 键盘快捷键

- `Ctrl+O`: 打开文件
- `Ctrl+S`: 保存输出
- `Ctrl+C`: 复制输出
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

默认会生成 `onedir` 结构，输出目录为 `dist/MarkItDown/`。
发布工作流会将该目录打包为按平台区分的 `.zip` 制品。
该构建会刻意排除 GLM-OCR 的 self-hosted 运行时栈；本地托管仍然在 GUI 外部完成。

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

- MarkItDown ([MIT 许可证](https://opensource.org/licenses/MIT))
- PySide6 ([LGPLv3 许可证](https://www.gnu.org/licenses/lgpl-3.0.html))
- Qt Quick Controls ([Qt 文档](https://doc.qt.io/qt-6/qtquickcontrols-index.html))
