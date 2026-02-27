"""Warehouse management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.warehouse import Warehouse
from schemas import WarehouseResponse

router = APIRouter()


@router.get("/", response_model=list[WarehouseResponse])
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    """List all active warehouses."""
    result = await db.execute(
        select(Warehouse).where(Warehouse.is_active == True).order_by(Warehouse.name)
    )
    return result.scalars().all()


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(warehouse_id: str, db: AsyncSession = Depends(get_db)):
    """Get warehouse by ID."""
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return wh
