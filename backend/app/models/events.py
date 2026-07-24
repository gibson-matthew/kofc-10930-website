from sqlalchemy import Column, Integer
from app.db.session import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    