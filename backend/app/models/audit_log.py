from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey
from backend.app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(Text, nullable=False)
    details = Column(Text)
    created_at = Column(TIMESTAMP)
