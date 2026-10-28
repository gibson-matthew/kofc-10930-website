"""Member prayer requests. Stored text is plain, with tags removed."""

from __future__ import annotations

import re
from html.parser import HTMLParser

TITLE_LIMIT = 120
BODY_LIMIT = 2000

_BLOCK_BREAK = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "br"}
_BLOCK_END = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag, attrs) -> None:
        if tag.lower() in _BLOCK_BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag) -> None:
        if tag.lower() in _BLOCK_END:
            self.parts.append("\n")


def _strip_markup(value: str) -> str:
    text = str(value or "").replace("\x00", "")
    parser = _PlainText()
    try:
        parser.feed(text)
        parser.close()
        extracted = "".join(parser.parts)
    except Exception:
        extracted = text
    extracted = re.sub(r"<[^>]*>", "", extracted)
    return extracted.replace("\r\n", "\n").replace("\r", "\n")


def _one_line(value: str) -> str:
    return re.sub(r"\s+", " ", _strip_markup(value)).strip()


def _paragraphs(value: str) -> str:
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in _strip_markup(value).split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return text


def clean_prayer_title(value: str) -> str:
    text = _one_line(value)
    if len(text) > TITLE_LIMIT:
        raise ValueError("Title must be 120 characters or fewer.")
    return text


def clean_prayer_body(value: str) -> str:
    text = _paragraphs(value)
    if not text:
        raise ValueError("Enter the prayer request.")
    if len(text) > BODY_LIMIT:
        raise ValueError("Prayer request must be 2000 characters or fewer.")
    return text


def display_prayer_title(value: str) -> str:
    return _one_line(value)[:TITLE_LIMIT]


def display_prayer_body(value: str) -> str:
    return _paragraphs(value)[:BODY_LIMIT]


def display_person_name(value: str) -> str:
    text = _one_line(value)[:TITLE_LIMIT]
    return text or "Member"


PRAYER_SEED = [
    {
        "member_id": "1000000",
        "title": "For the sick",
        "body": "Pray for the brothers who are ill and for their families.",
        "created_at": "2026-10-12T17:00:00+00:00",
        "updated_at": "2026-10-12T17:00:00+00:00",
    },
    {
        "member_id": "1000001",
        "title": "",
        "body": "Pray for our council and for the families we serve.",
        "created_at": "2026-09-28T17:00:00+00:00",
        "updated_at": "2026-09-28T17:00:00+00:00",
    },
]
