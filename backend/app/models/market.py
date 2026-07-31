from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, Numeric, ForeignKey
from app.db.session import Base


class MarketItem(Base):
    __tablename__ = "market_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("market_categories.id", ondelete="CASCADE")
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    image_path: Mapped[str | None] = mapped_column(Text)

    # relationships
    # category: Mapped["MarketCategory"] = relationship(back_populates="items")
