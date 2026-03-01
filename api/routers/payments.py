"""
Payment endpoints — COD + simulated Card/UPI payments.

Payment modes:
  COD  → Order goes straight to PAYMENT_CONFIRMED (collect on delivery)
  CARD → Simulated: DB entry recorded, status moves forward immediately
  UPI  → Simulated: DB entry recorded, status moves forward immediately
"""

import logging
import uuid

logger = logging.getLogger(__name__)
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.order import Order, OrderEvent
from models.rider import Rider
from models.warehouse import Warehouse
from services.otp import generate_otp
from services.notifications import notify_user_order_status, notify_rider_task
from services.maps import get_distance, geocode, haversine_distance

router = APIRouter()

# Riders within this radius (km) of pickup are "in zone"; if none available, assign nearest from anywhere
ZONE_RADIUS_KM = 25.0


def _rider_location(rider: Rider) -> tuple[float, float] | None:
    """Get rider's location: GPS if set, else warehouse location."""
    if rider.current_lat is not None and rider.current_lng is not None:
        return (float(rider.current_lat), float(rider.current_lng))
    if rider.warehouse_id and rider.warehouse:
        return (float(rider.warehouse.lat), float(rider.warehouse.lng))
    return None


async def _assign_nearest_pickup_rider(
    order: Order,
    db: AsyncSession,
):
    """
    Assign the nearest ON_DUTY rider to the order's pickup location.
    Uses rider GPS if available, else warehouse location.
    """
    logger.info("Rider assignment: order %s pickup_lat=%s pickup_lng=%s", order.order_number, order.pickup_lat, order.pickup_lng)
    pickup_lat = order.pickup_lat
    pickup_lng = order.pickup_lng
    if not pickup_lat or not pickup_lng:
        # Geocode pickup address if coords missing
        if order.pickup_address:
            geo = await geocode(order.pickup_address)
            if geo:
                pickup_lat, pickup_lng = geo["lat"], geo["lng"]
                order.pickup_lat = pickup_lat
                order.pickup_lng = pickup_lng
        if not pickup_lat or not pickup_lng:
            logger.warning("Rider assignment: no pickup coords for order %s", order.order_number)
            return None

    pickup_lat = float(pickup_lat)
    pickup_lng = float(pickup_lng)

    riders_result = await db.execute(
        select(Rider).where(Rider.status == "ON_DUTY").options(selectinload(Rider.warehouse))
    )
    riders = riders_result.scalars().all()
    if not riders:
        logger.warning("Rider assignment: no ON_DUTY riders")
        return None

    # Prefer riders with real GPS; only use warehouse-based location if no one has GPS
    riders_with_gps = [r for r in riders if r.current_lat is not None and r.current_lng is not None]
    riders_warehouse_only = [r for r in riders if r not in riders_with_gps and _rider_location(r)]
    eligible = riders_with_gps if riders_with_gps else riders_warehouse_only
    if not eligible:
        logger.warning("Rider assignment: no riders with location (GPS or warehouse)")
        return None

    logger.info(
        "Rider assignment: %d eligible (%d with GPS) for order %s",
        len(eligible),
        len(riders_with_gps),
        order.order_number,
    )

    # Two-tier: first try riders in zone (within ZONE_RADIUS_KM); if none, fall back to nearest from anywhere
    in_zone = []
    for r in eligible:
        loc = _rider_location(r)
        if loc:
            d = haversine_distance(pickup_lat, pickup_lng, loc[0], loc[1])
            if d <= ZONE_RADIUS_KM:
                in_zone.append(r)
    pool = in_zone if in_zone else eligible
    if in_zone:
        logger.info("Rider assignment: %d in-zone riders for order %s", len(in_zone), order.order_number)
    else:
        logger.info("Rider assignment: no in-zone riders, using nearest from anywhere for order %s", order.order_number)

    best_rider = None
    best_distance_km: float | None = None
    best_duration_min: int | None = None

    for rider in pool:
        loc = _rider_location(rider)
        if not loc:
            continue
        try:
            dist = await get_distance(
                loc[0], loc[1],
                pickup_lat,
                pickup_lng,
            )
        except Exception as e:
            logger.warning("Distance calc failed for rider %s: %s", rider.id, e)
            continue

        d_km = dist.get("distance_km")
        if d_km is None:
            continue

        if best_distance_km is None or d_km < best_distance_km:
            best_distance_km = d_km
            best_duration_min = dist.get("duration_min")
            best_rider = rider

    if not best_rider:
        return None

    logger.info("Assigning rider %s (id=%s) to order %s", best_rider.full_name, best_rider.id, order.order_number)
    old_status = order.status
    order.pickup_rider_id = best_rider.id
    order.status = "PICKUP_RIDER_ASSIGNED"

    best_rider.status = "ON_PICKUP"
    best_rider.current_load = (best_rider.current_load or 0) + 1

    event = OrderEvent(
        order_id=order.id,
        from_status=old_status,
        to_status="PICKUP_RIDER_ASSIGNED",
        actor_type="SYSTEM",
    )
    db.add(event)

    # Notify rider with parcel and delivery details
    try:
        await notify_rider_task(
            best_rider.telegram_id,
            "PICKUP",
            {
                "order_number": order.order_number,
                "address": order.pickup_address,
                "drop_address": order.drop_address,
                "total_cost": float(order.total_cost),
                "slot": "ASAP",
                "lat": pickup_lat,
                "lng": pickup_lng,
            },
        )
    except Exception as e:
        logger.warning("Failed to notify rider %s: %s", best_rider.id, e)

    # Notify user that a rider has been assigned
    try:
        if order.user:
            extra = f"Rider: {best_rider.full_name} ({best_rider.vehicle})"
            if best_duration_min is not None:
                extra += f"\nETA: ~{best_duration_min} min"
            await notify_user_order_status(
                order.user.telegram_id,
                order.order_number,
                "PICKUP_RIDER_ASSIGNED",
                extra,
            )
    except Exception as e:
        logger.warning("Failed to notify user for order %s: %s", order.id, e)

    return {
        "rider_id": str(best_rider.id),
        "distance_km": best_distance_km,
        "eta_min": best_duration_min,
    }


@router.post("/confirm/{order_id}")
async def confirm_payment(
    order_id: uuid.UUID,
    payment_mode: str = "COD",
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm payment for an order.

    For COD: mark as confirmed immediately (payment collected on delivery).
    For CARD/UPI: simulate the payment, record in DB, and proceed.
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment == "PAID":
        return {
            "status": "already_paid",
            "order_id": str(order_id),
            "payment_mode": order.payment_mode,
        }

    # Set payment mode
    mode = payment_mode.upper()
    if mode not in ("COD", "CARD", "UPI"):
        raise HTTPException(status_code=400, detail="Invalid payment mode. Use COD, CARD, or UPI.")

    order.payment_mode = mode

    if mode == "COD":
        # COD: Mark order as confirmed, payment will be collected on delivery
        order.payment = "PENDING"  # stays PENDING until rider collects cash
        order.status = "PAYMENT_CONFIRMED"
    else:
        # CARD / UPI: Simulated instant payment → mark as PAID
        order.payment = "PAID"
        order.status = "PAYMENT_CONFIRMED"
        order.razorpay_payment_id = f"SIM_{mode}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Generate OTPs
    pickup_otp = await generate_otp(str(order.id), "pickup")
    drop_otp = await generate_otp(str(order.id), "drop")

    # Audit event
    event = OrderEvent(
        order_id=order.id,
        from_status="ORDER_PLACED",
        to_status="PAYMENT_CONFIRMED",
        actor_type="SYSTEM",
    )
    db.add(event)

    await db.commit()

    # Notify user (payment confirmation)
    try:
        if order.user:
            mode_labels = {"COD": "💵 Cash on Delivery", "CARD": "💳 Card (simulated)", "UPI": "📱 UPI (simulated)"}
            await notify_user_order_status(
                order.user.telegram_id,
                order.order_number,
                "PAYMENT_CONFIRMED",
                f"Payment: {mode_labels.get(mode, mode)}\n"
                f"🔑 Pickup OTP: <code>{pickup_otp}</code>\n"
                f"🔑 Drop-off OTP: <code>{drop_otp}</code>\n\n"
                "Share these with the delivery rider at pickup and delivery.",
            )
    except Exception as e:
        print(f"⚠️ Notification error: {e}")

    # Assign nearest pickup rider based on current GPS and Google distance
    assignment = await _assign_nearest_pickup_rider(order, db)

    return {
        "status": "confirmed",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "payment_mode": mode,
        "payment_status": order.payment,
        "pickup_otp": pickup_otp,
        "drop_otp": drop_otp,
        "pickup_assignment": assignment,
    }


@router.post("/assign-rider/{order_id}")
async def assign_rider_to_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger rider assignment for an order that is PAYMENT_CONFIRMED
    but has no pickup rider. Use when assignment was skipped (e.g. old API).
    """
    result = await db.execute(
        select(Order).where(Order.id == order_id).options(selectinload(Order.user))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "PAYMENT_CONFIRMED":
        raise HTTPException(
            status_code=400,
            detail=f"Order status is {order.status}; only PAYMENT_CONFIRMED orders can be assigned a rider.",
        )
    if order.pickup_rider_id:
        return {"status": "already_assigned", "rider_id": str(order.pickup_rider_id)}

    assignment = await _assign_nearest_pickup_rider(order, db)
    if not assignment:
        raise HTTPException(
            status_code=503,
            detail="No eligible rider could be assigned (need ON_DUTY riders with location).",
        )
    return {"status": "assigned", "pickup_assignment": assignment}


@router.post("/cod-collected/{order_id}")
async def mark_cod_collected(
    order_id: uuid.UUID,
    rider_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a COD order's cash as collected by rider on delivery.
    Called when rider confirms cash collection at drop-off.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_mode != "COD":
        return {"status": "not_cod", "message": "This order is not Cash on Delivery."}

    order.payment = "PAID"

    event = OrderEvent(
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,  # Status doesn't change, just payment
        actor_type="RIDER",
        actor_id=rider_id,
    )
    db.add(event)

    await db.commit()

    return {
        "status": "cod_collected",
        "order_id": str(order_id),
        "amount": float(order.total_cost),
    }
