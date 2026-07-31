from sqlalchemy import Column, Integer, Text
from app.db.session import Base

class Director(Base):
    __tablename__ = "directors"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    email = Column(Text)
    phone = Column(Text)
