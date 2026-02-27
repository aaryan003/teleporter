"""
Pickup Scheduler — Smart slot management with business hours rules.

Rules:
  - Business hours: 8 AM to 8 PM
  - 90-minute cutoff before closing (no new slots after 6:30 PM)
  - After cutoff: only next-day slots shown
  - Slots are capacity-gated: only shows slots with available riders
  - Express: available before 4 PM, otherwise "first thing tomorrow"
"""

from __future__ import annotations
from datetime import datetime, date, time, timedelta
from dataclasses import dataclass

from config import settings


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    available_capacity: int


SLOT_DURATION_MIN = 60


def _combine_dt(d: date, t: time) -> datetime:
    """Combine date and time into datetime."""
    return datetime.combine(d, t)


def _is_within_business_hours(dt: datetime) -> bool:
    """Check if a datetime is within business hours."""
    return (
        time(settings.BUSINESS_HOURS_START, 0) <= dt.time()
        < time(settings.BUSINESS_HOURS_END, 0)
    )


def get_available_slots(
    now: datetime,
    rider_schedules: list[dict],
    scheduled_pickups: dict[int, int],  # {hour: booked_count}
    days_ahead: int = 2,
) -> list[TimeSlot]:
    """
    Get available pickup slots based on current time, rider availability, and bookings.

    Args:
        now: Current datetime
        rider_schedules: List of {"shift_start": time, "shift_end": time, "max_pickups_per_hour": int}
        scheduled_pickups: Already-booked pickups per hour slot {hour: count}
        days_ahead: How many days to show slots for (default 2)

    Returns:
        List of available TimeSlot objects
    """
    cutoff_time = time(
        settings.BUSINESS_HOURS_END - (settings.CUTOFF_BUFFER_MIN // 60),
        settings.CUTOFF_BUFFER_MIN % 60,
    )

    slots: list[TimeSlot] = []
    today = now.date()

    for day_offset in range(days_ahead + 1):
        current_date = today + timedelta(days=day_offset)
        start_hour = settings.BUSINESS_HOURS_START
        end_hour = settings.BUSINESS_HOURS_END

        for hour in range(start_hour, end_hour):
            slot_start = _combine_dt(current_date, time(hour, 0))
            slot_end = _combine_dt(current_date, time(hour + 1, 0)) if hour + 1 < 24 else _combine_dt(
                current_date + timedelta(days=1), time(0, 0)
            )

            # Skip past slots
            if slot_start < now:
                continue

            # Skip if today and past cutoff
            if current_date == today and now.time() >= cutoff_time:
                continue

            # Skip slots too close to now (need at least 30 min buffer)
            if slot_start < now + timedelta(minutes=30):
                continue

            # Calculate capacity for this slot
            capacity = _calculate_slot_capacity(hour, rider_schedules)
            booked = scheduled_pickups.get(hour, 0)
            available = max(capacity - booked, 0)

            if available > 0:
                slots.append(TimeSlot(
                    start=slot_start,
                    end=slot_end,
                    available_capacity=available,
                ))

    return slots


def _calculate_slot_capacity(hour: int, rider_schedules: list[dict]) -> int:
    """Calculate total pickup capacity for a given hour based on rider shifts."""
    capacity = 0
    slot_time = time(hour, 0)

    for rider in rider_schedules:
        if rider["shift_start"] <= slot_time < rider["shift_end"]:
            capacity += rider.get("max_pickups_per_hour", 3)

    return capacity


def get_scheduling_message(now: datetime, slots: list[TimeSlot]) -> str:
    """
    Generate user-friendly scheduling message for the bot.

    Returns:
        Message string explaining slot availability
    """
    cutoff_time = time(
        settings.BUSINESS_HOURS_END - (settings.CUTOFF_BUFFER_MIN // 60),
        settings.CUTOFF_BUFFER_MIN % 60,
    )

    if now.time() >= time(settings.BUSINESS_HOURS_END, 0):
        return (
            "🌙 We're closed for today.\n"
            f"📅 Next available pickup: Tomorrow {settings.BUSINESS_HOURS_START}:00 AM"
        )

    if now.time() >= cutoff_time:
        if slots:
            first_slot = slots[0]
            return (
                f"⏰ Today's pickup slots are closed.\n"
                f"📅 Next available: {first_slot.start.strftime('%b %d, %I:%M %p')}"
            )
        return "⏰ No pickup slots available today. Please try again tomorrow."

    if not slots:
        return (
            "😔 No pickup slots available right now. "
            "All our riders are fully booked. Please try again later."
        )

    today_slots = [s for s in slots if s.start.date() == now.date()]
    if today_slots:
        return f"✅ {len(today_slots)} pickup slots available today!"

    return f"📅 Next available pickup: {slots[0].start.strftime('%b %d, %I:%M %p')}"


def determine_time_factor(is_express: bool, pickup_slot: datetime, now: datetime) -> str:
    """
    Determine pricing time factor based on pickup type and timing.

    Returns:
        Time factor key: NEXT_DAY, STANDARD, SAME_DAY, or EXPRESS
    """
    if is_express:
        return "EXPRESS"

    if pickup_slot.date() > now.date():
        return "NEXT_DAY"

    hours_until = (pickup_slot - now).total_seconds() / 3600
    if hours_until <= 4:
        return "SAME_DAY"

    return "STANDARD"
