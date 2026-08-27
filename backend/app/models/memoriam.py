from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, Date
from app.db.session import Base


class Memoriam(Base):
    __tablename__ = "memoriam"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    biography: Mapped[str | None] = mapped_column(Text)
    date_of_passing: Mapped[Date | None] = mapped_column(Date)
