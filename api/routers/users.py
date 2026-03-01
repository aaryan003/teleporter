"""User management API endpoints."""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.user import User
from models.rider import Rider
from schemas import UserCreate, UserUpdate, UserResponse
from schemas.rider_application import IdentityResponse

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Identity Resolution ────────────────────────────────────

@router.get("/identity/{telegram_id}", response_model=IdentityResponse)
async def resolve_identity(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """
    Determine if a Telegram user is a customer, rider, both, or new.
    Called on every /start to route the bot experience.
    """
    # Check users table
    user_result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = user_result.scalar_one_or_none()

    # Check riders table
    rider_result = await db.execute(
        select(Rider).where(Rider.telegram_id == telegram_id)
    )
    rider = rider_result.scalar_one_or_none()

    # Check rider_applications table for pending/rejected
    from models.rider_application import RiderApplication
    app_result = await db.execute(
        select(RiderApplication).where(RiderApplication.telegram_id == telegram_id)
    )
    application = app_result.scalar_one_or_none()

    rider_status = None
    rider_id = None

    if rider:
        rider_status = rider.status
        rider_id = rider.id
    elif application:
        rider_status = application.status  # PENDING or REJECTED
        rider_id = None

    return IdentityResponse(
        is_customer=user is not None and user.phone is not None,
        is_rider=rider is not None,
        rider_status=rider_status,
        customer_id=user.id if user else None,
        rider_id=rider_id,
    )


@router.patch("/{telegram_id}", response_model=UserResponse)
async def update_user(telegram_id: int, data: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing user."""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if data.phone is not None:
        user.phone = data.phone
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.telegram_username is not None:
        user.telegram_username = data.telegram_username

    await db.commit()
    await db.refresh(user)
    logger.info("User updated: telegram_id=%s phone=%s", telegram_id, getattr(user, "phone", None))
    return user


@router.post("/", response_model=UserResponse)
async def create_or_get_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user or return existing one (by telegram_id)."""
    result = await db.execute(
        select(User).where(User.telegram_id == data.telegram_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    user = User(
        telegram_id=data.telegram_id,
        full_name=data.full_name,
        phone=data.phone,
        telegram_username=data.telegram_username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("User created: telegram_id=%s", data.telegram_id)
    return user


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by Telegram ID."""
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=list[UserResponse])
async def list_users(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List all users (paginated)."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    return result.scalars().all()
