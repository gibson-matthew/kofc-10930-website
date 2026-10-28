"""Officer titles stored on members.title and shown before the member's name."""

from __future__ import annotations

# Abbreviation is what the site shows: "GK John Smith".
TITLE_CHOICES: tuple[tuple[str, str], ...] = (
    ("Grand Knight", "GK"),
    ("Deputy Grand Knight", "DGK"),
    ("Chancellor", "CH"),
    ("Chaplain", "CHP"),
    ("Recorder", "REC"),
    ("Financial Secretary", "FS"),
    ("Treasurer", "TR"),
    ("Advocate", "ADV"),
    ("Warden", "WRD"),
    ("Inside Guard", "IG"),
    ("Outside Guard", "OG"),
    ("Lecturer", "LEC"),
    ("Trustee 1-Year", "T1"),
    ("Trustee 2-Year", "T2"),
    ("Trustee 3-Year", "T3"),
    ("Program Director", "PD"),
    ("Membership Director", "MD"),
    ("Faith Director", "FD"),
    ("Family Director", "FAM"),
    ("Community Director", "COM"),
    ("Life Director", "LIFE"),
    ("Vocations Director", "VOC"),
    ("Past Grand Knight", "PGK"),
)

TITLE_ABBREVS: tuple[str, ...] = tuple(abbrev for _, abbrev in TITLE_CHOICES)
TITLE_ABBREV_SET = frozenset(TITLE_ABBREVS)

# Current Officers, in the order the member page already shows them.
OFFICER_ROLE_ABBREVS: tuple[str, ...] = (
    "CHP",
    "GK",
    "DGK",
    "CH",
    "REC",
    "FS",
    "TR",
    "LEC",
    "ADV",
    "WRD",
    "IG",
    "OG",
    "T3",
    "T2",
    "T1",
)
# Current Directors, in the order the member page already shows them.
DIRECTOR_ROLE_ABBREVS: tuple[str, ...] = ("PD", "FD", "FAM", "COM", "LIFE", "MD")
OFFICER_ROLE_SET = frozenset(OFFICER_ROLE_ABBREVS)
DIRECTOR_ROLE_SET = frozenset(DIRECTOR_ROLE_ABBREVS)


class TitleError(ValueError):
    pass


def normalize_title(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    if not cleaned:
        return None
    if cleaned not in TITLE_ABBREV_SET:
        raise TitleError("Unknown officer title.")
    return cleaned
