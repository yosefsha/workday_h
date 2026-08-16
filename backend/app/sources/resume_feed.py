"""Parsing the résumé feed into domain candidates.

The upstream is a Sovren-shaped résumé export carrying far more than this
application reports — skills, education, the résumé as raw text. Everything not
named in the requirements is dropped here rather than carried through the
domain.

Two fields present in the feed are deliberately ignored:

- `duration_in_month` contradicts the dates it accompanies (a six-year role is
  labelled 11 months), so durations are derived from the dates instead.
- `last_job` is set inconsistently across candidates, and we establish ordering
  by sorting on dates anyway.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

from app.domain.candidate import DATE_FORMAT, Candidate, Employment, PersonName

logger = logging.getLogger(__name__)


class FeedFormatError(ValueError):
    """The feed body was not the document this parser expects."""


def parse_resume_feed(body: str) -> list[Candidate]:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise FeedFormatError(f"résumé feed is not valid JSON: {error}") from error

    if not isinstance(payload, list):
        raise FeedFormatError(f"résumé feed must be a JSON array, got {type(payload).__name__}")

    return [_candidate_from(record, index) for index, record in enumerate(payload)]


def _candidate_from(record: dict[str, Any], index: int) -> Candidate:
    contact = record.get("contact_info") or {}
    name = _name_from(contact.get("name") or contact.get("resume_name") or {})

    employments = tuple(
        _employment_from(entry, name.display or f"candidate #{index}")
        for entry in (record.get("experience") or [])
    )

    return Candidate(
        name=name,
        email=_clean(contact.get("email")),
        phone=_clean(contact.get("phone")),
        linkedin_url=None,  # Supplied by the LinkedIn feed, never by this one.
        employments=employments,
    )


def _name_from(raw: dict[str, Any]) -> PersonName:
    return PersonName(
        given_name=_clean(raw.get("given_name")),
        family_name=_clean(raw.get("family_name")),
        formatted_name=_clean(raw.get("formatted_name")),
    )


def _employment_from(entry: dict[str, Any], candidate_label: str) -> Employment:
    location = entry.get("location") or {}
    return Employment(
        role=_clean(entry.get("title")),
        start_date=_parse_date(entry.get("start_date"), candidate_label, "start_date"),
        end_date=_parse_date(entry.get("end_date"), candidate_label, "end_date"),
        location=_clean(location.get("short_display_address")),
        is_current=bool(entry.get("current_job")),
    )


def _parse_date(value: Any, candidate_label: str, field: str) -> date | None:
    """`Jan/01/2008`, and also `Sep/5/2016` — the feed does not zero-pad reliably.

    An unparseable date is not fatal. The employment is kept and rendered with
    the missing field named; it is the candidate's gap reporting that is
    suppressed, because the timeline now has a hole we know about.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        logger.warning("unparseable %s %r for %s", field, value, candidate_label)
        return None


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
