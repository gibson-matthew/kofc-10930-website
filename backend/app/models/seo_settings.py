from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, Text
from app.db.session import Base

class SEOSettings(Base):
    __tablename__ = "seo_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    meta_title: Mapped[str | None] = mapped_column(Text)
    meta_description: Mapped[str | None] = mapped_column(Text)
    meta_keywords: Mapped[str | None] = mapped_column(Text)
