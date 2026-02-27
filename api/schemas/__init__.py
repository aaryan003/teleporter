"""Pydantic schemas for API request/response models."""

from __future__ import annotations
import uuid
from datetime import datetime, time
from enum import Enum
from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────

class VehicleType(str, Enum):
    BIKE = "BIKE"
    AUTO = "AUTO"
    VAN = "VAN"


class WeightTier(str, Enum):
    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"


class OrderStatus(str, Enum):
    ORDER_PLACED = "ORDER_PLACED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    PICKUP_SCHEDULED = "PICKUP_SCHEDULED"
    PICKUP_RIDER_ASSIGNED = "PICKUP_RIDER_ASSIGNED"
    PICKUP_EN_ROUTE = "PICKUP_EN_ROUTE"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT_TO_WAREHOUSE = "IN_TRANSIT_TO_WAREHOUSE"
    AT_WAREHOUSE = "AT_WAREHOUSE"
    ROUTE_OPTIMIZED = "ROUTE_OPTIMIZED"
    DELIVERY_RIDER_ASSIGNED = "DELIVERY_RIDER_ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class RiderStatus(str, Enum):
    ON_DUTY = "ON_DUTY"
    OFF_DUTY = "OFF_DUTY"
    ON_DELIVERY = "ON_DELIVERY"
    ON_PICKUP = "ON_PICKUP"


class PaymentMode(str, Enum):
    COD = "COD"
    CARD = "CARD"
    UPI = "UPI"


class SubscriptionPlan(str, Enum):
    STARTER = "STARTER"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"


# ── User Schemas ───────────────────────────────────────────

class UserCreate(BaseModel):
    telegram_id: int
    full_name: str
    phone: str | None = None
    telegram_username: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    full_name: str
    phone: str | None
    telegram_username: str | None
    is_blocked: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Rider Schemas ──────────────────────────────────────────

class RiderCreate(BaseModel):
    telegram_id: int
    employee_id: str
    full_name: str
    phone: str
    vehicle: VehicleType = VehicleType.BIKE
    vehicle_reg: str | None = None
    warehouse_id: uuid.UUID | None = None
    shift_start: time = time(8, 0)
    shift_end: time = time(20, 0)
    max_capacity: int = 5


class RiderResponse(BaseModel):
    id: uuid.UUID
    telegram_id: int
    employee_id: str
    full_name: str
    phone: str
    vehicle: str
    status: str
    warehouse_id: uuid.UUID | None
    current_lat: float | None
    current_lng: float | None
    shift_start: time
    shift_end: time
    max_capacity: int
    current_load: int
    rating: float
    total_deliveries: int
    created_at: datetime

    class Config:
        from_attributes = True


class RiderLocationUpdate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


# ── Order Schemas ──────────────────────────────────────────

class OrderCreate(BaseModel):
    telegram_id: int
    pickup_address: str
    drop_address: str
    weight_tier: WeightTier = WeightTier.LIGHT
    weight_kg: float | None = None
    description: str | None = None
    is_express: bool = False
    is_batch_eligible: bool = True
    payment_mode: PaymentMode = PaymentMode.COD
    idempotency_key: uuid.UUID | None = None


class PriceEstimate(BaseModel):
    distance_km: float
    duration_min: int
    base_cost: float
    surge_multiplier: float
    surge_reason: str | None = None
    addons_cost: float = 0.0
    batch_discount: float = 0.0
    subscription_discount: float = 0.0
    total_cost: float
    vehicle_type: VehicleType
    price_valid_until: datetime


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    status: str
    pickup_address: str
    drop_address: str
    weight: str
    vehicle: str
    distance_km: float | None
    duration_min: int | None
    total_cost: float
    is_express: bool
    payment: str
    payment_mode: str | None = None
    created_at: datetime
    delivered_at: datetime | None

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    actor_type: str = "SYSTEM"
    actor_id: uuid.UUID | None = None
    metadata: dict | None = None


# ── Warehouse Schemas ──────────────────────────────────────

class WarehouseResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    lat: float
    lng: float
    city: str | None
    capacity: int
    current_load: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Delivery Route Schemas ─────────────────────────────────

class RouteResponse(BaseModel):
    id: uuid.UUID
    rider_id: uuid.UUID | None
    status: str
    optimized_sequence: list
    total_distance_km: float | None
    total_duration_min: int | None
    total_parcels: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Subscription Schemas ───────────────────────────────────

class SubscriptionCreate(BaseModel):
    user_id: uuid.UUID
    plan: SubscriptionPlan


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    plan: str
    monthly_price: float
    free_deliveries_total: int
    free_deliveries_used: int
    starts_at: datetime
    expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ── Pickup Slot Schemas ────────────────────────────────────

class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    available_capacity: int


class AvailableSlotsResponse(BaseModel):
    date: str
    slots: list[TimeSlot]
    message: str | None = None


# ── Analytics Schemas ──────────────────────────────────────

class DashboardStats(BaseModel):
    total_orders: int
    orders_today: int
    orders_in_transit: int
    orders_delivered: int
    orders_cancelled: int
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    active_riders: int
    avg_delivery_time_min: float | None
    sla_compliance_pct: float | None


class AIInsightResponse(BaseModel):
    id: int
    category: str
    severity: str
    title: str
    insight: str
    data: dict | None
    is_read: bool
    generated_at: datetime

    class Config:
        from_attributes = True


# ── OTP Schemas ────────────────────────────────────────────

class OTPVerifyRequest(BaseModel):
    order_id: uuid.UUID
    otp_type: str  # "pickup" or "drop"
    otp_code: str = Field(..., min_length=6, max_length=6)
    rider_id: uuid.UUID
