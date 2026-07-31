from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, TIMESTAMP, ForeignKey, UniqueConstraint
from app.db.session import Base


class VoteCast(Base):
    __tablename__ = "vote_cast"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    vote_id: Mapped[int] = mapped_column(
        ForeignKey("votes.id", ondelete="CASCADE")
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("vote_options.id")
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    cast_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    # relationships
    vote: Mapped["Vote"] = relationship(back_populates="casts")
    option: Mapped["VoteOption"] = relationship(back_populates="casts")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("vote_id", "user_id", name="uq_vote_user"),
    )
