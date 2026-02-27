"""Tests for the pricing engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from services.pricing import (
    calculate_price, determine_vehicle, calculate_surge,
    MINIMUM_CHARGE, VEHICLE_MULTIPLIER, SUBSCRIPTION_PLANS,
)


def test_determine_vehicle():
    """Weight tier should map to correct vehicle."""
    assert determine_vehicle("LIGHT") == "BIKE"
    assert determine_vehicle("MEDIUM") == "AUTO"
    assert determine_vehicle("HEAVY") == "VAN"
    assert determine_vehicle("UNKNOWN") == "BIKE"  # default


def test_minimum_charge():
    """Very short distance should still charge minimum."""
    price = calculate_price(distance_km=0.5, duration_min=3)
    assert price.total_cost >= MINIMUM_CHARGE


def test_base_cost_calculation():
    """Base cost = distance × rate × vehicle_mult × time_factor."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="LIGHT", time_factor_key="STANDARD",
    )
    # 10 km × ₹10/km × 1.0 (bike) × 1.0 (standard) = ₹100
    assert price.base_cost == 100.0
    assert price.vehicle_type == "BIKE"
    assert price.total_cost == 100.0


def test_heavy_vehicle_multiplier():
    """Heavy packages should use VAN multiplier."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="HEAVY", time_factor_key="STANDARD",
    )
    # 10 × 10 × 1.6 (VAN) × 1.0 = ₹160
    assert price.base_cost == 160.0
    assert price.vehicle_type == "VAN"


def test_express_time_factor():
    """Express should apply 1.8x time factor."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="LIGHT", time_factor_key="EXPRESS",
    )
    # 10 × 10 × 1.0 × 1.8 = ₹180
    assert price.base_cost == 180.0


def test_next_day_discount():
    """Next-day should apply 0.9x discount."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="LIGHT", time_factor_key="NEXT_DAY",
    )
    # 10 × 10 × 1.0 × 0.9 = ₹90
    assert price.base_cost == 90.0


def test_surge_applied():
    """Surge should multiply the base cost."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        surge_multiplier=1.4,
        surge_reason="High demand",
    )
    # Base: ₹100, Surged: ₹140
    assert price.total_cost == 140.0
    assert price.surge_reason == "High demand"
    assert price.rider_surge_bonus > 0  # 30% of surge premium


def test_batch_discount():
    """Batch-eligible should get 15% off."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        is_batch_eligible=True,
    )
    # Base: ₹100, Batch: -₹15 → Total: ₹85
    assert price.batch_discount == 15.0
    assert price.total_cost == 85.0


def test_surge_with_batch():
    """Surge + batch discount should combine correctly."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        surge_multiplier=1.2,
        is_batch_eligible=True,
    )
    # Base: ₹100, Surged: ₹120, Batch: -₹18 → Total: ₹102
    assert price.batch_discount == 18.0
    assert price.total_cost == 102.0


def test_free_subscription_delivery():
    """Free delivery from subscription should zero out cost."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        subscription_plan="STARTER",
        free_deliveries_remaining=3,
    )
    # Full discount but minimum charge applies
    assert price.total_cost == MINIMUM_CHARGE


def test_subscription_percentage_discount():
    """Business subscription should give 5% discount."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        subscription_plan="BUSINESS",
        free_deliveries_remaining=0,
    )
    # Base: ₹100, Discount: 5% → ₹95
    assert price.subscription_discount == 5.0
    assert price.total_cost == 95.0


def test_calculate_surge_no_surge():
    """Low demand should produce no surge."""
    mult, reason = calculate_surge(active_orders=3, available_riders=5)
    assert mult == 1.0
    assert reason is None


def test_calculate_surge_high():
    """High demand should produce surge."""
    mult, reason = calculate_surge(active_orders=15, available_riders=3)
    assert mult >= 1.4
    assert reason is not None


def test_calculate_surge_no_riders():
    """No available riders should produce max surge."""
    mult, reason = calculate_surge(active_orders=5, available_riders=0)
    assert mult == 1.6


def test_addons_cost():
    """Value-added services should add to total."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        addons=["PRIORITY_HANDLING", "PHOTO_PROOF"],
    )
    # Base: ₹100 + ₹30 + ₹10 = ₹140
    assert price.addons_cost == 40.0
    assert price.total_cost == 140.0
