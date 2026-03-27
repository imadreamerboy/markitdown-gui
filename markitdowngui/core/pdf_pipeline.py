from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Sequence

from markitdowngui.core.markdown_assets import GeneratedAsset

PDF_PIPELINE_MARKITDOWN = "markitdown"
PDF_PIPELINE_PYMUPDF = "pymupdf"


@dataclass(frozen=True)
class _PageBlock:
    markdown: str
    top: float
    left: float
    bbox: tuple[float, float, float, float] | None = None


def normalize_pdf_pipeline(pipeline: str) -> str:
    normalized = (pipeline or PDF_PIPELINE_MARKITDOWN).strip().lower()
    if normalized not in {PDF_PIPELINE_MARKITDOWN, PDF_PIPELINE_PYMUPDF}:
        return PDF_PIPELINE_MARKITDOWN
    return normalized


def extract_pdf_markdown(file_path: str) -> str:
    pymupdf = _import_pymupdf()
    page_markdowns: list[str] = []
    document = pymupdf.open(file_path)
    try:
        for page in document:
            blocks = _extract_page_blocks(page, pymupdf)
            page_markdown = "\n\n".join(
                block.markdown.strip() for block in blocks if block.markdown.strip()
            ).strip()
            if page_markdown:
                page_markdowns.append(page_markdown)
    finally:
        document.close()

    return "\n\n".join(page_markdowns).strip()


def convert_pdf_with_local_ocr(
    file_path: str,
    *,
    render_scale: float,
    run_ocr: Callable[[Any], str],
) -> str:
    pymupdf = _import_pymupdf(
        "Local PDF OCR requires PyMuPDF to be installed."
    )
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Local OCR requires Pillow to be installed.") from exc

    matrix = pymupdf.Matrix(render_scale, render_scale)
    page_texts: list[str] = []
    document = pymupdf.open(file_path)
    try:
        for page in document:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image_stream = io.BytesIO(pixmap.tobytes("png"))
            with Image.open(image_stream) as image:
                page_text = run_ocr(image.convert("RGB")).strip()
            if page_text:
                page_texts.append(page_text)
    finally:
        document.close()

    return "\n\n".join(page_texts).strip()


def extract_pdf_image_assets(
    file_path: str,
    *,
    min_width: int,
    min_height: int,
    min_bytes: int,
    logger,
) -> tuple[GeneratedAsset, ...]:
    pymupdf = _import_pymupdf()

    assets: list[GeneratedAsset] = []
    document = pymupdf.open(file_path)
    temp_dir: str | None = None
    seen_hashes: dict[str, str] = {}
    stem = Path(file_path).stem

    try:
        for page_index, page in enumerate(document, start=1):
            page_images = list(page.get_images(full=True))
            logger.info(
                f"PDF image extraction: detected {len(page_images)} image object(s) on page {page_index} for {file_path}"
            )

            for image_number, image_info in enumerate(page_images, start=1):
                xref = int(image_info[0]) if image_info else 0
                try:
                    image_bytes, width, height, extension = _extract_image_bytes(
                        document,
                        page,
                        xref,
                        pymupdf,
                    )
                except Exception as exc:
                    logger.warning(
                        f"Skipping PDF image on page {page_index} for {file_path}: {_summarize_error(exc)}"
                    )
                    continue

                if width < min_width:
                    logger.info(
                        f"Filtered PDF image on page {page_index} for {file_path}: width {width}px < {min_width}px"
                    )
                    continue
                if height < min_height:
                    logger.info(
                        f"Filtered PDF image on page {page_index} for {file_path}: height {height}px < {min_height}px"
                    )
                    continue
                if len(image_bytes) < min_bytes:
                    logger.info(
                        f"Filtered PDF image on page {page_index} for {file_path}: size {len(image_bytes)} bytes < {min_bytes} bytes"
                    )
                    continue

                sha256 = hashlib.sha256(image_bytes).hexdigest()
                if sha256 in seen_hashes:
                    temp_path = seen_hashes[sha256]
                    logger.info(
                        f"Deduplicated PDF image on page {page_index} for {file_path}: {sha256}"
                    )
                    assets.append(
                        GeneratedAsset(
                            filename=Path(temp_path).name,
                            temp_path=temp_path,
                            page_number=page_index,
                            image_number=image_number,
                            sha256=sha256,
                            width=width,
                            height=height,
                            size_bytes=len(image_bytes),
                        )
                    )
                    continue

                if temp_dir is None:
                    temp_dir = tempfile.mkdtemp(
                        prefix=f"markitdowngui_pdf_{Path(stem).stem}_"
                    )
                    logger.info(
                        f"Created temporary PDF assets directory for {file_path}: {temp_dir}"
                    )

                filename = f"page_{page_index:03d}_img_{image_number:03d}{extension}"
                temp_path = os.path.join(temp_dir, filename)
                with open(temp_path, "wb") as temp_file:
                    temp_file.write(image_bytes)
                seen_hashes[sha256] = temp_path
                assets.append(
                    GeneratedAsset(
                        filename=filename,
                        temp_path=temp_path,
                        page_number=page_index,
                        image_number=image_number,
                        sha256=sha256,
                        width=width,
                        height=height,
                        size_bytes=len(image_bytes),
                    )
                )
    finally:
        document.close()

    return tuple(assets)


def _extract_page_blocks(page, pymupdf) -> list[_PageBlock]:
    table_blocks = _extract_table_blocks(page, pymupdf)
    table_rects = [
        pymupdf.Rect(block.bbox)
        for block in table_blocks
        if block.bbox is not None
    ]
    text_blocks = _extract_text_blocks(page, table_rects, pymupdf)
    return sorted(
        [*table_blocks, *text_blocks],
        key=lambda block: (block.top, block.left),
    )


def _extract_table_blocks(page, pymupdf) -> list[_PageBlock]:
    if not hasattr(page, "find_tables"):
        return []

    try:
        table_finder = page.find_tables()
    except Exception:
        return []

    raw_tables = getattr(table_finder, "tables", table_finder)
    if not isinstance(raw_tables, Sequence):
        return []

    blocks: list[_PageBlock] = []
    for table in raw_tables:
        rows = _extract_table_rows(table)
        markdown = _to_markdown_table(rows)
        if not markdown:
            continue

        bbox = _get_bbox(table)
        rect = pymupdf.Rect(bbox) if bbox else pymupdf.Rect(0, 0, 0, 0)
        blocks.append(
            _PageBlock(
                markdown=markdown,
                top=float(rect.y0),
                left=float(rect.x0),
                bbox=(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
            )
        )
    return blocks


def _extract_text_blocks(page, table_rects, pymupdf) -> list[_PageBlock]:
    page_dict = page.get_text("dict", sort=True)
    blocks: list[_PageBlock] = []
    for block in page_dict.get("blocks", []):
        bbox = block.get("bbox")
        rect = pymupdf.Rect(bbox) if bbox else pymupdf.Rect(0, 0, 0, 0)
        if any(rect.intersects(table_rect) for table_rect in table_rects):
            continue

        text = _block_to_text(block)
        if not text:
            continue

        blocks.append(
            _PageBlock(
                markdown=text,
                top=float(rect.y0),
                left=float(rect.x0),
                bbox=(float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
            )
        )
    return blocks


def _extract_table_rows(table) -> list[list[str]]:
    if hasattr(table, "extract"):
        extracted = table.extract()
        if isinstance(extracted, list):
            return [
                ["" if cell is None else str(cell) for cell in row]
                for row in extracted
                if isinstance(row, list)
            ]
    return []

def _get_bbox(item) -> tuple[float, float, float, float] | None:
    bbox = getattr(item, "bbox", None)
    if bbox is None:
        bbox = getattr(item, "rect", None)
    if bbox is None:
        return None
    return tuple(float(value) for value in bbox)


def _block_to_text(block: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        line_text = "".join(str(span.get("text", "")) for span in spans).strip()
        if line_text:
            lines.append(line_text)
    return "\n".join(lines).strip()


def _to_markdown_table(table: list[list[str]]) -> str:
    if not table:
        return ""

    normalized = [[cell if cell is not None else "" for cell in row] for row in table]
    normalized = [row for row in normalized if any(cell.strip() for cell in row)]
    if not normalized:
        return ""

    col_count = max(len(row) for row in normalized)
    padded = [row + [""] * (col_count - len(row)) for row in normalized]
    col_widths = [
        max(len(str(row[col_index])) for row in padded)
        for col_index in range(col_count)
    ]

    def format_row(row: list[str]) -> str:
        return (
            "|"
            + "|".join(
                str(cell).ljust(col_widths[index]) for index, cell in enumerate(row)
            )
            + "|"
        )

    header, *rows = padded
    lines = [format_row(header)]
    lines.append("|" + "|".join("-" * width for width in col_widths) + "|")
    for row in rows:
        lines.append(format_row(row))
    return "\n".join(lines)


def _extract_image_bytes(document, page, xref: int, pymupdf) -> tuple[bytes, int, int, str]:
    image_data = document.extract_image(xref)
    if image_data:
        image_bytes = bytes(image_data.get("image", b""))
        width = int(image_data.get("width") or 0)
        height = int(image_data.get("height") or 0)
        extension = _normalize_extension(str(image_data.get("ext") or "png"))
        if image_bytes and width > 0 and height > 0:
            return image_bytes, width, height, extension

    if hasattr(page, "get_image_rects"):
        rects = page.get_image_rects(xref)
        if rects:
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(1, 1),
                clip=rects[0],
                alpha=False,
            )
            return pixmap.tobytes("png"), pixmap.width, pixmap.height, ".png"

    raise RuntimeError(f"Could not extract image xref {xref}")


def _normalize_extension(ext: str) -> str:
    normalized = (ext or "png").strip().lower().lstrip(".")
    if normalized == "jpeg":
        normalized = "jpg"
    if not normalized:
        normalized = "png"
    return f".{normalized}"


def _import_pymupdf(error_message: str = "PyMuPDF is required for PDF processing."):
    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError as exc:
            raise RuntimeError(error_message) from exc
    return pymupdf


def _summarize_error(error: Exception) -> str:
    message = str(error).strip()
    return message or type(error).__name__
