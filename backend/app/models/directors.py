from enum import Enum

from sqlalchemy import Column, Integer, Enum as PgEnum, Text
from app.db.session import Base

class DirectorPosition(str, Enum):
    program_director = "Program Director"
    faith_director = "Faith Director"
    family_director = "Family Director"
    community_director = "Community Director"
    life_director = "Life Director"
    membership_director = "Membership Director"

class Director(Base):
    __tablename__ = "directors"

    id = Column(Integer, primary_key=True)
    name = Column(
        PgEnum(
            DirectorPosition,
            name="director_position_enum",
            values_callable=lambda enum: [e.value for e in enum]
        ),
        nullable=False
    )
    description = Column(Text)
    email = Column(Text)
    phone = Column(Text)
