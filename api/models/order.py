import uuid

from sqlalchemy import Column, Numeric, String
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID

from api.models.base import Base


order_status_enum = ENUM(
    "ORDER_PLACED",
    "PAYMENT_CONFIRMED",
    "PICKUP_SCHEDULED",
    "PICKUP_RIDER_ASSIGNED",
    "PICKUP_EN_ROUTE",
    "PICKED_UP",
    "IN_TRANSIT_TO_WAREHOUSE",
    "AT_WAREHOUSE",
    "ROUTE_OPTIMIZED",
    "DELIVERY_RIDER_ASSIGNED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
    "REFUNDED",
    name="order_status",
    create_type=False,
)


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(20), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)

    pickup_rider_id = Column(UUID(as_uuid=True), nullable=True)
    pickup_slot = Column(TIMESTAMP, nullable=True)
    pickup_address = Column(String, nullable=False)
    pickup_lat = Column(String, nullable=True)
    pickup_lng = Column(String, nullable=True)
    pickup_otp = Column(String(6), nullable=True)
    pickup_confirmed_at = Column(TIMESTAMP, nullable=True)

    warehouse_id = Column(UUID(as_uuid=True), nullable=True)
    warehouse_received_at = Column(TIMESTAMP, nullable=True)

    delivery_rider_id = Column(UUID(as_uuid=True), nullable=True)
    delivery_route_id = Column(UUID(as_uuid=True), nullable=True)
    drop_address = Column(String, nullable=False)
    drop_lat = Column(String, nullable=True)
    drop_lng = Column(String, nullable=True)
    drop_otp = Column(String(6), nullable=True)

    weight_kg = Column(Numeric(5, 2), nullable=True)
    weight_tier = Column(String(10), nullable=True)
    vehicle_type = Column(String(20), nullable=True)

    distance_km = Column(Numeric(8, 2), nullable=True)
    base_cost = Column(Numeric(10, 2), nullable=True)
    surge_multiplier = Column(Numeric(3, 2), nullable=False, default=1.00)
    addons_cost = Column(Numeric(10, 2), nullable=False, default=0)
    total_cost = Column(Numeric(10, 2), nullable=True)

    status = Column(order_status_enum, nullable=False, default="ORDER_PLACED")
    is_express = Column(String, nullable=False, default="false")
    is_batch_eligible = Column(String, nullable=False, default="true")
    is_return_trip_pickup = Column(String, nullable=False, default="false")

    payment_status = Column(String(20), nullable=False, default="PENDING")
    razorpay_order_id = Column(String(255), nullable=True)

    created_at = Column(TIMESTAMP, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False)
    delivered_at = Column(TIMESTAMP, nullable=True)
    cancelled_at = Column(TIMESTAMP, nullable=True)

