from enum import Enum
from sqlalchemy import Column, Integer, Enum as PgEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class OfficerPosition(str, Enum):
    grand_knight = "grand_knight"
    deputy_grand_knight = "deputy_grand_knight"
    chancellor = "chancellor"
    financial_secretary = "financial_secretary"
    treasurer = "treasurer"
    warden = "warden"
    advocate = "advocate"
    lecturer = "lecturer"
    inside_guard = "inside_guard"
    outside_guard = "outside_guard"
    trustee_1_year = "trustee_1_year"
    trustee_2_year = "trustee_2_year"
    trustee_3_year = "trustee_3_year"


class Officer(Base):
    __tablename__ = "officers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position = Column(PgEnum(OfficerPosition, name="officer_position_enum"), nullable=False)

    user = relationship("User", back_populates="officer_positions")
