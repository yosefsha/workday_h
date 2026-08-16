"""The command line entry point.

`ingest` calls the same IngestService object the HTTP layer does, in-process.
The CLI is not an HTTP client: it has to work when the API container is down,
which is exactly when you reach for it.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from sqlalchemy.exc import OperationalError

from app.config import settings
from app.render.json_report import render_json
from app.render.text_report import render_text
from app.sources.protocols import SourceUnavailableError
from app.wiring import build_ingest_service, build_repository

logger = logging.getLogger(__name__)

NO_SNAPSHOT = "no ingest run has succeeded yet; run `python -m app ingest` first"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="python -m app", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("ingest", help="read both feeds and store a new snapshot")

    report = subcommands.add_parser("report", help="print the latest snapshot")
    report.add_argument(
        "--json", action="store_true", help="emit structured JSON instead of readable text"
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "ingest":
            return _ingest()
        return _report(as_json=args.json)
    except OperationalError as error:
        # An unreachable database is an operator's problem, not a bug. Say so
        # in one line rather than making them read a stack trace to find out
        # the port was wrong.
        print(f"database unavailable: {_first_line(error)}", file=sys.stderr)
        print(f"tried {settings.database_url}", file=sys.stderr)
        return 1


def _first_line(error: Exception) -> str:
    return str(error).strip().splitlines()[0]


def _ingest() -> int:
    try:
        result = build_ingest_service().run()
    except SourceUnavailableError as error:
        # The candidate source is the report. Without it there is nothing to
        # say, so this is a failure rather than an empty snapshot. A required
        # enrichment failing lands here too.
        print(f"ingest failed: {error}", file=sys.stderr)
        return 1

    for status in result.statuses:
        if not status.ok:
            print(f"warning: source {status.name!r} unavailable, omitted", file=sys.stderr)

    print(f"stored run {result.run_id}: {result.candidate_count} candidates")
    for status in result.statuses:
        detail = "unavailable" if not status.ok else _matched_label(status.matched)
        print(f"  {status.name}: {detail}")
    return 0


def _matched_label(matched: int | None) -> str:
    return "ok" if matched is None else f"matched {matched}"


def _report(*, as_json: bool) -> int:
    repository = build_repository()
    if repository.latest_successful_run_id() is None:
        print(NO_SNAPSHOT, file=sys.stderr)
        return 1

    candidates = repository.latest_candidates()

    if as_json:
        models = render_json(candidates, gap_threshold_days=settings.gap_threshold_days)
        payload = [model.model_dump(by_alias=True) for model in models]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(candidates, gap_threshold_days=settings.gap_threshold_days), end="")

    return 0
