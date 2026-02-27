from datetime import datetime

from api.services.pickup_scheduler import BUSINESS_HOURS, compute_pickup_slots


def test_after_hours_next_day_slots():
    # 9 PM today, after cutoff
    now = datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)
    slots = compute_pickup_slots(now)
    assert slots
    first_slot = slots[0]
    assert first_slot.start.date() > now.date()
    assert first_slot.start.hour == BUSINESS_HOURS["start"].hour

