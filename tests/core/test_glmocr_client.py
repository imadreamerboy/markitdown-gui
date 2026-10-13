"""Exercise the installed GLM-OCR client with a local HTTP endpoint."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from threading import Thread

import pymupdf
from PIL import Image
import pytest

from markitdowngui.core import conversion


@pytest.fixture
def glmocr_server():
    state = {"requests": [], "status": 200, "response": {"md_results": "OCR text"}}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            state["requests"].append(
                (self.path, self.headers["Authorization"], json.loads(body))
            )
            response = json.dumps(state["response"]).encode()
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}/glmocr/parse"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def source_pdf(tmp_path):
    source = tmp_path / "local.pdf"
    with pymupdf.open() as document:
        page = document.new_page(width=72, height=72)
        page.insert_text((10, 25), "SDK fixture", fontsize=6)
        document.save(source)
    return source


def client_options(monkeypatch, server, mode):
    monkeypatch.delenv("GLMOCR_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.setenv("GLMOCR_API_URL", server["url"])
    if mode == conversion.GLMOCR_MODE_MAAS:
        monkeypatch.setenv("ZHIPU_API_KEY", "local-test-key")
    return conversion.ConversionOptions(
        ocr_enabled=True,
        ocr_provider=conversion.OCR_PROVIDER_GLMOCR,
        glmocr_mode=mode,
        glmocr_sdk_server_url=server["url"],
        ocr_fallback_enabled=False,
    )


@pytest.mark.parametrize(
    "mode", [conversion.GLMOCR_MODE_MAAS, conversion.GLMOCR_MODE_SDK_SERVER]
)
def test_real_glmocr_client_sends_pdf_and_embeds_returned_crops(
    monkeypatch, glmocr_server, source_pdf, mode
):
    options = client_options(monkeypatch, glmocr_server, mode)
    glmocr_server["response"] = {
        "md_results": "OCR text\n\n![](page=0,bbox=[0, 0, 100, 100])",
        "layout_details": [[{"label": "image", "bbox_2d": [0, 0, 100, 100]}]],
        "data_info": {"pages": [{"width": 200, "height": 200}]},
    }

    outcome = conversion.convert_file_with_details(str(source_pdf), options)

    assert outcome.backend == conversion.BACKEND_GLMOCR
    assert outcome.markdown.startswith("OCR text\n\n![Image 0-0](data:image/png;base64,")
    assert "imgs/" not in outcome.markdown
    encoded = outcome.markdown.split("base64,", 1)[1].removesuffix(")")
    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        assert image.size == (100, 100)
    assert len(glmocr_server["requests"]) == 1
    path, authorization, payload = glmocr_server["requests"][0]
    assert path == "/glmocr/parse"
    expected_key = (
        "local-test-key"
        if mode == conversion.GLMOCR_MODE_MAAS
        else conversion.GLMOCR_SDK_SERVER_API_KEY
    )
    assert authorization == f"Bearer {expected_key}"
    assert payload["model"] == "glm-ocr"
    prefix, encoded_pdf = payload["file"].split(",", 1)
    assert prefix == "data:application/pdf;base64"
    assert base64.b64decode(encoded_pdf) == source_pdf.read_bytes()
    assert list(source_pdf.parent.iterdir()) == [source_pdf]


def test_real_glmocr_client_preserves_http_failure(monkeypatch, glmocr_server, source_pdf):
    options = client_options(monkeypatch, glmocr_server, conversion.GLMOCR_MODE_SDK_SERVER)
    glmocr_server["status"] = 401
    glmocr_server["response"] = {"error": "local fixture rejected key"}

    with pytest.raises(RuntimeError, match="status 401.*local fixture rejected key"):
        conversion.convert_file_with_details(str(source_pdf), options)

    assert len(glmocr_server["requests"]) == 1


def test_real_glmocr_client_plaintext_preserves_external_images(
    monkeypatch, glmocr_server, source_pdf
):
    options = client_options(monkeypatch, glmocr_server, conversion.GLMOCR_MODE_SDK_SERVER)
    markdown = "OCR text\n\n![Source image](https://example.test/image.png)"
    glmocr_server["response"]["md_results"] = markdown

    outcome = conversion.convert_file_with_details(str(source_pdf), options)

    assert outcome.backend == conversion.BACKEND_GLMOCR
    assert outcome.markdown == markdown


@pytest.mark.parametrize(
    "image_reference",
    [
        "![Image 0-0](imgs/cropped_page0_idx0.jpg)",
        "![](page=0,bbox=[0, 0, 100, 100])",
    ],
)
def test_real_glmocr_client_rejects_missing_image_data(
    monkeypatch, glmocr_server, source_pdf, image_reference
):
    options = client_options(monkeypatch, glmocr_server, conversion.GLMOCR_MODE_SDK_SERVER)
    glmocr_server["response"]["md_results"] = image_reference

    with pytest.raises(RuntimeError, match="image reference without its image data"):
        conversion.convert_file_with_details(str(source_pdf), options)
