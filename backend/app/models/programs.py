from sqlalchemy import Column, Integer
from app.db.session import Base

class Program(Base):
    __tablename__ = "programs"
    id = Column(Integer, primary_key=True, index=True)
