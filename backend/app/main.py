"""The FastAPI application."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import register_ingest_route, router
from app.config import settings
from app.sources.protocols import SourceUnavailableError
from app.wiring import build_ingest_service, build_repository

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Fill an empty database on first boot, and never again.

    A fresh `docker compose up` should produce a working service without a
    hidden setup step. Once a snapshot exists, startup does not touch the
    network — which is the point of storing it: a restart during an upstream
    outage still serves the data we already have.
    """
    if settings.ingest_on_startup_when_empty:
        try:
            if build_repository().latest_successful_run_id() is None:
                logger.info("no snapshot found, running initial ingest")
                build_ingest_service().run()
        except SourceUnavailableError as error:
            # Deliberately not fatal. Starting and reporting 503 per request is
            # more useful than a container that will not start.
            logger.error("initial ingest failed, service will report 503: %s", error)
        except Exception:
            logger.exception("initial ingest failed unexpectedly")

    yield


app = FastAPI(
    title="Candidate Résumé Reporting",
    description=(
        "Joins a résumé feed with supplemental LinkedIn data and reports each "
        "candidate's employment history, including significant gaps."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
register_ingest_route(app.router)
