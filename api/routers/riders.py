from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.models.rider import Rider

router = APIRouter(prefix="/riders", tags=["riders"])


class RiderStatusUpdate(BaseModel):
    status: str


@router.get("")
async def list_riders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rider))
    return result.scalars().all()


@router.patch("/{rider_id}/status")
async def update_rider_status(
    rider_id: str,
    body: RiderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        return {"detail": "not found"}
    rider.status = body.status
    await db.commit()
    return {"detail": "ok"}

