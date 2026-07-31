from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, TIMESTAMP
from app.db.session import Base


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    vote_month: Mapped[int | None] = mapped_column(Integer)
    vote_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    # relationships
    options: Mapped[list["VoteOption"]] = relationship(
        back_populates="vote",
        cascade="all, delete-orphan"
    )
    casts: Mapped[list["VoteCast"]] = relationship(
        back_populates="vote",
        cascade="all, delete-orphan"
    )
