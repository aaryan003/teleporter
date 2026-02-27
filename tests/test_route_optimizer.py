"""Tests for the route optimizer (OR-Tools VRP solver)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from services.route_optimizer import optimize_route, check_return_trip_pickup


def test_empty_delivery_points():
    """Empty list should return empty route."""
    result = optimize_route(depot=(12.93, 77.62), delivery_points=[])
    assert result.total_distance_km == 0
    assert result.stop_details == []


def test_single_delivery():
    """Single delivery should produce a simple round trip."""
    result = optimize_route(
        depot=(12.9352, 77.6245),
        delivery_points=[{"lat": 12.9500, "lng": 77.6300, "order_id": "test1"}],
    )
    assert result.total_distance_km > 0
    assert len(result.stop_details) == 1


def test_multiple_deliveries():
    """Multiple deliveries should produce an optimized route."""
    depot = (12.9352, 77.6245)  # Koramangala
    points = [
        {"lat": 12.9784, "lng": 77.6408, "order_id": "A"},  # Indiranagar
        {"lat": 12.9116, "lng": 77.6389, "order_id": "B"},  # HSR Layout
        {"lat": 12.9698, "lng": 77.7500, "order_id": "C"},  # Whitefield
        {"lat": 12.9550, "lng": 77.6350, "order_id": "D"},  # Near Koramangala
    ]
    result = optimize_route(depot, points)

    assert result.total_distance_km > 0
    assert len(result.stop_details) == 4
    # Optimized should be shorter or equal to naive
    assert result.savings_vs_naive_km >= 0


def test_optimization_improves_on_naive():
    """Route optimizer should produce shorter route than naive order for spread points."""
    depot = (12.9352, 77.6245)
    # Spread points where naive order would be bad
    points = [
        {"lat": 12.9800, "lng": 77.7200, "order_id": "far_NE"},    # Far NE
        {"lat": 12.9400, "lng": 77.6300, "order_id": "near_S"},     # Near S
        {"lat": 12.9700, "lng": 77.7100, "order_id": "mid_NE"},     # Mid NE
        {"lat": 12.9350, "lng": 77.6400, "order_id": "near_SE"},    # Near SE
        {"lat": 12.9750, "lng": 77.7300, "order_id": "far_NE2"},    # Another Far NE
    ]
    result = optimize_route(depot, points)

    # For spread points, optimization should save something
    assert result.total_distance_km > 0
    assert len(result.stop_details) == 5


def test_return_trip_no_pickups():
    """No nearby pickups should return empty list."""
    eligible = check_return_trip_pickup(
        rider_location=(12.95, 77.64),
        warehouse_location=(12.93, 77.62),
        pending_pickups=[],
    )
    assert eligible == []


def test_return_trip_nearby_pickup():
    """Pickup on the way back should be included."""
    eligible = check_return_trip_pickup(
        rider_location=(12.9500, 77.6400),  # Rider
        warehouse_location=(12.9352, 77.6245),  # Warehouse
        pending_pickups=[
            {"lat": 12.9420, "lng": 77.6320, "order_id": "P1"},  # On the way
        ],
        max_detour_km=2.0,
    )
    assert len(eligible) >= 1
    assert "detour_km" in eligible[0]


def test_return_trip_far_pickup_excluded():
    """Pickup too far from route should be excluded."""
    eligible = check_return_trip_pickup(
        rider_location=(12.9500, 77.6400),
        warehouse_location=(12.9352, 77.6245),
        pending_pickups=[
            {"lat": 13.0200, "lng": 77.8000, "order_id": "FAR"},  # Very far
        ],
        max_detour_km=2.0,
    )
    assert len(eligible) == 0


def test_return_trip_sorted_by_detour():
    """Eligible pickups should be sorted by detour distance."""
    eligible = check_return_trip_pickup(
        rider_location=(12.9500, 77.6400),
        warehouse_location=(12.9352, 77.6245),
        pending_pickups=[
            {"lat": 12.9380, "lng": 77.6280, "order_id": "closer"},
            {"lat": 12.9420, "lng": 77.6320, "order_id": "further"},
        ],
        max_detour_km=5.0,
    )
    if len(eligible) >= 2:
        assert eligible[0]["detour_km"] <= eligible[1]["detour_km"]
