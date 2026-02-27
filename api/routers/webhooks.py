from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/pickup-confirmed")
async def pickup_confirmed():
    # Placeholder endpoint to be called by future automation/orchestration (e.g. n8n)
    return {"status": "ok"}


@router.post("/delivery-completed")
async def delivery_completed():
    # Placeholder endpoint to be called when delivery OTP is verified
    return {"status": "ok"}

