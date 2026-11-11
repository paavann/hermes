from __future__ import annotations

import html
import secrets
import unicodedata
from html.parser import HTMLParser
from xml.sax.saxutils import escape


_STRIPPED_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})
_SKIPPED_HTML_TAGS = frozenset({"script", "style"})


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _SKIPPED_HTML_TAGS:
            self._skip_depth += 1
        self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIPPED_HTML_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        self._parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(f"&#{name};")

    def text(self) -> str:
        return "".join(self._parts)


def generate_boundary() -> str:
    return secrets.token_hex(6)


def clean_invisible_chars(value: str, *, preserve_newlines: bool = False) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    chars: list[str] = []
    for ch in normalized:
        if ch in {"\t", "\n", "\r"}:
            if preserve_newlines:
                chars.append("\n" if ch == "\n" else " ")
            else:
                chars.append(" ")
            continue
        if unicodedata.category(ch) in _STRIPPED_CATEGORIES:
            continue
        chars.append(ch)
    return "".join(chars)


def strip_html_text(value: str, *, limit: int | None = None) -> str:
    precleaned = clean_invisible_chars(value)
    unescaped = clean_invisible_chars(html.unescape(precleaned))
    parser = _HtmlTextExtractor()
    parser.feed(unescaped)
    parser.close()
    collapsed = " ".join(parser.text().split())
    if limit is not None:
        return collapsed[:limit].strip()
    return collapsed


def sanitize_query_text(value: str, *, limit: int) -> str:
    cleaned = clean_invisible_chars(value)
    collapsed = " ".join(cleaned.split())
    return collapsed[:limit].strip()


def clean_xml_text(
    value: str,
    *,
    limit: int | None = None,
    preserve_newlines: bool = False,
    escape_quotes: bool = True,
) -> str:
    cleaned = clean_invisible_chars(value, preserve_newlines=preserve_newlines)
    cleaned = cleaned.strip() if preserve_newlines else " ".join(cleaned.split())
    if limit is not None:
        cleaned = cleaned[:limit]
    if escape_quotes:
        return escape(cleaned, {'"': "&quot;", "'": "&apos;"})
    return escape(cleaned)


def wrap_untrusted(tag: str, content: str, *, boundary: str) -> str:
    return f"<{tag}_{boundary}>\n{content}\n</{tag}_{boundary}>"


__all__ = [
    "clean_invisible_chars",
    "clean_xml_text",
    "generate_boundary",
    "sanitize_query_text",
    "strip_html_text",
    "wrap_untrusted",
]
