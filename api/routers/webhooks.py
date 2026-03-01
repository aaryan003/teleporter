"""
n8n Webhook endpoints — triggers for automation workflows.

These endpoints are called BY n8n or call INTO n8n.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from db.database import get_db
from models.order import Order, OrderEvent
from models.rider import Rider
from models.delivery_route import DeliveryRoute
from models.warehouse import Warehouse
from services.route_optimizer import optimize_route, check_return_trip_pickup
from services.notifications import notify_rider_task, notify_user_order_status
from config import settings

router = APIRouter()


async def trigger_n8n_workflow(workflow_name: str, payload: dict) -> dict | None:
    """Call an n8n webhook to trigger a workflow."""
    url = f"{settings.N8N_WEBHOOK_URL}/webhook/{workflow_name}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            return resp.json() if resp.status_code == 200 else None
    except Exception as e:
        print(f"⚠️ n8n trigger failed ({workflow_name}): {e}")
        return None


@router.post("/warehouse-intake")
async def warehouse_intake(
    order_ids: list[str],
    warehouse_id: str,
    rider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Called when a pickup rider drops parcels at warehouse.
    Updates order status to AT_WAREHOUSE.
    Checks if batch threshold met for route optimization.
    """
    updated = []
    for oid in order_ids:
        result = await db.execute(select(Order).where(Order.id == uuid.UUID(oid)))
        order = result.scalar_one_or_none()
        if order:
            order.status = "AT_WAREHOUSE"
            order.warehouse_id = uuid.UUID(warehouse_id)
            order.warehouse_received_at = datetime.utcnow()

            event = OrderEvent(
                order_id=order.id,
                from_status="IN_TRANSIT_TO_WAREHOUSE",
                to_status="AT_WAREHOUSE",
                actor_type="RIDER",
                actor_id=uuid.UUID(rider_id),
            )
            db.add(event)
            updated.append(str(order.id))

    await db.commit()

    # Check batch threshold
    at_warehouse_count = (await db.execute(
        select(Order).where(
            and_(Order.status == "AT_WAREHOUSE", Order.warehouse_id == uuid.UUID(warehouse_id))
        )
    )).scalars().all()

    should_optimize = len(at_warehouse_count) >= settings.BATCH_THRESHOLD

    if should_optimize:
        # Trigger route optimization
        await trigger_n8n_workflow("route-optimizer", {
            "warehouse_id": warehouse_id,
            "parcel_count": len(at_warehouse_count),
        })

    return {
        "updated": updated,
        "warehouse_load": len(at_warehouse_count),
        "optimization_triggered": should_optimize,
    }


@router.post("/optimize-routes")
async def optimize_routes(
    warehouse_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Run VRP route optimization for all parcels at a warehouse.
    Groups parcels, runs OR-Tools, assigns routes to riders.
    """
    # Get warehouse location
    wh_result = await db.execute(select(Warehouse).where(Warehouse.id == uuid.UUID(warehouse_id)))
    warehouse = wh_result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    depot = (float(warehouse.lat), float(warehouse.lng))

    # Get pending parcels
    orders_result = await db.execute(
        select(Order).where(
            and_(Order.status == "AT_WAREHOUSE", Order.warehouse_id == uuid.UUID(warehouse_id))
        )
    )
    parcels = orders_result.scalars().all()
    if not parcels:
        return {"routes_created": 0, "message": "No parcels to optimize"}

    # Get available delivery riders
    riders_result = await db.execute(
        select(Rider).where(
            and_(Rider.status == "ON_DUTY", Rider.warehouse_id == uuid.UUID(warehouse_id))
        )
    )
    available_riders = riders_result.scalars().all()

    # Group parcels into routes (max 5 per route)
    max_per_route = settings.MAX_PARCELS_PER_ROUTE
    parcel_groups = [parcels[i:i + max_per_route] for i in range(0, len(parcels), max_per_route)]

    routes_created = []
    for group_idx, group in enumerate(parcel_groups):
        # Build delivery points
        delivery_points = [
            {
                "lat": float(o.drop_lat),
                "lng": float(o.drop_lng),
                "order_id": str(o.id),
                "order_number": o.order_number,
                "address": o.drop_address,
            }
            for o in group if o.drop_lat and o.drop_lng
        ]

        if not delivery_points:
            continue

        # Run OR-Tools optimizer
        optimized = optimize_route(depot, delivery_points)

        # Assign a rider (round-robin if available)
        assigned_rider = None
        if available_riders:
            assigned_rider = available_riders[group_idx % len(available_riders)]

        # Create delivery route record
        route = DeliveryRoute(
            rider_id=assigned_rider.id if assigned_rider else None,
            warehouse_id=uuid.UUID(warehouse_id),
            optimized_sequence=[
                {"order_id": s.get("order_id"), "address": s.get("address")}
                for s in optimized.stop_details
            ],
            total_distance_km=optimized.total_distance_km,
            total_duration_min=optimized.total_duration_min,
            total_parcels=len(group),
        )
        db.add(route)
        await db.flush()

        # Update orders
        for order in group:
            order.status = "DELIVERY_RIDER_ASSIGNED"
            order.delivery_route_id = route.id
            if assigned_rider:
                order.delivery_rider_id = assigned_rider.id

            event = OrderEvent(
                order_id=order.id,
                from_status="AT_WAREHOUSE",
                to_status="DELIVERY_RIDER_ASSIGNED",
                actor_type="SYSTEM",
            )
            db.add(event)

        # Update rider status
        if assigned_rider:
            assigned_rider.status = "ON_DELIVERY"
            assigned_rider.current_load = len(group)

            # Notify rider
            await notify_rider_task(
                assigned_rider.telegram_id,
                "DELIVERY",
                {
                    "stops": optimized.stop_details,
                    "total_km": optimized.total_distance_km,
                    "total_min": optimized.total_duration_min,
                },
            )

        routes_created.append({
            "route_id": str(route.id),
            "rider": assigned_rider.full_name if assigned_rider else "Unassigned",
            "parcels": len(group),
            "distance_km": optimized.total_distance_km,
            "savings_km": optimized.savings_vs_naive_km,
        })

    await db.commit()

    return {
        "routes_created": len(routes_created),
        "routes": routes_created,
    }


@router.post("/return-trip-check")
async def return_trip_check(
    rider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check for opportunistic pickups on rider's return to warehouse.
    Called when rider completes last delivery.
    """
    rider_result = await db.execute(select(Rider).where(Rider.id == uuid.UUID(rider_id)))
    rider = rider_result.scalar_one_or_none()
    if not rider or not rider.current_lat or not rider.current_lng:
        return {"eligible_pickups": []}

    # Get rider's home warehouse
    wh_result = await db.execute(select(Warehouse).where(Warehouse.id == rider.warehouse_id))
    warehouse = wh_result.scalar_one_or_none()
    if not warehouse:
        return {"eligible_pickups": []}

    # Get pending pickups (status = PICKUP_SCHEDULED, no rider assigned yet)
    pending_result = await db.execute(
        select(Order).where(
            and_(
                Order.status == "PICKUP_SCHEDULED",
                Order.pickup_rider_id.is_(None),
            )
        )
    )
    pending = pending_result.scalars().all()

    pending_list = [
        {
            "lat": float(o.pickup_lat),
            "lng": float(o.pickup_lng),
            "order_id": str(o.id),
            "order_number": o.order_number,
            "address": o.pickup_address,
        }
        for o in pending if o.pickup_lat and o.pickup_lng
    ]

    eligible = check_return_trip_pickup(
        rider_location=(float(rider.current_lat), float(rider.current_lng)),
        warehouse_location=(float(warehouse.lat), float(warehouse.lng)),
        pending_pickups=pending_list,
        max_detour_km=settings.MAX_DETOUR_KM,
    )

    # Limit to MAX_RETURN_PICKUPS
    eligible = eligible[:settings.MAX_RETURN_PICKUPS]

    return {"eligible_pickups": eligible}
