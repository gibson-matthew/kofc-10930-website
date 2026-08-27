from enum import Enum
from sqlalchemy import Column, Integer, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class OfficerPosition(str, Enum):
    grand_knight = "Grand Knight"
    deputy_grand_knight = "Deputy Grand Knight"
    chancellor = "Chancellor"
    recorder = "Recorder"
    treasurer = "Treasurer"
    advocate = "Advocate"
    warden = "Warden"
    inside_guard = "Inside Guard"
    outside_guard = "Outside Guard"
    trustee_1_year = "Trustee 1-Year"
    trustee_2_year = "Trustee 2-Year"
    trustee_3_year = "Trustee 3-Year"
    chaplain = "Chaplain"
    financial_secretary = "Financial Secretary"
    lecturer = "Lecturer"
    past_grand_knight = "Past Grand Knight"


class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position = Column(
        PgEnum(
            OfficerPosition,
            name="officer_position_enum",
            values_callable=lambda enum: [e.value for e in enum]
        ),
        nullable=False
    )

    user = relationship("User", back_populates="officer_positions")
