"""Mockup copy used when Postgres is down, and to build schema.sql."""

from __future__ import annotations

from announcements import ANNOUNCEMENT_SEED
from nominations import NOMINATION_SEED
from prayers import PRAYER_SEED
from media import SEED_DOCUMENTS, SEED_IMAGES, slot_check_sql
from test_seed import HONOR_SEED
from titles import TITLE_ABBREVS


def text(key: str, value: str) -> dict:
    return {"key": key, "field_type": "text", "value": value}


def lines(key: str, value: str) -> dict:
    return {"key": key, "field_type": "lines", "value": value}


def with_order(blocks: list[dict]) -> list[dict]:
    return [{**block, "sort_order": index + 1} for index, block in enumerate(blocks)]


OFFICERS = [
    ("Chaplain", "Rev. Sample Pastor"),
    ("Grand Knight", "James Harrington"),
    ("Deputy Grand Knight", "Michael Ortiz"),
    ("Chancellor", "David Nguyen"),
    ("Recorder", "Paul Brennan"),
    ("Financial Secretary", "Robert Hale"),
    ("Treasurer", "Anthony Ruiz"),
    ("Lecturer", "Thomas Keller"),
    ("Advocate", "William Grant"),
    ("Warden", "Christopher Walsh"),
    ("Inside Guard", "Joseph Patel"),
    ("Outside Guard", "Andrew Brooks"),
    ("Trustee, 3rd year", "Edward Collins"),
    ("Trustee, 2nd year", "Patrick Moore"),
    ("Trustee, 1st year", "Steven Alvarez"),
]

DIRECTORS = [
    ("Program Director", "Sample Program Director"),
    ("Faith Director", "Sample Faith Director"),
    ("Family Director", "Sample Family Director"),
    ("Community Director", "Sample Community Director"),
    ("Life Director", "Sample Life Director"),
    ("Membership Director", "Sample Membership Director"),
]

EVENTS = [
    ("Tuesday, October 13, 2026 · 7:00 p.m.", "Online officers meeting"),
    ("Wednesday, October 14, 2026 · 6:40 p.m.", "Council rosary"),
    ("Wednesday, October 14, 2026 · 7:00 p.m.", "Council business meeting"),
    ("Saturday, October 24, 2026 · 9:00 a.m. to 3:00 p.m.", "Red Cross blood drive"),
    ("Saturday, November 14, 2026 · 8:00 a.m.", "Coats for Kids distribution"),
]

BANNER = "Charity \u00a0·\u00a0 Unity \u00a0·\u00a0 Fraternity \u00a0·\u00a0 Patriotism"

PUBLIC_BLOCKS = with_order(
    [
        text("brand.name", "Council 10930"),
        text("brand.sub", "Knights of Columbus"),
        text("nav.who", "Who We Are"),
        text("nav.what", "What We Do"),
        text("nav.why", "Why Join"),
        text("nav.join", "Join Us"),
        text("nav.signin", "Sign in"),
        text("hero.eyebrow", "Knights of Columbus"),
        text("hero.title", "Council 10930"),
        text("hero.place", "Fort Worth, Texas"),
        text("hero.cta", "Become a Knight"),
        text("slide.1.alt", "Council 10930 gathering"),
        text("slide.2.alt", "Knights of Columbus service"),
        text("slide.3.alt", "Council 10930 fellowship"),
        text("slide.4.alt", "Charity in action"),
        text("who.eyebrow", "Our Brotherhood"),
        text("who.title", "Who We Are"),
        text(
            "who.intro",
            "We are a council of practicing Catholic men, bound together by faith and by a shared duty to our parish, our families, and our neighbors.",
        ),
        text("who.mission.title", "Our Mission"),
        text(
            "who.mission.body",
            "We live out the Order\u2019s founding principles \u2014 charity, unity, fraternity, and patriotism \u2014 through prayer, service, and fellowship rooted in the Catholic faith.",
        ),
        text("who.parish.title", "Our Parish"),
        text(
            "who.parish.body",
            "We stand behind our parish in ways both visible and quiet: staffing ministries, funding needs, and showing up wherever the work is.",
        ),
        text("who.members.title", "Our Members"),
        text(
            "who.members.body",
            "We are fathers, husbands, tradesmen, and professionals \u2014 ordinary men trying, together, to live our faith a little better each day.",
        ),
        text("legacy.eyebrow", "A Legacy of Service"),
        text("legacy.1882.year", "1882"),
        text(
            "legacy.1882.body",
            "Father Michael J. McGivney founds the Knights of Columbus in New Haven, Connecticut, to support Catholic families in need.",
        ),
        text("legacy.1900s.year", "1900s"),
        text(
            "legacy.1900s.body",
            "The Order spreads across the country, chartering councils in parishes that needed a brotherhood of service.",
        ),
        text("legacy.today.year", "Today"),
        text(
            "legacy.today.body",
            "Council 10930 carries that same charter forward here in Fort Worth, one meeting and one act of charity at a time.",
        ),
        text("what.eyebrow", "In Practice"),
        text("what.title", "What We Do"),
        text(
            "what.intro",
            "Faith, family, community, and youth \u2014 the four pillars our council builds its year around.",
        ),
        text("what.faith.title", "Faith"),
        text(
            "what.faith.body",
            "Rosary devotions, Holy Hours, and retreats that keep prayer at the center of our brotherhood.",
        ),
        text("what.family.title", "Family"),
        text(
            "what.family.body",
            "Gatherings and ministries \u2014 from Christmas baskets to family rosary nights \u2014 that support our households.",
        ),
        text("what.community.title", "Community"),
        text(
            "what.community.body",
            "Food drives, Coats for Kids, and support for Special Olympics athletes across our community.",
        ),
        text("what.youth.title", "Youth"),
        text(
            "what.youth.body",
            "Scholarships, mentorship, and support for seminarians discerning a vocation to the priesthood.",
        ),
        text("banner", BANNER),
        text("why.eyebrow", "The Case for Joining"),
        text("why.title", "Why Join"),
        text(
            "why.intro",
            "Membership asks something of you \u2014 and gives back more than most men expect.",
        ),
        text("why.faith.title", "Grow in Faith"),
        text(
            "why.faith.body",
            "Deepen your relationship with Christ alongside men pursuing the same thing.",
        ),
        text("why.serve.title", "Serve Your Community"),
        text(
            "why.serve.body",
            "Put your time toward charity that has a visible, lasting impact nearby.",
        ),
        text("why.brotherhood.title", "Build Brotherhood"),
        text(
            "why.brotherhood.body",
            "Form the kind of friendships that hold up under real life.",
        ),
        text("why.lead.title", "Lead & Inspire"),
        text(
            "why.lead.body",
            "Take on leadership within the council \u2014 and carry it home to your family.",
        ),
        text("join.title", "Ready to Join Council 10930?"),
        text(
            "join.body",
            "Take the first step toward becoming a Knight. We\u2019ll walk you through it.",
        ),
        text("join.cta", "Begin Your Journey"),
        text("footer.name", "Council 10930"),
        text("footer.sub", "Knights of Columbus · Fort Worth, TX"),
        text("footer.nav.who", "Who We Are"),
        text("footer.nav.what", "What We Do"),
        text("footer.nav.why", "Why Join"),
        text("footer.nav.join", "Join Us"),
        text("footer.copy", "© 2026 Knights of Columbus Council 10930 — Fort Worth, TX"),
        text("footer.principles", "Charity · Unity · Fraternity · Patriotism"),
        text("signin.title", "Member sign in"),
        text("signin.membership", "Membership ID"),
        text("signin.password", "Password"),
        text("signin.submit", "Sign in"),
        text("signin.cancel", "Cancel"),
    ]
)

_member: list[dict] = [
    text("brand.name", "Council 10930"),
    text("brand.sub", "Knights of Columbus"),
    text("nav.about", "About"),
    text("nav.officers", "Officers"),
    text("nav.directors", "Directors"),
    text("nav.events", "Events"),
    text("nav.blood", "Blood Drive"),
    text("nav.links", "Member Links"),
    text("profile.name", "James Harrington"),
    text("hero.eyebrow", "Fort Worth, Texas"),
    text("hero.title", "Members Area"),
    text("hero.place", "Council 10930 · Signed in"),
    text("about.eyebrow", "When we gather"),
    text("about.title", "About Our Council"),
    text("sched.0.title", "Council Online Officers Meeting"),
    text("sched.0.body", "1st Tuesday of the month at 7:00 pm"),
    text("sched.1.title", "Council Rosary"),
    text("sched.1.body", "2nd Wednesday of the month at 6:40 pm"),
    text("sched.2.title", "Council Business Meeting"),
    text("sched.2.body", "2nd Wednesday of the month at 7:00 pm"),
    text("sched.3.title", "Meetings Location"),
    lines("sched.3.body", "5953 Bowman Roberts Rd\nFort Worth, TX 76179 US"),
    text("recog.0.title", "Family of the Month"),
    text("recog.0.body", "The sample family led the parish food pantry weekend."),
    text("recog.0.more", "Read More..."),
    text("recog.1.title", "Knight of the Month"),
    text("recog.1.body", "A brother chaired the Coats for Kids sorting crew."),
    text("recog.1.more", "Read More..."),
    text("recog.2.title", "Family of the Year"),
    text("recog.2.body", "Year-long support of scholarships and family rosary nights."),
    text("recog.2.more", "Read More..."),
    text("recog.3.title", "Knight of the Year"),
    text("recog.3.body", "Steady charity hours and mentoring of new members."),
    text("recog.3.more", "Read More..."),
    text("officers.eyebrow", "Fraternal year 2026\u201327"),
    text("officers.title", "Current Officers"),
    text(
        "officers.intro",
        "Congratulations to the brothers serving Council 10930 in 2026\u201327.",
    ),
]

for index, row in enumerate(OFFICERS):
    _member.append(text(f"officer.{index}.role", row[0]))
    _member.append(text(f"officer.{index}.name", row[1]))

_member.extend(
    [
        text("directors.eyebrow", "Fraternal year 2026\u201327"),
        text("directors.title", "Current Directors"),
        text(
            "directors.intro",
            "Program directors for the 2026\u201327 fraternal year.",
        ),
    ]
)

for index, row in enumerate(DIRECTORS):
    _member.append(text(f"director.{index}.role", row[0]))
    _member.append(text(f"director.{index}.name", row[1]))

_member.extend(
    [
        text("events.eyebrow", "On the calendar"),
        text("events.title", "Upcoming Council Events"),
    ]
)

for index, row in enumerate(EVENTS):
    _member.append(text(f"event.{index}.when", row[0]))
    _member.append(text(f"event.{index}.title", row[1]))
    _member.append(text(f"event.{index}.more", "Read More..."))

_member.extend(
    [
        text("blood.eyebrow", "Charity in practice"),
        text("blood.title", "Blood Drive"),
        text("blood.place", "5953 Bowman Roberts Rd, Fort Worth, TX 76179"),
        text("blood.when", "Saturday, October 24, 2026 · 9:00 a.m. to 3:00 p.m."),
        text("blood.before", "Schedule at"),
        text("blood.link", "RedCrossBlood.org"),
        text("blood.after", ". Walk-ins are taken as the schedule allows."),
        text("stat.0.value", "18"),
        text("stat.0.label", "Units last drive"),
        text("stat.1.value", "42"),
        text("stat.1.label", "Lives potentially helped"),
        text("stat.2.value", "7"),
        text("stat.2.label", "First-time donors"),
        text("links.eyebrow", "Brothers only"),
        text("links.title", "Members Quick Links"),
        text("links.intro", "Dues open in a new tab. Council lists stay here."),
        text("links.0.title", "Pay your annual dues"),
        text("links.0.body", "Annual dues \u2014 Regular $44.00"),
        text("links.0.action", "Pay annual dues online"),
        text("links.1.title", "Upcoming member birthdays"),
        text("links.1.action", "View birthdays"),
        text("links.1.detail", "Sample only. Replace with the current birthday roll."),
        text("links.2.title", "Announcements for members only"),
        text("links.2.action", "Read announcements"),
        text("links.2.detail", "Exemplification practice details stay off the public site."),
        text("links.3.title", "Prayer requests for members only"),
        text("links.3.action", "Open prayer list"),
        text(
            "links.3.detail",
            "Pray for the brothers and families who asked for a private intention.",
        ),
        text("links.4.title", "Members list"),
        text("links.4.action", "Open members list"),
        text(
            "links.4.detail",
            "Restricted. Request the current roll from the Financial Secretary.",
        ),
        text("links.6.title", "Share a comment with an officer"),
        text("links.6.action", "Write the council"),
        text(
            "links.6.detail",
            "Address the Grand Knight or a trustee. Do not post private remarks publicly.",
        ),
        text("links.9.title", "Volunteer hours and visits"),
        text("links.9.action", "How to record hours"),
        text("links.9.before", "Record hours and visits at"),
        text("links.9.link", "www.UKnightMobile.org"),
        text("links.9.after", "."),
        text("links.11.title", "Knight and Family of the Month"),
        text("links.11.action", "Submit a nomination"),
        text("links.11.detail", "Include the name and a short reason for the nomination."),
        text("links.12.title", "Financial Secretary library"),
        text("links.12.action", "Open FS reports"),
        text("links.12.detail", "Replace with the current Financial Secretary reports."),
        text("links.13.title", "Treasurer report library"),
        text("links.13.action", "Open treasurer reports"),
        text("links.13.detail", "Replace with the current treasurer statements."),
        text("links.14.title", "Budget and opening documents"),
        text("links.14.action", "Open documents"),
        text("links.14.detail", "Council budget and opening documents live here."),
        text("links.15.title", "Email the webmaster"),
        text("links.15.action", "Email webmaster"),
        text("footer.name", "Council 10930"),
        text("footer.sub", "Knights of Columbus · Fort Worth, TX"),
        text("footer.nav.about", "About"),
        text("footer.nav.officers", "Officers"),
        text("footer.nav.directors", "Directors"),
        text("footer.nav.events", "Events"),
        text("footer.nav.blood", "Blood Drive"),
        text("footer.nav.links", "Member Links"),
        text("footer.nav.public", "Public page"),
        text("footer.copy", "© 2026 Knights of Columbus Council 10930 — Fort Worth, TX"),
        text("footer.principles", "Charity · Unity · Fraternity · Patriotism"),
        text(
            "recog.0.detail",
            "Neighbors packed boxes on Saturday and delivered them to families after Sunday Mass.",
        ),
        text(
            "recog.1.detail",
            "He organized sizes, labeled bags, and stayed until every coat had a home.",
        ),
        text(
            "recog.2.detail",
            "The family hosted monthly rosaries and raised scholarship funds through the parish festival.",
        ),
        text(
            "recog.3.detail",
            "He logged charity hours each month and walked new members through their first meeting.",
        ),
        text(
            "event.0.detail",
            "Brothers meet online to review the month's business before the council meeting.",
        ),
        text(
            "event.1.detail",
            "The council prays the rosary together in the parish hall before the business meeting.",
        ),
        text(
            "event.2.detail",
            "Officers report, motions are heard, and brothers plan the next charity work.",
        ),
        text(
            "event.3.detail",
            "Give blood at the council hall. Appointments and walk-ins are both welcome.",
        ),
        text(
            "event.4.detail",
            "Sorted coats are handed out to families at the parish from the morning shift.",
        ),
        text("year.fraternal", "2026\u201327"),
    ]
)

MEMBER_BLOCKS = with_order(_member)

PAGES = {
    "public": PUBLIC_BLOCKS,
    "member": MEMBER_BLOCKS,
}


def _quote(value: str, tag: str) -> str:
    fence = tag
    while f"${fence}$" in value:
        fence += "x"
    return f"${fence}${value}${fence}$"


def _title_choices_sql() -> str:
    for abbrev in TITLE_ABBREVS:
        if not abbrev.isascii() or not abbrev.isalnum() or abbrev != abbrev.upper():
            raise RuntimeError(f"Unexpected title abbreviation: {abbrev}")
    return ", ".join(f"'{abbrev}'" for abbrev in TITLE_ABBREVS)


def _image_values_sql() -> str:
    rows = []
    for path, original, content_type, slot in SEED_IMAGES:
        rows.append(
            "  ("
            + ", ".join(
                [
                    f"'{path}'",
                    f"'{original}'",
                    f"'{content_type}'",
                    "'library'",
                    f"'{slot}'",
                ]
            )
            + ")"
        )
    return ",\n".join(rows)


# Same occasions the member page used to keep in content blocks.
EVENT_SEED: tuple[dict, ...] = (
    {
        "title": "Online officers meeting",
        "event_date": "2026-10-13",
        "event_time": "7:00 p.m.",
        "location": None,
        "description": "Brothers meet online to review the month's business before the council meeting.",
        "sort_order": 1,
    },
    {
        "title": "Council rosary",
        "event_date": "2026-10-14",
        "event_time": "6:40 p.m.",
        "location": "Parish hall",
        "description": "The council prays the rosary together in the parish hall before the business meeting.",
        "sort_order": 2,
    },
    {
        "title": "Council business meeting",
        "event_date": "2026-10-14",
        "event_time": "7:00 p.m.",
        "location": "Parish hall",
        "description": "Officers report, motions are heard, and brothers plan the next charity work.",
        "sort_order": 3,
    },
    {
        "title": "Red Cross blood drive",
        "event_date": "2026-10-24",
        "event_time": "9:00 a.m. to 3:00 p.m.",
        "location": "5953 Bowman Roberts Rd",
        "description": "Give blood at the council hall. Appointments and walk-ins are both welcome.",
        "sort_order": 4,
    },
    {
        "title": "Coats for Kids distribution",
        "event_date": "2026-11-14",
        "event_time": "8:00 a.m.",
        "location": "Parish",
        "description": "Sorted coats are handed out to families at the parish from the morning shift.",
        "sort_order": 5,
    },
)


def _sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def _honor_values_sql() -> str:
    rows = []
    for item in HONOR_SEED:
        month = "NULL::integer" if item["sort_month"] is None else f"{int(item['sort_month'])}::integer"
        rows.append(
            "("
            + ", ".join(
                [
                    _sql_text(item["category"]),
                    _sql_text(item["name"]),
                    _sql_text(item["period"]),
                    f"{int(item['sort_year'])}::integer",
                    month,
                    _sql_text(item["note"]),
                    _sql_text(item["photo_path"]),
                    _sql_text(item["photo_type"]),
                ]
            )
            + ")"
        )
    return ",\n  ".join(rows)


def honor_seed_sql() -> str:
    """Insert past-honor rows that are missing. Leave a cleared photo cleared."""
    honor_rows = _honor_values_sql()
    return f"""CREATE TEMP TABLE IF NOT EXISTS honor_seed_rows (
  category TEXT,
  name TEXT,
  period TEXT,
  sort_year INTEGER,
  sort_month INTEGER,
  note TEXT,
  photo_path TEXT,
  photo_type TEXT
) ON COMMIT DROP;

INSERT INTO honor_seed_rows (category, name, period, sort_year, sort_month, note, photo_path, photo_type)
VALUES
  {honor_rows};

INSERT INTO honors (category, name, period, sort_year, sort_month, note, photo_path, photo_type)
SELECT s.category, s.name, s.period, s.sort_year, s.sort_month, s.note, s.photo_path, s.photo_type
FROM honor_seed_rows s
WHERE NOT EXISTS (
  SELECT 1 FROM honors h
  WHERE h.category = s.category AND h.name = s.name AND h.period = s.period
);
"""


def documents_schema_sql() -> str:
    """Library table and example rows. A later schema load can restore a deleted example title."""
    value_rows = ",\n  ".join(
        "("
        + ", ".join(
            [
                _sql_text(item["library"]),
                _sql_text(item["title"]),
                _sql_text(item["description"]),
                _sql_text(item["file_path"]),
                _sql_text(item["original_name"]),
                _sql_text(item["content_type"]),
                _sql_text(item["uploaded_by"]),
                f"TIMESTAMPTZ {_sql_text(item['uploaded_at'])}",
            ]
        )
        + ")"
        for item in SEED_DOCUMENTS
    )
    return f"""CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  library TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  file_path TEXT NOT NULL,
  original_name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  uploaded_by TEXT,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT documents_library_chk CHECK (
    library IN ('treasurer', 'financial_secretary')
  )
);

CREATE INDEX IF NOT EXISTS documents_library_idx
  ON documents (library, uploaded_at DESC, id DESC);

INSERT INTO documents (
  library, title, description, file_path, original_name, content_type, uploaded_by, uploaded_at
)
SELECT v.library, v.title, v.description, v.file_path, v.original_name, v.content_type, v.uploaded_by, v.uploaded_at
FROM (
  VALUES
  {value_rows}
) AS v(library, title, description, file_path, original_name, content_type, uploaded_by, uploaded_at)
WHERE NOT EXISTS (
  SELECT 1 FROM documents d
  WHERE d.library = v.library AND d.title = v.title
);
"""


def announcements_schema_sql() -> str:
    """Announcement table and example rows. A later schema load can restore a deleted example title."""
    value_rows = ",\n  ".join(
        "("
        + ", ".join(
            [
                _sql_text(item["title"]),
                _sql_text(item["summary"]),
                _sql_text(item["body"]),
                _sql_text(item["created_by"]),
                f"TIMESTAMPTZ {_sql_text(item['created_at'])}",
                f"TIMESTAMPTZ {_sql_text(item['updated_at'])}",
            ]
        )
        + ")"
        for item in ANNOUNCEMENT_SEED
    )
    return f"""CREATE TABLE IF NOT EXISTS announcements (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS announcements_created_idx
  ON announcements (created_at DESC, id DESC);

INSERT INTO announcements (title, summary, body, created_by, created_at, updated_at)
SELECT v.title, v.summary, v.body, v.created_by, v.created_at, v.updated_at
FROM (
  VALUES
  {value_rows}
) AS v(title, summary, body, created_by, created_at, updated_at)
WHERE NOT EXISTS (
  SELECT 1 FROM announcements a
  WHERE a.title = v.title
);
"""


def prayers_schema_sql() -> str:
    """Prayer-request table and example rows. A later schema load can restore a deleted example."""
    value_rows = ",\n  ".join(
        "("
        + ", ".join(
            [
                _sql_text(item["member_id"]),
                _sql_text(item["title"]),
                _sql_text(item["body"]),
                f"TIMESTAMPTZ {_sql_text(item['created_at'])}",
                f"TIMESTAMPTZ {_sql_text(item['updated_at'])}",
            ]
        )
        + ")"
        for item in PRAYER_SEED
    )
    return f"""CREATE TABLE IF NOT EXISTS prayer_requests (
  id SERIAL PRIMARY KEY,
  member_id TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS prayer_requests_created_idx
  ON prayer_requests (created_at DESC, id DESC);

INSERT INTO prayer_requests (member_id, title, body, created_at, updated_at)
SELECT v.member_id, v.title, v.body, v.created_at, v.updated_at
FROM (
  VALUES
  {value_rows}
) AS v(member_id, title, body, created_at, updated_at)
WHERE NOT EXISTS (
  SELECT 1 FROM prayer_requests p
  WHERE p.member_id = v.member_id AND p.body = v.body
);
"""


def nominations_schema_sql() -> str:
    """Nomination table and example rows. A later schema load can restore a deleted example."""
    value_rows = ",\n  ".join(
        "("
        + ", ".join(
            [
                _sql_text(item["member_id"]),
                _sql_text(item["category"]),
                _sql_text(item.get("nominee_member_id")),
                _sql_text(item["nominee_name"]),
                _sql_text(item.get("reason") or ""),
                _sql_text(item["period"]),
                f"TIMESTAMPTZ {_sql_text(item['created_at'])}",
            ]
        )
        + ")"
        for item in NOMINATION_SEED
    )
    return f"""CREATE TABLE IF NOT EXISTS nominations (
  id SERIAL PRIMARY KEY,
  member_id TEXT NOT NULL,
  category TEXT NOT NULL,
  nominee_member_id TEXT,
  nominee_name TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  period TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT nominations_category_chk CHECK (
    category IN ('knight_month', 'family_month', 'knight_year', 'family_year')
  ),
  CONSTRAINT nominations_one_per_period UNIQUE (member_id, category, period)
);

CREATE INDEX IF NOT EXISTS nominations_period_idx
  ON nominations (period, category);

INSERT INTO nominations (
  member_id, category, nominee_member_id, nominee_name, reason, period, created_at
)
SELECT v.member_id, v.category, v.nominee_member_id, v.nominee_name, v.reason, v.period, v.created_at
FROM (
  VALUES
  {value_rows}
) AS v(member_id, category, nominee_member_id, nominee_name, reason, period, created_at)
WHERE NOT EXISTS (
  SELECT 1 FROM nominations n
  WHERE n.member_id = v.member_id AND n.category = v.category AND n.period = v.period
);
"""


def records_schema_sql() -> str:
    event_rows = ",\n  ".join(
        "("
        + ", ".join(
            [
                _sql_text(item["title"]),
                f"DATE {_sql_text(item['event_date'])}",
                _sql_text(item["event_time"]),
                _sql_text(item["location"]),
                _sql_text(item["description"]),
                str(item["sort_order"]),
            ]
        )
        + ")"
        for item in EVENT_SEED
    )
    return f"""CREATE TABLE IF NOT EXISTS honors (
  id SERIAL PRIMARY KEY,
  category TEXT NOT NULL,
  name TEXT NOT NULL,
  period TEXT NOT NULL,
  sort_year INTEGER NOT NULL,
  sort_month INTEGER,
  note TEXT NOT NULL DEFAULT '',
  photo_path TEXT,
  photo_type TEXT,
  crop_x DOUBLE PRECISION NOT NULL DEFAULT 0,
  crop_y DOUBLE PRECISION NOT NULL DEFAULT 0,
  crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1,
  CONSTRAINT honors_category_chk CHECK (
    category IN ('knight_month', 'family_month', 'knight_year', 'family_year', 'past_gk')
  ),
  CONSTRAINT honors_month_chk CHECK (
    (category IN ('knight_month', 'family_month') AND sort_month BETWEEN 1 AND 12)
    OR (category IN ('knight_year', 'family_year', 'past_gk') AND sort_month IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS honors_category_idx
  ON honors (category, sort_year DESC, sort_month DESC);

ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_x DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_y DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE honors ADD COLUMN IF NOT EXISTS crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS council_events (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  event_date DATE NOT NULL,
  event_time TEXT,
  location TEXT,
  description TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS council_events_date_idx
  ON council_events (event_date, id);

{honor_seed_sql().rstrip()}

INSERT INTO council_events (title, event_date, event_time, location, description, sort_order)
SELECT v.title, v.event_date, v.event_time, v.location, v.description, v.sort_order
FROM (
  VALUES
  {event_rows}
) AS v(title, event_date, event_time, location, description, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM council_events);

{documents_schema_sql().rstrip()}

{announcements_schema_sql().rstrip()}

{prayers_schema_sql().rstrip()}

{nominations_schema_sql().rstrip()}
"""


def render_schema() -> str:
    rows: list[str] = []
    for slug, blocks in PAGES.items():
        for block in blocks:
            tag = f"{slug}_{block['sort_order']}"
            rows.append(
                "  ("
                + ", ".join(
                    [
                        f"'{slug}'",
                        f"'{block['key']}'",
                        f"'{block['field_type']}'",
                        _quote(block["value"], tag),
                        str(block["sort_order"]),
                    ]
                )
                + ")"
            )
    values = ",\n".join(rows)
    title_choices = _title_choices_sql()
    image_values = _image_values_sql()
    slot_check = slot_check_sql()
    records_sql = records_schema_sql()
    birthday_check = """CHECK (
  (birth_month IS NULL AND birth_day IS NULL)
  OR (
    birth_month BETWEEN 1 AND 12
    AND birth_day BETWEEN 1 AND 31
    AND (
      (birth_month = 2 AND birth_day <= 29)
      OR (birth_month IN (4, 6, 9, 11) AND birth_day <= 30)
      OR (birth_month IN (1, 3, 5, 7, 8, 10, 12) AND birth_day <= 31)
    )
  )
)"""
    fraternal_year = "2026\u201327"
    return f"""-- Council 10930 schema and content seed.
-- Create the database, then run this file:
--   createdb koc10930
--   psql -d koc10930 -f backend/schema.sql
-- The API reads DATABASE_URL
-- (default postgresql://postgres:postgres@localhost:5432/koc10930).
-- Passwords are bcrypt hashes. The API creates membership id 1000000
-- on startup when that row is missing, with officer title GK, admin
-- access, and webmaster access. It also creates membership id 1000001
-- without admin or webmaster access.
-- Test roster ids 1000100 through 1000149 are created the same way.
-- They share the password Password123! with 1000000 (David Hernandez, GK, admin, webmaster)
-- and 1000001 (Sample Brother, not an admin).
-- Profile photos are images/seed/members/<membership id>.png.
-- A test-roster profile photo is attached only when that member row is first created.
-- You can also run:
--   .\\.venv\\Scripts\\python.exe backend\\seed_member.py
-- members.title stores one officer-title abbreviation, or NULL.
-- members.is_admin grants full edit access.
-- members.is_webmaster grants that same access plus Logs & activity.
-- Only a webmaster can grant or revoke webmaster access. The last webmaster stays.
-- members.birth_month and members.birth_day store a birthday, or both stay NULL.
-- members.honorary_life marks an Honorary Life Member.
-- members.phone and members.email are optional. The member list omits them for non-admins.
-- year.fraternal stores the current fraternal year, such as {fraternal_year}.
-- images holds the logo, carousel photos, About photos, uploads, and profile photos.
-- Profile photos store crop_x, crop_y, and crop_scale for the viewing angle.
-- About photos use slots recog.0 through recog.3.
-- Membership 1000000 is renamed to David Hernandez when the row still says Test Member.
-- honors stores past Knights and Families of the Month and Year, and Past Grand Knights.
-- Each of those five lists is seeded with 20 rows. A row is inserted when that
-- category, name, and period are not already stored. Photos are
-- backend/uploads/seed/honors/<category>-NN.png.
-- honors.crop_x, crop_y, and crop_scale store the viewing angle.
-- A cleared honor photo is not filled back in.
-- council_events stores the member-view upcoming events.
-- council_events example rows are inserted when that table is empty.
-- documents stores treasurer and financial secretary library files.
-- library is treasurer or financial_secretary. uploaded_by is a membership id
-- with no foreign key, so example rows can be stored before members exist.
-- Example rows are inserted when that library and title are not already stored.
-- The API inserts those examples only when the documents table is first created.
-- Files are backend/uploads/treasurer/ and backend/uploads/financial-secretary/.
-- announcements stores member-only notices. body is sanitized HTML.
-- Example rows are inserted when that title is not already stored.
-- The API inserts those examples only when the announcements table is first created.
-- prayer_requests stores member-only intentions. title and body are plain text.
-- member_id is a membership id with no foreign key.
-- Example rows are inserted when that member and prayer text are not already stored.
-- The API inserts those examples only when the prayer_requests table is first created.
-- nominations stores one Knight or Family nomination per member, category, and period.
-- member_id is the voter. nominee_member_id is set for knight awards and has no foreign key.
-- period is YYYY-MM for month awards and YYYY for year awards.
-- Example rows are inserted when that voter, category, and period are not already stored.
-- The API inserts those examples only when the nominations table is first created.

BEGIN;

CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  membership_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  title TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  is_webmaster BOOLEAN NOT NULL DEFAULT FALSE,
  birth_month SMALLINT,
  birth_day SMALLINT,
  honorary_life BOOLEAN NOT NULL DEFAULT FALSE,
  phone TEXT,
  email TEXT
);

ALTER TABLE members ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_webmaster BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_month SMALLINT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_day SMALLINT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS honorary_life BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE members ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS email TEXT;

UPDATE members
SET honorary_life = TRUE, phone = '(817) 555-0140', email = 'david.hernandez@example.com'
WHERE membership_id = '1000000' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
UPDATE members
SET phone = '(817) 555-0142', email = 'christopher.nguyen@example.com'
WHERE membership_id = '1000104' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
UPDATE members
SET phone = '(817) 555-0144', email = 'andrew.callahan@example.com'
WHERE membership_id = '1000105' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
UPDATE members
SET honorary_life = TRUE, phone = '(817) 555-0168', email = 'richard.donnelly@example.com'
WHERE membership_id = '1000121' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
UPDATE members
SET honorary_life = TRUE, phone = '(817) 555-0176', email = 'walter.shaw@example.com'
WHERE membership_id = '1000135' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
UPDATE members
SET honorary_life = TRUE
WHERE membership_id = '1000144' AND honorary_life = FALSE AND phone IS NULL AND email IS NULL;
ALTER TABLE members DROP CONSTRAINT IF EXISTS members_title_abbrev;
ALTER TABLE members ADD CONSTRAINT members_title_abbrev
  CHECK (title IS NULL OR title IN ({title_choices}));
ALTER TABLE members DROP CONSTRAINT IF EXISTS members_birthday_chk;
ALTER TABLE members ADD CONSTRAINT members_birthday_chk
  {birthday_check};

CREATE TABLE IF NOT EXISTS refresh_tokens (
  jti TEXT PRIMARY KEY,
  membership_id TEXT NOT NULL REFERENCES members (membership_id) ON DELETE CASCADE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS refresh_tokens_member_idx ON refresh_tokens (membership_id);

CREATE TABLE IF NOT EXISTS pages (
  id SERIAL PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS content_blocks (
  id SERIAL PRIMARY KEY,
  page_id INTEGER NOT NULL REFERENCES pages (id) ON DELETE CASCADE,
  "key" TEXT NOT NULL,
  field_type TEXT NOT NULL,
  value TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (page_id, "key")
);

INSERT INTO pages (slug)
VALUES ('public'), ('member')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO content_blocks (page_id, "key", field_type, value, sort_order)
SELECT p.id, v.block_key, v.field_type, v.value, v.sort_order
FROM (
  VALUES
{values}
) AS v(slug, block_key, field_type, value, sort_order)
JOIN pages p ON p.slug = v.slug
ON CONFLICT (page_id, "key") DO NOTHING;

INSERT INTO content_blocks (page_id, "key", field_type, value, sort_order)
SELECT p.id, 'year.fraternal', 'text', $v${fraternal_year}$v$, 200
FROM pages p
WHERE p.slug = 'member'
ON CONFLICT (page_id, "key") DO NOTHING;

CREATE TABLE IF NOT EXISTS images (
  id SERIAL PRIMARY KEY,
  path TEXT NOT NULL,
  original_name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  purpose TEXT NOT NULL DEFAULT 'library',
  slot TEXT,
  owner_membership_id TEXT REFERENCES members (membership_id) ON DELETE SET NULL,
  crop_x DOUBLE PRECISION NOT NULL DEFAULT 0,
  crop_y DOUBLE PRECISION NOT NULL DEFAULT 0,
  crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT images_purpose_chk CHECK (purpose IN ('library', 'profile')),
  CONSTRAINT images_slot_chk {slot_check}
);

ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_x DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_y DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1;
ALTER TABLE images DROP CONSTRAINT IF EXISTS images_slot_chk;
ALTER TABLE images ADD CONSTRAINT images_slot_chk {slot_check};

CREATE UNIQUE INDEX IF NOT EXISTS images_slot_idx
  ON images (slot) WHERE slot IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS images_profile_idx
  ON images (owner_membership_id) WHERE purpose = 'profile';

INSERT INTO images (path, original_name, content_type, purpose, slot)
SELECT v.path, v.original_name, v.content_type, v.purpose, v.slot
FROM (
  VALUES
{image_values}
) AS v(path, original_name, content_type, purpose, slot)
WHERE NOT EXISTS (
  SELECT 1 FROM images i WHERE i.path = v.path OR (v.slot IS NOT NULL AND i.slot = v.slot)
);

UPDATE members
SET display_name = 'David Hernandez'
WHERE membership_id = '1000000'
  AND display_name = 'Test Member';

UPDATE members
SET is_admin = TRUE,
    title = COALESCE(title, 'GK')
WHERE membership_id = '1000000'
  AND NOT EXISTS (SELECT 1 FROM members WHERE is_admin);

UPDATE members
SET is_webmaster = TRUE
WHERE membership_id = '1000000'
  AND NOT EXISTS (SELECT 1 FROM members WHERE is_webmaster);

{records_sql}
COMMIT;
"""


if __name__ == "__main__":
    from pathlib import Path

    from test_seed import ensure_seed_photos

    ensure_seed_photos()
    target = Path(__file__).with_name("schema.sql")
    target.write_text(render_schema(), encoding="utf-8")
    print(f"Wrote {target}")
