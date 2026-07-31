from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, String, ForeignKey
from app.db.session import Base


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committees.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String, nullable=False)

    # relationships
    committee: Mapped["Committee"] = relationship(back_populates="programs")
    volunteers: Mapped[list["ProgramVolunteer"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan"
    )
