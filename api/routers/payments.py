from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.models.order import Order

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()
    razorpay_order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get(
        "order_id"
    )
    if not razorpay_order_id:
        return {"status": "ignored"}

    result = await db.execute(select(Order).where(Order.razorpay_order_id == razorpay_order_id))
    order = result.scalar_one_or_none()
    if not order:
        return {"status": "ignored"}

    order.payment_status = "PAID"
    order.status = "PAYMENT_CONFIRMED"
    await db.commit()
    return {"status": "ok"}

