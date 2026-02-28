"""
Geoapify Maps Service — Geocoding and Routing with aggressive caching.

Optimization strategy:
  1. Geocode cache in Redis (30-day TTL) → ~70% reduction
  2. Distance caching for pairwise calls → ~60% reduction
  3. Haversine fallback when API down → 100% savings
"""

import hashlib
import math
import httpx
import redis.asyncio as aioredis

from config import settings

_redis: aioredis.Redis | None = None
_http: httpx.AsyncClient | None = None

# Primary provider: Geoapify
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_ROUTING_URL = "https://api.geoapify.com/v1/routing"

# Fallback provider: Nominatim (OpenStreetMap)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Cache TTLs
GEOCODE_CACHE_TTL = 30 * 24 * 3600   # 30 days
DISTANCE_CACHE_TTL = 2 * 3600         # 2 hours


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def _get_http() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=10.0)
    return _http


def _address_hash(address: str) -> str:
    """Normalize and hash an address for cache key."""
    normalized = address.strip().lower().replace("  ", " ")
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _latlng_hash(lat: float, lng: float) -> str:
    """Hash lat/lng to 4 decimal places for distance cache."""
    key = f"{lat:.4f},{lng:.4f}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Haversine Fallback ─────────────────────────────────────

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate straight-line distance in km using Haversine formula.
    Multiply by 1.4 road factor to approximate actual road distance.
    """
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    straight_line = R * c
    return round(straight_line * 1.4, 2)  # Road factor


def estimate_duration(distance_km: float, avg_speed_kmh: float = 25.0) -> int:
    """Estimate duration in minutes from distance at average city speed."""
    return max(int((distance_km / avg_speed_kmh) * 60), 1)


# ── Geocoding ──────────────────────────────────────────────

def _parse_lat_lng(text: str) -> tuple[float, float] | None:
    """Parse 'lat,lng' or 'lat,lng' format (e.g. from Telegram location pin)."""
    if not text or "," not in text:
        return None
    parts = text.strip().split(",", 1)
    if len(parts) != 2:
        return None
    try:
        lat, lng = float(parts[0].strip()), float(parts[1].strip())
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return (lat, lng)
    except ValueError:
        pass
    return None


async def geocode(address: str) -> dict | None:
    """
    Geocode an address to lat/lng. Uses Redis cache first,
    then Geoapify, then Nominatim (OSM) as free fallback.
    Handles "lat,lng" format (from location pins) directly.

    Returns:
        {"lat": float, "lng": float, "formatted": str} or None
    """
    # ── Location pin (lat,lng) — return immediately ─────────
    coords = _parse_lat_lng(address)
    if coords is not None:
        return {"lat": coords[0], "lng": coords[1], "formatted": address}

    r = await _get_redis()
    cache_key = f"geo:{_address_hash(address)}"

    # Check cache
    cached = await r.hgetall(cache_key)
    if cached and "lat" in cached:
        return {
            "lat": float(cached["lat"]),
            "lng": float(cached["lng"]),
            "formatted": cached.get("formatted", address),
        }

    result = None

    # Build fallback candidates: full address first, then area+city, then progressively simpler
    # e.g. "12/A Tulsi Villa Bunglow, Maninagar, Ahmedabad" → try full, then "Maninagar, Ahmedabad", etc.
    def _geocode_candidates(addr: str) -> list[str]:
        candidates = [addr.strip()]
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        # Area + city: "Maninagar, Ahmedabad" or "Maninagar, Ahmedabad 380058"
        if len(parts) >= 2:
            area_city = ", ".join(parts[-2:])
            if len(area_city) > 5 and area_city not in candidates:
                candidates.append(area_city)
        if len(parts) >= 3:
            area_city = ", ".join(parts[-3:])
            if len(area_city) > 5 and area_city not in candidates:
                candidates.append(area_city)
        # Token stripping: drop leading parts (building names/numbers OSM often doesn't index)
        flat_parts = addr.replace(",", " ").split()
        for i in range(1, min(6, len(flat_parts))):
            shorter = " ".join(flat_parts[i:])
            if len(shorter) > 6 and shorter not in candidates:
                candidates.append(shorter)
        # Last resort: just the city
        if len(parts) >= 1 and parts[-1] not in candidates:
            candidates.append(parts[-1])
        return candidates

    candidates = _geocode_candidates(address)

    # ── Try Geoapify (each candidate until one works) ─────────
    if settings.GEOAPIFY_API_KEY:
        try:
            http = await _get_http()
            for q in candidates:
                resp = await http.get(
                    GEOAPIFY_GEOCODE_URL,
                    params={
                        "text": q,
                        "apiKey": settings.GEOAPIFY_API_KEY,
                    },
                )
                data = resp.json()
                features = data.get("features") or []
                if features:
                    props = features[0].get("properties", {}) or {}
                    lat = props.get("lat")
                    lon = props.get("lon")
                    if lat is not None and lon is not None:
                        result = {
                            "lat": float(lat),
                            "lng": float(lon),
                            "formatted": props.get("formatted")
                            or props.get("address_line2")
                            or q,
                        }
                        break
        except Exception as e:
            print(f"⚠️ Geoapify geocode exception: {e}")

    # ── Nominatim fallback (free, no key needed) ─────────────
    if result is None:
        try:
            http = await _get_http()
            for q in candidates:
                resp = await http.get(NOMINATIM_URL, params={
                    "q": q,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                    "countrycodes": "in",
                }, headers={"User-Agent": "TeleporterBot/2.0 (logistics@teleporter.app)"})
                hits = resp.json()
                if hits:
                    result = {
                        "lat": float(hits[0]["lat"]),
                        "lng": float(hits[0]["lon"]),
                        "formatted": hits[0].get("display_name", address),
                    }
                    break
        except Exception as e:
            print(f"⚠️ Nominatim geocode exception: {e}")

    # ── Cache successful result ──────────────────────────────
    if result:
        await r.hset(cache_key, mapping={
            "lat": str(result["lat"]),
            "lng": str(result["lng"]),
            "formatted": result["formatted"],
        })
        await r.expire(cache_key, GEOCODE_CACHE_TTL)

    return result


# ── Distance Matrix ────────────────────────────────────────

async def get_distance(
    origin_lat: float, origin_lng: float,
    dest_lat: float, dest_lng: float,
) -> dict:
    """
    Get distance and duration between two points.
    Uses cache, falls back to Haversine if API unavailable.

    Returns:
        {"distance_km": float, "duration_min": int, "source": "google"|"haversine"}
    """
    r = await _get_redis()
    o_hash = _latlng_hash(origin_lat, origin_lng)
    d_hash = _latlng_hash(dest_lat, dest_lng)
    cache_key = f"dist:{o_hash}:{d_hash}"

    # Check cache
    cached = await r.hgetall(cache_key)
    if cached and "distance_km" in cached:
        return {
            "distance_km": float(cached["distance_km"]),
            "duration_min": int(cached["duration_min"]),
            "source": "cache",
        }

    # Try Geoapify Routing
    if settings.GEOAPIFY_API_KEY:
        try:
            http = await _get_http()
            resp = await http.get(
                GEOAPIFY_ROUTING_URL,
                params={
                    "waypoints": f"{origin_lat},{origin_lng}|{dest_lat},{dest_lng}",
                    "mode": "drive",
                    "apiKey": settings.GEOAPIFY_API_KEY,
                },
            )
            data = resp.json()
            features = data.get("features") or []
            if features:
                props = features[0].get("properties", {}) or {}
                distance_m = props.get("distance")
                time_s = props.get("time")
                if isinstance(distance_m, (int, float)) and isinstance(time_s, (int, float)):
                    distance_km = round(distance_m / 1000.0, 2)
                    duration_min = max(int(round(time_s / 60.0)), 1)

                    # Cache
                    await r.hset(
                        cache_key,
                        mapping={
                            "distance_km": str(distance_km),
                            "duration_min": str(duration_min),
                        },
                    )
                    await r.expire(cache_key, DISTANCE_CACHE_TTL)

                    return {
                        "distance_km": distance_km,
                        "duration_min": duration_min,
                        "source": "geoapify",
                    }
            print(
                f"⚠️ Geoapify routing failed for "
                f"{origin_lat},{origin_lng} → {dest_lat},{dest_lng}"
            )
        except Exception as e:
            print(f"⚠️ Geoapify routing exception: {e}")

    # Haversine fallback
    distance_km = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
    duration_min = estimate_duration(distance_km)

    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "source": "haversine",
    }


# ── Batch Distance Matrix ─────────────────────────────────

async def get_distance_matrix(
    points: list[tuple[float, float]],
) -> list[list[dict]]:
    """
    Get distance matrix for multiple points (for route optimization).
    Uses Google Maps Distance Matrix API with batching.

    Args:
        points: List of (lat, lng) tuples. First point should be warehouse.

    Returns:
        n×n matrix where matrix[i][j] = {"distance_km": float, "duration_min": int}
    """
    n = len(points)
    matrix = [[{"distance_km": 0.0, "duration_min": 0} for _ in range(n)] for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            result = await get_distance(
                points[i][0], points[i][1],
                points[j][0], points[j][1],
            )
            matrix[i][j] = {
                "distance_km": result["distance_km"],
                "duration_min": result["duration_min"],
            }

    return matrix
