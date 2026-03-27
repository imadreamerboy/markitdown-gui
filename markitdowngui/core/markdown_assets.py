from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from typing import Sequence

ASSET_LAYOUT_SEPARATE = "separate"
ASSET_LAYOUT_SINGLE = "single"


@dataclass(frozen=True)
class GeneratedAsset:
    """Extracted asset tracked for preview and final save materialization."""

    filename: str
    temp_path: str
    page_number: int | None = None
    image_number: int | None = None
    sha256: str = ""
    width: int | None = None
    height: int | None = None
    size_bytes: int = 0


@dataclass(frozen=True)
class SavedMarkdownAsset:
    """Asset copied into a markdown-adjacent directory."""

    relative_path: str
    source_path: str


@dataclass(frozen=True)
class MarkdownAssetReference:
    """Reference inserted into markdown output."""

    relative_path: str
    page_number: int | None = None
    alt_text: str = ""


def normalize_assets_layout(layout: str) -> str:
    normalized = (layout or ASSET_LAYOUT_SEPARATE).strip().lower()
    if normalized not in {ASSET_LAYOUT_SEPARATE, ASSET_LAYOUT_SINGLE}:
        return ASSET_LAYOUT_SEPARATE
    return normalized


def sanitize_stem(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._-")
    return sanitized or "document"


def build_markdown_with_asset_references(
    markdown: str,
    references: Sequence[MarkdownAssetReference],
) -> str:
    """Append grouped image references to markdown content."""
    if not references:
        return markdown

    normalized_markdown = markdown.rstrip()
    lines: list[str] = []
    current_page: int | None = None

    for index, reference in enumerate(references, start=1):
        if reference.page_number != current_page:
            current_page = reference.page_number
            if lines:
                lines.append("")
            if current_page is None:
                lines.append("### Images")
            else:
                lines.append(f"### Page {current_page}")
            lines.append("")

        alt_text = reference.alt_text.strip() or (
            f"Page {reference.page_number or '?'} image {index}"
        )
        relative_path = PurePosixPath(reference.relative_path).as_posix()
        lines.append(f"![{alt_text}]({relative_path})")

    images_section = "\n".join(
        [
            "## Extracted Images",
            "",
            *lines,
        ]
    ).rstrip()

    if not normalized_markdown:
        return images_section

    return f"{normalized_markdown}\n\n{images_section}"


def materialize_assets_and_rewrite_markdown(
    source_file: str,
    markdown: str,
    assets: Sequence[GeneratedAsset],
    output_md_path: str | Path,
    asset_layout: str,
    *,
    combined: bool = False,
    used_relative_paths: set[str] | None = None,
) -> str:
    """Copy assets next to a markdown file and return rewritten markdown."""
    references, saved_assets = resolve_asset_references(
        source_file,
        assets,
        output_md_path,
        asset_layout,
        combined=combined,
        used_relative_paths=used_relative_paths,
    )
    _copy_saved_assets(Path(output_md_path).parent, saved_assets)
    return build_markdown_with_asset_references(markdown, references)


def resolve_asset_references(
    source_file: str,
    assets: Sequence[GeneratedAsset],
    output_md_path: str | Path,
    asset_layout: str,
    *,
    combined: bool = False,
    used_relative_paths: set[str] | None = None,
) -> tuple[list[MarkdownAssetReference], list[SavedMarkdownAsset]]:
    """Resolve final relative paths for assets and deduplicate writes."""
    normalized_layout = normalize_assets_layout(asset_layout)
    output_md_path = Path(output_md_path)
    references: list[MarkdownAssetReference] = []
    saved_assets: list[SavedMarkdownAsset] = []
    temp_path_to_relative: dict[str, str] = {}
    claimed_paths = used_relative_paths if used_relative_paths is not None else set()

    for asset in assets:
        temp_path = asset.temp_path
        if temp_path in temp_path_to_relative:
            relative_path = temp_path_to_relative[temp_path]
        else:
            relative_path = _build_relative_asset_path(
                source_file,
                asset,
                output_md_path,
                normalized_layout,
                combined=combined,
                claimed_paths=claimed_paths,
            )
            temp_path_to_relative[temp_path] = relative_path
            saved_assets.append(
                SavedMarkdownAsset(
                    relative_path=relative_path,
                    source_path=temp_path,
                )
            )

        references.append(
            MarkdownAssetReference(
                relative_path=relative_path,
                page_number=asset.page_number,
                alt_text=_build_alt_text(asset),
            )
        )

    return references, saved_assets


def _build_relative_asset_path(
    source_file: str,
    asset: GeneratedAsset,
    output_md_path: Path,
    asset_layout: str,
    *,
    combined: bool,
    claimed_paths: set[str],
) -> str:
    source_stem = sanitize_stem(Path(source_file).stem)
    output_stem = sanitize_stem(output_md_path.stem)

    if combined:
        assets_root = PurePosixPath(f"{output_stem}_assets")
        if asset_layout == ASSET_LAYOUT_SEPARATE:
            candidate = PurePosixPath(assets_root, source_stem, asset.filename).as_posix()
        else:
            candidate = PurePosixPath(
                assets_root,
                f"{source_stem}_{asset.filename}",
            ).as_posix()
    else:
        if asset_layout == ASSET_LAYOUT_SEPARATE:
            candidate = PurePosixPath(f"{output_stem}_assets", asset.filename).as_posix()
        else:
            candidate = PurePosixPath(
                "assets",
                f"{source_stem}_{asset.filename}",
            ).as_posix()

    if candidate not in claimed_paths:
        claimed_paths.add(candidate)
        return candidate

    base = PurePosixPath(candidate)
    stem = base.stem
    suffix = base.suffix
    hashed = sanitize_stem(source_file)[-8:] or "asset"
    collision_candidate = base.with_name(f"{stem}_{hashed}{suffix}").as_posix()
    claimed_paths.add(collision_candidate)
    return collision_candidate


def _copy_saved_assets(base_dir: Path, saved_assets: Sequence[SavedMarkdownAsset]) -> None:
    for asset in saved_assets:
        source_path = Path(asset.source_path)
        if not source_path.exists():
            continue
        output_path = base_dir / Path(*PurePosixPath(asset.relative_path).parts)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, output_path)


def _build_alt_text(asset: GeneratedAsset) -> str:
    page = asset.page_number or "?"
    image_number = asset.image_number or "?"
    return f"Page {page} image {image_number}"
