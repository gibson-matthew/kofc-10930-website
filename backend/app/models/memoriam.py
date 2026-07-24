from sqlalchemy import Column, Integer, Text, Date
from backend.app.db.session import Base

class Memoriam(Base):
    __tablename__ = "memoriam"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    biography = Column(Text)
    date_of_passing = Column(Date)
