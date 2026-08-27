from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, ForeignKey
from app.db.session import Base


class VoteOption(Base):
    __tablename__ = "vote_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vote_id: Mapped[int] = mapped_column(
        ForeignKey("votes.id", ondelete="CASCADE")
    )

    label: Mapped[str] = mapped_column(Text, nullable=False)

    # relationships
    vote: Mapped["Vote"] = relationship(back_populates="options")
    casts: Mapped[list["VoteCast"]] = relationship(
        back_populates="option",
        cascade="all, delete-orphan"
    )
