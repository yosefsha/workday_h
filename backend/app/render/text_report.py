"""The human-readable report.

Absence is always stated rather than left blank: a reader can tell "this
candidate has no LinkedIn profile" from "the renderer dropped a line".
"""

from __future__ import annotations

from app.domain.candidate import Candidate, Employment
from app.domain.history import build_history
from app.render.formatting import PRESENT, format_date, format_gap

NO_LINKEDIN = "LinkedIn: not available"
NO_HISTORY = "No employment history on record."
GAPS_UNAVAILABLE = "Gap reporting unavailable — incomplete dates in this history."

MISSING_ROLE = "role not available"
MISSING_START = "start date missing"
MISSING_END = "end date missing"
MISSING_LOCATION = "location not available"


def render_text(candidates: list[Candidate], *, gap_threshold_days: int) -> str:
    blocks = [_render_candidate(person, gap_threshold_days) for person in candidates]
    return "\n\n".join(blocks) + "\n" if blocks else ""


def _render_candidate(person: Candidate, gap_threshold_days: int) -> str:
    lines = [f"Hello {person.name.display},"]

    if person.linkedin_url:
        lines.append(f"LinkedIn: {person.linkedin_url}")
    else:
        lines.append(NO_LINKEDIN)

    history = build_history(person.employments, gap_threshold_days)

    if history.is_empty:
        lines.append(NO_HISTORY)
        return "\n".join(lines)

    if not history.gaps_reportable:
        lines.append(GAPS_UNAVAILABLE)

    for entry in history.entries:
        lines.append(_render_employment(entry.employment))
        # The gap belongs to the job above it and describes the time before
        # that job started, so the line sits between the two roles it separates.
        if entry.gap_days is not None:
            lines.append(f"Gap in CV for {format_gap(entry.gap_days)}")

    return "\n".join(lines)


def _render_employment(job: Employment) -> str:
    role = job.role or MISSING_ROLE
    start = format_date(job.start_date) or MISSING_START
    end = format_date(job.end_date) or (PRESENT if job.is_current else MISSING_END)
    location = job.location or MISSING_LOCATION
    return f"Worked as: {role}, From {start} To {end} in {location}"
