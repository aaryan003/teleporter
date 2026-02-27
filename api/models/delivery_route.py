"""DeliveryRoute ORM model — optimized multi-stop routes."""

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, JSON, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class DeliveryRoute(Base):
    __tablename__ = "delivery_routes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riders.id"))
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(
        PgEnum("PLANNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="route_status", create_type=False),
        default="PLANNED",
    )
    optimized_sequence: Mapped[list] = mapped_column(JSON, default=[])
    total_distance_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    total_duration_min: Mapped[int | None] = mapped_column(Integer)
    total_parcels: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    rider = relationship("Rider", back_populates="delivery_routes", lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    orders = relationship("Order", back_populates="delivery_route", lazy="selectin")
