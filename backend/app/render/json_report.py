"""The structured report."""

from __future__ import annotations

from app.domain.candidate import Candidate
from app.domain.history import build_history
from app.models import CandidateModel, JobExperienceModel, NameModel
from app.render.formatting import format_date, format_gap


def render_json(candidates: list[Candidate], *, gap_threshold_days: int) -> list[CandidateModel]:
    return [_render_candidate(person, gap_threshold_days) for person in candidates]


def _render_candidate(person: Candidate, gap_threshold_days: int) -> CandidateModel:
    history = build_history(person.employments, gap_threshold_days)

    jobs = [
        JobExperienceModel(
            role=entry.employment.role,
            start_date=format_date(entry.employment.start_date),
            # An ongoing role has no end date to state. Null is the structured
            # equivalent of the text format's "Present".
            end_date=format_date(entry.employment.end_date),
            location=entry.employment.location,
            gap=format_gap(entry.gap_days) if entry.gap_days is not None else None,
        )
        for entry in history.entries
    ]

    return CandidateModel(
        name=NameModel(
            first_name=person.name.given_name,
            last_name=person.name.family_name,
        ),
        linkedin_url=person.linkedin_url,
        job_experience=jobs,
    )
