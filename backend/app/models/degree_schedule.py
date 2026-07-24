from sqlalchemy import Column, Integer, Text, TIMESTAMP
from backend.app.db.session import Base

class DegreeSchedule(Base):
    __tablename__ = "degree_schedule"

    id = Column(Integer, primary_key=True)
    degree_level = Column(Text, nullable=False)
    location = Column(Text)
    date = Column(TIMESTAMP, nullable=False)
