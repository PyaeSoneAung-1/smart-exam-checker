"""Time helpers.

All timestamps in this project are stored as naive UTC datetimes (SQLite has no
timezone support). ``datetime.utcnow()`` is deprecated as of Python 3.12, so use
:func:`utcnow` instead — it returns the same value without the deprecation
warning.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite-friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
