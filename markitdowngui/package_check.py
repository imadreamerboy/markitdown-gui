"""Internal, offline functional checks for the actual packaged executable."""

from __future__ import annotations

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Thread
import traceback

from markitdowngui import __version__


SENTINEL = "MARKITDOWNPACKAGESENTINEL"
BACKENDS = ("anydoc", "pdf_inspector", "pdfium", "glmocr")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _create_pdf(path: Path) -> None:
    import pymupdf

    with pymupdf.open() as document:
        page = document.new_page(width=612, height=792)
        lines = [SENTINEL, "Local native document extraction and rendering check."] * 8
        page.insert_text((72, 72), "\n".join(lines), fontsize=11)
        document.save(path)


def _check_anydoc(path: Path) -> dict:
    import anydoc
    import anydoc._anydoc as native

    markdown = anydoc.to_markdown(str(path), ocr="reject")
    _require(SENTINEL in markdown, "Anydoc did not extract the PDF sentinel.")
    return {"native_module": native.__file__, "sentinel_extracted": True}


def _check_pdf_inspector(path: Path) -> dict:
    import pdf_inspector
    import pdf_inspector.pdf_inspector as native

    result = pdf_inspector.process_pdf(str(path))
    _require(SENTINEL in result.markdown, "PDF Inspector did not extract the PDF sentinel.")
    _require(result.pdf_type == "text_based", f"Unexpected PDF type: {result.pdf_type}")
    return {
        "native_module": native.__file__,
        "pdf_type": result.pdf_type,
        "confidence": result.confidence,
        "sentinel_extracted": True,
    }


def _check_pdfium(path: Path) -> dict:
    import pypdfium2
    from pypdfium2_raw import bindings

    with pypdfium2.PdfDocument(str(path)) as document:
        _require(len(document) == 1, "PDFium did not read the one-page fixture.")
        page = document[0]
        try:
            bitmap = page.render(scale=0.5)
            try:
                size = [bitmap.width, bitmap.height]
                _require(size == [306, 396], f"Unexpected PDFium bitmap size: {size}")
            finally:
                bitmap.close()
        finally:
            page.close()
    return {"native_library": str(bindings._libs["pdfium"]._name), "bitmap_size": size}


def _check_glmocr(path: Path) -> dict:
    import glmocr.api
    import pymupdf._mupdf as native
    from PIL import Image

    from markitdowngui.core.conversion import ConversionOptions, convert_file_with_details

    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append((self.path, payload))
            body = json.dumps({
                "md_results": SENTINEL + "\n\n![](page=0,bbox=[0, 0, 306, 396])",
                "layout_details": [[{"label": "image", "bbox_2d": [0, 0, 306, 396]}]],
                "data_info": {"pages": [{"width": 612, "height": 792}]},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    old_proxy = {key: os.environ.get(key) for key in ("NO_PROXY", "no_proxy")}
    # The SDK uses requests' environment settings. Keep its loopback request local.
    os.environ.update(NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
    thread.start()
    try:
        outcome = convert_file_with_details(str(path), ConversionOptions(
            ocr_enabled=True,
            ocr_provider="glmocr",
            glmocr_mode="sdk_server",
            glmocr_sdk_server_url=f"http://127.0.0.1:{server.server_port}/glmocr/parse",
            ocr_fallback_enabled=False,
        ))
        _require(outcome.backend == "glmocr", f"Unexpected OCR backend: {outcome.backend}")
        prefix = SENTINEL + "\n\n![Image 0-0](data:image/png;base64,"
        _require(outcome.markdown.startswith(prefix), "GLM-OCR did not embed its PDF crop.")
        encoded = outcome.markdown[len(prefix):].removesuffix(")")
        with Image.open(BytesIO(base64.b64decode(encoded, validate=True))) as image:
            crop_size = list(image.size)
            _require(crop_size == [850, 1100], f"Unexpected GLM PDF crop: {crop_size}")
        _require(len(requests) == 1, f"Unexpected GLM HTTP request count: {len(requests)}")
        endpoint, payload = requests[0]
        _require(endpoint == "/glmocr/parse", f"Unexpected GLM endpoint: {endpoint}")
        _require(payload["model"] == "glm-ocr", "GLM model was not glm-ocr.")
        mime, encoded_pdf = payload["file"].split(",", 1)
        _require(mime == "data:application/pdf;base64", f"Unexpected GLM MIME: {mime}")
        _require(base64.b64decode(encoded_pdf, validate=True) == path.read_bytes(),
                 "GLM request PDF differs from the local fixture.")
        return {
            "sdk_module": glmocr.api.__file__,
            "native_module": native.__file__,
            "crop_size": crop_size,
            "localhost_requests": len(requests),
            "pdf_payload_verified": True,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        for key, value in old_proxy.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_package_checks(report_path: Path) -> int:
    """Write a receipt even on backend failure; never rely on a GUI app's stdout."""
    report = {
        "schema_version": 1,
        "status": "failed",
        "app_version": __version__,
        "executable": sys.executable,
        "frozen": bool(getattr(sys, "frozen", False)),
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "checks": {},
    }
    current = "fixture"
    try:
        with tempfile.TemporaryDirectory(prefix="markitdown-package-check-") as directory:
            source = Path(directory) / "native.pdf"
            _create_pdf(source)
            for current, check in zip(BACKENDS, (
                _check_anydoc, _check_pdf_inspector, _check_pdfium, _check_glmocr,
            )):
                report["checks"][current] = {"status": "passed", **check(source)}
            _require(list(Path(directory).iterdir()) == [source],
                     "A backend wrote unexpected files beside the fixture.")
        report["status"] = "passed"
    except Exception as error:
        report["checks"][current] = {"status": "failed", "error": str(error)}
        report["traceback"] = traceback.format_exc()
        if sys.stderr is not None:
            sys.stderr.write(report["traceback"])

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except OSError:
        if sys.stderr is not None:
            sys.stderr.write(traceback.format_exc())
        return 1
    return 0 if report["status"] == "passed" else 1
