import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Pure haversine distance between two coordinates in kilometers.
    No external APIs, no Redis.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def distance_km_between(
    origin: tuple[float, float],
    dest: tuple[float, float],
) -> float:
    return haversine_km(origin[0], origin[1], dest[0], dest[1])

