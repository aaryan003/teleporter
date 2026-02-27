from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


VehicleType = Literal["BIKE", "AUTO", "VAN"]
TimeType = Literal["STANDARD", "EXPRESS", "SAME_DAY", "NEXT_DAY"]


VEHICLE_MULTIPLIER: dict[VehicleType, float] = {
    "BIKE": 1.0,
    "AUTO": 1.3,
    "VAN": 1.6,
}

TIME_FACTOR: dict[TimeType, float] = {
    "STANDARD": 1.0,
    "EXPRESS": 1.8,
    "SAME_DAY": 1.3,
    "NEXT_DAY": 0.9,
}

RATE_PER_KM = 10.0
MIN_CHARGE = 35.0
BATCH_DISCOUNT_PERCENT = 15.0


@dataclass
class PricingContext:
    distance_km: float
    weight_kg: float
    vehicle_type: VehicleType
    time_type: TimeType
    surge_multiplier: float = 1.0
    is_batch_eligible: bool = True
    has_subscription_free_delivery: bool = False
    addons_cost: float = 0.0


def calculate_base_cost(ctx: PricingContext) -> float:
    vehicle_mul = VEHICLE_MULTIPLIER[ctx.vehicle_type]
    time_factor = TIME_FACTOR[ctx.time_type]
    base_cost = ctx.distance_km * RATE_PER_KM * vehicle_mul * time_factor
    return max(base_cost, MIN_CHARGE)


def apply_batch_discount(amount: float, ctx: PricingContext) -> float:
    if not ctx.is_batch_eligible:
        return amount
    discount = amount * (BATCH_DISCOUNT_PERCENT / 100.0)
    return amount - discount


def apply_subscription(amount: float, ctx: PricingContext) -> float:
    if ctx.has_subscription_free_delivery:
        return 0.0
    return amount


def calculate_total(ctx: PricingContext) -> dict[str, float]:
    base = calculate_base_cost(ctx)
    after_batch = apply_batch_discount(base, ctx)
    surged = after_batch * ctx.surge_multiplier
    subtotal = surged + ctx.addons_cost
    subtotal = apply_subscription(subtotal, ctx)
    total = round(subtotal, 2)
    return {
        "distance_km": ctx.distance_km,
        "base_cost": round(base, 2),
        "addons_cost": round(ctx.addons_cost, 2),
        "surge_multiplier": round(ctx.surge_multiplier, 2),
        "total_cost": total,
    }

