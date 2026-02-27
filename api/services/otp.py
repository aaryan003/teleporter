import random
import string
from datetime import datetime, timedelta
from typing import Dict


_otp_store: Dict[str, tuple[str, datetime]] = {}
OTP_TTL_MIN = 15


def generate_otp(key: str) -> str:
    code = "".join(random.choices(string.digits, k=6))
    _otp_store[key] = (code, datetime.utcnow() + timedelta(minutes=OTP_TTL_MIN))
    return code


def verify_otp(key: str, code: str) -> bool:
    stored = _otp_store.get(key)
    if not stored:
        return False
    value, expires_at = stored
    if datetime.utcnow() > expires_at:
        _otp_store.pop(key, None)
        return False
    if value != code:
        return False
    _otp_store.pop(key, None)
    return True

