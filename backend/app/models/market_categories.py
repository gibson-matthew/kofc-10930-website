from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text
from app.db.session import Base


class MarketCategory(Base):
    __tablename__ = "market_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["MarketItem"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )
