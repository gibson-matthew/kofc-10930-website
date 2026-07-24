from sqlalchemy import Column, Integer, Text, TIMESTAMP
from backend.app.db.session import Base

class Newsletter(Base):
    __tablename__ = "newsletters"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    published_at = Column(TIMESTAMP)
