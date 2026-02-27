"""Order and OrderEvent ORM models — hub-and-spoke lifecycle."""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Integer, Numeric, Boolean, DateTime, ForeignKey, Text,
    Enum as PgEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Pickup phase
    pickup_rider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riders.id"))
    pickup_slot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_address: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    pickup_lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    pickup_otp_hash: Mapped[str | None] = mapped_column(String(128))
    pickup_otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pickup_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Warehouse phase
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("warehouses.id"))
    warehouse_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Delivery phase
    delivery_rider_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("riders.id"))
    delivery_route_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("delivery_routes.id"))
    drop_address: Mapped[str] = mapped_column(Text, nullable=False)
    drop_lat: Mapped[float | None] = mapped_column(Numeric(10, 7))
    drop_lng: Mapped[float | None] = mapped_column(Numeric(10, 7))
    drop_otp_hash: Mapped[str | None] = mapped_column(String(128))
    drop_otp_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Recipient contact (for OTP forwarding)
    drop_contact_name: Mapped[str | None] = mapped_column(String(255))
    drop_contact_phone: Mapped[str | None] = mapped_column(String(20))
    drop_contact_telegram_id: Mapped[int | None] = mapped_column(Integer)

    # Package info
    package_size: Mapped[str] = mapped_column(
        PgEnum("SMALL", "MEDIUM", "LARGE", "BULKY", name="package_size", create_type=False),
        default="SMALL",
    )
    vehicle: Mapped[str] = mapped_column(
        PgEnum("BIKE", "MINI_VAN", "MINI_TRUCK", "TRUCK", name="vehicle_type", create_type=False),
        default="BIKE",
    )
    description: Mapped[str | None] = mapped_column(Text)

    # Pricing
    distance_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    duration_min: Mapped[int | None] = mapped_column(Integer)
    base_cost: Mapped[float | None] = mapped_column(Numeric(10, 2))
    surge_multiplier: Mapped[float] = mapped_column(Numeric(3, 2), default=1.00)
    addons_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    batch_discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    subscription_discount: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    total_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Status and flags
    status: Mapped[str] = mapped_column(
        PgEnum(
            "ORDER_PLACED", "PAYMENT_CONFIRMED", "PICKUP_SCHEDULED",
            "PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE", "PICKED_UP",
            "IN_TRANSIT_TO_WAREHOUSE", "AT_WAREHOUSE",
            "ROUTE_OPTIMIZED", "DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY",
            "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
            name="order_status", create_type=False,
        ),
        default="ORDER_PLACED",
    )
    payment: Mapped[str] = mapped_column(
        PgEnum("PENDING", "PAID", "REFUNDED", "FAILED", name="payment_status", create_type=False),
        default="PENDING",
    )
    is_express: Mapped[bool] = mapped_column(Boolean, default=False)
    is_batch_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    is_return_trip_pickup: Mapped[bool] = mapped_column(Boolean, default=False)

    # Payment method & references
    payment_mode: Mapped[str] = mapped_column(
        PgEnum("COD", "CARD", "UPI", name="payment_mode", create_type=False),
        default="COD",
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(String(255))   # kept for future
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(255)) # kept for future

    # Idempotency
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(unique=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="orders", lazy="selectin")
    pickup_rider = relationship("Rider", foreign_keys=[pickup_rider_id], lazy="selectin")
    delivery_rider = relationship("Rider", foreign_keys=[delivery_rider_id], lazy="selectin")
    warehouse = relationship("Warehouse", lazy="selectin")
    delivery_route = relationship("DeliveryRoute", back_populates="orders", lazy="selectin")
    events = relationship("OrderEvent", back_populates="order", lazy="selectin", order_by="OrderEvent.created_at")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(
        PgEnum(
            "ORDER_PLACED", "PAYMENT_CONFIRMED", "PICKUP_SCHEDULED",
            "PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE", "PICKED_UP",
            "IN_TRANSIT_TO_WAREHOUSE", "AT_WAREHOUSE",
            "ROUTE_OPTIMIZED", "DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY",
            "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
            name="order_status", create_type=False,
        ),
    )
    to_status: Mapped[str] = mapped_column(
        PgEnum(
            "ORDER_PLACED", "PAYMENT_CONFIRMED", "PICKUP_SCHEDULED",
            "PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE", "PICKED_UP",
            "IN_TRANSIT_TO_WAREHOUSE", "AT_WAREHOUSE",
            "ROUTE_OPTIMIZED", "DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY",
            "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED",
            name="order_status", create_type=False,
        ),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # USER, RIDER, SYSTEM, N8N
    actor_id: Mapped[uuid.UUID | None] = mapped_column()
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="events")
