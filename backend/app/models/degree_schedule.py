from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, TIMESTAMP
from app.db.session import Base


class DegreeSchedule(Base):
    __tablename__ = "degree_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    degree_level: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    date: Mapped[str] = mapped_column(TIMESTAMP, nullable=False)
