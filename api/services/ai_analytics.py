"""
AI Analytics Service — OpenAI-powered insights for the admin dashboard.

Generates:
  - Fleet intelligence (hire recommendations, utilization %)
  - Revenue analysis (trends, plan performance)
  - Demand forecasting (next 7 days)
  - Route efficiency metrics
  - Customer retention insights
"""

from __future__ import annotations
import json
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.order import Order
from models.rider import Rider
from models.ai_insight import AIInsight
from config import settings

try:
    import openai

    _client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except ImportError:
    _client = None


async def gather_kpis(db: AsyncSession) -> dict:
    """Gather raw KPI data for AI analysis."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Orders
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    orders_today = (await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )).scalar() or 0
    delivered_today = (await db.execute(
        select(func.count(Order.id)).where(
            and_(Order.status == "DELIVERED", Order.delivered_at >= today_start)
        )
    )).scalar() or 0
    cancelled = (await db.execute(
        select(func.count(Order.id)).where(Order.status == "CANCELLED")
    )).scalar() or 0

    # Revenue
    revenue_today = (await db.execute(
        select(func.sum(Order.total_cost)).where(
            and_(Order.payment == "PAID", Order.created_at >= today_start)
        )
    )).scalar() or 0
    revenue_week = (await db.execute(
        select(func.sum(Order.total_cost)).where(
            and_(Order.payment == "PAID", Order.created_at >= week_start)
        )
    )).scalar() or 0
    revenue_month = (await db.execute(
        select(func.sum(Order.total_cost)).where(
            and_(Order.payment == "PAID", Order.created_at >= month_start)
        )
    )).scalar() or 0

    # Riders
    total_riders = (await db.execute(select(func.count(Rider.id)))).scalar() or 0
    active_riders = (await db.execute(
        select(func.count(Rider.id)).where(Rider.status == "ON_DUTY")
    )).scalar() or 0
    busy_riders = (await db.execute(
        select(func.count(Rider.id)).where(
            Rider.status.in_(["ON_DELIVERY", "ON_PICKUP"])
        )
    )).scalar() or 0

    # Avg delivery time (for delivered orders today)
    avg_delivery_time = None
    if delivered_today > 0:
        result = await db.execute(
            select(func.avg(
                func.extract("epoch", Order.delivered_at - Order.created_at) / 60
            )).where(
                and_(Order.status == "DELIVERED", Order.delivered_at >= today_start)
            )
        )
        avg_delivery_time = result.scalar()

    return {
        "total_orders": total_orders,
        "orders_today": orders_today,
        "delivered_today": delivered_today,
        "cancelled_total": cancelled,
        "revenue_today": float(revenue_today),
        "revenue_this_week": float(revenue_week),
        "revenue_this_month": float(revenue_month),
        "total_riders": total_riders,
        "active_riders": active_riders,
        "busy_riders": busy_riders,
        "rider_utilization_pct": round((busy_riders / max(active_riders, 1)) * 100, 1),
        "avg_delivery_time_min": round(avg_delivery_time, 1) if avg_delivery_time else None,
        "timestamp": now.isoformat(),
    }


async def generate_ai_insights(db: AsyncSession, kpis: dict | None = None) -> list[dict]:
    """
    Generate AI-powered insights from KPIs using OpenAI.
    Falls back to rule-based insights if OpenAI unavailable.
    """
    if kpis is None:
        kpis = await gather_kpis(db)

    # Try AI-powered insights
    if _client:
        try:
            return await _generate_openai_insights(db, kpis)
        except Exception as e:
            print(f"⚠️ OpenAI insight generation failed: {e}")

    # Fallback: rule-based insights
    return _generate_rule_based_insights(kpis)


async def _generate_openai_insights(db: AsyncSession, kpis: dict) -> list[dict]:
    """Use OpenAI to generate natural-language insights."""
    prompt = f"""You are an AI logistics analyst for TeleporterBot, a delivery company.
Analyze these KPIs and provide exactly 4 actionable insights.

KPIs:
{json.dumps(kpis, indent=2)}

For each insight, provide:
1. category: one of REVENUE, FLEET, DEMAND, ROUTE, CUSTOMER
2. severity: INFO, WARNING, or ACTION_REQUIRED
3. title: short headline (max 60 chars)
4. insight: 2-3 sentence analysis with specific recommendation

Respond in JSON array format: [{{"category": "...", "severity": "...", "title": "...", "insight": "..."}}]
"""
    response = await _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)
    insights = parsed.get("insights", parsed) if isinstance(parsed, dict) else parsed

    # Save to DB
    saved = []
    for item in insights[:5]:
        insight = AIInsight(
            category=item.get("category", "REVENUE"),
            severity=item.get("severity", "INFO"),
            title=item.get("title", "AI Insight"),
            insight=item.get("insight", ""),
            data=kpis,
        )
        db.add(insight)
        saved.append(item)

    await db.commit()
    return saved


def _generate_rule_based_insights(kpis: dict) -> list[dict]:
    """Fallback rule-based insights when OpenAI is unavailable."""
    insights = []

    # Fleet utilization check
    utilization = kpis.get("rider_utilization_pct", 0)
    if utilization > 85:
        insights.append({
            "category": "FLEET",
            "severity": "ACTION_REQUIRED",
            "title": f"Rider utilization at {utilization}%",
            "insight": (
                f"Riders are at {utilization}% utilization. Consider hiring more riders "
                "to prevent service degradation during peak hours."
            ),
        })
    elif utilization < 30:
        insights.append({
            "category": "FLEET",
            "severity": "WARNING",
            "title": f"Low rider utilization ({utilization}%)",
            "insight": (
                f"Rider utilization is only {utilization}%. Consider reducing shift hours "
                "or reassigning riders to higher-demand zones."
            ),
        })

    # Revenue trend
    daily = kpis.get("revenue_today", 0)
    weekly = kpis.get("revenue_this_week", 0)
    if weekly > 0 and daily > 0:
        avg_daily = weekly / 7
        if daily > avg_daily * 1.2:
            insights.append({
                "category": "REVENUE",
                "severity": "INFO",
                "title": "Revenue trending above average today",
                "insight": (
                    f"Today's revenue (${daily:.0f}) is {((daily/avg_daily - 1)*100):.0f}% "
                    f"above the weekly average (${avg_daily:.0f}/day)."
                ),
            })

    # Order volume
    orders_today = kpis.get("orders_today", 0)
    if orders_today == 0:
        insights.append({
            "category": "DEMAND",
            "severity": "WARNING",
            "title": "No orders today",
            "insight": "Zero orders received today. Check if the bot and payment systems are operational.",
        })

    # Always provide at least one insight
    if not insights:
        insights.append({
            "category": "REVENUE",
            "severity": "INFO",
            "title": "System operating normally",
            "insight": (
                f"All systems operational. {kpis.get('orders_today', 0)} orders today, "
                f"{kpis.get('active_riders', 0)} riders active."
            ),
        })

    return insights
