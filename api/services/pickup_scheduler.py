from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List


BUSINESS_HOURS = {
    "start": time(8, 0),
    "end": time(20, 0),
    "slot_duration": 60,
}

CUTOFF_BUFFER_MIN = 90


@dataclass
class TimeSlot:
    start: datetime
    capacity_remaining: int


def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def next_business_day(now: datetime) -> date:
    d = now.date()
    while True:
        d += timedelta(days=1)
        if not is_weekend(d):
            return d


def compute_pickup_slots(now: datetime, zone_capacity_per_hour: int = 10) -> List[TimeSlot]:
    """
    Compute available pickup slots from now onward for the current and next day.
    This is a simplified implementation; capacity is a single number per hour for the zone.
    """
    slots: list[TimeSlot] = []

    cutoff_today = datetime.combine(
        now.date(),
        (datetime.combine(now.date(), BUSINESS_HOURS["end"]) - timedelta(minutes=CUTOFF_BUFFER_MIN)).time(),
    )

    start_date = now.date()
    if now > cutoff_today:
        start_date = next_business_day(now)

    for day_offset in range(0, 2):
        d = start_date + timedelta(days=day_offset)
        if is_weekend(d):
            continue

        for hour in range(BUSINESS_HOURS["start"].hour, BUSINESS_HOURS["end"].hour):
            start_dt = datetime.combine(d, time(hour, 0))
            if start_dt <= now:
                continue
            slots.append(TimeSlot(start=start_dt, capacity_remaining=zone_capacity_per_hour))

    return slots

