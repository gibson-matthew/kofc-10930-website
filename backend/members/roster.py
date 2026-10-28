"""Test roster and past-honor rows.

Admin login: membership id 1000000, password Password123! (David Hernandez, GK).
Membership ids 1000001 and 1000100–1000149 use that same password.
The API and backend/seed_member.py insert missing rows. Profile photos are
images/seed/members/<membership id>.png. Honor photos are
backend/uploads/seed/honors/<category>-NN.png.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import NamedTuple

from members.titles import TITLE_ABBREVS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EN_DASH = "\u2013"
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class SeedMember(NamedTuple):
    membership_id: str
    display_name: str
    title: str | None
    is_admin: bool
    birth_month: int
    birth_day: int


# Optional directory examples. Applied when that member row is first created.
# The API also applies them once, when the phone column is first added.
# honorary_life, phone, email. Empty phone and email stay unset.
DIRECTORY_SEED: dict[str, tuple[bool, str, str]] = {
    "1000000": (True, "(817) 555-0140", "david.hernandez@example.com"),
    "1000104": (False, "(817) 555-0142", "christopher.nguyen@example.com"),
    "1000105": (False, "(817) 555-0144", "andrew.callahan@example.com"),
    "1000121": (True, "(817) 555-0168", "richard.donnelly@example.com"),
    "1000135": (True, "(817) 555-0176", "walter.shaw@example.com"),
    "1000144": (True, "", ""),
}


def directory_fields(membership_id: str) -> tuple[bool, str | None, str | None]:
    honorary, phone, email = DIRECTORY_SEED.get(membership_id, (False, "", ""))
    return bool(honorary), phone or None, email or None


# 50 members. GK stays with David Hernandez (1000000). Shared password: Password123!
MEMBER_SEED: tuple[SeedMember, ...] = (
    SeedMember("1000100", "Michael Brennan", "DGK", True, 10, 3),
    SeedMember("1000101", "Thomas Alvarez", "CH", False, 11, 7),
    SeedMember("1000102", "Paul Okonkwo", "CHP", False, 3, 19),
    SeedMember("1000103", "Daniel Wright", "REC", True, 10, 18),
    SeedMember("1000104", "Christopher Nguyen", "FS", False, 1, 22),
    SeedMember("1000105", "Andrew Callahan", "TR", False, 11, 14),
    SeedMember("1000106", "Joseph Ramirez", "ADV", False, 6, 9),
    SeedMember("1000107", "Matthew Brooks", "WRD", False, 10, 27),
    SeedMember("1000108", "Anthony Delgado", "IG", False, 4, 11),
    SeedMember("1000109", "Ryan Patel", "OG", False, 11, 2),
    SeedMember("1000110", "Kevin O'Brien", "LEC", False, 8, 30),
    SeedMember("1000111", "Brian Kowalski", "T1", False, 2, 17),
    SeedMember("1000112", "Steven Park", "T2", False, 12, 5),
    SeedMember("1000113", "Timothy Walsh", "T3", False, 5, 21),
    SeedMember("1000114", "Patrick Moretti", "PD", True, 10, 9),
    SeedMember("1000115", "Edward Vasquez", "MD", False, 7, 13),
    SeedMember("1000116", "Gregory Thompson", "FD", False, 11, 21),
    SeedMember("1000117", "Samuel Green", "FAM", False, 9, 4),
    SeedMember("1000118", "Benjamin Carter", "COM", False, 3, 28),
    SeedMember("1000119", "Nicholas Reed", "LIFE", False, 1, 8),
    SeedMember("1000120", "Jonathan Ellis", "VOC", False, 10, 31),
    SeedMember("1000121", "Richard Donnelly", "PGK", False, 11, 11),
    SeedMember("1000122", "Adam Herrera", None, False, 2, 8),
    SeedMember("1000123", "Noah Bennett", None, False, 5, 14),
    SeedMember("1000124", "Luis Ortega", None, True, 4, 2),
    SeedMember("1000125", "Caleb Frost", None, False, 6, 25),
    SeedMember("1000126", "Sean Gallagher", None, False, 10, 6),
    SeedMember("1000127", "Eric Bowman", None, False, 12, 19),
    SeedMember("1000128", "Colin Fraser", None, False, 11, 16),
    SeedMember("1000129", "Ivan Petrov", None, False, 1, 29),
    SeedMember("1000130", "Marcus Ellison", None, False, 3, 3),
    SeedMember("1000131", "Henry Wallace", None, True, 11, 28),
    SeedMember("1000132", "Diego Castillo", None, False, 7, 7),
    SeedMember("1000133", "Joel Navarro", None, False, 8, 15),
    SeedMember("1000134", "Francis Doyle", None, False, 9, 23),
    SeedMember("1000135", "Walter Shaw", None, False, 12, 11),
    SeedMember("1000136", "Aaron Blake", None, False, 10, 22),
    SeedMember("1000137", "Vincent Rossi", None, False, 2, 26),
    SeedMember("1000138", "Victor Santos", None, False, 11, 4),
    SeedMember("1000139", "George Lanier", None, False, 5, 5),
    SeedMember("1000140", "Mark Jensen", None, True, 10, 12),
    SeedMember("1000141", "Harold Ibarra", None, False, 1, 17),
    SeedMember("1000142", "Philip Okada", None, False, 4, 29),
    SeedMember("1000143", "Clarence Holt", None, False, 6, 2),
    SeedMember("1000144", "Eugene Moss", None, False, 7, 30),
    SeedMember("1000145", "Bernard Cruz", None, False, 9, 12),
    SeedMember("1000146", "Stanley Peck", None, False, 12, 28),
    SeedMember("1000147", "Albert Kim", None, False, 3, 8),
    SeedMember("1000148", "Raymond Doyle", None, False, 5, 30),
    SeedMember("1000149", "Lawrence Kim", None, False, 8, 8),
)


def member_photo_path(membership_id: str) -> str:
    return f"images/seed/members/{membership_id}.png"


def _shift_month(year: int, month: int, back: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) - back
    return index // 12, index % 12 + 1


def _month_rows(category: str, people: tuple[tuple[str, str], ...], end_year: int, end_month: int) -> list[dict]:
    rows = []
    for back, (name, note) in enumerate(people):
        year, month = _shift_month(end_year, end_month, back)
        rows.append(
            {
                "category": category,
                "name": name,
                "period": f"{MONTHS[month - 1]} {year}",
                "sort_year": year,
                "sort_month": month,
                "note": note,
            }
        )
    return rows


def _year_rows(category: str, people: tuple[tuple[str, str], ...], end_year: int) -> list[dict]:
    rows = []
    for back, (name, note) in enumerate(people):
        year = end_year - back
        rows.append(
            {
                "category": category,
                "name": name,
                "period": str(year),
                "sort_year": year,
                "sort_month": None,
                "note": note,
            }
        )
    return rows


def _gk_rows(people: tuple[tuple[str, str], ...], end_start: int) -> list[dict]:
    rows = []
    for back, (name, note) in enumerate(people):
        start = end_start - back
        end = (start + 1) % 100
        rows.append(
            {
                "category": "past_gk",
                "name": name,
                "period": f"{start}{EN_DASH}{end:02d}",
                "sort_year": start,
                "sort_month": None,
                "note": note,
            }
        )
    return rows


def _with_photos(rows: list[dict]) -> list[dict]:
    prepared = []
    for index, item in enumerate(rows, start=1):
        path = f"backend/uploads/seed/honors/{item['category']}-{index:02d}.png"
        prepared.append({**item, "photo_path": path, "photo_type": "image/png"})
    return prepared


_KNIGHT_MONTH = (
    ("James Harrington", "He chaired the Coats for Kids sorting crew."),
    ("Peter Lang", "He organized the wheelchair mission delivery."),
    ("Marcus Webb", "He recruited three new members at the parish festival."),
    ("Owen Keller", "He led the Saturday pancake breakfast crew."),
    ("Nathan Cho", "He coordinated the blood-drive volunteer shift."),
    ("Elliot Marsh", "He repaired the hall tables before the fish fry."),
    ("Caleb Ruiz", "He drove veterans to the monthly social."),
    ("Dominic Price", "He ran the Tootsie Roll weekend with the youth helpers."),
    ("Isaac Romero", "He set up the living rosary in the parish courtyard."),
    ("Gabriel Santos", "He collected winter coats from the school families."),
    ("Felix Navarro", "He hosted the exemplification reception."),
    ("Hugo Bennett", "He kept the scholarship applications moving."),
    ("Adrian Cole", "He led the Keep Christ in Christmas card sale."),
    ("Wesley Grant", "He paired new members with sponsors."),
    ("Simon Pearce", "He cooked for the widows' luncheon."),
    ("Julian Hart", "He logged the council's charity hours for the report."),
    ("Vincent Rossi", "He built a ramp for a brother knight's porch."),
    ("Malcolm Reid", "He chaired the soccer challenge at the parish school."),
    ("Oscar Pham", "He delivered food boxes after the parish mission."),
    ("Leon Duarte", "He organized the corporate communion breakfast."),
)

_FAMILY_MONTH = (
    ("The Nguyen Family", "They led the parish food pantry weekend."),
    ("The Brennan Family", "They hosted the council picnic and watched the younger children."),
    ("The Alvarez Family", "They sorted coats and stayed through the distribution."),
    ("The Okonkwo Family", "They led the family rosary after Sunday Mass."),
    ("The Callahan Family", "They baked for the Lenten fish fry every Friday."),
    ("The Ramirez Family", "They welcomed new families at the membership drive."),
    ("The Patel Family", "They staffed the Special Olympics hydration tent."),
    ("The Kowalski Family", "They prepared the hall for the widows' luncheon."),
    ("The Park Family", "They ran the Christmas poster contest at the school."),
    ("The Moretti Family", "They delivered meals to homebound parishioners."),
    ("The Vasquez Family", "They helped measure children for winter coats."),
    ("The Thompson Family", "They kept the scholarship candy sale stocked."),
    ("The Carter Family", "They hosted a vocations dinner for seminarians."),
    ("The Donnelly Family", "They led the living nativity volunteers."),
    ("The Ortega Family", "They organized the parish festival kids' games."),
    ("The Wallace Family", "They drove the food-pantry truck that Saturday."),
    ("The Gallagher Family", "They prayed the rosary with the council each week."),
    ("The Santos Family", "They set up and cleared the pancake breakfast."),
    ("The Herrera Family", "They welcomed guests at the blood drive."),
    ("The Berg Family", "They packed ultrasound-initiative appeal letters."),
)

_KNIGHT_YEAR = (
    ("Robert Hale", "He logged charity hours each month and mentored new members."),
    ("Carl Mendel", "He kept the coat drive and the blood drive fully staffed."),
    ("Evan Brooks", "He revived the council's visit schedule for homebound brothers."),
    ("Hugh Salazar", "He led the soccer challenge and the free-throw contest."),
    ("Martin Ellison", "He balanced a full program calendar without missing a meeting."),
    ("Derek Fontaine", "He raised the scholarship fund past its goal."),
    ("Philip Okada", "He trained the new officers before the election."),
    ("George Lanier", "He organized disaster-relief collections after the spring storms."),
    ("Arthur Nguyen", "He grew the rosary attendance through the year."),
    ("Lawrence Kim", "He finished the hall accessibility repairs."),
    ("Raymond Doyle", "He chaired Coats for Kids from kickoff to the last delivery."),
    ("Clifford Barnes", "He mentored the youth programs through the school year."),
    ("Harold Ibarra", "He carried the ultrasound initiative appeal to every meeting."),
    ("Eugene Moss", "He kept the food pantry partnership running each month."),
    ("Walter Brennan", "He welcomed the largest exemplification class of the decade."),
    ("Francis Delgado", "He published the charity report the state council requested."),
    ("Albert Shaw", "He led the veterans' breakfast through the winter."),
    ("Clarence Holt", "He restored the council's contingent for the parish festival."),
    ("Bernard Cruz", "He paired every new knight with a working committee."),
    ("Stanley Peck", "He held the council's charity budget on target."),
)

_FAMILY_YEAR = (
    ("The Ortiz Family", "They hosted monthly rosaries and supported the scholarship fund."),
    ("The Lang Family", "They staffed every fish fry and the coat distribution."),
    ("The Webb Family", "They opened their home for the council's family prayer night."),
    ("The Keller Family", "They led the parish festival meal line."),
    ("The Cho Family", "They tutored students before the free-throw and soccer events."),
    ("The Marsh Family", "They visited homebound parishioners with the council each month."),
    ("The Ruiz Family", "They ran the Christmas poster contest and the card sale."),
    ("The Price Family", "They cooked the veterans' breakfast from January through November."),
    ("The Romero Family", "They kept the food pantry shelves labeled and full."),
    ("The Navarro Family", "They hosted seminarians during the vocations weekend."),
    ("The Bennett Family", "They organized rides for elderly members."),
    ("The Cole Family", "They prepared the hall for every major fundraiser."),
    ("The Pearce Family", "They led the family Mass ushers for the year."),
    ("The Hart Family", "They packed and delivered coats with their children."),
    ("The Rossi Family", "They chaired the Special Olympics family tent."),
    ("The Reid Family", "They supported the ultrasound initiative bake sales."),
    ("The Pham Family", "They welcomed new families at every membership drive."),
    ("The Duarte Family", "They kept the scholarship candy sale going each month."),
    ("The Mendel Family", "They hosted the corporate communion brunch."),
    ("The Fontaine Family", "They prayed with the council and staffed the blood drive."),
)

_PAST_GK = (
    ("William Grant", "He led the council through the Coats for Kids year."),
    ("Thomas Reilly", "He handed the council a balanced charity budget."),
    ("Edward Castillo", "He restarted the monthly family picnic."),
    ("Joseph Brennan", "He grew the roster and kept meetings on time."),
    ("Paul Griffin", "He launched the council's ultrasound initiative support."),
    ("Anthony Marino", "He guided the hall renovation to completion."),
    ("Charles Nguyen", "He strengthened the council's tie to the parish school."),
    ("Frank Kowalski", "He led through the year the blood drive doubled."),
    ("Stephen Walsh", "He installed a full slate of program directors."),
    ("Patrick Donnelly", "He hosted the district's exemplification."),
    ("Daniel Okonkwo", "He kept charity hours at the front of every meeting."),
    ("Michael Ruiz", "He opened meetings with a steady formation program."),
    ("Andrew Park", "He left the scholarship fund larger than he found it."),
    ("Christopher Walsh", "He organized the council's first Special Olympics team."),
    ("Timothy Brooks", "He renewed the food-pantry partnership."),
    ("Brian Callahan", "He led the widows' luncheon into an annual event."),
    ("Steven Alvarez", "He finished the year with every officer chair filled."),
    ("Kevin Moretti", "He carried Coats for Kids through a cold winter."),
    ("Ryan Thompson", "He set the council's visit schedule for homebound knights."),
    ("Matthew Carter", "He began the council's corporate communion tradition."),
)

# Twenty rows for each past-honor list. The five original examples stay in place.
HONOR_SEED: tuple[dict, ...] = tuple(
    _with_photos(_month_rows("knight_month", _KNIGHT_MONTH, 2025, 10))
    + _with_photos(_month_rows("family_month", _FAMILY_MONTH, 2025, 9))
    + _with_photos(_year_rows("knight_year", _KNIGHT_YEAR, 2025))
    + _with_photos(_year_rows("family_year", _FAMILY_YEAR, 2025))
    + _with_photos(_gk_rows(_PAST_GK, 2024))
)


def _check_seed() -> None:
    if len(MEMBER_SEED) != 50:
        raise RuntimeError(f"Expected 50 test members, found {len(MEMBER_SEED)}.")
    ids = [member.membership_id for member in MEMBER_SEED]
    if len(set(ids)) != len(ids):
        raise RuntimeError("Test membership ids are not unique.")
    if ids != [str(1000100 + index) for index in range(50)]:
        raise RuntimeError("Test membership ids must run from 1000100 through 1000149.")
    titles = [member.title for member in MEMBER_SEED if member.title]
    if len(titles) != len(set(titles)):
        raise RuntimeError("A test title is assigned twice.")
    if set(titles) != set(TITLE_ABBREVS) - {"GK"}:
        raise RuntimeError("Every title except GK must be held by one new member.")
    admins = [member for member in MEMBER_SEED if member.is_admin]
    if len(admins) < 3 or len(admins) == len(MEMBER_SEED):
        raise RuntimeError("The test roster needs a mix of admin and non-admin members.")
    for member in MEMBER_SEED:
        limit = 29 if member.birth_month == 2 else 30 if member.birth_month in (4, 6, 9, 11) else 31
        if member.birth_month < 1 or member.birth_month > 12 or member.birth_day < 1 or member.birth_day > limit:
            raise RuntimeError(f"Invalid birthday for {member.membership_id}.")
    october = sum(1 for member in MEMBER_SEED if member.birth_month == 10)
    november = sum(1 for member in MEMBER_SEED if member.birth_month == 11)
    if october < 6 or november < 6:
        raise RuntimeError("Birthdays need several dates in October and November.")
    counts: dict[str, int] = {}
    seen: set[tuple[str, str, str]] = set()
    for item in HONOR_SEED:
        key = (item["category"], item["name"], item["period"])
        if key in seen:
            raise RuntimeError(f"Duplicate honor: {key}.")
        seen.add(key)
        counts[item["category"]] = counts.get(item["category"], 0) + 1
        if len(item["name"]) > 80 or len(item["note"]) > 280:
            raise RuntimeError(f"Honor text is too long: {item['name']}.")
        if not item["photo_path"] or item["photo_type"] != "image/png":
            raise RuntimeError(f"Honor photo is missing: {item['name']}.")
    if counts != {
        "knight_month": 20,
        "family_month": 20,
        "knight_year": 20,
        "family_year": 20,
        "past_gk": 20,
    }:
        raise RuntimeError(f"Honor counts are wrong: {counts}.")


_check_seed()


def _hash(text: str) -> int:
    value = 2166136261
    for char in text:
        value ^= ord(char)
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def _png(width: int, height: int, pixel) -> bytes:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            red, green, blue = pixel(x, y)
            raw.extend((red & 255, green & 255, blue & 255))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(bytes(raw), 6)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


_SKIN = (
    (236, 206, 176),
    (222, 184, 146),
    (198, 154, 114),
    (168, 118, 84),
    (128, 86, 62),
    (96, 66, 48),
)
_HAIR = (
    (36, 26, 18),
    (74, 48, 28),
    (126, 88, 48),
    (48, 48, 52),
    (176, 176, 180),
    (22, 22, 24),
)
_SHIRTS = (
    (14, 36, 64),
    (110, 24, 40),
    (28, 62, 96),
    (24, 58, 48),
    (58, 46, 34),
    (32, 40, 72),
)


def _in_ellipse(x: int, y: int, cx: int, cy: int, rx: int, ry: int) -> bool:
    dx = x - cx
    dy = y - cy
    return dx * dx * ry * ry + dy * dy * rx * rx <= rx * rx * ry * ry


def _person(x: int, y: int, cx: int, skin, hair, shirt, accent, style: int, gold: bool):
    if _in_ellipse(x, y, cx, 96, 34, 28) and y >= 74:
        if abs(x - cx) <= 2 and y >= 80:
            return accent
        if gold and 76 <= y <= 80 and abs(x - cx) <= 20:
            return (201, 162, 39)
        return shirt
    dx = x - cx
    dy = y - 46
    if dx * dx + dy * dy <= 20 * 20:
        if style % 7 != 0 and (dy < -5 or (dy < 1 and abs(dx) > 13)):
            return hair
        if style % 5 == 1 and dy > 8 and dx * dx + (dy - 6) * (dy - 6) < 160:
            return hair
        if abs(dy) <= 1 and abs(abs(dx) - 7) <= 1:
            return (42, 32, 28)
        if dy == 8 and abs(dx) <= 4:
            return (150, 92, 84)
        return skin
    if 19 * 19 < dx * dx + dy * dy <= 23 * 23:
        return accent
    return None


def _portrait(key: str, kind: str) -> bytes:
    number = _hash(key + ":" + kind)
    width = 144 if kind == "family" else 96
    height = 112
    bg = (
        16 + (number % 36),
        28 + ((number // 3) % 32),
        48 + ((number // 7) % 40),
    )

    def paint(x: int, y: int):
        wash = (x * 2 + y + (number % 11)) % 18
        color = (
            min(255, bg[0] + wash // 2),
            min(255, bg[1] + wash // 3),
            min(255, bg[2] + wash // 2),
        )
        centers = (40, 104) if kind == "family" else (width // 2,)
        for offset, cx in enumerate(centers):
            style = number // (offset + 3)
            drawn = _person(
                x,
                y,
                cx,
                _SKIN[(style + offset) % len(_SKIN)],
                _HAIR[(style // 5 + offset) % len(_HAIR)],
                _SHIRTS[(style // 9 + offset) % len(_SHIRTS)],
                (
                    150 + (style % 80),
                    110 + ((style // 13) % 90),
                    36 + ((style // 17) % 70),
                ),
                style,
                kind == "gk",
            )
            if drawn is not None:
                return drawn
        return color

    return _png(width, height, paint)


def _write_png(relative: str, data: bytes) -> None:
    target = REPO_ROOT / relative
    if target.is_file() and target.stat().st_size > 32:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def ensure_seed_photos() -> None:
    """Write any missing roster and honor placeholder photos."""
    for member in MEMBER_SEED:
        _write_png(member_photo_path(member.membership_id), _portrait(member.membership_id, "member"))
    for item in HONOR_SEED:
        kind = "family" if item["category"] in {"family_month", "family_year"} else "knight"
        if item["category"] == "past_gk":
            kind = "gk"
        _write_png(item["photo_path"], _portrait(item["photo_path"], kind))


if __name__ == "__main__":
    ensure_seed_photos()
    print(f"Wrote photos for {len(MEMBER_SEED)} members and {len(HONOR_SEED)} honors.")
