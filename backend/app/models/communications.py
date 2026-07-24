from sqlalchemy import Column, Integer
from app.db.session import Base

class Communication(Base):
    __tablename__ = "communications"
    id = Column(Integer, primary_key=True, index=True)
