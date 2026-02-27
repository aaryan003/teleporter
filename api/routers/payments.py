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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.order import Order, OrderEvent
from services.otp import generate_otp
from services.notifications import notify_user_order_status

router = APIRouter()


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

    # Notify user
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

    return {
        "status": "confirmed",
        "order_id": str(order_id),
        "order_number": order.order_number,
        "payment_mode": mode,
        "payment_status": order.payment,
        "pickup_otp": pickup_otp,
        "drop_otp": drop_otp,
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
