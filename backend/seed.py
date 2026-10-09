"""Mockup copy used when Postgres is down, and to build schema.sql."""

from __future__ import annotations


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
            "Program directors for the 2026\u201327 fraternal year. Replace the sample names.",
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
        text("links.5.title", "Our elder statesmen"),
        text("links.5.action", "View honor roll"),
        text("links.5.detail", "Replace with the elder statesmen list."),
        text("links.6.title", "Share a comment with an officer"),
        text("links.6.action", "Write the council"),
        text(
            "links.6.detail",
            "Address the Grand Knight or a trustee. Do not post private remarks publicly.",
        ),
        text("links.7.title", "SFS officer roles"),
        text("links.7.action", "Open role guide"),
        text("links.7.detail", "Officer duty summaries belong in this members library."),
        text("links.8.title", "Event management center"),
        text("links.8.action", "Open chairmen tools"),
        text("links.8.detail", "Confirm the parish calendar before an event is announced."),
        text("links.9.title", "Volunteer hours and visits"),
        text("links.9.action", "How to record hours"),
        text("links.9.before", "Record hours and visits at"),
        text("links.9.link", "www.UKnightMobile.org"),
        text("links.9.after", "."),
        text("links.10.title", "Hours goal & blood donor status"),
        text(
            "links.10.body",
            "Your Goal for this year (2026) is 0.00 hours per month. You are not a blood donor.",
        ),
        text("links.10.action", "Update goal"),
        text(
            "links.10.detail",
            "Your Goal for this year (2026) is 0.00 hours per month. You are not a blood donor.",
        ),
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
    ]
)

MEMBER_BLOCKS = with_order(_member)

MEMBERS = [
    {
        "membership_id": "10930",
        "password_hash": "sha256:demo-not-checked",
        "display_name": "James Harrington",
    }
]

PAGES = {
    "public": PUBLIC_BLOCKS,
    "member": MEMBER_BLOCKS,
}


def _quote(value: str, tag: str) -> str:
    fence = tag
    while f"${fence}$" in value:
        fence += "x"
    return f"${fence}${value}${fence}$"


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
    return f"""-- Council 10930 schema and mockup seed.
-- Create the database, then run this file:
--   createdb koc10930
--   psql -d koc10930 -f backend/schema.sql
-- The API reads DATABASE_URL
-- (default postgresql://postgres:postgres@localhost:5432/koc10930).
-- Login accepts any membership id and password. The hash below is not checked.

BEGIN;

CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  membership_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL
);

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

INSERT INTO members (membership_id, password_hash, display_name)
VALUES ('10930', 'sha256:demo-not-checked', 'James Harrington')
ON CONFLICT (membership_id) DO NOTHING;

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

COMMIT;
"""


if __name__ == "__main__":
    from pathlib import Path

    target = Path(__file__).with_name("schema.sql")
    target.write_text(render_schema(), encoding="utf-8")
    print(f"Wrote {target}")
