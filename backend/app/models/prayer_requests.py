from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Text, DateTime, Integer

from app.db.session import Base


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    requester_name: Mapped[str] = mapped_column(String, nullable=False)
    requester_email: Mapped[str] = mapped_column(String, nullable=False)

    is_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    request_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
