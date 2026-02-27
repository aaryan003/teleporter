from api.services.pricing import PricingContext, calculate_total


def test_pricing_minimum_charge():
    ctx = PricingContext(
        distance_km=1.0,
        weight_kg=1.0,
        vehicle_type="BIKE",
        time_type="STANDARD",
    )
    result = calculate_total(ctx)
    assert result["base_cost"] >= 35.0
    assert result["total_cost"] >= 35.0


def test_pricing_batch_discount():
    ctx = PricingContext(
        distance_km=10.0,
        weight_kg=1.0,
        vehicle_type="BIKE",
        time_type="STANDARD",
        is_batch_eligible=True,
    )
    result_batch = calculate_total(ctx)

    ctx_no_batch = PricingContext(
        distance_km=10.0,
        weight_kg=1.0,
        vehicle_type="BIKE",
        time_type="STANDARD",
        is_batch_eligible=False,
    )
    result_no_batch = calculate_total(ctx_no_batch)

    assert result_batch["total_cost"] < result_no_batch["total_cost"]

