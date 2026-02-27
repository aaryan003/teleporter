"""Rider ORM model — company employees."""

import uuid
from datetime import datetime, time
from sqlalchemy import String, BigInteger, Integer, Numeric, Boolean, Time, DateTime, ForeignKey, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class Rider(Base):
    __tablename__ = "riders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    vehicle: Mapped[str] = mapped_column(PgEnum("BIKE", "AUTO", "VAN", name="vehicle_type", create_type=False), default="BIKE")
    vehicle_reg: Mapped[str | None] = mapped_column(String(30))
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    current_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    current_lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    status: Mapped[str] = mapped_column(
        PgEnum("ON_DUTY", "OFF_DUTY", "ON_DELIVERY", "ON_PICKUP", name="rider_status", create_type=False),
        default="OFF_DUTY",
    )
    shift_start: Mapped[time] = mapped_column(Time, default=time(8, 0))
    shift_end: Mapped[time] = mapped_column(Time, default=time(20, 0))
    max_capacity: Mapped[int] = mapped_column(Integer, default=5)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.00)
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    last_location_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    warehouse = relationship("Warehouse", back_populates="riders", lazy="selectin")
    delivery_routes = relationship("DeliveryRoute", back_populates="rider", lazy="selectin")
