"""
OTP Service — Generation, hashing, and verification.

Security:
  - 6-digit numeric codes
  - Hashed with bcrypt before storage
  - Max 3 verification attempts
  - Stored in Redis with 10-minute TTL
"""

import secrets
import bcrypt
import redis.asyncio as aioredis

from config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Singleton Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def generate_otp(order_id: str, otp_type: str) -> str:
    """
    Generate a 6-digit OTP, store its bcrypt hash in Redis.

    Args:
        order_id: UUID of the order
        otp_type: "pickup" or "drop"

    Returns:
        Plaintext OTP (to send to user via Telegram)
    """
    otp = f"{secrets.randbelow(1000000):06d}"
    otp_hash = bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()

    r = await get_redis()
    key = f"otp:{order_id}:{otp_type}"

    await r.hset(key, mapping={
        "hash": otp_hash,
        "attempts": "0",
    })
    await r.expire(key, 600)  # 10-minute TTL

    return otp


async def verify_otp(order_id: str, otp_type: str, provided_otp: str) -> dict:
    """
    Verify an OTP against stored hash.

    Returns:
        {"valid": True} on success
        {"valid": False, "error": "...", "remaining": N} on failure
    """
    r = await get_redis()
    key = f"otp:{order_id}:{otp_type}"

    data = await r.hgetall(key)
    if not data:
        return {"valid": False, "error": "OTP expired. Please request a new one.", "remaining": 0}

    attempts = int(data.get("attempts", 0))
    if attempts >= 3:
        return {"valid": False, "error": "Too many attempts. Contact support.", "remaining": 0}

    # Increment attempts
    await r.hincrby(key, "attempts", 1)

    if bcrypt.checkpw(provided_otp.encode(), data["hash"].encode()):
        await r.delete(key)  # Invalidate on success
        return {"valid": True}

    remaining = 2 - attempts
    return {
        "valid": False,
        "error": f"Incorrect OTP. {max(remaining, 0)} attempts remaining.",
        "remaining": max(remaining, 0),
    }


async def get_otp_hash(order_id: str, otp_type: str) -> str | None:
    """Get the stored OTP hash for database storage (for audit)."""
    r = await get_redis()
    key = f"otp:{order_id}:{otp_type}"
    data = await r.hgetall(key)
    return data.get("hash") if data else None
