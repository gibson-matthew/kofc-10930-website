from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text
from app.db.session import Base


class Committee(Base):
    __tablename__ = "committees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # relationships
    programs: Mapped[list["Program"]] = relationship(
        back_populates="committee",
        cascade="all, delete-orphan"
    )
