from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

WEB_URL_SCHEMES = {"http", "https"}
UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def is_web_url(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False

    parsed = urlparse(candidate)
    return parsed.scheme.lower() in WEB_URL_SCHEMES and bool(parsed.netloc)


def source_display_name(source: str) -> str:
    return source.strip() if is_web_url(source) else Path(source).name or source


def source_output_stem(source: str) -> str:
    if not is_web_url(source):
        return Path(source).stem or "converted"

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
