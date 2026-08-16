"""HTTP routes. Thin — every handler delegates and formats."""

from __future__ import annotations

import logging
import secrets

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import OperationalError

from app.config import settings
from app.domain.candidate import Candidate
from app.models import CandidateModel
from app.render.json_report import render_json
from app.render.text_report import render_text
from app.sources.protocols import SourceStatus, SourceUnavailableError
from app.wiring import (
    build_candidate_source,
    build_enrichments,
    build_ingest_service,
    build_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter()

NO_SNAPSHOT = "no ingest run has succeeded yet; run `python -m app ingest`"


def _latest_candidates() -> list[Candidate]:
    """The most recent successful snapshot, or a 503 explaining its absence.

    An empty database and a genuinely empty feed are different situations, and
    a caller that cannot tell them apart will misread one as the other.
    """
    repository = build_repository()
    try:
        if repository.latest_successful_run_id() is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, NO_SNAPSHOT)
        return repository.latest_candidates()
    except OperationalError as error:
        # The store being unreachable is an outage, not a request error. 503
        # says "try again", which is true, where a 500 says "we are broken".
        logger.error("database unavailable: %s", error)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable"
        ) from error


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sources")
def sources() -> dict[str, object]:
    """The registered sources, and what each did in the latest snapshot.

    Walks the registry in app/wiring.py rather than a hardcoded list, so a
    newly registered source appears here without touching this handler.

    `registered` is what the running process is configured to read;
    `latest_run` is what actually happened last time. They differ whenever a
    source has been added since the last ingest, which is exactly the state
    worth being able to see.
    """
    candidate_source = build_candidate_source()
    registered = [
        {"name": candidate_source.name, "kind": "candidate", "required": True},
        *(
            {"name": source.name, "kind": "enrichment", "required": source.required}
            for source in build_enrichments()
        ),
    ]

    try:
        statuses = build_repository().latest_source_statuses()
    except OperationalError as error:
        logger.error("database unavailable: %s", error)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "database unavailable"
        ) from error

    return {
        "registered": registered,
        "latest_run": [_status_payload(s) for s in statuses],
    }


def _status_payload(source_status: SourceStatus) -> dict[str, object]:
    return {
        "name": source_status.name,
        "ok": source_status.ok,
        "matched": source_status.matched,
        "detail": source_status.detail,
    }


@router.get("/candidates", response_model=list[CandidateModel])
def candidates_json() -> list[CandidateModel]:
    return render_json(_latest_candidates(), gap_threshold_days=settings.gap_threshold_days)


@router.get("/candidates.txt", response_class=PlainTextResponse)
def candidates_text() -> str:
    return render_text(_latest_candidates(), gap_threshold_days=settings.gap_threshold_days)


def register_ingest_route(app_router: APIRouter) -> None:
    """Register POST /ingest, but only when a token is configured.

    An unauthenticated write endpoint on a read-only service is an invitation
    to make us hammer someone else's server. With no INGEST_TOKEN set the route
    does not exist at all, so it cannot be left accidentally open and there is
    no placeholder secret to forget about.
    """
    if not settings.ingest_token:
        logger.info("INGEST_TOKEN is unset; POST /ingest not registered")
        return

    @app_router.post("/ingest", status_code=status.HTTP_201_CREATED)
    def ingest(x_ingest_token: str = Header(default="")) -> dict[str, object]:
        if not secrets.compare_digest(x_ingest_token, settings.ingest_token or ""):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid ingest token")

        try:
            result = build_ingest_service().run()
        except SourceUnavailableError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error

        return {
            "run_id": result.run_id,
            "candidates": result.candidate_count,
            "sources": [_status_payload(s) for s in result.statuses],
        }
