"""Rider management API endpoints (admin-managed company employees)."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.rider import Rider
from schemas import RiderCreate, RiderResponse, RiderLocationUpdate

router = APIRouter()


@router.post("/", response_model=RiderResponse)
async def create_rider(data: RiderCreate, db: AsyncSession = Depends(get_db)):
    """Admin creates a new rider (company employee)."""
    # Check for duplicate telegram_id or employee_id
    existing = await db.execute(
        select(Rider).where(
            (Rider.telegram_id == data.telegram_id) | (Rider.employee_id == data.employee_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Rider with this Telegram ID or Employee ID already exists")

    rider = Rider(
        telegram_id=data.telegram_id,
        employee_id=data.employee_id,
        full_name=data.full_name,
        phone=data.phone,
        vehicle=data.vehicle.value,
        vehicle_reg=data.vehicle_reg,
        warehouse_id=data.warehouse_id,
        shift_start=data.shift_start,
        shift_end=data.shift_end,
        max_capacity=data.max_capacity,
    )
    db.add(rider)
    await db.flush()
    await db.refresh(rider)
    return rider


@router.get("/", response_model=list[RiderResponse])
async def list_riders(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all riders with optional status filter."""
    query = select(Rider)
    if status:
        query = query.where(Rider.status == status)
    query = query.order_by(Rider.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/telegram/{telegram_id}", response_model=RiderResponse)
async def get_rider_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get rider by Telegram ID."""
    result = await db.execute(select(Rider).where(Rider.telegram_id == telegram_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider


@router.get("/{rider_id}", response_model=RiderResponse)
async def get_rider(rider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get rider by ID."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider



@router.patch("/{rider_id}/location")
async def update_rider_location(
    rider_id: uuid.UUID,
    data: RiderLocationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update rider's current GPS location."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rider.current_lat = data.lat
    rider.current_lng = data.lng
    from datetime import datetime
    rider.last_location_update = datetime.utcnow()

    return {"rider_id": str(rider_id), "lat": data.lat, "lng": data.lng}


@router.patch("/{rider_id}/status")
async def update_rider_status(
    rider_id: uuid.UUID,
    status: str,
    db: AsyncSession = Depends(get_db),
):
    """Update rider status (ON_DUTY, OFF_DUTY, etc.)."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    valid_statuses = ["ON_DUTY", "OFF_DUTY", "ON_DELIVERY", "ON_PICKUP"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    old_status = rider.status
    rider.status = status
    return {"rider_id": str(rider_id), "old_status": old_status, "new_status": status}


@router.get("/telegram/{telegram_id}", response_model=RiderResponse)
async def get_rider_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get rider by Telegram ID."""
    result = await db.execute(select(Rider).where(Rider.telegram_id == telegram_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")
    return rider
