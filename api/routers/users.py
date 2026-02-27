from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    telegram_id: int | None = None
    full_name: str | None = None
    phone: str | None = None


@router.post("")
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(
        telegram_id=body.telegram_id,
        full_name=body.full_name,
        phone=body.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/by-telegram/{telegram_id}")
async def get_by_telegram(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    return user

