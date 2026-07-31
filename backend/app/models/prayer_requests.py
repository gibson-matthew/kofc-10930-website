from sqlalchemy import Column, Integer
from app.db.session import Base

class PrayerRequest(Base):
    __tablename__ = "prayer_requests"
    id = Column(Integer, primary_key=True, index=True)
