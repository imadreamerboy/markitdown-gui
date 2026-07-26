from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from secrets import token_hex
import shutil
import tempfile
from typing import Protocol, Sequence
from uuid import uuid4

from markitdowngui.core.input_sources import source_output_stem


_ASSET_ROOT_MARKER = ".markitdowngui-assets.json"
_ASSET_ROOT_MANIFEST = {
    "format": "markitdowngui-assets",
    "version": 1,
}


class AssetLike(Protocol):
    filename: str
    source_path: str | None
    preview_markdown_path: str


@dataclass(frozen=True)
class MarkdownSaveInput:
    source: str
    markdown: str
    assets: Sequence[AssetLike]


@dataclass
class PreparedMarkdownAssets:
    """Staged asset changes that can be committed with a Markdown file write."""

    markdown: str
    asset_root: Path
    staging_root: Path | None = None
    remove_owned_asset_root: bool = False
    _backup_root: Path | None = None
    _assets_committed: bool = False
    _new_asset_root_committed: bool = False
    _finalized: bool = False

    def commit_assets(self) -> None:
        """Activate staged assets while retaining the previous owned root for rollback."""
        if self._assets_committed:
            return
        if self.staging_root is None and not self.remove_owned_asset_root:
            self._assets_committed = True
            return

        _ensure_asset_root_can_be_replaced(self.asset_root)
        backup_root: Path | None = None
        if _asset_root_exists(self.asset_root):
            backup_root = _asset_root_backup_path(self.asset_root)
            self.asset_root.replace(backup_root)
            self._backup_root = backup_root

        try:
            if self.staging_root is not None:
                self.staging_root.replace(self.asset_root)
                self.staging_root = None
                self._new_asset_root_committed = True
        except Exception:
            if backup_root is not None:
                try:
                    backup_root.replace(self.asset_root)
                    self._backup_root = None
                except Exception as rollback_error:
                    raise RuntimeError(
                        "Could not activate the staged asset directory; "
                        f"the previous assets remain at {backup_root}."
                    ) from rollback_error
            raise

        self._assets_committed = True

    def rollback_assets(self) -> None:
        """Restore the pre-save asset directory after a Markdown write failure."""
        if self._finalized:
            return
        try:
            if self._assets_committed:
                if self._new_asset_root_committed:
                    _remove_owned_transaction_asset_root(self.asset_root)
                    self._new_asset_root_committed = False
                if self._backup_root is not None:
                    self._backup_root.replace(self.asset_root)
                    self._backup_root = None
                self._assets_committed = False
        finally:
            _remove_directory_if_present(self.staging_root)
            self.staging_root = None

    def finalize_assets(self) -> None:
        """Discard retained backup data after the Markdown replacement succeeds."""
        if self._finalized:
            return
        _remove_directory_if_present(self._backup_root)
        _remove_directory_if_present(self.staging_root)
        self._backup_root = None
        self.staging_root = None
        self._finalized = True


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
    """Prepare and immediately commit assets for legacy single-step callers."""
    prepared = prepare_markdown_for_separate_save_transaction(
        markdown,
        assets,
        output_path,
    )
    return _commit_prepared_markdown_assets(prepared)


def prepare_markdown_for_separate_save_transaction(
    markdown: str,
    assets: Sequence[AssetLike],
    output_path: str | Path,
) -> PreparedMarkdownAssets:
    """Stage separate-output assets until the corresponding Markdown is ready."""
    destination_path = Path(output_path)
    asset_root = destination_path.with_name(f"{destination_path.stem}_assets")

    return _prepare_markdown_with_assets_transaction(
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
    """Prepare and immediately commit assets for legacy single-step callers."""
    prepared = prepare_combined_markdown_for_save_transaction(
        documents,
        output_path,
        source_heading_template=source_heading_template,
    )
    return _commit_prepared_markdown_assets(prepared)


def prepare_combined_markdown_for_save_transaction(
    documents: Sequence[MarkdownSaveInput],
    output_path: str | Path,
    *,
    source_heading_template: str,
) -> PreparedMarkdownAssets:
    """Stage combined-output assets until the corresponding Markdown is ready."""
    destination_path = Path(output_path)
    asset_root = destination_path.with_name(f"{destination_path.stem}_assets")
    parts: list[str] = []

    if not _documents_have_copyable_assets(documents):
        for document in documents:
            parts.append(
                source_heading_template.format(source=document.source)
                + f"\n{document.markdown}"
            )
        return PreparedMarkdownAssets(
            markdown="\n\n".join(parts),
            asset_root=asset_root,
            remove_owned_asset_root=_is_app_owned_asset_root(asset_root),
        )

    _ensure_asset_root_can_be_replaced(asset_root)
    staging_root = _create_asset_root_staging_directory(asset_root)
    try:
        for index, document in enumerate(documents, start=1):
            rewritten_markdown = _copy_assets_and_rewrite_markdown(
                document.markdown,
                document.assets,
                asset_root=staging_root,
                markdown_asset_root_name=asset_root.name,
                document_scope=_document_scope_name(document.source, index),
            )
            parts.append(
                source_heading_template.format(source=document.source)
                + f"\n{rewritten_markdown}"
            )

        _write_asset_root_marker(staging_root)
        return PreparedMarkdownAssets(
            markdown="\n\n".join(parts),
            asset_root=asset_root,
            staging_root=staging_root,
        )
    except Exception:
        _remove_directory_if_present(staging_root)
        raise


def _prepare_markdown_with_assets_transaction(
    markdown: str,
    assets: Sequence[AssetLike],
    *,
    asset_root: Path,
) -> PreparedMarkdownAssets:
    if not _assets_have_copyable_sources(assets):
        return PreparedMarkdownAssets(
            markdown=markdown,
            asset_root=asset_root,
            remove_owned_asset_root=_is_app_owned_asset_root(asset_root),
        )

    _ensure_asset_root_can_be_replaced(asset_root)
    staging_root = _create_asset_root_staging_directory(asset_root)
    try:
        rewritten_markdown = _copy_assets_and_rewrite_markdown(
            markdown,
            assets,
            asset_root=staging_root,
            markdown_asset_root_name=asset_root.name,
        )
        _write_asset_root_marker(staging_root)
        return PreparedMarkdownAssets(
            markdown=rewritten_markdown,
            asset_root=asset_root,
            staging_root=staging_root,
        )
    except Exception:
        _remove_directory_if_present(staging_root)
        raise


def _commit_prepared_markdown_assets(prepared: PreparedMarkdownAssets) -> str:
    try:
        prepared.commit_assets()
    except Exception:
        prepared.rollback_assets()
        raise
    prepared.finalize_assets()
    return prepared.markdown


def _assets_have_copyable_sources(assets: Sequence[AssetLike]) -> bool:
    return any(asset.source_path for asset in assets)


def _documents_have_copyable_assets(documents: Sequence[MarkdownSaveInput]) -> bool:
    return any(_assets_have_copyable_sources(document.assets) for document in documents)


def _create_asset_root_staging_directory(asset_root: Path) -> Path:
    asset_root.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        staging_root = asset_root.parent / (
            f".markitdowngui-assets-{token_hex(16)}.staging"
        )
        try:
            staging_root.mkdir(mode=0o777)
        except FileExistsError:
            continue
        return staging_root
    raise FileExistsError(
        f"Could not create a staging asset directory for {asset_root}"
    )


def _ensure_asset_root_can_be_replaced(asset_root: Path) -> None:
    if not _asset_root_exists(asset_root):
        return
    if _is_app_owned_asset_root(asset_root):
        return
    raise FileExistsError(
        "Refusing to replace unowned asset directory: "
        f"{asset_root}. Rename or remove it before saving assets here."
    )


def _asset_root_backup_path(asset_root: Path) -> Path:
    return asset_root.with_name(f".markitdowngui-assets-{uuid4().hex}.backup")


def _remove_owned_transaction_asset_root(asset_root: Path) -> None:
    if not _asset_root_exists(asset_root):
        return
    if not _is_app_owned_asset_root(asset_root):
        raise RuntimeError(
            "Could not restore the previous asset directory because the new "
            f"asset directory is no longer app-owned: {asset_root}."
        )
    shutil.rmtree(asset_root)


def _asset_root_exists(asset_root: Path) -> bool:
    return asset_root.exists() or asset_root.is_symlink()


def _is_app_owned_asset_root(asset_root: Path) -> bool:
    if asset_root.is_symlink() or not asset_root.is_dir():
        return False

    marker_path = asset_root / _ASSET_ROOT_MARKER
    if marker_path.is_symlink() or not marker_path.is_file():
        return False

    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return marker == _ASSET_ROOT_MANIFEST


def _write_asset_root_marker(asset_root: Path) -> None:
    marker_path = asset_root / _ASSET_ROOT_MARKER
    marker_path.write_text(
        json.dumps(_ASSET_ROOT_MANIFEST, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _remove_directory_if_present(path: Path | None) -> None:
    if path and path.exists() and path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)


def _copy_assets_and_rewrite_markdown(
    markdown: str,
    assets: Sequence[AssetLike],
    *,
    asset_root: Path,
    markdown_asset_root_name: str | None = None,
    document_scope: str = "",
) -> str:
    if not assets:
        return markdown

    replacements: dict[str, str] = {}
    used_relative_paths: set[Path] = set()
    if not document_scope:
        used_relative_paths.add(Path(_ASSET_ROOT_MARKER))

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
            Path(
                markdown_asset_root_name or asset_root.name,
                *relative_path.parts,
            ).as_posix()
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
