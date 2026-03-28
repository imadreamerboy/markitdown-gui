from markitdowngui.core.input_sources import (
    is_web_url,
    source_display_name,
    source_output_stem,
)


def test_is_web_url_accepts_http_and_https():
    assert is_web_url("https://example.com/article") is True
    assert is_web_url("http://example.com/article") is True
    assert is_web_url("example.com/article") is False
    assert is_web_url(r"C:\docs\article.html") is False
    assert is_web_url("https://example.com/hello world") is False
    assert is_web_url("https://example.com/hello\tworld") is False


def test_source_display_name_uses_basename_for_files():
    assert source_display_name(r"C:\docs\article.html") == "article.html"


def test_source_display_name_preserves_full_url():
    url = "https://example.com/posts/hello-world?ref=test"
    assert source_display_name(url) == url


def test_source_output_stem_sanitizes_urls():
    stem = source_output_stem("https://example.com/posts/hello-world?ref=test")
    assert stem == "example.com-hello-world"
