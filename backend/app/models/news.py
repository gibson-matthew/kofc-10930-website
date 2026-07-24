from sqlalchemy import Column, Integer
from app.db.session import Base

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
