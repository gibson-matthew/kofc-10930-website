from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text, String, TIMESTAMP
from app.db.session import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    job_type: Mapped[str] = mapped_column(String, nullable=False)  # commissioned, hourly, salaried
    posted_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )
