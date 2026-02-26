"""Unit tests for date utility functions — no DB required."""

from datetime import date

from app.utils.date_helpers import dates_overlap, night_count


def test_night_count_basic():
    assert night_count(date(2026, 3, 1), date(2026, 3, 5)) == 4


def test_night_count_same_day():
    assert night_count(date(2026, 3, 1), date(2026, 3, 1)) == 0


def test_night_count_never_negative():
    assert night_count(date(2026, 3, 5), date(2026, 3, 1)) == 0


def test_dates_overlap_true():
    assert dates_overlap(date(2026, 3, 1), date(2026, 3, 5), date(2026, 3, 3), date(2026, 3, 7))


def test_dates_overlap_adjacent_no_overlap():
    # Check-out on day 5, next check-in on day 5 — should NOT overlap
    assert not dates_overlap(date(2026, 3, 1), date(2026, 3, 5), date(2026, 3, 5), date(2026, 3, 8))


def test_dates_overlap_contained():
    assert dates_overlap(date(2026, 3, 1), date(2026, 3, 10), date(2026, 3, 3), date(2026, 3, 6))


def test_dates_no_overlap():
    assert not dates_overlap(date(2026, 3, 1), date(2026, 3, 5), date(2026, 3, 6), date(2026, 3, 9))
