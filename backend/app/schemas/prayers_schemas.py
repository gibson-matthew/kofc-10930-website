from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ============================================================
#  BASE SCHEMA
# ============================================================

class PrayerRequestBase(BaseModel):
    request_text: str = Field(..., min_length=5, max_length=5000)


# ============================================================
#  MEMBER SUBMISSION
# ============================================================

class PrayerRequestCreate(PrayerRequestBase):
    """
    Schema for authenticated member prayer submissions.
    """
    pass


# ============================================================
#  GUEST SUBMISSION
# ============================================================

class PrayerRequestGuestCreate(PrayerRequestBase):
    """
    Schema for guest prayer submissions.
    """
    requester_name: str = Field(..., min_length=2, max_length=100)
    requester_email: EmailStr


# ============================================================
#  RESPONSE SCHEMA
# ============================================================

class PrayerRequestResponse(BaseModel):
    id: int
    requester_name: str | None
    requester_email: str | None
    is_member: bool
    request_text: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
