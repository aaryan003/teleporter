"""Tests for the pricing engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from services.pricing import (
    calculate_price, determine_vehicle, calculate_surge,
    MINIMUM_CHARGE, VEHICLE_MULTIPLIER, SUBSCRIPTION_PLANS,
    RATE_PER_KM,
)


def test_determine_vehicle():
    """Package size should map to correct vehicle."""
    assert determine_vehicle("SMALL") == "BIKE"
    assert determine_vehicle("MEDIUM") == "BIKE"
    assert determine_vehicle("LARGE") == "MINI_VAN"
    assert determine_vehicle("BULKY") == "MINI_TRUCK"
    assert determine_vehicle("UNKNOWN") == "BIKE"  # default


def test_minimum_charge():
    """Very short distance should still charge minimum."""
    price = calculate_price(distance_km=0.5, duration_min=3)
    assert price.total_cost >= MINIMUM_CHARGE


def test_base_cost_small():
    """Small package base cost = distance × rate × BIKE mult × time."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="SMALL", time_factor_key="STANDARD",
    )
    # 10 km × $2.50/km × 1.0 (bike) × 1.0 (standard) = $25.00
    expected = 10.0 * RATE_PER_KM * 1.0 * 1.0
    assert price.base_cost == expected
    assert price.vehicle_type == "BIKE"
    assert price.total_cost == expected


def test_large_mini_van_multiplier():
    """Large packages should use MINI_VAN multiplier."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="LARGE", time_factor_key="STANDARD",
    )
    # 10 × $2.50 × 1.3 (MINI_VAN) × 1.0 = $32.50
    expected = 10.0 * RATE_PER_KM * VEHICLE_MULTIPLIER["MINI_VAN"]
    assert price.base_cost == expected
    assert price.vehicle_type == "MINI_VAN"


def test_bulky_mini_truck_multiplier():
    """Bulky packages should use MINI_TRUCK multiplier."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="BULKY", time_factor_key="STANDARD",
    )
    # 10 × $2.50 × 1.5 (MINI_TRUCK) × 1.0 = $37.50
    expected = 10.0 * RATE_PER_KM * VEHICLE_MULTIPLIER["MINI_TRUCK"]
    assert price.base_cost == expected
    assert price.vehicle_type == "MINI_TRUCK"


def test_express_time_factor():
    """Express should apply 1.8x time factor."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="SMALL", time_factor_key="EXPRESS",
    )
    # 10 × $2.50 × 1.0 × 1.8 = $45.00
    expected = 10.0 * RATE_PER_KM * 1.0 * 1.8
    assert price.base_cost == expected


def test_next_day_discount():
    """Next-day should apply 0.9x discount."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="SMALL", time_factor_key="NEXT_DAY",
    )
    # 10 × $2.50 × 1.0 × 0.9 = $22.50
    expected = 10.0 * RATE_PER_KM * 1.0 * 0.9
    assert price.base_cost == expected


def test_surge_applied():
    """Surge should multiply the base cost."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        surge_multiplier=1.4,
        surge_reason="High demand",
    )
    base = 10.0 * RATE_PER_KM  # $25.00
    surged = base * 1.4          # $35.00
    assert price.total_cost == round(surged, 2)
    assert price.surge_reason == "High demand"
    assert price.rider_surge_bonus > 0  # 30% of surge premium


def test_batch_discount():
    """Batch-eligible should get 15% off."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        is_batch_eligible=True,
    )
    base = 10.0 * RATE_PER_KM                    # $25.00
    batch = base * 0.15                            # $3.75
    assert price.batch_discount == round(batch, 2)
    assert price.total_cost == round(base - batch, 2)


def test_surge_with_batch():
    """Surge + batch discount should combine correctly."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        surge_multiplier=1.2,
        is_batch_eligible=True,
    )
    base = 10.0 * RATE_PER_KM      # $25.00
    surged = base * 1.2              # $30.00
    batch = surged * 0.15            # $4.50
    assert price.batch_discount == round(batch, 2)
    assert price.total_cost == round(surged - batch, 2)


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
    base = 10.0 * RATE_PER_KM              # $25.00
    discount = base * 0.05                   # $1.25
    assert price.subscription_discount == round(discount, 2)
    assert price.total_cost == round(base - discount, 2)


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
    base = 10.0 * RATE_PER_KM                              # $25.00
    addons = 7.99 + 2.99                                     # $10.98
    assert price.addons_cost == addons
    assert price.total_cost == round(base + addons, 2)


def test_medium_uses_bike():
    """Medium packages should still use BIKE (not mini_van)."""
    price = calculate_price(
        distance_km=10.0, duration_min=20,
        weight_tier="MEDIUM", time_factor_key="STANDARD",
    )
    assert price.vehicle_type == "BIKE"
    assert price.base_cost == 10.0 * RATE_PER_KM


def test_truck_multiplier_exists():
    """TRUCK multiplier should be defined and > MINI_TRUCK."""
    assert "TRUCK" in VEHICLE_MULTIPLIER
    assert VEHICLE_MULTIPLIER["TRUCK"] > VEHICLE_MULTIPLIER["MINI_TRUCK"]
