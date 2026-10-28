"""Member announcements. Stored HTML is reduced to a small safe set of tags."""

from __future__ import annotations

import re
from html import escape
from html.parser import HTMLParser

MAX_HTML = 20000
MAX_INPUT = 40000
_ALLOWED = {"p", "br", "strong", "b", "em", "i", "u", "mark", "h2", "h3", "h4", "ul", "ol", "li", "a", "span", "div"}
_DROP = {"script", "style", "iframe", "object", "embed", "noscript", "template", "svg", "math", "link", "meta", "form"}
_ALIGN = {"left", "center", "right"}
_HEX = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{6})$")
_RGB = re.compile(r"^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$")

# Example notices. The API inserts them only when the table is first created.
# Memory fallback always starts from this list.
ANNOUNCEMENT_SEED: tuple[dict[str, str], ...] = (
    {
        "title": "Exemplification practice",
        "summary": "Practice details stay with the council.",
        "body": (
            "<p>Exemplification practice stays with the council. "
            "Come ready to review the degree and the evening duties.</p>"
            "<ul><li>Parish hall</li><li>Brothers only</li></ul>"
        ),
        "created_by": "1000000",
        "created_at": "2026-10-08T17:00:00+00:00",
        "updated_at": "2026-10-08T17:00:00+00:00",
    },
    {
        "title": "Business meeting reminder",
        "summary": "Officers report on Wednesday.",
        "body": (
            "<p>Officers report at the business meeting. "
            "Brothers plan the next charity work in the parish hall.</p>"
        ),
        "created_by": "1000000",
        "created_at": "2026-09-20T17:00:00+00:00",
        "updated_at": "2026-09-20T17:00:00+00:00",
    },
)


def _safe_color(value: str) -> bool:
    if _HEX.match(value):
        return True
    match = _RGB.match(value)
    if not match:
        return False
    return all(int(part) <= 255 for part in match.groups())


def _safe_style(value: str) -> str:
    kept: list[str] = []
    for part in str(value or "").split(";"):
        if ":" not in part:
            continue
        prop, raw = part.split(":", 1)
        prop = prop.strip().lower()
        val = raw.strip().lower()
        if any(token in val for token in ("url", "expression", "javascript", "\\", "@", "/*")):
            continue
        if prop == "text-align" and val in _ALIGN:
            kept.append(f"text-align: {val}")
        elif prop == "background-color" and _safe_color(val):
            kept.append(f"background-color: {val}")
        elif prop == "font-weight" and val in {"bold", "700"}:
            kept.append("font-weight: bold")
        elif prop == "font-style" and val == "italic":
            kept.append("font-style: italic")
        elif prop in {"text-decoration", "text-decoration-line"} and val == "underline":
            kept.append("text-decoration: underline")
    return "; ".join(kept)


def _safe_href(value: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 500 or any(ord(ch) < 32 or ch.isspace() for ch in text):
        return ""
    lowered = text.lower()
    if lowered.startswith("https://") or lowered.startswith("http://"):
        return text
    if lowered.startswith("mailto:"):
        rest = text[7:]
        if rest and "@" in rest and " " not in rest and "/" not in rest:
            return text
    return ""


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.skip = 0

    def result(self) -> str:
        while self.stack:
            self.parts.append(f"</{self.stack.pop()}>")
        return "".join(self.parts).strip()

    def _emit(self, text: str) -> None:
        if not text:
            return
        size = sum(len(part) for part in self.parts)
        if size >= MAX_HTML:
            return
        room = MAX_HTML - size
        self.parts.append(text[:room])

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.skip:
            if tag in _DROP:
                self.skip += 1
            return
        if tag in _DROP:
            self.skip = 1
            return
        if tag not in _ALLOWED or len(self.stack) >= 12:
            return
        attr_text = self._attributes(tag, attrs)
        if tag == "a" and "href=" not in attr_text:
            return
        if tag == "br":
            self._emit("<br>")
            return
        self.stack.append(tag)
        self._emit(f"<{tag}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.skip:
            if tag in _DROP:
                self.skip = max(0, self.skip - 1)
            return
        if tag not in self.stack:
            return
        while self.stack:
            open_tag = self.stack.pop()
            self._emit(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        if self.skip or not data:
            return
        self._emit(escape(data.replace("\x00", "")))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() != "br":
            self.handle_endtag(tag)

    def _attributes(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        style = ""
        align = ""
        href = ""
        for name, value in attrs:
            key = str(name or "").lower()
            raw = "" if value is None else str(value)
            if key.startswith("on") or key in {"src", "srcdoc", "href"} and tag != "a":
                continue
            if key == "href" and tag == "a":
                href = _safe_href(raw)
            elif key == "style":
                style = _safe_style(raw)
            elif key == "align" and raw.lower() in _ALIGN:
                align = raw.lower()
        if align and "text-align:" not in style:
            style = f"{style}; text-align: {align}" if style else f"text-align: {align}"
        parts: list[str] = []
        if tag == "a" and href:
            parts.append(f'href="{escape(href, quote=True)}"')
            if href.lower().startswith(("http://", "https://")):
                parts.append('target="_blank"')
                parts.append('rel="noopener noreferrer"')
        if style:
            parts.append(f'style="{escape(style, quote=True)}"')
        if not parts:
            return ""
        return " " + " ".join(parts)


def sanitize_html(value: str) -> str:
    """Return announcement HTML that cannot run a script."""
    raw = str(value or "").replace("\x00", "")
    if len(raw) > MAX_INPUT:
        raw = raw[:MAX_INPUT]
    parser = _Sanitizer()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        return ""
    return parser.result()


def html_text(value: str) -> str:
    class _Text(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    parser = _Text()
    try:
        parser.feed(value or "")
        parser.close()
    except Exception:
        return ""
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def _plain(value: str) -> str:
    text = re.sub(r"<[^>]*>", "", str(value or ""))
    return re.sub(r"\s+", " ", text.replace("\x00", "")).strip()


def clean_announcement_title(value: str) -> str:
    title = _plain(value)
    if not title:
        raise ValueError("Enter a title.")
    if len(title) > 120:
        raise ValueError("Title must be 120 characters or fewer.")
    return title


def clean_announcement_summary(value: str) -> str:
    summary = _plain(value)
    if len(summary) > 280:
        raise ValueError("Summary must be 280 characters or fewer.")
    return summary


def clean_announcement_body(value: str) -> str:
    html = sanitize_html(value)
    if len(html) > MAX_HTML:
        raise ValueError("Announcement is too long.")
    if not html_text(html):
        raise ValueError("Enter the announcement.")
    return html
