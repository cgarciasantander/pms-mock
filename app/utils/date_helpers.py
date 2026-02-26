from datetime import date


def night_count(check_in: date, check_out: date) -> int:
    """Return the number of nights between check-in and check-out."""
    delta = check_out - check_in
    return max(delta.days, 0)


def dates_overlap(
    start1: date, end1: date, start2: date, end2: date
) -> bool:
    """Return True if two date ranges overlap (exclusive end dates, hotel convention)."""
    return start1 < end2 and start2 < end1
