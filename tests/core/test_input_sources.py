import pytest

from markitdowngui.core.input_sources import (
    BATCH_URL_LIMIT,
    decode_batch_url_file,
    is_web_url,
    parse_batch_urls,
    source_display_name,
    source_output_dir,
    source_output_stem,
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
