"""Shared rendering primitives, so the two formats cannot drift apart."""

from __future__ import annotations

from datetime import date

from app.domain.candidate import DATE_FORMAT

PRESENT = "Present"


def format_date(value: date | None) -> str | None:
    """`Jan/01/2008`, always zero-padded.

    Dates are stored as DATE, so the feed's inconsistent `Sep/5/2016` is
    normalised to `Sep/05/2016` on the way out without any special case here.
    """
    return value.strftime(DATE_FORMAT) if value else None


def format_gap(days: int) -> str:
    return f"{days} day" if days == 1 else f"{days} days"
