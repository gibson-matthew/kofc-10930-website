from sqlalchemy import Column, Integer
from app.db.session import Base

class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
