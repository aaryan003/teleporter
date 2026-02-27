"""Tests for the pickup scheduler."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from datetime import datetime, time, date
from services.pickup_scheduler import (
    get_available_slots, get_scheduling_message, determine_time_factor,
)


def _mock_riders(count=3):
    """Create mock rider schedules."""
    return [
        {"shift_start": time(8, 0), "shift_end": time(20, 0), "max_pickups_per_hour": 3}
        for _ in range(count)
    ]


def test_available_slots_during_business_hours():
    """Should return slots within business hours."""
    now = datetime(2026, 2, 27, 10, 0)  # 10 AM
    slots = get_available_slots(now, _mock_riders(), {})
    assert len(slots) > 0
    for slot in slots:
        assert 8 <= slot.start.hour < 20


def test_no_slots_after_cutoff():
    """After 6:30 PM, no today slots should be available."""
    now = datetime(2026, 2, 27, 18, 31)  # 6:31 PM
    slots = get_available_slots(now, _mock_riders(), {}, days_ahead=0)
    today_slots = [s for s in slots if s.start.date() == now.date()]
    assert len(today_slots) == 0


def test_next_day_slots_after_cutoff():
    """After cutoff, next-day slots should still be available."""
    now = datetime(2026, 2, 27, 19, 0)  # 7 PM
    slots = get_available_slots(now, _mock_riders(), {}, days_ahead=1)
    # Should have tomorrow slots
    tomorrow = date(2026, 2, 28)
    tomorrow_slots = [s for s in slots if s.start.date() == tomorrow]
    assert len(tomorrow_slots) > 0


def test_capacity_limiting():
    """Full slots should be excluded."""
    now = datetime(2026, 2, 27, 10, 0)
    # 3 riders × 3 pickups/hr = 9 capacity; book 9 for 11 AM
    scheduled = {11: 9}
    slots = get_available_slots(now, _mock_riders(), scheduled)
    slot_11 = [s for s in slots if s.start.hour == 11 and s.start.date() == now.date()]
    assert len(slot_11) == 0  # Should be fully booked


def test_30min_buffer():
    """Slots within 30 minutes of now should be excluded."""
    now = datetime(2026, 2, 27, 10, 45)  # 10:45 AM
    slots = get_available_slots(now, _mock_riders(), {})
    for slot in slots:
        assert slot.start >= datetime(2026, 2, 27, 11, 15)  # At least 30 min later


def test_scheduling_message_open():
    """During business hours with slots, should show availability."""
    now = datetime(2026, 2, 27, 10, 0)
    slots = get_available_slots(now, _mock_riders(), {})
    msg = get_scheduling_message(now, slots)
    assert "available" in msg.lower()


def test_scheduling_message_closed():
    """After business hours, should show closed message."""
    now = datetime(2026, 2, 27, 21, 0)  # 9 PM
    msg = get_scheduling_message(now, [])
    assert "closed" in msg.lower()


def test_time_factor_express():
    """Express should return EXPRESS."""
    now = datetime(2026, 2, 27, 10, 0)
    slot = datetime(2026, 2, 27, 12, 0)
    assert determine_time_factor(True, slot, now) == "EXPRESS"


def test_time_factor_next_day():
    """Tomorrow pickup should return NEXT_DAY."""
    now = datetime(2026, 2, 27, 10, 0)
    slot = datetime(2026, 2, 28, 9, 0)
    assert determine_time_factor(False, slot, now) == "NEXT_DAY"


def test_time_factor_same_day():
    """Same-day within 4 hours should return SAME_DAY."""
    now = datetime(2026, 2, 27, 10, 0)
    slot = datetime(2026, 2, 27, 12, 0)  # 2 hours away
    assert determine_time_factor(False, slot, now) == "SAME_DAY"


def test_time_factor_standard():
    """Same-day beyond 4 hours should return STANDARD."""
    now = datetime(2026, 2, 27, 8, 0)
    slot = datetime(2026, 2, 27, 14, 0)  # 6 hours away
    assert determine_time_factor(False, slot, now) == "STANDARD"
