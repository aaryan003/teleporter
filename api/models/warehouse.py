"""Warehouse ORM model."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    capacity: Mapped[int] = mapped_column(Integer, default=500)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    operating_hours: Mapped[dict] = mapped_column(JSON, default={"start": "07:00", "end": "21:00"})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    riders = relationship("Rider", back_populates="warehouse", lazy="selectin")
