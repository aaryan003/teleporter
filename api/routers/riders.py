"""Rider management API endpoints — CRUD, status, tasks, earnings, stats."""

import uuid
from datetime import datetime, timedelta, time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models.rider import Rider
from models.order import Order, OrderEvent
from models.delivery_route import DeliveryRoute
from schemas import RiderCreate, RiderResponse, RiderLocationUpdate
from config import settings

router = APIRouter()


# ── Request Body Schemas (rider-specific) ──────────────────

class RiderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ON_DUTY|OFF_DUTY|ON_DELIVERY|ON_PICKUP)$")


class RiderShiftUpdate(BaseModel):
    shift_start: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    shift_end: str = Field(..., pattern=r"^\d{2}:\d{2}$")


class RiderWarehouseUpdate(BaseModel):
    warehouse_id: uuid.UUID


# ── CRUD ───────────────────────────────────────────────────

@router.post("/", response_model=RiderResponse)
async def create_rider(data: RiderCreate, db: AsyncSession = Depends(get_db)):
    """Admin creates a new rider (company employee)."""
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
    await db.commit()
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


# ── Location ───────────────────────────────────────────────

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
    rider.last_location_update = datetime.utcnow()

    await db.commit()
    return {"rider_id": str(rider_id), "lat": data.lat, "lng": data.lng}


# ── Status (JSON Body) ────────────────────────────────────

@router.patch("/{rider_id}/status")
async def update_rider_status(
    rider_id: uuid.UUID,
    data: RiderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update rider status (ON_DUTY, OFF_DUTY, etc.)."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    old_status = rider.status
    rider.status = data.status
    await db.commit()
    return {"rider_id": str(rider_id), "old_status": old_status, "new_status": data.status}


# ── Shift Hours ────────────────────────────────────────────

@router.patch("/{rider_id}/shift")
async def update_shift_hours(
    rider_id: uuid.UUID,
    data: RiderShiftUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update rider's shift start/end times."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    sh, sm = map(int, data.shift_start.split(":"))
    eh, em = map(int, data.shift_end.split(":"))
    rider.shift_start = time(sh, sm)
    rider.shift_end = time(eh, em)
    await db.commit()
    return {
        "rider_id": str(rider_id),
        "shift_start": data.shift_start,
        "shift_end": data.shift_end,
    }


# ── Warehouse / Hub Change ────────────────────────────────

@router.patch("/{rider_id}/warehouse")
async def update_rider_warehouse(
    rider_id: uuid.UUID,
    data: RiderWarehouseUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Change rider's assigned warehouse hub."""
    result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    rider.warehouse_id = data.warehouse_id
    await db.commit()
    return {"rider_id": str(rider_id), "warehouse_id": str(data.warehouse_id)}


# ── Active Tasks ───────────────────────────────────────────

@router.get("/{rider_id}/active-tasks")
async def get_active_tasks(rider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get all orders currently assigned to this rider that need action.
    Returns pickup tasks and delivery tasks in chronological order.
    """
    # Pickup tasks assigned to this rider
    pickup_statuses = ["PICKUP_RIDER_ASSIGNED", "PICKUP_EN_ROUTE"]
    pickup_q = (
        select(Order)
        .where(and_(Order.pickup_rider_id == rider_id, Order.status.in_(pickup_statuses)))
        .order_by(Order.pickup_slot.asc().nullslast())
    )
    pickup_result = await db.execute(pickup_q)
    pickup_orders = pickup_result.scalars().all()

    # Delivery tasks assigned to this rider
    delivery_statuses = ["DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY"]
    delivery_q = (
        select(Order)
        .where(and_(Order.delivery_rider_id == rider_id, Order.status.in_(delivery_statuses)))
        .order_by(Order.created_at.asc())
    )
    delivery_result = await db.execute(delivery_q)
    delivery_orders = delivery_result.scalars().all()

    tasks = []
    for o in pickup_orders:
        tasks.append({
            "id": str(o.id),
            "order_number": o.order_number,
            "task_type": "PICKUP",
            "status": o.status,
            "pickup_address": o.pickup_address,
            "pickup_lat": float(o.pickup_lat) if o.pickup_lat else None,
            "pickup_lng": float(o.pickup_lng) if o.pickup_lng else None,
            "drop_address": o.drop_address,
            "package_size": o.package_size,
            "vehicle": o.vehicle,
            "pickup_slot": o.pickup_slot.isoformat() if o.pickup_slot else None,
            "created_at": o.created_at.isoformat(),
        })
    for o in delivery_orders:
        tasks.append({
            "id": str(o.id),
            "order_number": o.order_number,
            "task_type": "DELIVERY",
            "status": o.status,
            "pickup_address": o.pickup_address,
            "drop_address": o.drop_address,
            "drop_lat": float(o.drop_lat) if o.drop_lat else None,
            "drop_lng": float(o.drop_lng) if o.drop_lng else None,
            "package_size": o.package_size,
            "vehicle": o.vehicle,
            "created_at": o.created_at.isoformat(),
        })

    return tasks


# ── Current Route ──────────────────────────────────────────

@router.get("/{rider_id}/current-route")
async def get_current_route(rider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get the rider's current active delivery route with optimized sequence.
    """
    result = await db.execute(
        select(DeliveryRoute)
        .where(and_(
            DeliveryRoute.rider_id == rider_id,
            DeliveryRoute.status.in_(["PLANNED", "IN_PROGRESS"]),
        ))
        .order_by(DeliveryRoute.created_at.desc())
        .limit(1)
    )
    route = result.scalar_one_or_none()
    if not route:
        return None

    return {
        "id": str(route.id),
        "status": route.status,
        "optimized_sequence": route.optimized_sequence or [],
        "total_distance_km": float(route.total_distance_km) if route.total_distance_km else 0,
        "total_duration_min": route.total_duration_min or 0,
        "total_parcels": route.total_parcels,
        "started_at": route.started_at.isoformat() if route.started_at else None,
        "created_at": route.created_at.isoformat(),
    }


# ── Earnings ───────────────────────────────────────────────

@router.get("/{rider_id}/earnings")
async def get_rider_earnings(rider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Calculate rider's earnings — today, this week, this month, all-time.
    Earnings = per_delivery_rate × completed deliveries in the period.
    """
    per_delivery = settings.RIDER_PER_DELIVERY_RATE
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Base query: orders delivered by this rider
    base_filter = and_(
        Order.delivery_rider_id == rider_id,
        Order.status.in_(["DELIVERED", "COMPLETED"]),
    )

    # Today
    today_count = (await db.execute(
        select(func.count(Order.id)).where(and_(base_filter, Order.delivered_at >= today_start))
    )).scalar() or 0

    # This week
    week_count = (await db.execute(
        select(func.count(Order.id)).where(and_(base_filter, Order.delivered_at >= week_start))
    )).scalar() or 0

    # This month
    month_count = (await db.execute(
        select(func.count(Order.id)).where(and_(base_filter, Order.delivered_at >= month_start))
    )).scalar() or 0

    # All time
    total_count = (await db.execute(
        select(func.count(Order.id)).where(base_filter)
    )).scalar() or 0

    # Also count pickup-confirmed orders (riders earn for both legs)
    pickup_filter = and_(
        Order.pickup_rider_id == rider_id,
        Order.status.in_(["PICKED_UP", "IN_TRANSIT_TO_WAREHOUSE", "AT_WAREHOUSE",
                          "ROUTE_OPTIMIZED", "DELIVERY_RIDER_ASSIGNED", "OUT_FOR_DELIVERY",
                          "DELIVERED", "COMPLETED"]),
    )

    pickup_today = (await db.execute(
        select(func.count(Order.id)).where(and_(pickup_filter, Order.pickup_confirmed_at >= today_start))
    )).scalar() or 0

    pickup_week = (await db.execute(
        select(func.count(Order.id)).where(and_(pickup_filter, Order.pickup_confirmed_at >= week_start))
    )).scalar() or 0

    pickup_month = (await db.execute(
        select(func.count(Order.id)).where(and_(pickup_filter, Order.pickup_confirmed_at >= month_start))
    )).scalar() or 0

    pickup_total = (await db.execute(
        select(func.count(Order.id)).where(pickup_filter)
    )).scalar() or 0

    # Get rider rating
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    avg_rating = float(rider.rating) if rider else 5.0

    return {
        "today": (today_count + pickup_today) * per_delivery,
        "deliveries_today": today_count + pickup_today,
        "this_week": (week_count + pickup_week) * per_delivery,
        "deliveries_week": week_count + pickup_week,
        "this_month": (month_count + pickup_month) * per_delivery,
        "deliveries_month": month_count + pickup_month,
        "total_all_time": (total_count + pickup_total) * per_delivery,
        "avg_rating": avg_rating,
    }


# ── Delivery History ───────────────────────────────────────

@router.get("/{rider_id}/deliveries")
async def get_rider_deliveries(
    rider_id: uuid.UUID,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of completed deliveries for this rider."""
    per_delivery = settings.RIDER_PER_DELIVERY_RATE

    result = await db.execute(
        select(Order)
        .where(and_(
            Order.delivery_rider_id == rider_id,
            Order.status.in_(["DELIVERED", "COMPLETED"]),
        ))
        .order_by(Order.delivered_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    orders = result.scalars().all()

    return [
        {
            "id": str(o.id),
            "order_number": o.order_number,
            "pickup_address": o.pickup_address,
            "drop_address": o.drop_address,
            "package_size": o.package_size,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "created_at": o.created_at.isoformat(),
            "earned": per_delivery,
        }
        for o in orders
    ]


# ── Stats (P1 — performance scorecard) ────────────────────

@router.get("/{rider_id}/stats")
async def get_rider_stats(rider_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Performance scorecard: completion rate, on-time rate, total km, avg deliveries/day, etc.
    """
    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()
    if not rider:
        raise HTTPException(status_code=404, detail="Rider not found")

    # Total assigned (pickup + delivery)
    total_assigned = (await db.execute(
        select(func.count(Order.id)).where(
            (Order.pickup_rider_id == rider_id) | (Order.delivery_rider_id == rider_id)
        )
    )).scalar() or 0

    # Total completed
    total_completed = (await db.execute(
        select(func.count(Order.id)).where(and_(
            (Order.pickup_rider_id == rider_id) | (Order.delivery_rider_id == rider_id),
            Order.status.in_(["DELIVERED", "COMPLETED"]),
        ))
    )).scalar() or 0

    completion_rate = (total_completed / total_assigned * 100) if total_assigned > 0 else 0

    # On-time rate (simplified: delivered within estimated duration)
    on_time_rate = 95.0  # TODO: compute from actual delivery times vs estimates

    # Total km (sum of delivered orders' distance)
    total_km = (await db.execute(
        select(func.sum(Order.distance_km)).where(and_(
            Order.delivery_rider_id == rider_id,
            Order.status.in_(["DELIVERED", "COMPLETED"]),
        ))
    )).scalar() or 0

    # Avg deliveries per day (since rider created)
    days_active = max((datetime.utcnow() - rider.created_at.replace(tzinfo=None)).days, 1)
    avg_per_day = total_completed / days_active

    # Best day earnings
    per_delivery = settings.RIDER_PER_DELIVERY_RATE
    best_day_q = (
        select(func.count(Order.id).label("day_count"))
        .where(and_(
            Order.delivery_rider_id == rider_id,
            Order.status.in_(["DELIVERED", "COMPLETED"]),
            Order.delivered_at.isnot(None),
        ))
        .group_by(func.date(Order.delivered_at))
        .order_by(func.count(Order.id).desc())
        .limit(1)
    )
    best_day_result = (await db.execute(best_day_q)).scalar()
    best_day_earnings = (best_day_result or 0) * per_delivery

    # Streak days (consecutive days with at least 1 delivery, ending today)
    # Simplified: count distinct delivery dates in the last 30 days
    streak_days = 0
    for i in range(30):
        day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day + timedelta(days=1)
        count = (await db.execute(
            select(func.count(Order.id)).where(and_(
                Order.delivery_rider_id == rider_id,
                Order.status.in_(["DELIVERED", "COMPLETED"]),
                Order.delivered_at >= day,
                Order.delivered_at < day_end,
            ))
        )).scalar() or 0
        if count > 0:
            streak_days += 1
        else:
            break

    return {
        "completion_rate": round(completion_rate, 1),
        "on_time_rate": on_time_rate,
        "total_km_ridden": float(total_km),
        "avg_deliveries_per_day": round(avg_per_day, 1),
        "best_day_earnings": best_day_earnings,
        "streak_days": streak_days,
        "total_assigned": total_assigned,
        "total_completed": total_completed,
    }
