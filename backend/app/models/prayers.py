from sqlalchemy import Column, Integer
from app.db.session import Base

class Prayer(Base):
    __tablename__ = "prayer"
    id = Column(Integer, primary_key=True, index=True)
