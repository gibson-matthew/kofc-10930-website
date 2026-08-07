"""
Deterministic KOFC-themed full database population script.
Wipes all tables and repopulates with realistic test data.

Run:
    python scripts/populate_test_data.py
"""

# CRUD services
import asyncio
import datetime
from datetime import timedelta
from sqlalchemy import text
from passlib.hash import bcrypt

from dotenv import load_dotenv
load_dotenv()

import os
print("Using DB:", os.getenv("DATABASE_URL"))

from app.services.base_crud_service import BaseCRUDService

# AUTH
from app.models.role import Role
from app.models.user import User

# PUBLIC CONTENT
from app.models.news import News
from app.models.recognition import Recognition
from app.models.memoriam import Memoriam
from app.models.links import Link
from app.models.homepage_hero_images import HomepageHeroImage

# EVENTS
from app.models.events import Event
from app.models.event_volunteers import EventVolunteer

# LEADERSHIP
from app.models.officers import Officer
from app.models.directors import Director

# PROGRAMS & COMMITTEES
from app.models.committees import Committee
from app.models.programs import Program
from app.models.program_volunteers import ProgramVolunteer

# PRAYER REQUESTS
from app.models.prayer_requests import PrayerRequest

# MEDIA
from app.models.media_albums import MediaAlbum
from app.models.media_items import MediaItem
from app.models.newsletters import Newsletter

# MARKET CENTER
from app.models.market_categories import MarketCategory
from app.models.market_items import MarketItem
from app.models.merchants import Merchant
from app.models.merchant_reports import MerchantReport

# JOBS
from app.models.jobs import Job

# DEGREE SCHEDULE
from app.models.degree_schedule import DegreeSchedule

# DOCUMENTS
from app.models.documents import Document

# VOTING
from app.models.votes import Vote
from app.models.vote_options import VoteOption
from app.models.vote_cast import VoteCast

# SEO
from app.models.seo_settings import SEOSettings  # confirm class name

# UPLOADS
from app.models.uploads import Upload

# AUDIT LOG
from app.models.audit_log import AuditLog
from app.db.session import AsyncSessionLocal
from app.services.auth_service import AuthService

# Instantiate CRUD services
role_service = BaseCRUDService(Role)
news_service = BaseCRUDService(News)
recognition_service = BaseCRUDService(Recognition)
memoriam_service = BaseCRUDService(Memoriam)
links_service = BaseCRUDService(Link)
hero_service = BaseCRUDService(HomepageHeroImage)

events_service = BaseCRUDService(Event)
event_vol_service = BaseCRUDService(EventVolunteer)

officers_service = BaseCRUDService(Officer)
directors_service = BaseCRUDService(Director)

committees_service = BaseCRUDService(Committee)
programs_service = BaseCRUDService(Program)
program_vol_service = BaseCRUDService(ProgramVolunteer)

prayer_service = BaseCRUDService(PrayerRequest)

media_album_service = BaseCRUDService(MediaAlbum)
media_item_service = BaseCRUDService(MediaItem)
newsletter_service = BaseCRUDService(Newsletter)

market_cat_service = BaseCRUDService(MarketCategory)
market_item_service = BaseCRUDService(MarketItem)
merchants_service = BaseCRUDService(Merchant)
merchant_reports_service = BaseCRUDService(MerchantReport)

jobs_service = BaseCRUDService(Job)

degree_service = BaseCRUDService(DegreeSchedule)

documents_service = BaseCRUDService(Document)

votes_service = BaseCRUDService(Vote)
vote_options_service = BaseCRUDService(VoteOption)
vote_cast_service = BaseCRUDService(VoteCast)

seo_service = BaseCRUDService(SEOSettings)

uploads_service = BaseCRUDService(Upload)

audit_service = BaseCRUDService(AuditLog)


# ============================================================
#  DATA SETS
# ============================================================

ROLES = [
    "Member", "Admin", "Grand Knight", "Deputy Grand Knight", "Chancellor",
    "Recorder", "Treasurer", "Advocate", "Warden", "Inside Guard",
    "Outside Guard", "Trustee 1-Year", "Trustee 2-Year", "Trustee 3-Year",
    "Chaplain", "Financial Secretary", "Lecturer", "Past Grand Knight",
    "Program Director", "Faith Director", "Family Director",
    "Community Director", "Life Director", "Membership Director",
    "Webmaster", "Content Manager", "Media Coordinator"
]

officer_positions = [
    "Grand Knight",
    "Deputy Grand Knight",
    "Chancellor",
    "Recorder",
    "Treasurer",
    "Advocate",
    "Warden",
    "Inside Guard",
    "Outside Guard",
    "Trustee 1-Year",
    "Trustee 2-Year",
    "Trustee 3-Year",
    "Chaplain",
    "Financial Secretary",
    "Lecturer",
    "Past Grand Knight"
]

DIRECTOR_POSITIONS = [
    "Program Director", "Faith Director", "Family Director",
    "Community Director", "Life Director", "Membership Director"
]

FIRST_NAMES = [
    "John", "David", "Michael", "Paul", "Luke", "Mark", "James",
    "Andrew", "Peter", "Thomas", "Robert", "Anthony", "Joseph",
    "Stephen", "Daniel"
]

LAST_NAMES = [
    "Knight", "Strong", "Faith", "Helper", "Miller", "Johnson",
    "Garcia", "Martinez", "Lopez", "Davis", "Clark", "Bennett",
    "Reeves", "Foster", "Hayes"
]


# ============================================================
#  WIPE DATABASE
# ============================================================

async def wipe_database(db):
    print("Wiping database...")

    # Get SQLAlchemy async connection
    conn = await db.connection()

    tables = [
        "audit_log", "uploads", "seo_settings", "vote_cast", "vote_options",
        "votes", "documents", "degree_schedule", "jobs", "merchant_reports",
        "merchants", "market_items", "market_categories", "newsletters",
        "media_items", "media_albums", "prayer_requests", "program_volunteers",
        "programs", "committees", "directors", "officers", "event_volunteers",
        "events", "homepage_hero_images", "links", "memoriam", "recognition",
        "news", "user_roles", "users", "roles"
    ]

    # Disable FK checks
    await conn.exec_driver_sql("SET session_replication_role = 'replica'")

    # Truncate all tables with cascade + identity reset
    for table in tables:
        await conn.exec_driver_sql(
            f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"
        )

    # Restore FK checks
    await conn.exec_driver_sql("SET session_replication_role = 'origin'")

    print("Database wiped.")




# ============================================================
#  POPULATE ROLES
# ============================================================

async def populate_roles(db):
    print("Creating roles...")
    for role in ROLES:
        await role_service.create(db, {"name": role})
    print("Roles created.")


# ============================================================
#  POPULATE USERS
# ============================================================

async def populate_users(db):
    print("Creating users...")

    users = []

    for i, role_name in enumerate(ROLES[:40], start=1):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]

        # 1. Fetch role object
        role = await db.execute(
            text("SELECT id FROM roles WHERE name = :name"),
            {"name": role_name}
        )
        role_id = role.scalar()

        # 2. Hash password manually
        hashed_pw = bcrypt.hash("TestPassword123!")

        # 3. Create user directly
        result = await db.execute(
            text("""
                INSERT INTO users (
                    membership_number, email, password_hash,
                    first_name, last_name, phone, address
                )
                VALUES (:membership_number, :email, :password_hash,
                        :first_name, :last_name, :phone, :address)
                RETURNING id
            """),
            {
                "membership_number": f"91000{i:03d}",
                "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                "password_hash": hashed_pw,
                "first_name": first,
                "last_name": last,
                "phone": f"555-100-{1000+i}",
                "address": f"{100+i} Council Drive"
            }
        )

        user_id = result.scalar()

        # 4. Insert into user_roles association table
        await db.execute(
            text("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:user_id, :role_id)
            """),
            {"user_id": user_id, "role_id": role_id}
        )

        users.append(
            User(
                id=user_id,
                membership_number=f"91000{i:03d}",
                email=f"{first.lower()}.{last.lower()}{i}@example.com",
                first_name=first,
                last_name=last
            )
        )

    await db.flush()
    await db.commit()

    print(f"{len(users)} users created.")
    return users

# async def populate_users(db):
#     print("Creating users...")

#     users = []
#     for i, role in enumerate(ROLES[:40], start=1):
#         first = FIRST_NAMES[i % len(FIRST_NAMES)]
#         last = LAST_NAMES[i % len(LAST_NAMES)]

#         user = await AuthService.create_user(
#             db=db,
#             membership_number=f"91000{i:03d}",
#             email=f"{first.lower()}.{last.lower()}@example.com",
#             password="TestPassword123!",
#             first_name=first,
#             last_name=last,
#             phone=f"555-100-{1000+i}",
#             address=f"{100+i} Council Drive",
#             role_names=[role]
#         )
#         users.append(user)

#     print(f"{len(users)} users created.")
#     return users


# ============================================================
#  POPULATE OFFICERS
# ============================================================

async def populate_officers(db, users):
    # These MUST match the PostgreSQL enum exactly
    officer_positions = [
        "Grand Knight",
        "Deputy Grand Knight",
        "Chancellor",
        "Recorder",
        "Treasurer",
        "Advocate",
        "Warden",
        "Inside Guard",
        "Outside Guard",
        "Trustee 1-Year",
        "Trustee 2-Year",
        "Trustee 3-Year",
        "Chaplain",
        "Financial Secretary",
        "Lecturer",
        "Past Grand Knight"
    ]

    # Create officers by assigning first N users to these positions
    for i, pos in enumerate(officer_positions):
        await officers_service.create(db, {
            "user_id": users[i].id,
            "position": str(pos)   # <-- CRITICAL FIX
        })



# ============================================================
#  POPULATE DIRECTORS
# ============================================================

async def populate_directors(db):
    print("Creating directors...")

    for pos in DIRECTOR_POSITIONS:
        await directors_service.create(db, {
            "name": pos,
            "description": f"{pos} oversees KOFC {pos.split()[0]} initiatives.",
            "email": f"{pos.lower().replace(' ', '_')}@example.com",
            "phone": "555-200-3000"
        })

    print("Directors created.")


# ============================================================
#  POPULATE COMMITTEES & PROGRAMS
# ============================================================

async def populate_committees_programs(db, users):
    print("Creating committees and programs...")

    committee_names = [
        "Faith Committee", "Family Committee", "Community Committee",
        "Life Committee", "Membership Committee", "Program Committee"
    ]

    committees = []
    for name in committee_names:
        c = await committees_service.create(db, {
            "name": name,
            "description": f"{name} oversees KOFC initiatives."
        })
        committees.append(c)

    program_data = [
        ("Rosary Night", "Faith", committees[0].id),
        ("Bible Study", "Faith", committees[0].id),
        ("Family Picnic", "Family", committees[1].id),
        ("Marriage Retreat", "Family", committees[1].id),
        ("Food Drive", "Community", committees[2].id),
        ("Highway Cleanup", "Community", committees[2].id),
        ("Pro-Life March", "Life", committees[3].id),
        ("Blood Drive", "Life", committees[3].id),
        ("Membership Drive", "Membership", committees[4].id),
        ("New Member Orientation", "Membership", committees[4].id),
        ("Council Planning", "Program", committees[5].id),
        ("Volunteer Training", "Program", committees[5].id),
    ]

    programs = []
    for title, category, cid in program_data:
        p = await programs_service.create(db, {
            "committee_id": cid,
            "name": title,
            "description": f"{title} program for KOFC {category}.",
            "category": category
        })
        programs.append(p)

    # Volunteers
    for i, p in enumerate(programs[:10]):
        await program_vol_service.create(db, {
            "program_id": p.id,
            "user_id": users[i].id,
            "notes": "Active volunteer."
        })

    print("Committees, programs, and volunteers created.")


# ============================================================
#  POPULATE EVENTS
# ============================================================

async def populate_events(db, users):
    print("Creating events...")

    event_titles = [
        "Fish Fry Friday",
        "Council Meeting",
        "Rosary Night",
        "Parish Cleanup",
        "Family Picnic",
        "Blood Drive",
        "Food Drive",
        "Christmas Party",
        "Easter Breakfast",
        "Membership Drive"
    ]

    events = []
    base_date = datetime.datetime.now()

    for i, title in enumerate(event_titles):
        e = await events_service.create(db, {
            "title": title,
            "description": f"{title} hosted by the Knights of Columbus.",
            "location": "St. Joseph Parish Hall",
            "start_time": base_date + datetime.timedelta(days=i),
            "end_time": base_date + datetime.timedelta(days=i, hours=2),
            "is_public": True,
            "created_by": users[0].id
        })
        events.append(e)

    # Volunteers
    for i, e in enumerate(events[:8]):
        await event_vol_service.create(db, {
            "event_id": e.id,
            "user_id": users[i].id,
            "hours": 2.0,
            "notes": "Helped with setup."
        })

    print("Events and volunteers created.")


# ============================================================
#  POPULATE NEWS, RECOGNITION, MEMORIAM, LINKS
# ============================================================

async def populate_public_content(db):
    print("Creating public content...")

    # News
    for i in range(12):
        await news_service.create(db, {
            "title": f"Council News Update #{i+1}",
            "body": "This is a KOFC news update for testing.",
            "author_id": 1
        })

    # Recognition
    for i in range(10):
        await recognition_service.create(db, {
            "title": f"Knight of the Month #{i+1}",
            "description": "Recognizing outstanding service.",
            "awarded_to": f"Member {i+1}",
            "awarded_at": datetime.datetime(2024, 1, i+1)
        })

    # Memoriam
    for i in range(6):
        await memoriam_service.create(db, {
            "name": f"Brother Knight {i+1}",
            "biography": "A faithful member of our council.",
            "date_of_passing": datetime.datetime(2023, 12, i+1)
        })

    # Links
    for i in range(10):
        await links_service.create(db, {
            "label": f"Resource Link {i+1}",
            "url": f"https://example.com/resource/{i+1}"
        })

    print("News, recognition, memoriam, and links created.")


# ============================================================
#  POPULATE HERO IMAGES
# ============================================================

async def populate_hero_images(db):
    print("Creating hero images...")

    for i in range(5):
        await hero_service.create(db, {
            "url": f"/static/test/hero_{i+1}.jpg",
            "caption": f"Hero Image {i+1}",
            "order": i,
            "is_active": True
        })

    print("Hero images created.")


# ============================================================
#  POPULATE MEDIA
# ============================================================

async def populate_media(db):
    print("Creating media albums and items...")

    album_titles = [
        "Parish Events", "Council Activities",
        "Family Programs", "Community Outreach"
    ]

    albums = []
    for title in album_titles:
        a = await media_album_service.create(db, {
            "title": title,
            "description": f"Photos from {title}."
        })
        albums.append(a)

    # Media items
    for i in range(40):
        await media_item_service.create(db, {
            "album_id": albums[i % len(albums)].id,
            "file_path": f"/static/test/media_{i+1}.jpg",
            "caption": f"Media Item {i+1}"
        })

    print("Media albums and items created.")


# ============================================================
#  POPULATE MARKET CENTER
# ============================================================

async def populate_market(db, users):
    print("Creating market categories, items, merchants...")

    categories = []
    for name in ["Apparel", "Accessories", "Decals", "Books", "Gifts", "Misc"]:
        c = await market_cat_service.create(db, {
            "name": name,
            "description": f"KOFC {name} items."
        })
        categories.append(c)

    # Items
    for i in range(12):
        await market_item_service.create(db, {
            "category_id": categories[i % len(categories)].id,
            "title": f"KOFC Item {i+1}",
            "description": "High-quality KOFC merchandise.",
            "price": 10.00 + i,
            "image_path": f"/static/test/market_{i+1}.jpg"
        })

    # Merchants
    merchants = []
    for i in range(6):
        m = await merchants_service.create(db, {
            "user_id": users[i].id,
            "business_name": f"Merchant {i+1}",
            "contact_email": f"merchant{i+1}@example.com",
            "contact_phone": "555-300-4000"
        })
        merchants.append(m)

    # Merchant Reports
    for i, m in enumerate(merchants):
        await merchant_reports_service.create(db, {
            "merchant_id": m.id,
            "report_path": f"/static/test/report_{i+1}.pdf"
        })

    print("Market center populated.")


# ============================================================
#  POPULATE JOBS
# ============================================================

async def populate_jobs(db):
    print("Creating jobs...")

    job_titles = [
        "Parish Maintenance Worker",
        "Event Coordinator",
        "Volunteer Organizer",
        "Kitchen Helper",
        "Groundskeeper",
        "Office Assistant"
    ]

    for title in job_titles:
        await jobs_service.create(db, {
            "title": title,
            "description": f"{title} position for KOFC.",
            "job_type": "Part-Time"
        })

    print("Jobs created.")


# ============================================================
#  POPULATE DEGREE SCHEDULE
# ============================================================

async def populate_degree_schedule(db):
    print("Creating degree schedule...")

    for i in range(6):
        await degree_service.create(db, {
            "degree_level": f"Degree {i+1}",
            "location": "St. Joseph Parish",
            "date": datetime.datetime.now() + datetime.timedelta(days=i * 30)
        })

    print("Degree schedule created.")


# ============================================================
#  POPULATE DOCUMENTS
# ============================================================

async def populate_documents(db):
    print("Creating documents...")

    for i in range(20):
        await documents_service.create(db, {
            "title": f"Document {i+1}",
            "file_path": f"/static/test/doc_{i+1}.pdf",
            "is_public": i % 2 == 0
        })

    print("Documents created.")


# ============================================================
#  POPULATE VOTING
# ============================================================

async def populate_voting(db, users):
    print("Creating votes...")

    votes = []
    for i in range(3):
        v = await votes_service.create(db, {
            "title": f"Vote #{i+1}",
            "description": "Council vote.",
            "vote_month": 1 + i,
            "vote_year": 2024
        })
        votes.append(v)

    # Options
    options = []
    for v in votes:
        for label in ["Yes", "No", "Abstain"]:
            o = await vote_options_service.create(db, {
                "vote_id": v.id,
                "label": label
            })
            options.append(o)

    # Cast votes
    for i, user in enumerate(users[:30]):
        v = votes[i % len(votes)]
        # Each vote has 3 options: Yes, No, Abstain
        # options are stored sequentially: [v1_yes, v1_no, v1_abstain, v2_yes, ...]
        option_index = (v.id - 1) * 3 + (i % 3)
        o = options[option_index]

        await vote_cast_service.create(db, {
            "vote_id": v.id,
            "option_id": o.id,
            "user_id": user.id
        })

    print("Voting system populated.")


# ============================================================
#  POPULATE PRAYER REQUESTS
# ============================================================

async def populate_prayer_requests(db):
    print("Creating prayer requests...")

    for i in range(15):
        await prayer_service.create(db, {
            "requester_name": f"Requester {i+1}",
            "requester_email": f"requester{i+1}@example.com",
            "is_member": i % 2 == 0,
            "request_text": "Please pray for my family.",
        })

    print("Prayer requests created.")


# ============================================================
#  POPULATE NEWSLETTERS
# ============================================================

async def populate_newsletters(db):
    print("Creating newsletters...")

    for i in range(12):
        await newsletter_service.create(db, {
            "title": f"Newsletter {i+1}",
            "file_path": f"/static/test/newsletter_{i+1}.pdf"
        })

    print("Newsletters created.")


# ============================================================
#  POPULATE SEO SETTINGS
# ============================================================

async def populate_seo_settings(db):
    print("Creating SEO settings...")

    pages = [
        "home", "about", "contact", "events", "programs",
        "market", "jobs", "news", "gallery", "prayer"
    ]

    for page in pages:
        await seo_service.create(db, {
            "page": page,
            "meta_title": f"{page.title()} - KOFC Council",
            "meta_description": f"SEO description for {page}.",
            "meta_keywords": f"{page}, kofc, council"
        })

    print("SEO settings created.")


# ============================================================
#  POPULATE UPLOADS
# ============================================================

async def populate_uploads(db, users):
    print("Creating uploads...")

    for i in range(20):
        await uploads_service.create(db, {
            "file_path": f"/static/uploads/upload_{i+1}.dat",
            "uploaded_by": users[i % len(users)].id
        })

    print("Uploads created.")


# ============================================================
#  POPULATE AUDIT LOG
# ============================================================

async def populate_audit_log(db, users):
    print("Creating audit log entries...")

    for i in range(50):
        await audit_service.create(db, {
            "user_id": users[i % len(users)].id,
            "action": "TEST_ACTION",
            "details": f"Performed test action #{i+1}"
        })

    print("Audit log created.")


# ============================================================
#  MAIN EXECUTION
# ============================================================

async def main():
    async with AsyncSessionLocal() as db:

        # 1. Wipe database
        await wipe_database(db)

        # 2. Populate roles
        await populate_roles(db)

        # 3. Populate users
        users = await populate_users(db)

        # 4. Officers & Directors
        await populate_officers(db, users)
        await populate_directors(db)

        # 5. Committees, Programs, Volunteers
        await populate_committees_programs(db, users)

        # 6. Events & Volunteers
        await populate_events(db, users)

        # 7. Public content
        await populate_public_content(db)

        # 8. Hero images
        await populate_hero_images(db)

        # 9. Media albums & items
        await populate_media(db)

        # 10. Market center
        await populate_market(db, users)

        # 11. Jobs
        await populate_jobs(db)

        # 12. Degree schedule
        await populate_degree_schedule(db)

        # 13. Documents
        await populate_documents(db)

        # 14. Voting system
        await populate_voting(db, users)

        # 15. Prayer requests
        await populate_prayer_requests(db)

        # 16. Newsletters
        await populate_newsletters(db)

        # 17. SEO settings
        await populate_seo_settings(db)

        # 18. Uploads
        await populate_uploads(db, users)

        # 19. Audit log
        await populate_audit_log(db, users)

        print("\n======================================")
        print(" KOFC TEST DATA POPULATION COMPLETE ")
        print("======================================\n")


if __name__ == "__main__":
    asyncio.run(main())
