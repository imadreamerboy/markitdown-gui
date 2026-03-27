from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Sequence

from markitdowngui.core.markdown_assets import (
    GeneratedAsset,
    build_asset_placeholder,
    build_inline_image_markdown,
)

PDF_PIPELINE_MARKITDOWN = "markitdown"
PDF_PIPELINE_PYMUPDF = "pymupdf"


@dataclass(frozen=True)
class PdfTextBlock:
    markdown: str
    bbox: tuple[float, float, float, float]
    page_number: int
    order_key: tuple[float, float]


@dataclass(frozen=True)
class PdfImageBlock:
    asset: GeneratedAsset
    bbox: tuple[float, float, float, float] | None
    page_number: int
    order_key: tuple[float, float]


@dataclass(frozen=True)
class PdfPageLayout:
    page_number: int
    blocks: tuple[PdfTextBlock, ...]
    inline_images_by_block: tuple[tuple[int, tuple[PdfImageBlock, ...]], ...]
    trailing_images: tuple[PdfImageBlock, ...]


def normalize_pdf_pipeline(pipeline: str) -> str:
    normalized = (pipeline or PDF_PIPELINE_MARKITDOWN).strip().lower()
    if normalized not in {PDF_PIPELINE_MARKITDOWN, PDF_PIPELINE_PYMUPDF}:
        return PDF_PIPELINE_MARKITDOWN
    return normalized


def extract_pdf_markdown(file_path: str) -> str:
    page_layouts, _assets = _extract_pdf_page_layouts(
        file_path,
        include_images=False,
        min_width=0,
        min_height=0,
        min_bytes=0,
        logger=None,
    )
    return _render_pdf_page_layouts(page_layouts)


def extract_pdf_markdown_with_inline_assets(
    file_path: str,
    *,
    min_width: int,
    min_height: int,
    min_bytes: int,
    logger,
) -> tuple[str, tuple[GeneratedAsset, ...]]:
    page_layouts, assets = _extract_pdf_page_layouts(
        file_path,
        include_images=True,
        min_width=min_width,
        min_height=min_height,
        min_bytes=min_bytes,
        logger=logger,
    )
    return _render_pdf_page_layouts(page_layouts), assets


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
    _page_layouts, assets = _extract_pdf_page_layouts(
        file_path,
        include_images=True,
        min_width=min_width,
        min_height=min_height,
        min_bytes=min_bytes,
        logger=logger,
    )
    return assets


def _extract_pdf_page_layouts(
    file_path: str,
    *,
    include_images: bool,
    min_width: int,
    min_height: int,
    min_bytes: int,
    logger,
) -> tuple[tuple[PdfPageLayout, ...], tuple[GeneratedAsset, ...]]:
    pymupdf = _import_pymupdf()
    document = pymupdf.open(file_path)
    assets: list[GeneratedAsset] = []
    seen_hashes: dict[str, str] = {}
    temp_dir: str | None = None
    page_layouts: list[PdfPageLayout] = []

    try:
        for page_index, page in enumerate(document, start=1):
            text_blocks = _extract_page_text_blocks(page, page_index, pymupdf)
            image_blocks: list[PdfImageBlock] = []
            if include_images:
                page_image_blocks, temp_dir = _extract_page_image_blocks(
                    file_path,
                    document,
                    page,
                    page_index,
                    min_width=min_width,
                    min_height=min_height,
                    min_bytes=min_bytes,
                    logger=logger,
                    seen_hashes=seen_hashes,
                    temp_dir=temp_dir,
                    pymupdf=pymupdf,
                )
                image_blocks.extend(page_image_blocks)
                assets.extend(block.asset for block in page_image_blocks)

            inline_map: dict[int, list[PdfImageBlock]] = {}
            trailing_images: list[PdfImageBlock] = []
            for image_block in image_blocks:
                anchor_index = _find_nearest_preceding_text_block_index(
                    text_blocks,
                    image_block,
                )
                if anchor_index is None:
                    trailing_images.append(image_block)
                else:
                    inline_map.setdefault(anchor_index, []).append(image_block)

            inline_images = tuple(
                (index, tuple(blocks))
                for index, blocks in sorted(inline_map.items())
            )
            page_layouts.append(
                PdfPageLayout(
                    page_number=page_index,
                    blocks=tuple(text_blocks),
                    inline_images_by_block=inline_images,
                    trailing_images=tuple(trailing_images),
                )
            )
    finally:
        document.close()

    return tuple(page_layouts), tuple(assets)


def _extract_page_text_blocks(page, page_number: int, pymupdf) -> list[PdfTextBlock]:
    table_blocks = _extract_table_blocks(page, page_number, pymupdf)
    table_rects = [pymupdf.Rect(block.bbox) for block in table_blocks]
    text_blocks = _extract_text_blocks(page, page_number, table_rects, pymupdf)
    return sorted(
        [*table_blocks, *text_blocks],
        key=lambda block: block.order_key,
    )


def _extract_table_blocks(page, page_number: int, pymupdf) -> list[PdfTextBlock]:
    if not hasattr(page, "find_tables"):
        return []

    try:
        table_finder = page.find_tables()
    except Exception:
        return []

    raw_tables = getattr(table_finder, "tables", table_finder)
    if not isinstance(raw_tables, Sequence):
        return []

    blocks: list[PdfTextBlock] = []
    for table in raw_tables:
        rows = _extract_table_rows(table)
        markdown = _to_markdown_table(rows)
        if not markdown:
            continue

        bbox = _get_bbox(table)
        rect = pymupdf.Rect(bbox) if bbox else pymupdf.Rect(0, 0, 0, 0)
        blocks.append(
            PdfTextBlock(
                markdown=markdown,
                bbox=_rect_to_bbox(rect),
                page_number=page_number,
                order_key=(float(rect.y0), float(rect.x0)),
            )
        )
    return blocks


def _extract_text_blocks(
    page,
    page_number: int,
    table_rects,
    pymupdf,
) -> list[PdfTextBlock]:
    page_dict = page.get_text("dict", sort=True)
    blocks: list[PdfTextBlock] = []
    for block in page_dict.get("blocks", []):
        bbox = block.get("bbox")
        rect = pymupdf.Rect(bbox) if bbox else pymupdf.Rect(0, 0, 0, 0)
        if any(rect.intersects(table_rect) for table_rect in table_rects):
            continue

        text = _block_to_text(block)
        if not text:
            continue

        blocks.append(
            PdfTextBlock(
                markdown=text,
                bbox=_rect_to_bbox(rect),
                page_number=page_number,
                order_key=(float(rect.y0), float(rect.x0)),
            )
        )
    return blocks


def _extract_page_image_blocks(
    file_path: str,
    document,
    page,
    page_index: int,
    *,
    min_width: int,
    min_height: int,
    min_bytes: int,
    logger,
    seen_hashes: dict[str, str],
    temp_dir: str | None,
    pymupdf,
) -> tuple[list[PdfImageBlock], str | None]:
    page_images = list(page.get_images(full=True))
    if logger is not None:
        logger.info(
            f"PDF image extraction: detected {len(page_images)} image object(s) on page {page_index} for {file_path}"
        )

    image_blocks: list[PdfImageBlock] = []
    for image_number, image_info in enumerate(page_images, start=1):
        xref = int(image_info[0]) if image_info else 0
        rects = _get_image_rects(page, xref)
        primary_rect = rects[0] if rects else None
        try:
            image_bytes, width, height, extension = _extract_image_bytes(
                document,
                page,
                xref,
                primary_rect,
                pymupdf,
            )
        except Exception as exc:
            if logger is not None:
                logger.warning(
                    f"Skipping PDF image on page {page_index} for {file_path}: {_summarize_error(exc)}"
                )
            continue

        if width < min_width:
            if logger is not None:
                logger.info(
                    f"Filtered PDF image on page {page_index} for {file_path}: width {width}px < {min_width}px"
                )
            continue
        if height < min_height:
            if logger is not None:
                logger.info(
                    f"Filtered PDF image on page {page_index} for {file_path}: height {height}px < {min_height}px"
                )
            continue
        if len(image_bytes) < min_bytes:
            if logger is not None:
                logger.info(
                    f"Filtered PDF image on page {page_index} for {file_path}: size {len(image_bytes)} bytes < {min_bytes} bytes"
                )
            continue

        sha256 = hashlib.sha256(image_bytes).hexdigest()
        if sha256 in seen_hashes:
            temp_path = seen_hashes[sha256]
            if logger is not None:
                logger.info(
                    f"Deduplicated PDF image on page {page_index} for {file_path}: {sha256}"
                )
        else:
            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(
                    prefix=f"markitdowngui_pdf_{Path(file_path).stem}_"
                )
                if logger is not None:
                    logger.info(
                        f"Created temporary PDF assets directory for {file_path}: {temp_dir}"
                    )
            filename = f"page_{page_index:03d}_img_{image_number:03d}{extension}"
            temp_path = os.path.join(temp_dir, filename)
            with open(temp_path, "wb") as temp_file:
                temp_file.write(image_bytes)
            seen_hashes[sha256] = temp_path

        asset = GeneratedAsset(
            filename=Path(temp_path).name,
            temp_path=temp_path,
            page_number=page_index,
            image_number=image_number,
            sha256=sha256,
            width=width,
            height=height,
            size_bytes=len(image_bytes),
            bbox=_rect_to_bbox(primary_rect) if primary_rect is not None else None,
        )
        bbox = asset.bbox
        order_key = (
            float(bbox[1]) if bbox is not None else float("inf"),
            float(bbox[0]) if bbox is not None else float("inf"),
        )
        image_blocks.append(
            PdfImageBlock(
                asset=asset,
                bbox=bbox,
                page_number=page_index,
                order_key=order_key,
            )
        )

    return image_blocks, temp_dir


def _find_nearest_preceding_text_block_index(
    text_blocks: Sequence[PdfTextBlock],
    image_block: PdfImageBlock,
) -> int | None:
    if image_block.bbox is None:
        return None

    image_left, image_top, image_right, _image_bottom = image_block.bbox
    image_center_x = (image_left + image_right) / 2.0
    best_index: int | None = None
    best_distance: float | None = None
    best_horizontal_distance: float | None = None

    for index, block in enumerate(text_blocks):
        _left, _top, right, bottom = block.bbox
        if bottom > image_top:
            continue

        vertical_distance = image_top - bottom
        horizontal_distance = abs(((block.bbox[0] + right) / 2.0) - image_center_x)

        if best_index is None:
            best_index = index
            best_distance = vertical_distance
            best_horizontal_distance = horizontal_distance
            continue

        if vertical_distance < best_distance:
            best_index = index
            best_distance = vertical_distance
            best_horizontal_distance = horizontal_distance
            continue

        if (
            vertical_distance == best_distance
            and horizontal_distance < best_horizontal_distance
        ):
            best_index = index
            best_horizontal_distance = horizontal_distance

    return best_index


def _render_pdf_page_layouts(page_layouts: Sequence[PdfPageLayout]) -> str:
    rendered_pages: list[str] = []
    for page_layout in page_layouts:
        parts: list[str] = []
        inline_map = {
            index: list(blocks)
            for index, blocks in page_layout.inline_images_by_block
        }
        for index, block in enumerate(page_layout.blocks):
            block_markdown = block.markdown.strip()
            if block_markdown:
                parts.append(block_markdown)
            for image_block in inline_map.get(index, []):
                parts.append(_render_image_block(image_block))
        for image_block in page_layout.trailing_images:
            parts.append(_render_image_block(image_block))

        page_markdown = "\n\n".join(part for part in parts if part.strip()).strip()
        if page_markdown:
            rendered_pages.append(page_markdown)

    return "\n\n".join(rendered_pages).strip()


def _render_image_block(image_block: PdfImageBlock) -> str:
    asset = image_block.asset
    placeholder = build_asset_placeholder(asset.sha256) or asset.filename
    alt_text = f"Page {asset.page_number or '?'} image {asset.image_number or '?'}"
    return build_inline_image_markdown(placeholder, alt_text)


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


def _extract_image_bytes(
    document,
    page,
    xref: int,
    primary_rect,
    pymupdf,
) -> tuple[bytes, int, int, str]:
    image_data = document.extract_image(xref)
    if image_data:
        image_bytes = bytes(image_data.get("image", b""))
        width = int(image_data.get("width") or 0)
        height = int(image_data.get("height") or 0)
        extension = _normalize_extension(str(image_data.get("ext") or "png"))
        if image_bytes and width > 0 and height > 0:
            return image_bytes, width, height, extension

    if primary_rect is not None:
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(1, 1),
            clip=primary_rect,
            alpha=False,
        )
        return pixmap.tobytes("png"), pixmap.width, pixmap.height, ".png"

    raise RuntimeError(f"Could not extract image xref {xref}")


def _get_bbox(item) -> tuple[float, float, float, float] | None:
    bbox = getattr(item, "bbox", None)
    if bbox is None:
        bbox = getattr(item, "rect", None)
    if bbox is None:
        return None
    return tuple(float(value) for value in bbox)


def _get_image_rects(page, xref: int) -> list[Any]:
    if not hasattr(page, "get_image_rects"):
        return []
    try:
        return list(page.get_image_rects(xref))
    except Exception:
        return []


def _rect_to_bbox(rect) -> tuple[float, float, float, float]:
    return (float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1))


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
