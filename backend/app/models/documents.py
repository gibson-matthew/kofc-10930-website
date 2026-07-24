from sqlalchemy import Column, Integer
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
