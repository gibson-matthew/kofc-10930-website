# from app.models.event_volunteers import EventVolunteer
# from app.models.user import User
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, String, TIMESTAMP, Boolean, ForeignKey
from app.db.session import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String)

    start_time: Mapped[str] = mapped_column(TIMESTAMP, nullable=False)
    end_time: Mapped[str | None] = mapped_column(TIMESTAMP)

    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # relationships
    creator: Mapped["User"] = relationship()
    volunteers: Mapped[list["EventVolunteer"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan"
    )
