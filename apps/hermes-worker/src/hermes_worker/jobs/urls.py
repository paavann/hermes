"""URL identity helpers for the article ledger.

Canonicalization is deliberately conservative: it removes representation
noise (case, default ports, fragments, tracking parameters, trailing slashes)
without guessing at site-specific redirects. Two URLs that canonicalize to the
same string are treated as the same ledger article.
"""

from __future__ import annotations
import hashlib
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMS: Final[frozenset[str]] = frozenset(
    {
        "at_campaign",
        "at_custom1",
        "at_custom2",
        "at_medium",
        "dclid",
        "fbclid",
        "gclid",
        "igshid",
        "maca",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "traffic_source",
        "utm_campaign",
        "utm_content",
        "utm_id",
        "utm_medium",
        "utm_source",
        "utm_term",
    }
)
DEFAULT_PORTS: Final[dict[str, int]] = {"http": 80, "https": 443}
GOOGLE_NEWS_HOST: Final[str] = "news.google.com"


def canonicalize_url(raw: str) -> str | None:
    """Return a stable canonical form, or None for a non-http(s) URL."""
    candidate = raw.strip()
    if not candidate:
        return None

    try:
        parts = urlsplit(candidate)
        port = parts.port
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        return None

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return None

    netloc = host if port in (None, DEFAULT_PORTS[scheme]) else f"{host}:{port}"

    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
        and not (host == GOOGLE_NEWS_HOST and key.lower() == "oc")
    ]
    kept.sort(key=lambda pair: (pair[0], pair[1]))

    return urlunsplit((scheme, netloc, path, urlencode(kept), ""))


def canonical_url_hash(canonical_url: str) -> str:
    """Return the sha256 hex digest stored in articles.canonical_url_hash."""
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()
