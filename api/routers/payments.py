"""
Payment endpoints — COD + simulated Card/UPI payments.

Payment modes:
  COD  → Order goes straight to PAYMENT_CONFIRMED (collect on delivery)
  CARD → Simulated: DB entry recorded, status moves forward immediately
  UPI  → Simulated: DB entry recorded, status moves forward immediately
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.order import Order, OrderEvent
from models.rider import Rider
from services.otp import generate_otp
from services.notifications import notify_user_order_status, notify_rider_task
from services.maps import get_distance

router = APIRouter()


async def _assign_nearest_pickup_rider(
    order: Order,
    db: AsyncSession,
):
    """
    Assign the nearest ON_DUTY rider to the order's pickup location
    using Google Distance Matrix (via services.maps.get_distance).
    """
    if not order.pickup_lat or not order.pickup_lng:
        return None

    riders_result = await db.execute(
        select(Rider).where(
            and_(
                Rider.status == "ON_DUTY",
                Rider.current_lat.is_not(None),
                Rider.current_lng.is_not(None),
            )
        )
    )
    riders = riders_result.scalars().all()
    if not riders:
        return None

    best_rider = None
    best_distance_km: float | None = None
    best_duration_min: int | None = None

    pickup_lat = float(order.pickup_lat)
    pickup_lng = float(order.pickup_lng)

    for rider in riders:
        try:
            dist = await get_distance(
                float(rider.current_lat),
                float(rider.current_lng),
                pickup_lat,
                pickup_lng,
            )
        except Exception as e:
            print(f"⚠️ Distance calc failed for rider {rider.id}: {e}")
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
        print(f"⚠️ Failed to notify rider {best_rider.id}: {e}")

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
        print(f"⚠️ Failed to notify user for order {order.id}: {e}")

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
    result = await db.execute(select(Order).where(Order.id == order_id))
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

    return {
        "status": "cod_collected",
        "order_id": str(order_id),
        "amount": float(order.total_cost),
    }
