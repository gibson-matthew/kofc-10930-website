from sqlalchemy import Column, Integer, Text
from backend.app.db.session import Base

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    label = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
