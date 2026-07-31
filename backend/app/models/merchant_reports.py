from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, TIMESTAMP, ForeignKey
from app.db.session import Base


class MerchantReport(Base):
    __tablename__ = "merchant_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id", ondelete="CASCADE")
    )

    report_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        TIMESTAMP, server_default="NOW()"
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="reports")
