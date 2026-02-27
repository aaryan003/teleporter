from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class OrderPreviewRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    drop_lat: float
    drop_lng: float
    weight_kg: float = Field(gt=0)
    vehicle_type: Literal["BIKE", "AUTO", "VAN"] = "BIKE"
    time_type: Literal["STANDARD", "EXPRESS", "SAME_DAY", "NEXT_DAY"] = "STANDARD"
    is_batch_eligible: bool = True
    addons: list[str] = []


class OrderPreviewResponse(BaseModel):
    distance_km: float
    base_cost: float
    surge_multiplier: float
    addons_cost: float
    total_cost: float
    currency: str = "INR"


class OrderCreate(BaseModel):
    user_id: Optional[str] = None
    preview: OrderPreviewRequest
    pickup_slot: datetime


class OrderRead(BaseModel):
    id: str
    order_number: str
    status: str
    total_cost: float
    pickup_address: str
    drop_address: str
    created_at: datetime

    class Config:
        from_attributes = True

