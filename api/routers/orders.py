"""Order management API endpoints."""

import uuid
import random
import string
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.order import Order, OrderEvent
from models.user import User
from schemas import (
    OrderCreate, OrderResponse, OrderStatusUpdate,
    PriceEstimate, VehicleType, OTPVerifyRequest,
    AvailableSlotsResponse, TimeSlot,
)
from services.pricing import calculate_price, determine_vehicle, calculate_surge
from services.maps import geocode, get_distance
from services.otp import generate_otp, verify_otp
from services.pickup_scheduler import (
    get_available_slots, get_scheduling_message, determine_time_factor,
)

router = APIRouter()


def _generate_order_number() -> str:
    """Generate human-readable order number: DLV-YYMMDD-XXXX."""
    now = datetime.utcnow()
    date_part = now.strftime("%y%m%d")
    rand_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"DLV-{date_part}-{rand_part}"


@router.post("/estimate", response_model=PriceEstimate)
async def estimate_price(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Calculate price estimate without creating an order."""
    # Geocode addresses
    pickup_geo = await geocode(data.pickup_address)
    drop_geo = await geocode(data.drop_address)

    if not pickup_geo or not drop_geo:
        raise HTTPException(status_code=400, detail="Could not geocode one or both addresses")

    # Get distance
    dist = await get_distance(
        pickup_geo["lat"], pickup_geo["lng"],
        drop_geo["lat"], drop_geo["lng"],
    )

    # Calculate surge (simplified — count active orders vs riders)
    active_orders = (await db.execute(
        select(func.count(Order.id)).where(
            Order.status.in_(["PICKUP_SCHEDULED", "PICKUP_EN_ROUTE", "OUT_FOR_DELIVERY"])
        )
    )).scalar() or 0
    # Available riders count is simplified for estimate
    surge_mult, surge_reason = calculate_surge(active_orders, 5)  # Default 5 riders

    # Calculate price
    time_factor = "EXPRESS" if data.is_express else "STANDARD"
    price = calculate_price(
        distance_km=dist["distance_km"],
        duration_min=dist["duration_min"],
        weight_tier=data.weight_tier.value,
        time_factor_key=time_factor,
        surge_multiplier=surge_mult,
        surge_reason=surge_reason,
        is_batch_eligible=data.is_batch_eligible,
    )

    return PriceEstimate(
        distance_km=price.distance_km,
        duration_min=price.duration_min,
        base_cost=price.base_cost,
        surge_multiplier=price.surge_multiplier,
        surge_reason=price.surge_reason,
        addons_cost=price.addons_cost,
        batch_discount=price.batch_discount,
        subscription_discount=price.subscription_discount,
        total_cost=price.total_cost,
        vehicle_type=VehicleType(price.vehicle_type),
        price_valid_until=datetime.utcnow(),
    )


@router.post("/", response_model=OrderResponse)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new order."""
    # Check idempotency
    if data.idempotency_key:
        existing = await db.execute(
            select(Order).where(Order.idempotency_key == data.idempotency_key)
        )
        found = existing.scalar_one_or_none()
        if found:
            return found

    # Get user
    user_result = await db.execute(
        select(User).where(User.telegram_id == data.telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not registered")

    # Geocode
    pickup_geo = await geocode(data.pickup_address)
    drop_geo = await geocode(data.drop_address)
    if not pickup_geo or not drop_geo:
        raise HTTPException(status_code=400, detail="Could not geocode addresses")

    # Distance & pricing
    dist = await get_distance(
        pickup_geo["lat"], pickup_geo["lng"],
        drop_geo["lat"], drop_geo["lng"],
    )

    time_factor = "EXPRESS" if data.is_express else "STANDARD"
    price = calculate_price(
        distance_km=dist["distance_km"],
        duration_min=dist["duration_min"],
        weight_tier=data.weight_tier.value,
        time_factor_key=time_factor,
        is_batch_eligible=data.is_batch_eligible,
    )

    vehicle = determine_vehicle(data.weight_tier.value)

    order = Order(
        order_number=_generate_order_number(),
        user_id=user.id,
        pickup_address=data.pickup_address,
        pickup_lat=pickup_geo["lat"],
        pickup_lng=pickup_geo["lng"],
        drop_address=data.drop_address,
        drop_lat=drop_geo["lat"],
        drop_lng=drop_geo["lng"],
        weight_kg=data.weight_kg,
        weight=data.weight_tier.value,
        vehicle=vehicle,
        description=data.description,
        distance_km=price.distance_km,
        duration_min=price.duration_min,
        base_cost=price.base_cost,
        surge_multiplier=price.surge_multiplier,
        total_cost=price.total_cost,
        is_express=data.is_express,
        is_batch_eligible=data.is_batch_eligible,
        payment_mode=data.payment_mode.value if data.payment_mode else "COD",
        idempotency_key=data.idempotency_key,
    )
    db.add(order)

    # Create order event
    event = OrderEvent(
        order_id=order.id,
        to_status="ORDER_PLACED",
        actor_type="USER",
        actor_id=user.id,
    )
    db.add(event)

    await db.flush()
    await db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get order by ID."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List orders with optional status filter."""
    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    query = query.offset(skip).limit(limit).order_by(Order.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update order status with audit event."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = data.status.value

    if data.status.value == "DELIVERED":
        order.delivered_at = datetime.utcnow()
    elif data.status.value == "CANCELLED":
        order.cancelled_at = datetime.utcnow()

    event = OrderEvent(
        order_id=order.id,
        from_status=old_status,
        to_status=data.status.value,
        actor_type=data.actor_type,
        actor_id=data.actor_id,
    )
    db.add(event)

    return {"order_id": str(order_id), "old_status": old_status, "new_status": data.status.value}


@router.post("/{order_id}/otp/generate")
async def generate_order_otp(
    order_id: uuid.UUID,
    otp_type: str = Query(..., regex="^(pickup|drop)$"),
    db: AsyncSession = Depends(get_db),
):
    """Generate OTP for pickup or drop-off."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    otp = await generate_otp(str(order_id), otp_type)
    return {"otp": otp, "otp_type": otp_type, "expires_in_seconds": 600}


@router.post("/{order_id}/otp/verify")
async def verify_order_otp(data: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP for pickup or drop-off."""
    result = await verify_otp(str(data.order_id), data.otp_type, data.otp_code)

    if result["valid"]:
        # Update order status
        order_result = await db.execute(select(Order).where(Order.id == data.order_id))
        order = order_result.scalar_one_or_none()
        if order:
            if data.otp_type == "pickup":
                order.status = "PICKED_UP"
                order.pickup_confirmed_at = datetime.utcnow()
            else:
                order.status = "DELIVERED"
                order.delivered_at = datetime.utcnow()

            event = OrderEvent(
                order_id=order.id,
                from_status=order.status,
                to_status="PICKED_UP" if data.otp_type == "pickup" else "DELIVERED",
                actor_type="RIDER",
                actor_id=data.rider_id,
            )
            db.add(event)

    return result


@router.get("/user/{telegram_id}", response_model=list[OrderResponse])
async def get_user_orders(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get all orders for a specific user."""
    user_result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    )
    return result.scalars().all()
