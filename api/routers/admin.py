"""Admin dashboard API endpoints — zero manual work, all AI-powered."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from db.database import get_db
from models.order import Order
from models.rider import Rider
from models.ai_insight import AIInsight
from schemas import DashboardStats, AIInsightResponse
from services.ai_analytics import gather_kpis, generate_ai_insights

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get real-time dashboard KPI statistics."""
    kpis = await gather_kpis(db)

    return DashboardStats(
        total_orders=kpis["total_orders"],
        orders_today=kpis["orders_today"],
        orders_in_transit=(await db.execute(
            select(func.count(Order.id)).where(Order.status == "OUT_FOR_DELIVERY")
        )).scalar() or 0,
        orders_delivered=kpis["delivered_today"],
        orders_cancelled=kpis["cancelled_total"],
        revenue_today=kpis["revenue_today"],
        revenue_this_week=kpis["revenue_this_week"],
        revenue_this_month=kpis["revenue_this_month"],
        active_riders=kpis["active_riders"],
        avg_delivery_time_min=kpis["avg_delivery_time_min"],
        sla_compliance_pct=None,  # TODO: Calculate from delivery times
    )


@router.get("/insights", response_model=list[AIInsightResponse])
async def get_ai_insights(
    limit: int = 10,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated insights (latest first)."""
    query = select(AIInsight).order_by(AIInsight.generated_at.desc()).limit(limit)
    if category:
        query = query.where(AIInsight.category == category)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/insights/generate")
async def trigger_ai_analysis(db: AsyncSession = Depends(get_db)):
    """Manually trigger AI insight generation."""
    insights = await generate_ai_insights(db)
    return {"generated": len(insights), "insights": insights}


@router.get("/fleet-summary")
async def fleet_summary(db: AsyncSession = Depends(get_db)):
    """Fleet overview for dashboard."""
    riders = (await db.execute(select(Rider))).scalars().all()

    return {
        "total": len(riders),
        "on_duty": sum(1 for r in riders if r.status == "ON_DUTY"),
        "on_delivery": sum(1 for r in riders if r.status == "ON_DELIVERY"),
        "on_pickup": sum(1 for r in riders if r.status == "ON_PICKUP"),
        "off_duty": sum(1 for r in riders if r.status == "OFF_DUTY"),
        "avg_rating": round(sum(float(r.rating) for r in riders) / max(len(riders), 1), 2),
        "total_deliveries_today": sum(r.total_deliveries for r in riders),
        "riders": [
            {
                "id": str(r.id),
                "name": r.full_name,
                "employee_id": r.employee_id,
                "status": r.status,
                "vehicle": r.vehicle,
                "current_load": r.current_load,
                "rating": float(r.rating),
                "lat": float(r.current_lat) if r.current_lat else None,
                "lng": float(r.current_lng) if r.current_lng else None,
            }
            for r in riders
        ],
    }


@router.get("/revenue-chart")
async def revenue_chart(days: int = 30, db: AsyncSession = Depends(get_db)):
    """Daily revenue data for chart visualization."""
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Order.created_at).label("date"),
            func.sum(Order.total_cost).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(and_(Order.payment == "PAID", Order.created_at >= start))
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    data = []
    for row in result:
        data.append({
            "date": str(row.date),
            "revenue": float(row.revenue) if row.revenue else 0,
            "orders": row.orders,
        })

    return {"period_days": days, "data": data}
