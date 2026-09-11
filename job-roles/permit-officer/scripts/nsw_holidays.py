#!/usr/bin/env python3
"""Business-day arithmetic for the weekly BA report ageing (PO-11).

Business days = Monday to Friday excluding NSW public holidays. The pilot is
NSW-first (role CLAUDE.md), so NSW is the only calendar carried; add a QLD set
when QLD jobs join. Weekend-fall holidays that NSW does not substitute (Anzac
Day) are listed anyway for completeness — they never affect the count.

Verify each new year against the NSW Government's published list before the
first Monday run of that year.
"""
from datetime import date, timedelta

NSW_PUBLIC_HOLIDAYS = {
    # 2026
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 26),   # Australia Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 4),    # Easter Saturday
    date(2026, 4, 5),    # Easter Sunday
    date(2026, 4, 6),    # Easter Monday
    date(2026, 4, 25),   # Anzac Day (Saturday, no substitute in NSW)
    date(2026, 6, 8),    # King's Birthday
    date(2026, 10, 5),   # Labour Day
    date(2026, 12, 25),  # Christmas Day
    date(2026, 12, 26),  # Boxing Day (Saturday)
    date(2026, 12, 28),  # Boxing Day additional day
    # 2027
    date(2027, 1, 1),    # New Year's Day
    date(2027, 1, 26),   # Australia Day
    date(2027, 3, 26),   # Good Friday
    date(2027, 3, 27),   # Easter Saturday
    date(2027, 3, 28),   # Easter Sunday
    date(2027, 3, 29),   # Easter Monday
    date(2027, 4, 25),   # Anzac Day (Sunday, no substitute in NSW)
    date(2027, 6, 14),   # King's Birthday
    date(2027, 10, 4),   # Labour Day
    date(2027, 12, 25),  # Christmas Day (Saturday)
    date(2027, 12, 27),  # Christmas Day additional day
    date(2027, 12, 26),  # Boxing Day (Sunday)
    date(2027, 12, 28),  # Boxing Day additional day
}


def _to_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def is_business_day(d, holidays=NSW_PUBLIC_HOLIDAYS):
    d = _to_date(d)
    return d.weekday() < 5 and d not in holidays


def business_days(start, end, holidays=NSW_PUBLIC_HOLIDAYS):
    """Business days strictly after ``start`` up to and including ``end``.

    Same-day or end-before-start gives 0. An item handed over on a Monday and
    checked the following Monday reads 5 (no holidays in between).
    """
    start, end = _to_date(start), _to_date(end)
    if end <= start:
        return 0
    count = 0
    d = start + timedelta(days=1)
    while d <= end:
        if is_business_day(d, holidays):
            count += 1
        d += timedelta(days=1)
    return count


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: nsw_holidays.py START END   (ISO dates) -> business days")
        sys.exit(2)
    print(business_days(sys.argv[1], sys.argv[2]))
