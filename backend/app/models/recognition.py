from sqlalchemy import Column, Integer, Text, Date
from backend.app.db.session import Base

class Recognition(Base):
    __tablename__ = "recognition"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    awarded_to = Column(Text)
    awarded_at = Column(Date)
