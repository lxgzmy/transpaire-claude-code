#!/usr/bin/env python3
"""Business-day arithmetic for the weekly BA report ageing (PO-11).

Business days = Monday to Friday excluding NSW public holidays and the
Christmas shutdown (SHUTDOWNS). The pilot is
NSW-first (role CLAUDE.md), so NSW is the only calendar carried; add a QLD set
when QLD jobs join. Weekend-fall holidays that NSW does not substitute (Anzac
Day) are listed anyway for completeness — they never affect the count.

Verify each new year against the NSW Government's published list before the
first Monday run of that year.

Also turns OSC's UTC timestamps into Sydney calendar dates (``sydney_date``):
a document dragged in at 08:30 on a Monday in Sydney is stamped Sunday
evening in UTC.
"""
from datetime import date, datetime, timedelta, timezone

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


LAST_YEAR = max(d.year for d in NSW_PUBLIC_HOLIDAYS)

# The Christmas shutdown, left out of the count (PO-11d: the industry is all but closed then). One pair
# per break in the officer's own words, (last business day, the day work resumes); the days between are
# closed. Every run from 1 December to 31 January says so while that break's pair is missing.
SHUTDOWNS = [
    (date(2026, 12, 23), date(2027, 1, 11)),  # 2026-27, the officer, 5 November 2026
]


def covers(value):
    """True while the holiday table reaches the year of ``value``; past it, counts would miss holidays."""
    return _to_date(value).year <= LAST_YEAR


def reopens(value):
    """The day work resumes, when ``value`` falls in a Christmas shutdown; else None."""
    d = _to_date(value)
    return next((back for last_open, back in SHUTDOWNS if last_open < d < back), None)


def in_shutdown(value):
    return reopens(value) is not None


def shutdown_missing(value):
    """The break (e.g. "2026-27") whose shutdown dates are not set, while ``value`` falls between 1 December
    and 31 January; else None."""
    d = _to_date(value)
    if d.month not in (12, 1):
        return None
    year = d.year if d.month == 12 else d.year - 1
    if in_shutdown(date(year, 12, 29)):  # inside any Christmas shutdown
        return None
    return f"{year}-{str(year + 1)[2:]}"


def calendar_upkeep(value):
    """What a person must add before the calendar goes wrong, as of ``value``: [] when nothing.

    From 1 November the table must hold next year's public holidays and that Christmas's shutdown
    dates; until the break is over, its dates. The weekly run only says so in its own log, which
    nobody reads on a scheduled Monday, so the status check (ba_weekly_status.ps1) asks for these."""
    d = _to_date(value)
    need = d.year + 1 if d.month >= 11 else d.year
    out = []
    if LAST_YEAR < need:
        out.append(f"nsw_holidays.py has no NSW public holidays for {need}: add them from the NSW Government's "
                   "published list")
    unset = shutdown_missing(date(d.year, 12, 1) if d.month == 11 else d)
    if unset:
        out.append(f"the {unset} Christmas shutdown dates are not set: ask the officer, then add them to "
                   "SHUTDOWNS in nsw_holidays.py")
    return out


def _to_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def sydney_date(value):
    """The Sydney calendar date (ISO) of an OSC timestamp; a plain date is returned as it is.

    No time-zone database is needed (the server's Python has none): NSW daylight
    saving runs from the first Sunday in October to the first Sunday in April,
    both changes at 16:00 UTC on the Saturday before. OSC activity completion
    dates are stored at midnight UTC, which stays the same date.
    """
    text = str(value or "").strip()
    if len(text) <= 10:
        return text
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:10]
    moment = (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)

    def change(month):
        first = datetime(moment.year, month, 1, tzinfo=timezone.utc)
        return first + timedelta(days=(6 - first.weekday()) % 7) - timedelta(hours=8)

    summer = moment >= change(10) or moment < change(4)
    return (moment + timedelta(hours=11 if summer else 10)).date().isoformat()


def is_business_day(d, holidays=NSW_PUBLIC_HOLIDAYS):
    d = _to_date(d)
    return d.weekday() < 5 and d not in holidays and not in_shutdown(d)


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
    if len(sys.argv) in (2, 3) and sys.argv[1] == "--upkeep":
        # One line per thing to add and exit 3; nothing and exit 0 when the calendar is in hand. Not 1,
        # which is Python's own exit on an error.
        todo = calendar_upkeep(sys.argv[2] if len(sys.argv) == 3 else date.today())
        print("\n".join(todo))
        sys.exit(3 if todo else 0)
    if len(sys.argv) != 3:
        print("usage: nsw_holidays.py START END   (ISO dates) -> business days\n"
              "       nsw_holidays.py --upkeep [DATE]  -> what to add to the calendar, exit 3 when anything")
        sys.exit(2)
    print(business_days(sys.argv[1], sys.argv[2]))
