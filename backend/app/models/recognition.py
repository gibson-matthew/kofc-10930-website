from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, Date
from app.db.session import Base


class Recognition(Base):
    __tablename__ = "recognition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    awarded_to: Mapped[str | None] = mapped_column(Text)
    awarded_at: Mapped[Date | None] = mapped_column(Date)
