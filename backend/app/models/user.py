from datetime import datetime
from typing import List

from app.models.user_roles import UserRole
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    membership_number = Column(String, unique=True, nullable=False)

    email = Column(String, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)

    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)

    profile_photo = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # REQUIRED for mapped association table
    # user_roles = relationship("UserRole", back_populates="user")

    # Many-to-many relationship with roles
    # roles = relationship(
    #     "Role",
    #     secondary="user_roles",
    #     back_populates="users",
    #     lazy="raise",
    # )
    roles = relationship(
        "Role",
        secondary=UserRole,        # <-- Use the Table, not a string
        back_populates="users",
        lazy="raise",
    )
            

    officer_positions = relationship("Officer", back_populates="user")

    # Example relationships (optional, but helpful)
    # news_posts = relationship("News", back_populates="author")
    # events_created = relationship("Event", back_populates="creator")
    # merchant_profile = relationship("Merchant", back_populates="user")

    # Convenience property to access roles cleanly
    # @property
    # def roles(self):
    #     return [ur.role for ur in self.user_roles]

    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
