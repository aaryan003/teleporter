"""Tests for the OTP service (mocked Redis)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_otp_format():
    """Generated OTP should be a 6-digit string."""
    with patch("services.otp.get_redis") as mock_get_redis:
        mock_conn = AsyncMock()
        mock_get_redis.return_value = mock_conn
        
        from services.otp import generate_otp
        code = await generate_otp("test-order-id", "pickup")
        assert len(code) == 6
        assert code.isdigit()


@pytest.mark.asyncio
async def test_otp_stored_in_redis():
    """OTP hash should be stored via Redis hset with TTL."""
    with patch("services.otp.get_redis") as mock_get_redis:
        mock_conn = AsyncMock()
        mock_get_redis.return_value = mock_conn
        
        from services.otp import generate_otp
        await generate_otp("test-order-id", "pickup")

        # verify hset and expire were called
        mock_conn.hset.assert_called_once()
        mock_conn.expire.assert_called_once()


@pytest.mark.asyncio
async def test_otp_verify_success():
    """Correct OTP should verify successfully."""
    import bcrypt
    from services.otp import verify_otp

    test_otp = "123456"
    otp_hash = bcrypt.hashpw(test_otp.encode(), bcrypt.gensalt()).decode()

    with patch("services.otp.get_redis") as mock_get_redis:
        mock_conn = AsyncMock()
        mock_get_redis.return_value = mock_conn
        
        # mock returned data
        mock_conn.hgetall.return_value = {"hash": otp_hash, "attempts": "0"}
        
        result = await verify_otp("test-order-id", "pickup", test_otp)
        assert result["valid"] is True
        mock_conn.delete.assert_called_once()


@pytest.mark.asyncio
async def test_otp_verify_wrong_code():
    """Wrong OTP should fail verification."""
    import bcrypt
    from services.otp import verify_otp

    correct_otp = "123456"
    otp_hash = bcrypt.hashpw(correct_otp.encode(), bcrypt.gensalt()).decode()

    with patch("services.otp.get_redis") as mock_get_redis:
        mock_conn = AsyncMock()
        mock_get_redis.return_value = mock_conn
        
        mock_conn.hgetall.return_value = {"hash": otp_hash, "attempts": "1"}
        
        result = await verify_otp("test-order-id", "pickup", "000000")
        assert result["valid"] is False
        assert "Incorrect OTP" in result["error"]
        assert result["remaining"] == 0
