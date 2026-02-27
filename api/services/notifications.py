from __future__ import annotations

import os
from typing import Any

import httpx


TELEGRAM_API_BASE = "https://api.telegram.org"


async def send_telegram_message(telegram_id: int, text: str, parse_mode: str | None = None) -> None:
    """
    Minimal sender using raw Telegram HTTP API.
    Used by the backend for simple notifications.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    params: dict[str, Any] = {
        "chat_id": telegram_id,
        "text": text,
    }
    if parse_mode:
        params["parse_mode"] = parse_mode

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage", data=params)

