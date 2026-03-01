"""Pydantic schemas for rider application endpoints."""

from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VehicleTypeEnum(str, Enum):
    BIKE = "BIKE"
    MINI_VAN = "MINI_VAN"
    MINI_TRUCK = "MINI_TRUCK"
    TRUCK = "TRUCK"


class RiderApplicationCreate(BaseModel):
    """Schema for submitting a new rider application from the bot."""
    telegram_id: int
    full_name: str = Field(..., min_length=3, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    email: str | None = None
    vehicle: VehicleTypeEnum = VehicleTypeEnum.BIKE
    vehicle_reg: str | None = Field(None, min_length=5, max_length=30)
    license_file_id: str | None = None
    license_file_url: str | None = None
    aadhar_file_id: str | None = None
    aadhar_file_url: str | None = None
    preferred_warehouse_id: uuid.UUID | None = None


class RiderApplicationResponse(BaseModel):
    """Schema for returning a rider application."""
    id: uuid.UUID
    telegram_id: int
    full_name: str
    phone: str
    email: str | None
    vehicle: str
    vehicle_reg: str | None
    license_file_id: str | None
    license_file_url: str | None
    aadhar_file_id: str | None
    aadhar_file_url: str | None
    preferred_warehouse_id: uuid.UUID | None
    status: str
    admin_note: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewAction(BaseModel):
    """Schema for approving or rejecting a rider application."""
    action: str = Field(..., pattern="^(APPROVE|REJECT)$")
    admin_note: str | None = None
    reviewed_by: str = "admin"


class IdentityResponse(BaseModel):
    """Response for identity resolution — determines user type on /start."""
    is_customer: bool
    is_rider: bool
    rider_status: str | None = None
    customer_id: uuid.UUID | None = None
    rider_id: uuid.UUID | None = None
