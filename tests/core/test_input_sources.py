import pytest

from pathlib import Path

from markitdowngui.core.input_sources import (
    BATCH_URL_LIMIT,
    collect_folder_files,
    decode_batch_url_file,
    is_web_url,
    parse_batch_urls,
    relocated_output_stem,
    source_display_name,
    source_output_dir,
    source_output_stem,
    source_relative_label,
)


def test_is_web_url_accepts_http_and_https():
    assert is_web_url("https://example.com/article") is True
    assert is_web_url("http://example.com/article") is True
    assert is_web_url("https://user@example.com:8443/article") is True
    assert is_web_url("example.com/article") is False
    assert is_web_url(r"C:\docs\article.html") is False
    assert is_web_url("https://example.com/hello world") is False
    assert is_web_url("https://example.com/hello\tworld") is False
    assert is_web_url("https://[") is False


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com:bad",
        "https://example.com:65536",
        "https://user@",
        "https://:443",
    ],
)
def test_is_web_url_rejects_malformed_authorities(url):
    assert is_web_url(url) is False


def test_parse_batch_urls_trims_lines_and_ignores_blanks():
    result = parse_batch_urls(
        "  https://example.com/one  \n\n\thttp://example.com/two?x=1#part\t\n"
    )

    assert result.ok is True
    assert result.urls == (
        "https://example.com/one",
        "http://example.com/two?x=1#part",
    )
    assert result.added_count == 2
    assert result.skipped_count == 0


def test_parse_batch_urls_rejects_all_input_and_reports_invalid_line_numbers():
    result = parse_batch_urls(
        "https://example.com/valid\n"
        "See https://example.com/in-prose\n"
        "\n"
        "ftp://example.com/not-supported\n"
        "https://example.com/also-valid"
    )

    assert result.ok is False
    assert result.urls == ()
    assert result.invalid_line_numbers == (2, 4)
    assert result.added_count == 0


def test_parse_batch_urls_atomically_rejects_malformed_authorities():
    result = parse_batch_urls(
        "https://example.com/valid\n"
        "https://example.com:bad\n"
        "https://user@\n"
        "https://example.com/also-valid"
    )

    assert result.ok is False
    assert result.urls == ()
    assert result.invalid_line_numbers == (2, 3)
    assert result.added_count == 0


def test_parse_batch_urls_deduplicates_exact_trimmed_urls_only():
    result = parse_batch_urls(
        "https://example.com/item\n"
        " https://example.com/item \n"
        "https://example.com/item/\n"
        "https://example.com/item?x=1\n"
        "https://EXAMPLE.com/item",
        existing_urls=("https://example.com/item",),
    )

    assert result.ok is True
    assert result.urls == (
        "https://example.com/item/",
        "https://example.com/item?x=1",
        "https://EXAMPLE.com/item",
    )
    assert result.skipped_count == 2


def test_parse_batch_urls_accepts_exactly_the_total_queue_limit():
    existing = tuple(f"https://example.com/{index}" for index in range(99))

    result = parse_batch_urls("https://example.com/final", existing)

    assert result.ok is True
    assert result.urls == ("https://example.com/final",)
    assert result.limit == BATCH_URL_LIMIT


def test_parse_batch_urls_atomically_rejects_queue_limit_overflow():
    existing = tuple(f"https://example.com/{index}" for index in range(99))

    result = parse_batch_urls(
        "https://example.com/new-one\nhttps://example.com/new-two",
        existing,
    )

    assert result.ok is False
    assert result.urls == ()
    assert result.overflow_count == 1
    assert result.limit == 100
    assert result.added_count == 0


def test_parse_batch_urls_counts_duplicates_before_applying_limit():
    existing = tuple(f"https://example.com/{index}" for index in range(99))

    result = parse_batch_urls(
        "https://example.com/0\n"
        "https://example.com/new\n"
        "https://example.com/new",
        existing,
    )

    assert result.ok is True
    assert result.urls == ("https://example.com/new",)
    assert result.skipped_count == 2


def test_parse_batch_urls_treats_all_duplicates_as_a_valid_empty_addition():
    result = parse_batch_urls(
        "https://example.com/queued\n https://example.com/queued ",
        existing_urls=("https://example.com/queued",),
    )

    assert result.ok is True
    assert result.urls == ()
    assert result.added_count == 0
    assert result.skipped_count == 2


def test_parse_batch_urls_rejects_negative_limit():
    with pytest.raises(ValueError, match="must not be negative"):
        parse_batch_urls("", limit=-1)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (b"https://example.com", "https://example.com"),
        (b"\xef\xbb\xbfhttps://example.com", "https://example.com"),
    ],
)
def test_decode_batch_url_file_accepts_utf8_with_optional_bom(data, expected):
    assert decode_batch_url_file(data) == expected


def test_decode_batch_url_file_rejects_non_utf8():
    with pytest.raises(UnicodeDecodeError):
        decode_batch_url_file(b"https://example.com/\xff")


def test_source_display_name_uses_basename_for_files():
    assert source_display_name(r"C:\docs\article.html") == "article.html"


def test_source_display_name_preserves_full_url():
    url = "https://example.com/posts/hello-world?ref=test"
    assert source_display_name(url) == url


def test_source_output_stem_sanitizes_urls():
    stem = source_output_stem("https://example.com/posts/hello-world?ref=test")
    assert stem == "example.com-hello-world"


def test_source_output_dir_returns_file_parent():
    assert source_output_dir(r"C:\docs\article.html") == r"C:\docs"


def test_source_output_dir_is_empty_for_urls():
    assert source_output_dir("https://example.com/posts/hello-world") == ""


def _build_folder_tree(tmp_path):
    nested = tmp_path / "b"
    nested.mkdir()
    deeper = nested / "deep"
    deeper.mkdir()
    skipped = tmp_path / "node_modules"
    skipped.mkdir()
    hidden = tmp_path / ".git"
    hidden.mkdir()

    (tmp_path / "top.pdf").write_text("top", encoding="utf-8")
    (nested / "report.pdf").write_text("nested", encoding="utf-8")
    (deeper / "report.docx").write_text("deeper", encoding="utf-8")
    (nested / "photo.png").write_text("image", encoding="utf-8")
    (tmp_path / "notes.bin").write_text("unsupported", encoding="utf-8")
    (skipped / "ignored.pdf").write_text("ignored", encoding="utf-8")
    (hidden / "config.pdf").write_text("hidden", encoding="utf-8")
    (tmp_path / ".hidden.pdf").write_text("hidden file", encoding="utf-8")
    return tmp_path


def test_collect_folder_files_walks_subfolders_and_reports_skipped(tmp_path):
    root = _build_folder_tree(tmp_path)

    files, skipped = collect_folder_files(
        str(root),
        supported_extensions={".docx", ".pdf", ".png"},
    )

    names = [Path(path).name for path in files]
    assert names == ["top.pdf", "photo.png", "report.pdf", "report.docx"]
    assert all("node_modules" not in path for path in files)
    assert all(".git" not in Path(path).parts for path in files)
    assert all(".hidden.pdf" not in path for path in files)
    assert skipped == 1


def test_collect_folder_files_keeps_every_file_without_extension_filter(tmp_path):
    root = _build_folder_tree(tmp_path)

    files, skipped = collect_folder_files(str(root))

    assert skipped == 0
    assert any(path.endswith("notes.bin") for path in files)


def test_relocated_output_stem_disambiguates_nested_same_name_files(tmp_path):
    root = _build_folder_tree(tmp_path)

    assert relocated_output_stem(str(root / "top.pdf"), str(root)) == "top"
    stem = relocated_output_stem(str(root / "b" / "report.pdf"), str(root))
    assert stem == "report-b"
    assert relocated_output_stem(
        str(root / "b" / "deep" / "report.docx"),
        str(root),
    ) == "report-deep"


def test_relocated_output_stem_ignores_files_outside_the_folder_root(tmp_path):
    root = _build_folder_tree(tmp_path)

    outside = tmp_path.parent / "outside" / "report.pdf"
    assert relocated_output_stem(str(outside), str(root)) == "report"
    assert relocated_output_stem(
        "https://example.com/a/report.pdf",
        str(root),
    ) == "example.com-report.pdf"


def test_source_relative_label_prefixes_the_picked_folder(tmp_path):
    root = _build_folder_tree(tmp_path)

    assert source_relative_label(str(root / "top.pdf"), str(root)) == f"{root.name}/top.pdf"
    assert source_relative_label(
        str(root / "b" / "deep" / "report.docx"),
        str(root),
    ) == f"{root.name}/b/deep/report.docx"
    assert source_relative_label(str(root / "top.pdf"), "") == "top.pdf"
    assert source_relative_label(str(tmp_path.parent / "other" / "x.pdf"), str(root)) == (
        "x.pdf"
    )
