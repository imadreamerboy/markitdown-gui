from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
from typing import Protocol, Sequence

from markitdowngui.core.input_sources import source_output_stem


class AssetLike(Protocol):
    filename: str
    source_path: str | None
    preview_markdown_path: str


@dataclass(frozen=True)
class MarkdownSaveInput:
    source: str
    markdown: str
    assets: Sequence[AssetLike]


def create_temp_asset_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="markitdowngui-pdf-assets-")).resolve()


def cleanup_temp_asset_root(asset_root: str | Path | None) -> None:
    if not asset_root:
        return
    shutil.rmtree(Path(asset_root), ignore_errors=True)


def rewrite_markdown_for_preview(markdown: str, assets: Sequence[AssetLike]) -> str:
    replacements: dict[str, str] = {}
    for asset in assets:
        if not asset.source_path:
            continue
        replacements[asset.preview_markdown_path] = (
            Path(asset.source_path).resolve().as_uri()
        )
    return _replace_markdown_paths(markdown, replacements)


def prepare_markdown_for_separate_save(
    markdown: str,
    assets: Sequence[AssetLike],
    output_path: str | Path,
) -> str:
    destination_path = Path(output_path)
    asset_root = destination_path.with_name(f"{destination_path.stem}_assets")
    if asset_root.exists():
        shutil.rmtree(asset_root)
    return _copy_assets_and_rewrite_markdown(
        markdown,
        assets,
        asset_root=asset_root,
    )


def prepare_combined_markdown_for_save(
    documents: Sequence[MarkdownSaveInput],
    output_path: str | Path,
    *,
    source_heading_template: str,
) -> str:
    destination_path = Path(output_path)
    asset_root = destination_path.with_name(f"{destination_path.stem}_assets")
    if asset_root.exists():
        shutil.rmtree(asset_root)
    parts: list[str] = []

    for index, document in enumerate(documents, start=1):
        rewritten_markdown = _copy_assets_and_rewrite_markdown(
            document.markdown,
            document.assets,
            asset_root=asset_root,
            document_scope=_document_scope_name(document.source, index),
        )
        parts.append(
            source_heading_template.format(source=document.source)
            + f"\n{rewritten_markdown}"
        )

    return "\n\n".join(parts)


def _copy_assets_and_rewrite_markdown(
    markdown: str,
    assets: Sequence[AssetLike],
    *,
    asset_root: Path,
    document_scope: str = "",
) -> str:
    if not assets:
        return markdown

    replacements: dict[str, str] = {}
    used_relative_paths: set[Path] = set()

    for asset in assets:
        if not asset.source_path:
            continue

        source_path = Path(asset.source_path)
        if not source_path.is_file():
            raise FileNotFoundError(f"Missing asset file: {source_path}")

        relative_path = _reserve_relative_path(
            asset.filename,
            used_relative_paths,
            document_scope=document_scope,
        )
        destination_path = asset_root / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        replacements[asset.preview_markdown_path] = (
            Path(asset_root.name, *relative_path.parts).as_posix()
        )

    return _replace_markdown_paths(markdown, replacements)


def _reserve_relative_path(
    filename: str,
    used_relative_paths: set[Path],
    *,
    document_scope: str,
) -> Path:
    base_name = Path(filename).stem or "asset"
    suffix = Path(filename).suffix
    prefix = Path(document_scope) if document_scope else Path()
    candidate = prefix / f"{base_name}{suffix}"
    counter = 1

    while candidate in used_relative_paths:
        candidate = prefix / f"{base_name}_{counter}{suffix}"
        counter += 1

    used_relative_paths.add(candidate)
    return candidate


def _document_scope_name(source: str, index: int) -> str:
    return f"{index:03d}_{source_output_stem(source)}"


def _replace_markdown_paths(markdown: str, replacements: dict[str, str]) -> str:
    rewritten = markdown
    for old_path, new_path in sorted(
        replacements.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        rewritten = rewritten.replace(old_path, new_path)
    return rewritten
