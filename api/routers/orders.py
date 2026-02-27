from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.models.order import Order
from api.schemas.order import (
    OrderCreate,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderRead,
)
from api.services.pickup_scheduler import compute_pickup_slots
from api.services.pricing import PricingContext, calculate_total
from api.services.maps import distance_km_between

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/preview", response_model=OrderPreviewResponse)
async def preview_order(body: OrderPreviewRequest) -> OrderPreviewResponse:
    distance_km = distance_km_between(
        (body.pickup_lat, body.pickup_lng),
        (body.drop_lat, body.drop_lng),
    )

    ctx = PricingContext(
        distance_km=distance_km,
        weight_kg=body.weight_kg,
        vehicle_type=body.vehicle_type,
        time_type=body.time_type,
        surge_multiplier=1.0,
        is_batch_eligible=body.is_batch_eligible,
        has_subscription_free_delivery=False,
        addons_cost=0.0,
    )
    result = calculate_total(ctx)
    return OrderPreviewResponse(**result)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    slots = compute_pickup_slots(datetime.utcnow())
    if not any(s.start == body.pickup_slot for s in slots):
        raise HTTPException(status_code=400, detail="Invalid or unavailable pickup slot")

    # Very simple order number
    order_number = datetime.utcnow().strftime("DLV-%m%d%H%M%S")

    preview = body.preview
    distance_km = distance_km_between(
        (preview.pickup_lat, preview.pickup_lng),
        (preview.drop_lat, preview.drop_lng),
    )

    ctx = PricingContext(
        distance_km=distance_km,
        weight_kg=preview.weight_kg,
        vehicle_type=preview.vehicle_type,
        time_type=preview.time_type,
        surge_multiplier=1.0,
        is_batch_eligible=preview.is_batch_eligible,
        has_subscription_free_delivery=False,
        addons_cost=0.0,
    )
    pricing = calculate_total(ctx)

    order = Order(
        order_number=order_number,
        user_id=body.user_id,
        pickup_address="",
        drop_address="",
        pickup_lat=str(preview.pickup_lat),
        pickup_lng=str(preview.pickup_lng),
        drop_lat=str(preview.drop_lat),
        drop_lng=str(preview.drop_lng),
        pickup_slot=body.pickup_slot,
        distance_km=pricing["distance_km"],
        base_cost=pricing["base_cost"],
        surge_multiplier=pricing["surge_multiplier"],
        addons_cost=pricing["addons_cost"],
        total_cost=pricing["total_cost"],
        status="ORDER_PLACED",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return OrderRead.model_validate(order)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> OrderRead:
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderRead.model_validate(order)

