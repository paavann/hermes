import pytest
from hermes_worker.jobs.urls import (
    canonical_url_hash,
    canonicalize_url,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "HTTPS://WWW.Example.COM:443/World/Story/?b=2&a=1#section",
            "https://www.example.com/World/Story?a=1&b=2",
        ),
        (
            "http://example.com:80/news/../world/?utm_source=rss&utm_medium=feed",
            "http://example.com/news/../world",
        ),
        (
            "https://example.com/path/",
            "https://example.com/path",
        ),
        (
            "https://example.com/",
            "https://example.com/",
        ),
        (
            "https://example.com/a?fbclid=abc&gclid=def&keep=1",
            "https://example.com/a?keep=1",
        ),
        (
            "https://news.google.com/rss/articles/ABC?oc=5",
            "https://news.google.com/rss/articles/ABC",
        ),
        (
            "https://news.google.com/rss/articles/ABC?oc=5&hl=en-US",
            "https://news.google.com/rss/articles/ABC?hl=en-US",
        ),
        (
            "https://example.com/path?b=2&a=2&a=1",
            "https://example.com/path?a=1&a=2&b=2",
        ),
        (
            "https://EXAMPLE.com./Path",
            "https://example.com/Path",
        ),
    ],
)
def test_canonicalize_url(raw: str, expected: str) -> None:
    assert canonicalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "mailto:news@example.com",
        "ftp://example.com/file",
        "not-a-url",
        "https:///missing-host",
        "https://example.com:bad-port/path",
    ],
)
def test_canonicalize_url_rejects_non_http_or_malformed(raw: str) -> None:
    assert canonicalize_url(raw) is None


def test_canonicalize_url_is_idempotent() -> None:
    once = canonicalize_url("https://Example.com/a/?utm_source=x&b=1#top")
    assert once is not None

    assert canonicalize_url(once) == once


def test_canonical_url_hash_is_stable_sha256() -> None:
    canonical = "https://example.com/story?a=1"

    assert canonical_url_hash(canonical) == canonical_url_hash(canonical)
    assert len(canonical_url_hash(canonical)) == 64
    assert canonical_url_hash(canonical) != canonical_url_hash(f"{canonical}&b=2")
