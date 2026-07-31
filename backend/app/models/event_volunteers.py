# from app.models.user import User
# from app.models.events import Event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, Numeric, ForeignKey
from app.db.session import Base


class EventVolunteer(Base):
    __tablename__ = "event_volunteers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    hours: Mapped[float | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    # relationships
    event: Mapped["Event"] = relationship(back_populates="volunteers")
    user: Mapped["User"] = relationship()
