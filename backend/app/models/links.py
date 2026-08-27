from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text
from app.db.session import Base


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
