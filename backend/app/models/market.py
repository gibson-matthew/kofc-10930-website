from sqlalchemy import Column, Integer
from app.db.session import Base

class MarketItem(Base):
    __tablename__ = "market_items"
    id = Column(Integer, primary_key=True, index=True)
