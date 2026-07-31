from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, ForeignKey
from app.db.session import Base


class ProgramVolunteer(Base):
    __tablename__ = "program_volunteers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)

    # relationships
    program: Mapped["Program"] = relationship(back_populates="volunteers")
    user: Mapped["User"] = relationship()
