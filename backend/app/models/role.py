from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base

from app.models.user_roles import UserRole



class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # REQUIRED for mapped association table
    # role_users = relationship("UserRole", back_populates="role")

    # Many-to-many relationship with users
    # users = relationship(
    #     "User",
    #     secondary="user_roles",
    #     back_populates="roles",
    #     lazy="raise",
    # )
    users = relationship(
        "User",
        secondary=UserRole,
        back_populates="roles",
        lazy="raise",
    )


# @property
# def users(self):
#     return [ur.user for ur in self.role_users]
