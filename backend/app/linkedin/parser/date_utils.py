from __future__ import annotations

from typing import Any, Optional

_MONTHS = (
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def format_date(date_obj: Any) -> Optional[str]:
    """Format a LinkedIn `{"month": int, "year": int}` date object as "Mon YYYY"."""
    if not isinstance(date_obj, dict):
        return None
    year = date_obj.get("year")
    month = date_obj.get("month")
    if not year:
        return None
    if month and 1 <= month <= 12:
        return f"{_MONTHS[month]} {year}"
    return str(year)


def format_time_period(time_period: Any) -> tuple[Optional[str], Optional[str]]:
    """Return (start_date, end_date) display strings from a `timePeriod` object.

    A missing `endDate` means the position/education is current/ongoing.
    """
    if not isinstance(time_period, dict):
        return None, None
    start = format_date(time_period.get("startDate"))
    end = format_date(time_period.get("endDate"))
    return start, end


def compute_duration(start_date: Optional[str], end_date: Optional[str]) -> Optional[str]:
    """Best-effort human-readable duration; returns None if dates are unparseable."""
    if not start_date:
        return None
    return f"{start_date} - {end_date or 'Present'}"
