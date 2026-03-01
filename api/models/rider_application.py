"""RiderApplication ORM model — rider onboarding KYC applications."""

import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, DateTime, ForeignKey, Text, Enum as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class RiderApplication(Base):
    __tablename__ = "rider_applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    vehicle: Mapped[str] = mapped_column(
        PgEnum("BIKE", "MINI_VAN", "MINI_TRUCK", "TRUCK", name="vehicle_type", create_type=False),
        default="BIKE",
    )
    vehicle_reg: Mapped[str | None] = mapped_column(String(30))
    license_file_id: Mapped[str | None] = mapped_column(String(255))
    license_file_url: Mapped[str | None] = mapped_column(Text)
    aadhar_file_id: Mapped[str | None] = mapped_column(String(255))
    aadhar_file_url: Mapped[str | None] = mapped_column(Text)
    preferred_warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    status: Mapped[str] = mapped_column(
        PgEnum("PENDING", "APPROVED", "REJECTED", name="application_status", create_type=False),
        default="PENDING",
    )
    admin_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    preferred_warehouse = relationship("Warehouse", lazy="selectin")
