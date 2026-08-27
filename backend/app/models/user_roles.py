# from sqlalchemy import Column, Integer, ForeignKey
# from sqlalchemy.orm import relationship
# from app.db.session import Base

# class UserRole(Base):
#     __tablename__ = "user_roles"

#     user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
#     role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

#     # REQUIRED for mapped association tables
#     user = relationship("User", back_populates="user_roles")
#     role = relationship("Role", back_populates="role_users")


from sqlalchemy import Table, Column, Integer, ForeignKey
from app.db.session import Base

UserRole = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)
