from sqlalchemy import Column, Integer, Text
from app.db.session import Base

class Assembly(Base):
    __tablename__ = "assemblies"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
