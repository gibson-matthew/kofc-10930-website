from sqlalchemy import Column, Integer, Text, TIMESTAMP
from backend.app.db.session import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    job_type = Column(Text, nullable=False)
    posted_at = Column(TIMESTAMP)
