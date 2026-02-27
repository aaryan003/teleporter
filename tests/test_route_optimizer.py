from api.services.route_optimizer import optimize_delivery_route


def test_optimize_route_basic():
    # Simple symmetric distance matrix for 4 locations (0 is warehouse)
    distance_matrix = [
        [0, 2, 9, 10],
        [1, 0, 6, 4],
        [15, 7, 0, 8],
        [6, 3, 12, 0],
    ]

    route = optimize_delivery_route(warehouse_location=0, distance_matrix=distance_matrix)

    assert route[0] == 0
    assert route[-1] == 0
    assert set(route[1:-1]) == {1, 2, 3}

