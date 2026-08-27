from sqlalchemy import Column, Integer
from app.db.session import Base

class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, index=True)
