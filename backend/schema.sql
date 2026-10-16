-- Council 10930 schema and content seed.
-- Create the database, then run this file:
--   createdb koc10930
--   psql -d koc10930 -f backend/schema.sql
-- The API reads DATABASE_URL
-- (default postgresql://postgres:postgres@localhost:5432/koc10930).
-- Passwords are bcrypt hashes. The API creates membership id 1000000
-- on startup when that row is missing, with officer title GK and admin
-- access. It also creates membership id 1000001 without admin access.
-- Test roster ids 1000100 through 1000149 are created the same way.
-- They share the password Password123! with 1000000 (David Hernandez, GK, admin)
-- and 1000001 (Sample Brother, not an admin).
-- Profile photos are images/seed/members/<membership id>.png.
-- A test-roster profile photo is attached only when that member row is first created.
-- You can also run:
--   .\.venv\Scripts\python.exe backend\seed_member.py
-- members.title stores one officer-title abbreviation, or NULL.
-- members.is_admin grants full edit access.
-- members.birth_month and members.birth_day store a birthday, or both stay NULL.
-- year.fraternal stores the current fraternal year, such as 2026–27.
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

BEGIN;

CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  membership_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  title TEXT,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  birth_month SMALLINT,
  birth_day SMALLINT
);

ALTER TABLE members ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_month SMALLINT;
ALTER TABLE members ADD COLUMN IF NOT EXISTS birth_day SMALLINT;
ALTER TABLE members DROP CONSTRAINT IF EXISTS members_title_abbrev;
ALTER TABLE members ADD CONSTRAINT members_title_abbrev
  CHECK (title IS NULL OR title IN ('GK', 'DGK', 'CH', 'CHP', 'REC', 'FS', 'TR', 'ADV', 'WRD', 'IG', 'OG', 'LEC', 'T1', 'T2', 'T3', 'PD', 'MD', 'FD', 'FAM', 'COM', 'LIFE', 'VOC', 'PGK'));
ALTER TABLE members DROP CONSTRAINT IF EXISTS members_birthday_chk;
ALTER TABLE members ADD CONSTRAINT members_birthday_chk CHECK (
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
);

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
  ('public', 'brand.name', 'text', $v$Council 10930$v$, 1),
  ('public', 'brand.sub', 'text', $v$Knights of Columbus$v$, 2),
  ('public', 'nav.who', 'text', $v$Who We Are$v$, 3),
  ('public', 'nav.what', 'text', $v$What We Do$v$, 4),
  ('public', 'nav.why', 'text', $v$Why Join$v$, 5),
  ('public', 'nav.join', 'text', $v$Join Us$v$, 6),
  ('public', 'nav.signin', 'text', $v$Sign in$v$, 7),
  ('public', 'hero.eyebrow', 'text', $v$Knights of Columbus$v$, 8),
  ('public', 'hero.title', 'text', $v$Council 10930$v$, 9),
  ('public', 'hero.place', 'text', $v$Fort Worth, Texas$v$, 10),
  ('public', 'hero.cta', 'text', $v$Become a Knight$v$, 11),
  ('public', 'slide.1.alt', 'text', $v$Council 10930 gathering$v$, 12),
  ('public', 'slide.2.alt', 'text', $v$Knights of Columbus service$v$, 13),
  ('public', 'slide.3.alt', 'text', $v$Council 10930 fellowship$v$, 14),
  ('public', 'slide.4.alt', 'text', $v$Charity in action$v$, 15),
  ('public', 'who.eyebrow', 'text', $v$Our Brotherhood$v$, 16),
  ('public', 'who.title', 'text', $v$Who We Are$v$, 17),
  ('public', 'who.intro', 'text', $v$We are a council of practicing Catholic men, bound together by faith and by a shared duty to our parish, our families, and our neighbors.$v$, 18),
  ('public', 'who.mission.title', 'text', $v$Our Mission$v$, 19),
  ('public', 'who.mission.body', 'text', $v$We live out the Order’s founding principles — charity, unity, fraternity, and patriotism — through prayer, service, and fellowship rooted in the Catholic faith.$v$, 20),
  ('public', 'who.parish.title', 'text', $v$Our Parish$v$, 21),
  ('public', 'who.parish.body', 'text', $v$We stand behind our parish in ways both visible and quiet: staffing ministries, funding needs, and showing up wherever the work is.$v$, 22),
  ('public', 'who.members.title', 'text', $v$Our Members$v$, 23),
  ('public', 'who.members.body', 'text', $v$We are fathers, husbands, tradesmen, and professionals — ordinary men trying, together, to live our faith a little better each day.$v$, 24),
  ('public', 'legacy.eyebrow', 'text', $v$A Legacy of Service$v$, 25),
  ('public', 'legacy.1882.year', 'text', $v$1882$v$, 26),
  ('public', 'legacy.1882.body', 'text', $v$Father Michael J. McGivney founds the Knights of Columbus in New Haven, Connecticut, to support Catholic families in need.$v$, 27),
  ('public', 'legacy.1900s.year', 'text', $v$1900s$v$, 28),
  ('public', 'legacy.1900s.body', 'text', $v$The Order spreads across the country, chartering councils in parishes that needed a brotherhood of service.$v$, 29),
  ('public', 'legacy.today.year', 'text', $v$Today$v$, 30),
  ('public', 'legacy.today.body', 'text', $v$Council 10930 carries that same charter forward here in Fort Worth, one meeting and one act of charity at a time.$v$, 31),
  ('public', 'what.eyebrow', 'text', $v$In Practice$v$, 32),
  ('public', 'what.title', 'text', $v$What We Do$v$, 33),
  ('public', 'what.intro', 'text', $v$Faith, family, community, and youth — the four pillars our council builds its year around.$v$, 34),
  ('public', 'what.faith.title', 'text', $v$Faith$v$, 35),
  ('public', 'what.faith.body', 'text', $v$Rosary devotions, Holy Hours, and retreats that keep prayer at the center of our brotherhood.$v$, 36),
  ('public', 'what.family.title', 'text', $v$Family$v$, 37),
  ('public', 'what.family.body', 'text', $v$Gatherings and ministries — from Christmas baskets to family rosary nights — that support our households.$v$, 38),
  ('public', 'what.community.title', 'text', $v$Community$v$, 39),
  ('public', 'what.community.body', 'text', $v$Food drives, Coats for Kids, and support for Special Olympics athletes across our community.$v$, 40),
  ('public', 'what.youth.title', 'text', $v$Youth$v$, 41),
  ('public', 'what.youth.body', 'text', $v$Scholarships, mentorship, and support for seminarians discerning a vocation to the priesthood.$v$, 42),
  ('public', 'banner', 'text', $v$Charity  ·  Unity  ·  Fraternity  ·  Patriotism$v$, 43),
  ('public', 'why.eyebrow', 'text', $v$The Case for Joining$v$, 44),
  ('public', 'why.title', 'text', $v$Why Join$v$, 45),
  ('public', 'why.intro', 'text', $v$Membership asks something of you — and gives back more than most men expect.$v$, 46),
  ('public', 'why.faith.title', 'text', $v$Grow in Faith$v$, 47),
  ('public', 'why.faith.body', 'text', $v$Deepen your relationship with Christ alongside men pursuing the same thing.$v$, 48),
  ('public', 'why.serve.title', 'text', $v$Serve Your Community$v$, 49),
  ('public', 'why.serve.body', 'text', $v$Put your time toward charity that has a visible, lasting impact nearby.$v$, 50),
  ('public', 'why.brotherhood.title', 'text', $v$Build Brotherhood$v$, 51),
  ('public', 'why.brotherhood.body', 'text', $v$Form the kind of friendships that hold up under real life.$v$, 52),
  ('public', 'why.lead.title', 'text', $v$Lead & Inspire$v$, 53),
  ('public', 'why.lead.body', 'text', $v$Take on leadership within the council — and carry it home to your family.$v$, 54),
  ('public', 'join.title', 'text', $v$Ready to Join Council 10930?$v$, 55),
  ('public', 'join.body', 'text', $v$Take the first step toward becoming a Knight. We’ll walk you through it.$v$, 56),
  ('public', 'join.cta', 'text', $v$Begin Your Journey$v$, 57),
  ('public', 'footer.name', 'text', $v$Council 10930$v$, 58),
  ('public', 'footer.sub', 'text', $v$Knights of Columbus · Fort Worth, TX$v$, 59),
  ('public', 'footer.nav.who', 'text', $v$Who We Are$v$, 60),
  ('public', 'footer.nav.what', 'text', $v$What We Do$v$, 61),
  ('public', 'footer.nav.why', 'text', $v$Why Join$v$, 62),
  ('public', 'footer.nav.join', 'text', $v$Join Us$v$, 63),
  ('public', 'footer.copy', 'text', $v$© 2026 Knights of Columbus Council 10930 — Fort Worth, TX$v$, 64),
  ('public', 'footer.principles', 'text', $v$Charity · Unity · Fraternity · Patriotism$v$, 65),
  ('public', 'signin.title', 'text', $v$Member sign in$v$, 66),
  ('public', 'signin.membership', 'text', $v$Membership ID$v$, 67),
  ('public', 'signin.password', 'text', $v$Password$v$, 68),
  ('public', 'signin.submit', 'text', $v$Sign in$v$, 69),
  ('public', 'signin.cancel', 'text', $v$Cancel$v$, 70),
  ('member', 'brand.name', 'text', $v$Council 10930$v$, 1),
  ('member', 'brand.sub', 'text', $v$Knights of Columbus$v$, 2),
  ('member', 'nav.about', 'text', $v$About$v$, 3),
  ('member', 'nav.officers', 'text', $v$Officers$v$, 4),
  ('member', 'nav.directors', 'text', $v$Directors$v$, 5),
  ('member', 'nav.events', 'text', $v$Events$v$, 6),
  ('member', 'nav.blood', 'text', $v$Blood Drive$v$, 7),
  ('member', 'nav.links', 'text', $v$Member Links$v$, 8),
  ('member', 'profile.name', 'text', $v$James Harrington$v$, 9),
  ('member', 'hero.eyebrow', 'text', $v$Fort Worth, Texas$v$, 10),
  ('member', 'hero.title', 'text', $v$Members Area$v$, 11),
  ('member', 'hero.place', 'text', $v$Council 10930 · Signed in$v$, 12),
  ('member', 'about.eyebrow', 'text', $v$When we gather$v$, 13),
  ('member', 'about.title', 'text', $v$About Our Council$v$, 14),
  ('member', 'sched.0.title', 'text', $v$Council Online Officers Meeting$v$, 15),
  ('member', 'sched.0.body', 'text', $v$1st Tuesday of the month at 7:00 pm$v$, 16),
  ('member', 'sched.1.title', 'text', $v$Council Rosary$v$, 17),
  ('member', 'sched.1.body', 'text', $v$2nd Wednesday of the month at 6:40 pm$v$, 18),
  ('member', 'sched.2.title', 'text', $v$Council Business Meeting$v$, 19),
  ('member', 'sched.2.body', 'text', $v$2nd Wednesday of the month at 7:00 pm$v$, 20),
  ('member', 'sched.3.title', 'text', $v$Meetings Location$v$, 21),
  ('member', 'sched.3.body', 'lines', $v$5953 Bowman Roberts Rd
Fort Worth, TX 76179 US$v$, 22),
  ('member', 'recog.0.title', 'text', $v$Family of the Month$v$, 23),
  ('member', 'recog.0.body', 'text', $v$The sample family led the parish food pantry weekend.$v$, 24),
  ('member', 'recog.0.more', 'text', $v$Read More...$v$, 25),
  ('member', 'recog.1.title', 'text', $v$Knight of the Month$v$, 26),
  ('member', 'recog.1.body', 'text', $v$A brother chaired the Coats for Kids sorting crew.$v$, 27),
  ('member', 'recog.1.more', 'text', $v$Read More...$v$, 28),
  ('member', 'recog.2.title', 'text', $v$Family of the Year$v$, 29),
  ('member', 'recog.2.body', 'text', $v$Year-long support of scholarships and family rosary nights.$v$, 30),
  ('member', 'recog.2.more', 'text', $v$Read More...$v$, 31),
  ('member', 'recog.3.title', 'text', $v$Knight of the Year$v$, 32),
  ('member', 'recog.3.body', 'text', $v$Steady charity hours and mentoring of new members.$v$, 33),
  ('member', 'recog.3.more', 'text', $v$Read More...$v$, 34),
  ('member', 'officers.eyebrow', 'text', $v$Fraternal year 2026–27$v$, 35),
  ('member', 'officers.title', 'text', $v$Current Officers$v$, 36),
  ('member', 'officers.intro', 'text', $v$Congratulations to the brothers serving Council 10930 in 2026–27.$v$, 37),
  ('member', 'officer.0.role', 'text', $v$Chaplain$v$, 38),
  ('member', 'officer.0.name', 'text', $v$Rev. Sample Pastor$v$, 39),
  ('member', 'officer.1.role', 'text', $v$Grand Knight$v$, 40),
  ('member', 'officer.1.name', 'text', $v$James Harrington$v$, 41),
  ('member', 'officer.2.role', 'text', $v$Deputy Grand Knight$v$, 42),
  ('member', 'officer.2.name', 'text', $v$Michael Ortiz$v$, 43),
  ('member', 'officer.3.role', 'text', $v$Chancellor$v$, 44),
  ('member', 'officer.3.name', 'text', $v$David Nguyen$v$, 45),
  ('member', 'officer.4.role', 'text', $v$Recorder$v$, 46),
  ('member', 'officer.4.name', 'text', $v$Paul Brennan$v$, 47),
  ('member', 'officer.5.role', 'text', $v$Financial Secretary$v$, 48),
  ('member', 'officer.5.name', 'text', $v$Robert Hale$v$, 49),
  ('member', 'officer.6.role', 'text', $v$Treasurer$v$, 50),
  ('member', 'officer.6.name', 'text', $v$Anthony Ruiz$v$, 51),
  ('member', 'officer.7.role', 'text', $v$Lecturer$v$, 52),
  ('member', 'officer.7.name', 'text', $v$Thomas Keller$v$, 53),
  ('member', 'officer.8.role', 'text', $v$Advocate$v$, 54),
  ('member', 'officer.8.name', 'text', $v$William Grant$v$, 55),
  ('member', 'officer.9.role', 'text', $v$Warden$v$, 56),
  ('member', 'officer.9.name', 'text', $v$Christopher Walsh$v$, 57),
  ('member', 'officer.10.role', 'text', $v$Inside Guard$v$, 58),
  ('member', 'officer.10.name', 'text', $v$Joseph Patel$v$, 59),
  ('member', 'officer.11.role', 'text', $v$Outside Guard$v$, 60),
  ('member', 'officer.11.name', 'text', $v$Andrew Brooks$v$, 61),
  ('member', 'officer.12.role', 'text', $v$Trustee, 3rd year$v$, 62),
  ('member', 'officer.12.name', 'text', $v$Edward Collins$v$, 63),
  ('member', 'officer.13.role', 'text', $v$Trustee, 2nd year$v$, 64),
  ('member', 'officer.13.name', 'text', $v$Patrick Moore$v$, 65),
  ('member', 'officer.14.role', 'text', $v$Trustee, 1st year$v$, 66),
  ('member', 'officer.14.name', 'text', $v$Steven Alvarez$v$, 67),
  ('member', 'directors.eyebrow', 'text', $v$Fraternal year 2026–27$v$, 68),
  ('member', 'directors.title', 'text', $v$Current Directors$v$, 69),
  ('member', 'directors.intro', 'text', $v$Program directors for the 2026–27 fraternal year.$v$, 70),
  ('member', 'director.0.role', 'text', $v$Program Director$v$, 71),
  ('member', 'director.0.name', 'text', $v$Sample Program Director$v$, 72),
  ('member', 'director.1.role', 'text', $v$Faith Director$v$, 73),
  ('member', 'director.1.name', 'text', $v$Sample Faith Director$v$, 74),
  ('member', 'director.2.role', 'text', $v$Family Director$v$, 75),
  ('member', 'director.2.name', 'text', $v$Sample Family Director$v$, 76),
  ('member', 'director.3.role', 'text', $v$Community Director$v$, 77),
  ('member', 'director.3.name', 'text', $v$Sample Community Director$v$, 78),
  ('member', 'director.4.role', 'text', $v$Life Director$v$, 79),
  ('member', 'director.4.name', 'text', $v$Sample Life Director$v$, 80),
  ('member', 'director.5.role', 'text', $v$Membership Director$v$, 81),
  ('member', 'director.5.name', 'text', $v$Sample Membership Director$v$, 82),
  ('member', 'events.eyebrow', 'text', $v$On the calendar$v$, 83),
  ('member', 'events.title', 'text', $v$Upcoming Council Events$v$, 84),
  ('member', 'event.0.when', 'text', $v$Tuesday, October 13, 2026 · 7:00 p.m.$v$, 85),
  ('member', 'event.0.title', 'text', $v$Online officers meeting$v$, 86),
  ('member', 'event.0.more', 'text', $v$Read More...$v$, 87),
  ('member', 'event.1.when', 'text', $v$Wednesday, October 14, 2026 · 6:40 p.m.$v$, 88),
  ('member', 'event.1.title', 'text', $v$Council rosary$v$, 89),
  ('member', 'event.1.more', 'text', $v$Read More...$v$, 90),
  ('member', 'event.2.when', 'text', $v$Wednesday, October 14, 2026 · 7:00 p.m.$v$, 91),
  ('member', 'event.2.title', 'text', $v$Council business meeting$v$, 92),
  ('member', 'event.2.more', 'text', $v$Read More...$v$, 93),
  ('member', 'event.3.when', 'text', $v$Saturday, October 24, 2026 · 9:00 a.m. to 3:00 p.m.$v$, 94),
  ('member', 'event.3.title', 'text', $v$Red Cross blood drive$v$, 95),
  ('member', 'event.3.more', 'text', $v$Read More...$v$, 96),
  ('member', 'event.4.when', 'text', $v$Saturday, November 14, 2026 · 8:00 a.m.$v$, 97),
  ('member', 'event.4.title', 'text', $v$Coats for Kids distribution$v$, 98),
  ('member', 'event.4.more', 'text', $v$Read More...$v$, 99),
  ('member', 'blood.eyebrow', 'text', $v$Charity in practice$v$, 100),
  ('member', 'blood.title', 'text', $v$Blood Drive$v$, 101),
  ('member', 'blood.place', 'text', $v$5953 Bowman Roberts Rd, Fort Worth, TX 76179$v$, 102),
  ('member', 'blood.when', 'text', $v$Saturday, October 24, 2026 · 9:00 a.m. to 3:00 p.m.$v$, 103),
  ('member', 'blood.before', 'text', $v$Schedule at$v$, 104),
  ('member', 'blood.link', 'text', $v$RedCrossBlood.org$v$, 105),
  ('member', 'blood.after', 'text', $v$. Walk-ins are taken as the schedule allows.$v$, 106),
  ('member', 'stat.0.value', 'text', $v$18$v$, 107),
  ('member', 'stat.0.label', 'text', $v$Units last drive$v$, 108),
  ('member', 'stat.1.value', 'text', $v$42$v$, 109),
  ('member', 'stat.1.label', 'text', $v$Lives potentially helped$v$, 110),
  ('member', 'stat.2.value', 'text', $v$7$v$, 111),
  ('member', 'stat.2.label', 'text', $v$First-time donors$v$, 112),
  ('member', 'links.eyebrow', 'text', $v$Brothers only$v$, 113),
  ('member', 'links.title', 'text', $v$Members Quick Links$v$, 114),
  ('member', 'links.intro', 'text', $v$Dues open in a new tab. Council lists stay here.$v$, 115),
  ('member', 'links.0.title', 'text', $v$Pay your annual dues$v$, 116),
  ('member', 'links.0.body', 'text', $v$Annual dues — Regular $44.00$v$, 117),
  ('member', 'links.0.action', 'text', $v$Pay annual dues online$v$, 118),
  ('member', 'links.1.title', 'text', $v$Upcoming member birthdays$v$, 119),
  ('member', 'links.1.action', 'text', $v$View birthdays$v$, 120),
  ('member', 'links.1.detail', 'text', $v$Sample only. Replace with the current birthday roll.$v$, 121),
  ('member', 'links.2.title', 'text', $v$Announcements for members only$v$, 122),
  ('member', 'links.2.action', 'text', $v$Read announcements$v$, 123),
  ('member', 'links.2.detail', 'text', $v$Exemplification practice details stay off the public site.$v$, 124),
  ('member', 'links.3.title', 'text', $v$Prayer requests for members only$v$, 125),
  ('member', 'links.3.action', 'text', $v$Open prayer list$v$, 126),
  ('member', 'links.3.detail', 'text', $v$Pray for the brothers and families who asked for a private intention.$v$, 127),
  ('member', 'links.4.title', 'text', $v$Members list$v$, 128),
  ('member', 'links.4.action', 'text', $v$Open members list$v$, 129),
  ('member', 'links.4.detail', 'text', $v$Restricted. Request the current roll from the Financial Secretary.$v$, 130),
  ('member', 'links.5.title', 'text', $v$Our elder statesmen$v$, 131),
  ('member', 'links.5.action', 'text', $v$View honor roll$v$, 132),
  ('member', 'links.5.detail', 'text', $v$Replace with the elder statesmen list.$v$, 133),
  ('member', 'links.6.title', 'text', $v$Share a comment with an officer$v$, 134),
  ('member', 'links.6.action', 'text', $v$Write the council$v$, 135),
  ('member', 'links.6.detail', 'text', $v$Address the Grand Knight or a trustee. Do not post private remarks publicly.$v$, 136),
  ('member', 'links.7.title', 'text', $v$SFS officer roles$v$, 137),
  ('member', 'links.7.action', 'text', $v$Open role guide$v$, 138),
  ('member', 'links.7.detail', 'text', $v$Officer duty summaries belong in this members library.$v$, 139),
  ('member', 'links.8.title', 'text', $v$Event management center$v$, 140),
  ('member', 'links.8.action', 'text', $v$Open chairmen tools$v$, 141),
  ('member', 'links.8.detail', 'text', $v$Confirm the parish calendar before an event is announced.$v$, 142),
  ('member', 'links.9.title', 'text', $v$Volunteer hours and visits$v$, 143),
  ('member', 'links.9.action', 'text', $v$How to record hours$v$, 144),
  ('member', 'links.9.before', 'text', $v$Record hours and visits at$v$, 145),
  ('member', 'links.9.link', 'text', $v$www.UKnightMobile.org$v$, 146),
  ('member', 'links.9.after', 'text', $v$.$v$, 147),
  ('member', 'links.10.title', 'text', $v$Hours goal & blood donor status$v$, 148),
  ('member', 'links.10.body', 'text', $v$Your Goal for this year (2026) is 0.00 hours per month. You are not a blood donor.$v$, 149),
  ('member', 'links.10.action', 'text', $v$Update goal$v$, 150),
  ('member', 'links.10.detail', 'text', $v$Your Goal for this year (2026) is 0.00 hours per month. You are not a blood donor.$v$, 151),
  ('member', 'links.11.title', 'text', $v$Knight and Family of the Month$v$, 152),
  ('member', 'links.11.action', 'text', $v$Submit a nomination$v$, 153),
  ('member', 'links.11.detail', 'text', $v$Include the name and a short reason for the nomination.$v$, 154),
  ('member', 'links.12.title', 'text', $v$Financial Secretary library$v$, 155),
  ('member', 'links.12.action', 'text', $v$Open FS reports$v$, 156),
  ('member', 'links.12.detail', 'text', $v$Replace with the current Financial Secretary reports.$v$, 157),
  ('member', 'links.13.title', 'text', $v$Treasurer report library$v$, 158),
  ('member', 'links.13.action', 'text', $v$Open treasurer reports$v$, 159),
  ('member', 'links.13.detail', 'text', $v$Replace with the current treasurer statements.$v$, 160),
  ('member', 'links.14.title', 'text', $v$Budget and opening documents$v$, 161),
  ('member', 'links.14.action', 'text', $v$Open documents$v$, 162),
  ('member', 'links.14.detail', 'text', $v$Council budget and opening documents live here.$v$, 163),
  ('member', 'links.15.title', 'text', $v$Email the webmaster$v$, 164),
  ('member', 'links.15.action', 'text', $v$Email webmaster$v$, 165),
  ('member', 'footer.name', 'text', $v$Council 10930$v$, 166),
  ('member', 'footer.sub', 'text', $v$Knights of Columbus · Fort Worth, TX$v$, 167),
  ('member', 'footer.nav.about', 'text', $v$About$v$, 168),
  ('member', 'footer.nav.officers', 'text', $v$Officers$v$, 169),
  ('member', 'footer.nav.directors', 'text', $v$Directors$v$, 170),
  ('member', 'footer.nav.events', 'text', $v$Events$v$, 171),
  ('member', 'footer.nav.blood', 'text', $v$Blood Drive$v$, 172),
  ('member', 'footer.nav.links', 'text', $v$Member Links$v$, 173),
  ('member', 'footer.nav.public', 'text', $v$Public page$v$, 174),
  ('member', 'footer.copy', 'text', $v$© 2026 Knights of Columbus Council 10930 — Fort Worth, TX$v$, 175),
  ('member', 'footer.principles', 'text', $v$Charity · Unity · Fraternity · Patriotism$v$, 176),
  ('member', 'recog.0.detail', 'text', $v$Neighbors packed boxes on Saturday and delivered them to families after Sunday Mass.$v$, 177),
  ('member', 'recog.1.detail', 'text', $v$He organized sizes, labeled bags, and stayed until every coat had a home.$v$, 178),
  ('member', 'recog.2.detail', 'text', $v$The family hosted monthly rosaries and raised scholarship funds through the parish festival.$v$, 179),
  ('member', 'recog.3.detail', 'text', $v$He logged charity hours each month and walked new members through their first meeting.$v$, 180)
) AS v(slug, block_key, field_type, value, sort_order)
JOIN pages p ON p.slug = v.slug
ON CONFLICT (page_id, "key") DO NOTHING;

INSERT INTO content_blocks (page_id, "key", field_type, value, sort_order)
SELECT p.id, 'year.fraternal', 'text', $v$2026–27$v$, 200
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
  CONSTRAINT images_slot_chk CHECK (
    slot IS NULL OR slot IN (
      'logo', 'carousel.1', 'carousel.2', 'carousel.3', 'carousel.4',
      'recog.0', 'recog.1', 'recog.2', 'recog.3'
    )
  )
);

ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_x DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_y DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE images ADD COLUMN IF NOT EXISTS crop_scale DOUBLE PRECISION NOT NULL DEFAULT 1;
ALTER TABLE images DROP CONSTRAINT IF EXISTS images_slot_chk;
ALTER TABLE images ADD CONSTRAINT images_slot_chk CHECK (
  slot IS NULL OR slot IN (
    'logo', 'carousel.1', 'carousel.2', 'carousel.3', 'carousel.4',
    'recog.0', 'recog.1', 'recog.2', 'recog.3'
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS images_slot_idx
  ON images (slot) WHERE slot IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS images_profile_idx
  ON images (owner_membership_id) WHERE purpose = 'profile';

INSERT INTO images (path, original_name, content_type, purpose, slot)
SELECT v.path, v.original_name, v.content_type, v.purpose, v.slot
FROM (
  VALUES
  ('images/kofc-logo.png', 'kofc-logo.png', 'image/png', 'library', 'logo'),
  ('images/carousel1.jpg', 'carousel1.jpg', 'image/jpeg', 'library', 'carousel.1'),
  ('images/carousel2.jpg', 'carousel2.jpg', 'image/jpeg', 'library', 'carousel.2'),
  ('images/carousel3.jpg', 'carousel3.jpg', 'image/jpeg', 'library', 'carousel.3'),
  ('images/carousel4.jpg', 'carousel4.jpg', 'image/jpeg', 'library', 'carousel.4')
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

CREATE TABLE IF NOT EXISTS honors (
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

CREATE TEMP TABLE IF NOT EXISTS honor_seed_rows (
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
  ('knight_month', 'James Harrington', 'October 2025', 2025::integer, 10::integer, 'He chaired the Coats for Kids sorting crew.', 'backend/uploads/seed/honors/knight_month-01.png', 'image/png'),
  ('knight_month', 'Peter Lang', 'September 2025', 2025::integer, 9::integer, 'He organized the wheelchair mission delivery.', 'backend/uploads/seed/honors/knight_month-02.png', 'image/png'),
  ('knight_month', 'Marcus Webb', 'August 2025', 2025::integer, 8::integer, 'He recruited three new members at the parish festival.', 'backend/uploads/seed/honors/knight_month-03.png', 'image/png'),
  ('knight_month', 'Owen Keller', 'July 2025', 2025::integer, 7::integer, 'He led the Saturday pancake breakfast crew.', 'backend/uploads/seed/honors/knight_month-04.png', 'image/png'),
  ('knight_month', 'Nathan Cho', 'June 2025', 2025::integer, 6::integer, 'He coordinated the blood-drive volunteer shift.', 'backend/uploads/seed/honors/knight_month-05.png', 'image/png'),
  ('knight_month', 'Elliot Marsh', 'May 2025', 2025::integer, 5::integer, 'He repaired the hall tables before the fish fry.', 'backend/uploads/seed/honors/knight_month-06.png', 'image/png'),
  ('knight_month', 'Caleb Ruiz', 'April 2025', 2025::integer, 4::integer, 'He drove veterans to the monthly social.', 'backend/uploads/seed/honors/knight_month-07.png', 'image/png'),
  ('knight_month', 'Dominic Price', 'March 2025', 2025::integer, 3::integer, 'He ran the Tootsie Roll weekend with the youth helpers.', 'backend/uploads/seed/honors/knight_month-08.png', 'image/png'),
  ('knight_month', 'Isaac Romero', 'February 2025', 2025::integer, 2::integer, 'He set up the living rosary in the parish courtyard.', 'backend/uploads/seed/honors/knight_month-09.png', 'image/png'),
  ('knight_month', 'Gabriel Santos', 'January 2025', 2025::integer, 1::integer, 'He collected winter coats from the school families.', 'backend/uploads/seed/honors/knight_month-10.png', 'image/png'),
  ('knight_month', 'Felix Navarro', 'December 2024', 2024::integer, 12::integer, 'He hosted the exemplification reception.', 'backend/uploads/seed/honors/knight_month-11.png', 'image/png'),
  ('knight_month', 'Hugo Bennett', 'November 2024', 2024::integer, 11::integer, 'He kept the scholarship applications moving.', 'backend/uploads/seed/honors/knight_month-12.png', 'image/png'),
  ('knight_month', 'Adrian Cole', 'October 2024', 2024::integer, 10::integer, 'He led the Keep Christ in Christmas card sale.', 'backend/uploads/seed/honors/knight_month-13.png', 'image/png'),
  ('knight_month', 'Wesley Grant', 'September 2024', 2024::integer, 9::integer, 'He paired new members with sponsors.', 'backend/uploads/seed/honors/knight_month-14.png', 'image/png'),
  ('knight_month', 'Simon Pearce', 'August 2024', 2024::integer, 8::integer, 'He cooked for the widows'' luncheon.', 'backend/uploads/seed/honors/knight_month-15.png', 'image/png'),
  ('knight_month', 'Julian Hart', 'July 2024', 2024::integer, 7::integer, 'He logged the council''s charity hours for the report.', 'backend/uploads/seed/honors/knight_month-16.png', 'image/png'),
  ('knight_month', 'Vincent Rossi', 'June 2024', 2024::integer, 6::integer, 'He built a ramp for a brother knight''s porch.', 'backend/uploads/seed/honors/knight_month-17.png', 'image/png'),
  ('knight_month', 'Malcolm Reid', 'May 2024', 2024::integer, 5::integer, 'He chaired the soccer challenge at the parish school.', 'backend/uploads/seed/honors/knight_month-18.png', 'image/png'),
  ('knight_month', 'Oscar Pham', 'April 2024', 2024::integer, 4::integer, 'He delivered food boxes after the parish mission.', 'backend/uploads/seed/honors/knight_month-19.png', 'image/png'),
  ('knight_month', 'Leon Duarte', 'March 2024', 2024::integer, 3::integer, 'He organized the corporate communion breakfast.', 'backend/uploads/seed/honors/knight_month-20.png', 'image/png'),
  ('family_month', 'The Nguyen Family', 'September 2025', 2025::integer, 9::integer, 'They led the parish food pantry weekend.', 'backend/uploads/seed/honors/family_month-01.png', 'image/png'),
  ('family_month', 'The Brennan Family', 'August 2025', 2025::integer, 8::integer, 'They hosted the council picnic and watched the younger children.', 'backend/uploads/seed/honors/family_month-02.png', 'image/png'),
  ('family_month', 'The Alvarez Family', 'July 2025', 2025::integer, 7::integer, 'They sorted coats and stayed through the distribution.', 'backend/uploads/seed/honors/family_month-03.png', 'image/png'),
  ('family_month', 'The Okonkwo Family', 'June 2025', 2025::integer, 6::integer, 'They led the family rosary after Sunday Mass.', 'backend/uploads/seed/honors/family_month-04.png', 'image/png'),
  ('family_month', 'The Callahan Family', 'May 2025', 2025::integer, 5::integer, 'They baked for the Lenten fish fry every Friday.', 'backend/uploads/seed/honors/family_month-05.png', 'image/png'),
  ('family_month', 'The Ramirez Family', 'April 2025', 2025::integer, 4::integer, 'They welcomed new families at the membership drive.', 'backend/uploads/seed/honors/family_month-06.png', 'image/png'),
  ('family_month', 'The Patel Family', 'March 2025', 2025::integer, 3::integer, 'They staffed the Special Olympics hydration tent.', 'backend/uploads/seed/honors/family_month-07.png', 'image/png'),
  ('family_month', 'The Kowalski Family', 'February 2025', 2025::integer, 2::integer, 'They prepared the hall for the widows'' luncheon.', 'backend/uploads/seed/honors/family_month-08.png', 'image/png'),
  ('family_month', 'The Park Family', 'January 2025', 2025::integer, 1::integer, 'They ran the Christmas poster contest at the school.', 'backend/uploads/seed/honors/family_month-09.png', 'image/png'),
  ('family_month', 'The Moretti Family', 'December 2024', 2024::integer, 12::integer, 'They delivered meals to homebound parishioners.', 'backend/uploads/seed/honors/family_month-10.png', 'image/png'),
  ('family_month', 'The Vasquez Family', 'November 2024', 2024::integer, 11::integer, 'They helped measure children for winter coats.', 'backend/uploads/seed/honors/family_month-11.png', 'image/png'),
  ('family_month', 'The Thompson Family', 'October 2024', 2024::integer, 10::integer, 'They kept the scholarship candy sale stocked.', 'backend/uploads/seed/honors/family_month-12.png', 'image/png'),
  ('family_month', 'The Carter Family', 'September 2024', 2024::integer, 9::integer, 'They hosted a vocations dinner for seminarians.', 'backend/uploads/seed/honors/family_month-13.png', 'image/png'),
  ('family_month', 'The Donnelly Family', 'August 2024', 2024::integer, 8::integer, 'They led the living nativity volunteers.', 'backend/uploads/seed/honors/family_month-14.png', 'image/png'),
  ('family_month', 'The Ortega Family', 'July 2024', 2024::integer, 7::integer, 'They organized the parish festival kids'' games.', 'backend/uploads/seed/honors/family_month-15.png', 'image/png'),
  ('family_month', 'The Wallace Family', 'June 2024', 2024::integer, 6::integer, 'They drove the food-pantry truck that Saturday.', 'backend/uploads/seed/honors/family_month-16.png', 'image/png'),
  ('family_month', 'The Gallagher Family', 'May 2024', 2024::integer, 5::integer, 'They prayed the rosary with the council each week.', 'backend/uploads/seed/honors/family_month-17.png', 'image/png'),
  ('family_month', 'The Santos Family', 'April 2024', 2024::integer, 4::integer, 'They set up and cleared the pancake breakfast.', 'backend/uploads/seed/honors/family_month-18.png', 'image/png'),
  ('family_month', 'The Herrera Family', 'March 2024', 2024::integer, 3::integer, 'They welcomed guests at the blood drive.', 'backend/uploads/seed/honors/family_month-19.png', 'image/png'),
  ('family_month', 'The Berg Family', 'February 2024', 2024::integer, 2::integer, 'They packed ultrasound-initiative appeal letters.', 'backend/uploads/seed/honors/family_month-20.png', 'image/png'),
  ('knight_year', 'Robert Hale', '2025', 2025::integer, NULL::integer, 'He logged charity hours each month and mentored new members.', 'backend/uploads/seed/honors/knight_year-01.png', 'image/png'),
  ('knight_year', 'Carl Mendel', '2024', 2024::integer, NULL::integer, 'He kept the coat drive and the blood drive fully staffed.', 'backend/uploads/seed/honors/knight_year-02.png', 'image/png'),
  ('knight_year', 'Evan Brooks', '2023', 2023::integer, NULL::integer, 'He revived the council''s visit schedule for homebound brothers.', 'backend/uploads/seed/honors/knight_year-03.png', 'image/png'),
  ('knight_year', 'Hugh Salazar', '2022', 2022::integer, NULL::integer, 'He led the soccer challenge and the free-throw contest.', 'backend/uploads/seed/honors/knight_year-04.png', 'image/png'),
  ('knight_year', 'Martin Ellison', '2021', 2021::integer, NULL::integer, 'He balanced a full program calendar without missing a meeting.', 'backend/uploads/seed/honors/knight_year-05.png', 'image/png'),
  ('knight_year', 'Derek Fontaine', '2020', 2020::integer, NULL::integer, 'He raised the scholarship fund past its goal.', 'backend/uploads/seed/honors/knight_year-06.png', 'image/png'),
  ('knight_year', 'Philip Okada', '2019', 2019::integer, NULL::integer, 'He trained the new officers before the election.', 'backend/uploads/seed/honors/knight_year-07.png', 'image/png'),
  ('knight_year', 'George Lanier', '2018', 2018::integer, NULL::integer, 'He organized disaster-relief collections after the spring storms.', 'backend/uploads/seed/honors/knight_year-08.png', 'image/png'),
  ('knight_year', 'Arthur Nguyen', '2017', 2017::integer, NULL::integer, 'He grew the rosary attendance through the year.', 'backend/uploads/seed/honors/knight_year-09.png', 'image/png'),
  ('knight_year', 'Lawrence Kim', '2016', 2016::integer, NULL::integer, 'He finished the hall accessibility repairs.', 'backend/uploads/seed/honors/knight_year-10.png', 'image/png'),
  ('knight_year', 'Raymond Doyle', '2015', 2015::integer, NULL::integer, 'He chaired Coats for Kids from kickoff to the last delivery.', 'backend/uploads/seed/honors/knight_year-11.png', 'image/png'),
  ('knight_year', 'Clifford Barnes', '2014', 2014::integer, NULL::integer, 'He mentored the youth programs through the school year.', 'backend/uploads/seed/honors/knight_year-12.png', 'image/png'),
  ('knight_year', 'Harold Ibarra', '2013', 2013::integer, NULL::integer, 'He carried the ultrasound initiative appeal to every meeting.', 'backend/uploads/seed/honors/knight_year-13.png', 'image/png'),
  ('knight_year', 'Eugene Moss', '2012', 2012::integer, NULL::integer, 'He kept the food pantry partnership running each month.', 'backend/uploads/seed/honors/knight_year-14.png', 'image/png'),
  ('knight_year', 'Walter Brennan', '2011', 2011::integer, NULL::integer, 'He welcomed the largest exemplification class of the decade.', 'backend/uploads/seed/honors/knight_year-15.png', 'image/png'),
  ('knight_year', 'Francis Delgado', '2010', 2010::integer, NULL::integer, 'He published the charity report the state council requested.', 'backend/uploads/seed/honors/knight_year-16.png', 'image/png'),
  ('knight_year', 'Albert Shaw', '2009', 2009::integer, NULL::integer, 'He led the veterans'' breakfast through the winter.', 'backend/uploads/seed/honors/knight_year-17.png', 'image/png'),
  ('knight_year', 'Clarence Holt', '2008', 2008::integer, NULL::integer, 'He restored the council''s contingent for the parish festival.', 'backend/uploads/seed/honors/knight_year-18.png', 'image/png'),
  ('knight_year', 'Bernard Cruz', '2007', 2007::integer, NULL::integer, 'He paired every new knight with a working committee.', 'backend/uploads/seed/honors/knight_year-19.png', 'image/png'),
  ('knight_year', 'Stanley Peck', '2006', 2006::integer, NULL::integer, 'He held the council''s charity budget on target.', 'backend/uploads/seed/honors/knight_year-20.png', 'image/png'),
  ('family_year', 'The Ortiz Family', '2025', 2025::integer, NULL::integer, 'They hosted monthly rosaries and supported the scholarship fund.', 'backend/uploads/seed/honors/family_year-01.png', 'image/png'),
  ('family_year', 'The Lang Family', '2024', 2024::integer, NULL::integer, 'They staffed every fish fry and the coat distribution.', 'backend/uploads/seed/honors/family_year-02.png', 'image/png'),
  ('family_year', 'The Webb Family', '2023', 2023::integer, NULL::integer, 'They opened their home for the council''s family prayer night.', 'backend/uploads/seed/honors/family_year-03.png', 'image/png'),
  ('family_year', 'The Keller Family', '2022', 2022::integer, NULL::integer, 'They led the parish festival meal line.', 'backend/uploads/seed/honors/family_year-04.png', 'image/png'),
  ('family_year', 'The Cho Family', '2021', 2021::integer, NULL::integer, 'They tutored students before the free-throw and soccer events.', 'backend/uploads/seed/honors/family_year-05.png', 'image/png'),
  ('family_year', 'The Marsh Family', '2020', 2020::integer, NULL::integer, 'They visited homebound parishioners with the council each month.', 'backend/uploads/seed/honors/family_year-06.png', 'image/png'),
  ('family_year', 'The Ruiz Family', '2019', 2019::integer, NULL::integer, 'They ran the Christmas poster contest and the card sale.', 'backend/uploads/seed/honors/family_year-07.png', 'image/png'),
  ('family_year', 'The Price Family', '2018', 2018::integer, NULL::integer, 'They cooked the veterans'' breakfast from January through November.', 'backend/uploads/seed/honors/family_year-08.png', 'image/png'),
  ('family_year', 'The Romero Family', '2017', 2017::integer, NULL::integer, 'They kept the food pantry shelves labeled and full.', 'backend/uploads/seed/honors/family_year-09.png', 'image/png'),
  ('family_year', 'The Navarro Family', '2016', 2016::integer, NULL::integer, 'They hosted seminarians during the vocations weekend.', 'backend/uploads/seed/honors/family_year-10.png', 'image/png'),
  ('family_year', 'The Bennett Family', '2015', 2015::integer, NULL::integer, 'They organized rides for elderly members.', 'backend/uploads/seed/honors/family_year-11.png', 'image/png'),
  ('family_year', 'The Cole Family', '2014', 2014::integer, NULL::integer, 'They prepared the hall for every major fundraiser.', 'backend/uploads/seed/honors/family_year-12.png', 'image/png'),
  ('family_year', 'The Pearce Family', '2013', 2013::integer, NULL::integer, 'They led the family Mass ushers for the year.', 'backend/uploads/seed/honors/family_year-13.png', 'image/png'),
  ('family_year', 'The Hart Family', '2012', 2012::integer, NULL::integer, 'They packed and delivered coats with their children.', 'backend/uploads/seed/honors/family_year-14.png', 'image/png'),
  ('family_year', 'The Rossi Family', '2011', 2011::integer, NULL::integer, 'They chaired the Special Olympics family tent.', 'backend/uploads/seed/honors/family_year-15.png', 'image/png'),
  ('family_year', 'The Reid Family', '2010', 2010::integer, NULL::integer, 'They supported the ultrasound initiative bake sales.', 'backend/uploads/seed/honors/family_year-16.png', 'image/png'),
  ('family_year', 'The Pham Family', '2009', 2009::integer, NULL::integer, 'They welcomed new families at every membership drive.', 'backend/uploads/seed/honors/family_year-17.png', 'image/png'),
  ('family_year', 'The Duarte Family', '2008', 2008::integer, NULL::integer, 'They kept the scholarship candy sale going each month.', 'backend/uploads/seed/honors/family_year-18.png', 'image/png'),
  ('family_year', 'The Mendel Family', '2007', 2007::integer, NULL::integer, 'They hosted the corporate communion brunch.', 'backend/uploads/seed/honors/family_year-19.png', 'image/png'),
  ('family_year', 'The Fontaine Family', '2006', 2006::integer, NULL::integer, 'They prayed with the council and staffed the blood drive.', 'backend/uploads/seed/honors/family_year-20.png', 'image/png'),
  ('past_gk', 'William Grant', '2024–25', 2024::integer, NULL::integer, 'He led the council through the Coats for Kids year.', 'backend/uploads/seed/honors/past_gk-01.png', 'image/png'),
  ('past_gk', 'Thomas Reilly', '2023–24', 2023::integer, NULL::integer, 'He handed the council a balanced charity budget.', 'backend/uploads/seed/honors/past_gk-02.png', 'image/png'),
  ('past_gk', 'Edward Castillo', '2022–23', 2022::integer, NULL::integer, 'He restarted the monthly family picnic.', 'backend/uploads/seed/honors/past_gk-03.png', 'image/png'),
  ('past_gk', 'Joseph Brennan', '2021–22', 2021::integer, NULL::integer, 'He grew the roster and kept meetings on time.', 'backend/uploads/seed/honors/past_gk-04.png', 'image/png'),
  ('past_gk', 'Paul Griffin', '2020–21', 2020::integer, NULL::integer, 'He launched the council''s ultrasound initiative support.', 'backend/uploads/seed/honors/past_gk-05.png', 'image/png'),
  ('past_gk', 'Anthony Marino', '2019–20', 2019::integer, NULL::integer, 'He guided the hall renovation to completion.', 'backend/uploads/seed/honors/past_gk-06.png', 'image/png'),
  ('past_gk', 'Charles Nguyen', '2018–19', 2018::integer, NULL::integer, 'He strengthened the council''s tie to the parish school.', 'backend/uploads/seed/honors/past_gk-07.png', 'image/png'),
  ('past_gk', 'Frank Kowalski', '2017–18', 2017::integer, NULL::integer, 'He led through the year the blood drive doubled.', 'backend/uploads/seed/honors/past_gk-08.png', 'image/png'),
  ('past_gk', 'Stephen Walsh', '2016–17', 2016::integer, NULL::integer, 'He installed a full slate of program directors.', 'backend/uploads/seed/honors/past_gk-09.png', 'image/png'),
  ('past_gk', 'Patrick Donnelly', '2015–16', 2015::integer, NULL::integer, 'He hosted the district''s exemplification.', 'backend/uploads/seed/honors/past_gk-10.png', 'image/png'),
  ('past_gk', 'Daniel Okonkwo', '2014–15', 2014::integer, NULL::integer, 'He kept charity hours at the front of every meeting.', 'backend/uploads/seed/honors/past_gk-11.png', 'image/png'),
  ('past_gk', 'Michael Ruiz', '2013–14', 2013::integer, NULL::integer, 'He opened meetings with a steady formation program.', 'backend/uploads/seed/honors/past_gk-12.png', 'image/png'),
  ('past_gk', 'Andrew Park', '2012–13', 2012::integer, NULL::integer, 'He left the scholarship fund larger than he found it.', 'backend/uploads/seed/honors/past_gk-13.png', 'image/png'),
  ('past_gk', 'Christopher Walsh', '2011–12', 2011::integer, NULL::integer, 'He organized the council''s first Special Olympics team.', 'backend/uploads/seed/honors/past_gk-14.png', 'image/png'),
  ('past_gk', 'Timothy Brooks', '2010–11', 2010::integer, NULL::integer, 'He renewed the food-pantry partnership.', 'backend/uploads/seed/honors/past_gk-15.png', 'image/png'),
  ('past_gk', 'Brian Callahan', '2009–10', 2009::integer, NULL::integer, 'He led the widows'' luncheon into an annual event.', 'backend/uploads/seed/honors/past_gk-16.png', 'image/png'),
  ('past_gk', 'Steven Alvarez', '2008–09', 2008::integer, NULL::integer, 'He finished the year with every officer chair filled.', 'backend/uploads/seed/honors/past_gk-17.png', 'image/png'),
  ('past_gk', 'Kevin Moretti', '2007–08', 2007::integer, NULL::integer, 'He carried Coats for Kids through a cold winter.', 'backend/uploads/seed/honors/past_gk-18.png', 'image/png'),
  ('past_gk', 'Ryan Thompson', '2006–07', 2006::integer, NULL::integer, 'He set the council''s visit schedule for homebound knights.', 'backend/uploads/seed/honors/past_gk-19.png', 'image/png'),
  ('past_gk', 'Matthew Carter', '2005–06', 2005::integer, NULL::integer, 'He began the council''s corporate communion tradition.', 'backend/uploads/seed/honors/past_gk-20.png', 'image/png');

INSERT INTO honors (category, name, period, sort_year, sort_month, note, photo_path, photo_type)
SELECT s.category, s.name, s.period, s.sort_year, s.sort_month, s.note, s.photo_path, s.photo_type
FROM honor_seed_rows s
WHERE NOT EXISTS (
  SELECT 1 FROM honors h
  WHERE h.category = s.category AND h.name = s.name AND h.period = s.period
);

INSERT INTO council_events (title, event_date, event_time, location, description, sort_order)
SELECT v.title, v.event_date, v.event_time, v.location, v.description, v.sort_order
FROM (
  VALUES
  ('Online officers meeting', DATE '2026-10-13', '7:00 p.m.', NULL, 'Brothers meet online to review the month''s business before the council meeting.', 1),
  ('Council rosary', DATE '2026-10-14', '6:40 p.m.', 'Parish hall', 'The council prays the rosary together in the parish hall before the business meeting.', 2),
  ('Council business meeting', DATE '2026-10-14', '7:00 p.m.', 'Parish hall', 'Officers report, motions are heard, and brothers plan the next charity work.', 3),
  ('Red Cross blood drive', DATE '2026-10-24', '9:00 a.m. to 3:00 p.m.', '5953 Bowman Roberts Rd', 'Give blood at the council hall. Appointments and walk-ins are both welcome.', 4),
  ('Coats for Kids distribution', DATE '2026-11-14', '8:00 a.m.', 'Parish', 'Sorted coats are handed out to families at the parish from the morning shift.', 5)
) AS v(title, event_date, event_time, location, description, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM council_events);

COMMIT;
