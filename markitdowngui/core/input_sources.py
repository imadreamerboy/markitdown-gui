from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable
from urllib.parse import unquote, urlparse

BATCH_URL_LIMIT = 100
WEB_URL_SCHEMES = {"http", "https"}
UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class BatchUrlParseResult:
    """Result of validating and deduplicating a batch of URL lines."""

    urls: tuple[str, ...] = ()
    invalid_line_numbers: tuple[int, ...] = ()
    skipped_count: int = 0
    overflow_count: int = 0
    limit: int = BATCH_URL_LIMIT

    @property
    def ok(self) -> bool:
        return not self.invalid_line_numbers and self.overflow_count == 0

    @property
    def added_count(self) -> int:
        return len(self.urls)


def is_web_url(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    if any(ch.isspace() or ord(ch) < 32 for ch in candidate):
        return False

    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    return parsed.scheme.lower() in WEB_URL_SCHEMES and bool(hostname)


def parse_batch_urls(
    text: str,
    existing_urls: Iterable[str] = (),
    *,
    limit: int = BATCH_URL_LIMIT,
) -> BatchUrlParseResult:
    """Parse one HTTP(S) URL per line without partially accepting bad input.

    Blank lines are ignored. URLs are compared exactly after trimming surrounding
    whitespace; their casing and URL components are otherwise left unchanged.
    """

    if limit < 0:
        raise ValueError("URL limit must not be negative")

    existing = tuple(url.strip() for url in existing_urls if url.strip())
    existing_set = set(existing)
    candidates: list[str] = []
    seen = set(existing_set)
    invalid_line_numbers: list[int] = []
    skipped_count = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        candidate = line.strip()
        if not candidate:
            continue
        if not is_web_url(candidate):
            invalid_line_numbers.append(line_number)
            continue
        if candidate in seen:
            skipped_count += 1
            continue
        seen.add(candidate)
        candidates.append(candidate)

    if invalid_line_numbers:
        return BatchUrlParseResult(
            invalid_line_numbers=tuple(invalid_line_numbers),
            limit=limit,
        )

    overflow_count = max(0, len(existing) + len(candidates) - limit)
    if overflow_count:
        return BatchUrlParseResult(
            skipped_count=skipped_count,
            overflow_count=overflow_count,
            limit=limit,
        )

    return BatchUrlParseResult(
        urls=tuple(candidates),
        skipped_count=skipped_count,
        limit=limit,
    )


def decode_batch_url_file(data: bytes) -> str:
    """Decode a dedicated batch URL file as UTF-8, accepting an optional BOM."""

    return data.decode("utf-8-sig")


def _source_path(source: str) -> Path | PureWindowsPath:
    candidate = source.strip()
    if "\\" in candidate:
        return PureWindowsPath(candidate)
    return Path(candidate)


def source_display_name(source: str) -> str:
    return source.strip() if is_web_url(source) else _source_path(source).name or source


def source_output_stem(source: str) -> str:
    if not is_web_url(source):
        return _source_path(source).stem or "converted"

    parsed = urlparse(source.strip())
    path_parts = [part for part in parsed.path.split("/") if part]
    slug = unquote(path_parts[-1]) if path_parts else ""
    query = parsed.query.split("&", 1)[0] if parsed.query else ""

    segments = [parsed.netloc]
    if slug:
        segments.append(slug)
    elif query:
        segments.append(query)

    candidate = "-".join(segments)
    sanitized = UNSAFE_FILENAME_CHARS.sub("-", candidate).strip("._-")
    return sanitized or "website"


def source_output_dir(source: str) -> str:
    if is_web_url(source):
        return ""

    parent = _source_path(source).parent
    if str(parent) in {"", "."}:
        return ""
    return str(parent)
