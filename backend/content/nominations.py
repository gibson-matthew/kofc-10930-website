"""Member nominations for Knight and Family awards. Stored text is plain."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser

from content.media import uploaded_on

NAME_LIMIT = 120
REASON_LIMIT = 280

MONTH_CATEGORIES = ("knight_month", "family_month")
YEAR_CATEGORIES = ("knight_year", "family_year")
KNIGHT_CATEGORIES = ("knight_month", "knight_year")
FAMILY_CATEGORIES = ("family_month", "family_year")
CATEGORY_ORDER = ("knight_month", "family_month", "knight_year", "family_year")
CATEGORY_LABELS = {
    "knight_month": "Knight of the Month",
    "family_month": "Family of the Month",
    "knight_year": "Knight of the Year",
    "family_year": "Family of the Year",
}

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


def clean_nomination_name(value: str) -> str:
    text = _one_line(value)
    if not text:
        raise ValueError("Enter the nominee's name.")
    if len(text) > NAME_LIMIT:
        raise ValueError("Name must be 120 characters or fewer.")
    return text


def clean_nomination_reason(value: str) -> str:
    text = _one_line(value)
    if len(text) > REASON_LIMIT:
        raise ValueError("Reason must be 280 characters or fewer.")
    return text


def display_nomination_name(value: str) -> str:
    return _one_line(value)[:NAME_LIMIT]


def display_nomination_reason(value: str) -> str:
    return _one_line(value)[:REASON_LIMIT]


def display_voter_name(value: str) -> str:
    text = _one_line(value)[:NAME_LIMIT]
    return text or "Member"


def active_periods(moment: datetime | None = None) -> tuple[str, str]:
    """Current month (YYYY-MM) and calendar year in America/Chicago."""
    current = date.fromisoformat(uploaded_on(moment or datetime.now(timezone.utc)))
    return f"{current.year:04d}-{current.month:02d}", f"{current.year:04d}"


def period_for(category: str, moment: datetime | None = None) -> str:
    month_period, year_period = active_periods(moment)
    if category in MONTH_CATEGORIES:
        return month_period
    if category in YEAR_CATEGORIES:
        return year_period
    raise ValueError("Choose a category.")


def in_active_period(category: str, period: str, month_period: str, year_period: str) -> bool:
    if category in MONTH_CATEGORIES:
        return period == month_period
    if category in YEAR_CATEGORIES:
        return period == year_period
    return False


def resolve_nominee(category: str, nominee_member_id: str, nominee_name: str, lookup) -> tuple[str | None, str]:
    """Return (member id or None, display name). lookup(member id) returns a name or None."""
    if category in KNIGHT_CATEGORIES:
        member_id = str(nominee_member_id or "").strip()
        if not member_id:
            raise ValueError("Choose a member from the list.")
        raw = lookup(member_id)
        if raw is None:
            raise ValueError("Choose a member from the list.")
        try:
            name = clean_nomination_name(raw)
        except ValueError as exc:
            raise ValueError("Choose a member from the list.") from exc
        return member_id, name
    if category in FAMILY_CATEGORIES:
        return None, clean_nomination_name(nominee_name)
    raise ValueError("Choose a category.")


def _moment(row: dict) -> datetime:
    value = row.get("created_at")
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def build_results(rows: list[dict], month_period: str, year_period: str) -> dict:
    grouped: dict[str, dict] = {category: {} for category in CATEGORY_ORDER}
    for row in rows:
        category = str(row.get("category") or "")
        if category not in grouped:
            continue
        if not in_active_period(category, str(row.get("period") or ""), month_period, year_period):
            continue
        nominee_id = str(row.get("nominee_member_id") or "").strip()
        nominee_name = display_nomination_name(row.get("nominee_name") or "")
        if category in KNIGHT_CATEGORIES and nominee_id:
            key = f"id:{nominee_id}"
        else:
            key = f"name:{nominee_name.casefold()}"
        slot = grouped[category].get(key)
        moment = _moment(row)
        if slot is None:
            slot = {
                "nominee_name": nominee_name,
                "nominee_member_id": nominee_id if category in KNIGHT_CATEGORIES else "",
                "nominators": [],
                "_latest": moment,
            }
            grouped[category][key] = slot
        elif moment >= slot["_latest"]:
            slot["_latest"] = moment
            if nominee_name:
                slot["nominee_name"] = nominee_name
        slot["nominators"].append(
            {
                "member_id": str(row.get("member_id") or ""),
                "display_name": display_voter_name(row.get("voter_name") or ""),
                "reason": display_nomination_reason(row.get("reason") or ""),
            }
        )
    categories = []
    for category in CATEGORY_ORDER:
        nominees = []
        for slot in grouped[category].values():
            people = slot["nominators"]
            people.sort(key=lambda person: (person["display_name"].casefold(), person["member_id"]))
            nominees.append(
                {
                    "nominee_name": slot["nominee_name"],
                    "nominee_member_id": slot["nominee_member_id"],
                    "votes": len(people),
                    "nominators": people,
                }
            )
        nominees.sort(key=lambda item: (-item["votes"], item["nominee_name"].casefold(), item["nominee_member_id"]))
        categories.append(
            {
                "category": category,
                "label": CATEGORY_LABELS[category],
                "nominees": nominees,
            }
        )
    return {"month_period": month_period, "year_period": year_period, "categories": categories}


NOMINATION_SEED = [
    {
        "member_id": "1000000",
        "category": "knight_month",
        "nominee_member_id": "1000135",
        "nominee_name": "Walter Shaw",
        "reason": "He keeps the council charity work moving.",
        "period": "2026-10",
        "created_at": "2026-10-12T17:00:00+00:00",
    },
    {
        "member_id": "1000001",
        "category": "family_month",
        "nominee_member_id": None,
        "nominee_name": "The Nguyen Family",
        "reason": "They welcome new brothers and their families.",
        "period": "2026-10",
        "created_at": "2026-10-05T17:00:00+00:00",
    },
]
