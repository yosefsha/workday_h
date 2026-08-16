"""Ordering employments and deriving the gaps between them.

Gaps are never stored. They are computed here every time a report is rendered,
so the threshold stays a live policy knob — see docs/adr/0002.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.domain.candidate import Employment

# Sorts unparseable dates to the end rather than crashing on a None comparison.
_EPOCH = date.min


@dataclass(frozen=True)
class HistoryEntry:
    """One employment, plus the gap that preceded it if there was one.

    The gap belongs to the *later* job — it describes how long the candidate
    was out of work before starting this role — matching the example output.
    """

    employment: Employment
    gap_days: int | None = None


@dataclass(frozen=True)
class EmploymentHistory:
    entries: tuple[HistoryEntry, ...]
    gaps_reportable: bool

    @property
    def is_empty(self) -> bool:
        return not self.entries


def _sort_key(employment: Employment) -> tuple[date, date]:
    return (employment.start_date or _EPOCH, employment.end_date or _EPOCH)


def build_history(employments: tuple[Employment, ...], threshold_days: int) -> EmploymentHistory:
    """Order employments newest-first and attach significant gaps.

    Employments are sorted here rather than trusted in feed order: the upstream
    is not reliably sorted (one candidate lists a 2002 role before a 2003 one).

    Gaps are computed between consecutive entries in that order. This is exact
    for a candidate who held one job at a time; where two roles genuinely
    overlap, a concurrent role can leave an apparent gap that the overlapping
    job actually covered. Detecting that needs a merged coverage timeline,
    which was considered and deliberately not built.

    When any employment is missing a date we cannot see the whole timeline, so
    no gap is reported at all for that candidate. Reporting a gap we cannot
    vouch for is worse than reporting none.
    """
    if not employments:
        return EmploymentHistory(entries=(), gaps_reportable=True)

    ordered = sorted(employments, key=_sort_key, reverse=True)
    reportable = all(e.is_datable for e in ordered)

    entries: list[HistoryEntry] = []
    for index, employment in enumerate(ordered):
        gap_days: int | None = None
        if reportable and index + 1 < len(ordered):
            previous = ordered[index + 1]
            gap_days = _gap_between(previous, employment, threshold_days)
        entries.append(HistoryEntry(employment=employment, gap_days=gap_days))

    return EmploymentHistory(entries=tuple(entries), gaps_reportable=reportable)


def _gap_between(previous: Employment, later: Employment, threshold_days: int) -> int | None:
    """Days between one job ending and the next beginning, if significant.

    Plain subtraction, which is what the specification's worked example uses:
    Dec/31/2012 to Jan/20/2013 is reported there as 20 days. Overlapping and
    same-day handovers give zero or negative values and are never gaps.
    """
    if previous.end_date is None or later.start_date is None:
        return None
    delta = (later.start_date - previous.end_date).days
    return delta if delta > threshold_days else None
