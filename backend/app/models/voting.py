from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey
from backend.app.db.session import Base

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    vote_month = Column(Integer)
    vote_year = Column(Integer)
    created_at = Column(TIMESTAMP)

class VoteOption(Base):
    __tablename__ = "vote_options"

    id = Column(Integer, primary_key=True)
    vote_id = Column(Integer, ForeignKey("votes.id"))
    label = Column(Text, nullable=False)

class VoteCast(Base):
    __tablename__ = "vote_cast"

    id = Column(Integer, primary_key=True)
    vote_id = Column(Integer, ForeignKey("votes.id"))
    option_id = Column(Integer, ForeignKey("vote_options.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    cast_at = Column(TIMESTAMP)
