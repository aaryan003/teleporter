"""
Pricing Engine — Revenue model for TeleporterBot v2.

Revenue streams:
  1. Base pricing: distance × rate × vehicle_multiplier × time_factor
  2. Subscriptions: Starter (₹99), Business (₹499), Enterprise (₹1,999)
  3. Smart batching discount: 15% off for flexible timing
  4. Surge pricing: demand/supply ratio per zone
  5. Value-added upsells: priority, insurance, photo proof, etc.
"""

from dataclasses import dataclass
from enum import Enum


# ── Constants ──────────────────────────────────────────────

RATE_PER_KM = 10.0        # ₹10 per km (base)
MINIMUM_CHARGE = 35.0     # ₹35 floor price

VEHICLE_MULTIPLIER = {
    "BIKE": 1.0,
    "AUTO": 1.3,
    "VAN": 1.6,
}

TIME_FACTOR = {
    "NEXT_DAY": 0.9,      # Discount for patience
    "STANDARD": 1.0,      # Same-day standard
    "SAME_DAY": 1.3,      # Same-day priority
    "EXPRESS": 1.8,        # 2-hour express
}

WEIGHT_TO_VEHICLE = {
    "LIGHT": "BIKE",       # <5 kg
    "MEDIUM": "AUTO",      # 5-20 kg
    "HEAVY": "VAN",        # >20 kg
}

BATCH_DISCOUNT_PCT = 0.15  # 15% off for batch-eligible orders

# Subscription plans
SUBSCRIPTION_PLANS = {
    "STARTER": {
        "monthly_price": 99.0,
        "free_deliveries": 5,
        "discount_pct": 0.0,
    },
    "BUSINESS": {
        "monthly_price": 499.0,
        "free_deliveries": 25,
        "discount_pct": 0.05,  # 5% on top
    },
    "ENTERPRISE": {
        "monthly_price": 1999.0,
        "free_deliveries": 999,  # effectively unlimited
        "discount_pct": 0.10,    # 10% on top
    },
}

# Value-added service prices
ADDON_PRICES = {
    "PRIORITY_HANDLING": 30.0,
    "PHOTO_PROOF": 10.0,
    "INSURANCE_5K": 25.0,
    "INSURANCE_25K": 75.0,
    "SCHEDULED_SLOT": 20.0,
    "RETURN_SERVICE": 15.0,
}

# Surge thresholds (orders-to-riders ratio)
SURGE_BANDS = [
    (2.0, 1.0),   # ratio < 2 → no surge
    (4.0, 1.2),   # 2 ≤ ratio < 4 → 1.2x
    (6.0, 1.4),   # 4 ≤ ratio < 6 → 1.4x
    (999, 1.6),   # ratio ≥ 6 → 1.6x (cap)
]

RIDER_SURGE_SHARE = 0.30  # 30% of surge premium goes to rider


# ── Data classes ───────────────────────────────────────────

@dataclass
class PriceBreakdown:
    distance_km: float
    duration_min: int
    vehicle_type: str
    rate_per_km: float
    vehicle_multiplier: float
    time_factor_key: str
    time_factor_value: float
    base_cost: float
    surge_multiplier: float
    surge_reason: str | None
    addons_cost: float
    batch_discount: float
    subscription_discount: float
    total_cost: float
    rider_surge_bonus: float


# ── Core Functions ─────────────────────────────────────────

def determine_vehicle(weight_tier: str) -> str:
    """Map weight tier to vehicle type."""
    return WEIGHT_TO_VEHICLE.get(weight_tier, "BIKE")


def calculate_surge(active_orders: int, available_riders: int) -> tuple[float, str | None]:
    """
    Calculate surge multiplier from demand/supply ratio.
    Returns (multiplier, reason_string).
    """
    if available_riders <= 0:
        return 1.6, f"No riders available ({active_orders} active orders)"

    ratio = active_orders / available_riders

    for threshold, multiplier in SURGE_BANDS:
        if ratio < threshold:
            if multiplier > 1.0:
                reason = (
                    f"High demand: {active_orders} orders, "
                    f"{available_riders} riders (ratio: {ratio:.1f})"
                )
                return multiplier, reason
            return 1.0, None

    return 1.6, f"Extreme demand: {active_orders} orders, {available_riders} riders"


def calculate_price(
    distance_km: float,
    duration_min: int,
    weight_tier: str = "LIGHT",
    time_factor_key: str = "STANDARD",
    surge_multiplier: float = 1.0,
    surge_reason: str | None = None,
    addons: list[str] | None = None,
    is_batch_eligible: bool = False,
    subscription_plan: str | None = None,
    free_deliveries_remaining: int = 0,
) -> PriceBreakdown:
    """
    Calculate the full price breakdown for an order.

    Args:
        distance_km: Distance from pickup to drop-off
        duration_min: Estimated duration in minutes
        weight_tier: LIGHT, MEDIUM, or HEAVY
        time_factor_key: NEXT_DAY, STANDARD, SAME_DAY, or EXPRESS
        surge_multiplier: Pre-calculated surge factor
        surge_reason: Human-readable surge explanation
        addons: List of addon keys (e.g., ["PRIORITY_HANDLING", "PHOTO_PROOF"])
        is_batch_eligible: Whether user opted for flexible timing
        subscription_plan: Active subscription plan name or None
        free_deliveries_remaining: Free deliveries left on subscription

    Returns:
        PriceBreakdown with complete cost details
    """
    vehicle_type = determine_vehicle(weight_tier)
    vehicle_mult = VEHICLE_MULTIPLIER[vehicle_type]
    time_fact = TIME_FACTOR.get(time_factor_key, 1.0)

    # Base cost
    base_cost = distance_km * RATE_PER_KM * vehicle_mult * time_fact

    # Apply surge
    surged_cost = base_cost * surge_multiplier

    # Rider surge bonus (for company payroll)
    rider_surge_bonus = 0.0
    if surge_multiplier > 1.0:
        surge_premium = surged_cost - base_cost
        rider_surge_bonus = surge_premium * RIDER_SURGE_SHARE

    # Addons
    addons_cost = 0.0
    if addons:
        for addon in addons:
            addons_cost += ADDON_PRICES.get(addon, 0.0)

    # Batch discount
    batch_discount = 0.0
    if is_batch_eligible:
        batch_discount = surged_cost * BATCH_DISCOUNT_PCT

    # Subscription discount
    subscription_discount = 0.0
    if subscription_plan and free_deliveries_remaining > 0:
        # Free delivery — discount the entire base
        subscription_discount = surged_cost
    elif subscription_plan:
        plan_info = SUBSCRIPTION_PLANS.get(subscription_plan, {})
        disc_pct = plan_info.get("discount_pct", 0.0)
        subscription_discount = surged_cost * disc_pct

    # Total
    total = surged_cost + addons_cost - batch_discount - subscription_discount
    total = max(total, MINIMUM_CHARGE)  # Floor

    return PriceBreakdown(
        distance_km=distance_km,
        duration_min=duration_min,
        vehicle_type=vehicle_type,
        rate_per_km=RATE_PER_KM,
        vehicle_multiplier=vehicle_mult,
        time_factor_key=time_factor_key,
        time_factor_value=time_fact,
        base_cost=round(base_cost, 2),
        surge_multiplier=surge_multiplier,
        surge_reason=surge_reason,
        addons_cost=round(addons_cost, 2),
        batch_discount=round(batch_discount, 2),
        subscription_discount=round(subscription_discount, 2),
        total_cost=round(total, 2),
        rider_surge_bonus=round(rider_surge_bonus, 2),
    )
