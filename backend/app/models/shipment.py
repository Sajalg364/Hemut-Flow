from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # e.g. "SHIP-1042"
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # in_transit, delivered, delayed, pending
    carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    weight_kg: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    items_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Shipment(id={self.id}, status={self.status})>"
