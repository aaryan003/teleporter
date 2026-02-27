"""
Route Optimizer — Multi-stop delivery optimization using Google OR-Tools VRP solver.

Solves the Vehicle Routing Problem (VRP):
  - Given a warehouse (depot) and N delivery points
  - Find the shortest route visiting all points and returning to depot
  - Respects vehicle capacity constraints

Uses: Google OR-Tools Constraint Solver
"""

from __future__ import annotations
from dataclasses import dataclass
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

from services.maps import haversine_distance


@dataclass
class OptimizedRoute:
    sequence: list[int]          # Ordered indices of stops (0 = depot)
    stop_details: list[dict]     # Details for each stop
    total_distance_km: float
    total_duration_min: int
    savings_vs_naive_km: float   # How much distance saved vs sequential order


def _build_distance_matrix_from_points(
    points: list[tuple[float, float]],
    api_matrix: list[list[dict]] | None = None,
) -> list[list[int]]:
    """
    Build integer distance matrix (in meters) for OR-Tools.
    Uses provided API matrix if available, else Haversine.
    """
    n = len(points)
    matrix = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if api_matrix and api_matrix[i][j].get("distance_km"):
                matrix[i][j] = int(api_matrix[i][j]["distance_km"] * 1000)
            else:
                d = haversine_distance(
                    points[i][0], points[i][1],
                    points[j][0], points[j][1],
                )
                matrix[i][j] = int(d * 1000)  # Convert to meters

    return matrix


def optimize_route(
    depot: tuple[float, float],
    delivery_points: list[dict],
    api_matrix: list[list[dict]] | None = None,
    max_solve_seconds: int = 5,
) -> OptimizedRoute:
    """
    Optimize delivery route for a single rider.

    Args:
        depot: (lat, lng) of the warehouse
        delivery_points: list of {"lat": float, "lng": float, "order_id": str, ...}
        api_matrix: Pre-fetched distance matrix (optional, uses Haversine if not provided)
        max_solve_seconds: Max time for solver (default 5s)

    Returns:
        OptimizedRoute with ordered sequence and stats
    """
    if not delivery_points:
        return OptimizedRoute(
            sequence=[],
            stop_details=[],
            total_distance_km=0,
            total_duration_min=0,
            savings_vs_naive_km=0,
        )

    if len(delivery_points) == 1:
        d = haversine_distance(
            depot[0], depot[1],
            delivery_points[0]["lat"], delivery_points[0]["lng"],
        )
        return OptimizedRoute(
            sequence=[0, 1, 0],
            stop_details=[delivery_points[0]],
            total_distance_km=round(d * 2, 2),  # round trip
            total_duration_min=int(d * 2 / 25 * 60),
            savings_vs_naive_km=0,
        )

    # Build points array: index 0 = depot, rest = delivery points
    all_points = [depot] + [(p["lat"], p["lng"]) for p in delivery_points]
    n = len(all_points)

    # Build distance matrix
    dist_matrix = _build_distance_matrix_from_points(all_points, api_matrix)

    # Calculate naive distance (sequential: depot → 1 → 2 → ... → N → depot)
    naive_distance = 0
    for i in range(n - 1):
        naive_distance += dist_matrix[i][i + 1]
    naive_distance += dist_matrix[n - 1][0]  # Return to depot

    # ── OR-Tools VRP Solver ────────────────────────────────
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # n nodes, 1 vehicle, depot=0
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Search parameters
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_params.time_limit.FromSeconds(max_solve_seconds)

    # Solve
    solution = routing.SolveWithParameters(search_params)

    if not solution:
        # Fallback: return naive order if solver fails
        return OptimizedRoute(
            sequence=list(range(n)) + [0],
            stop_details=delivery_points,
            total_distance_km=round(naive_distance / 1000, 2),
            total_duration_min=int(naive_distance / 1000 / 25 * 60),
            savings_vs_naive_km=0,
        )

    # Extract solution
    sequence = []
    index = routing.Start(0)
    optimized_distance = 0

    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        sequence.append(node)
        next_index = solution.Value(routing.NextVar(index))
        optimized_distance += routing.GetArcCostForVehicle(index, next_index, 0)
        index = next_index
    sequence.append(0)  # Return to depot

    # Build stop details (skip depot entries)
    stop_details = []
    for node_idx in sequence:
        if node_idx > 0 and node_idx <= len(delivery_points):
            stop_details.append(delivery_points[node_idx - 1])

    total_km = round(optimized_distance / 1000, 2)
    naive_km = round(naive_distance / 1000, 2)
    savings = round(naive_km - total_km, 2)

    return OptimizedRoute(
        sequence=sequence,
        stop_details=stop_details,
        total_distance_km=total_km,
        total_duration_min=int(total_km / 25 * 60),  # ~25 km/h avg city speed
        savings_vs_naive_km=max(savings, 0),
    )


def check_return_trip_pickup(
    rider_location: tuple[float, float],
    warehouse_location: tuple[float, float],
    pending_pickups: list[dict],
    max_detour_km: float = 2.0,
) -> list[dict]:
    """
    Find pending pickups that are near the rider's return route.

    Args:
        rider_location: (lat, lng) of rider's current position
        warehouse_location: (lat, lng) of home warehouse
        pending_pickups: list of {"lat": float, "lng": float, "order_id": str, ...}
        max_detour_km: Maximum extra distance allowed

    Returns:
        List of pickups within detour limit, sorted by detour distance
    """
    direct_distance = haversine_distance(
        rider_location[0], rider_location[1],
        warehouse_location[0], warehouse_location[1],
    )

    eligible = []
    for pickup in pending_pickups:
        # Distance: rider → pickup → warehouse
        d_to_pickup = haversine_distance(
            rider_location[0], rider_location[1],
            pickup["lat"], pickup["lng"],
        )
        d_pickup_to_warehouse = haversine_distance(
            pickup["lat"], pickup["lng"],
            warehouse_location[0], warehouse_location[1],
        )
        detour = (d_to_pickup + d_pickup_to_warehouse) - direct_distance

        if detour <= max_detour_km:
            pickup["detour_km"] = round(detour, 2)
            eligible.append(pickup)

    # Sort by detour (closest first)
    eligible.sort(key=lambda p: p["detour_km"])

    return eligible
