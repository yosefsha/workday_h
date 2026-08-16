# Data sources are protocols, registered in one place

The ingest pipeline originally named its two feeds directly: fetch the résumé
JSON, fetch the LinkedIn CSV, join them. Adding a third source — another
enrichment feed, an internal database, a vendor API — meant editing the
pipeline, the result type, the store schema and both entry points.

Sources now implement one of two protocols in `app/sources/protocols.py`.
A **CandidateSource** produces candidates and there is exactly one; an
**EnrichmentSource** adds to candidates that already exist and there may be any
number. `IngestService` loops over whatever it is handed and names no feed.
Adding a source is a class in `app/sources/` plus a line in
`app/wiring.py:build_enrichments()`.

Two protocols rather than one, because the two roles genuinely differ: without
the candidate source there is no report, whereas an enrichment contributes an
optional field. That asymmetry is expressed as `EnrichmentSource.required`
— a property of the source, not a branch in the pipeline — so making a source
mandatory is a change to that source alone.

`Enrichment.apply()` takes the whole candidate list rather than one candidate,
so an implementation backed by a database or an API can do a single bulk
lookup instead of N round trips.

Consequently the per-feed columns `ingest_run.resume_feed_ok` and
`linkedin_feed_ok` were replaced by an `ingest_source_status` row per source
per run (migration 0002). A schema that names sources would need a migration
every time one is registered, which defeats the point. Those rows are also what
distinguishes "the source ran and matched nobody" from "the source was
unreachable" — a distinction a NULL `linkedin_url` cannot carry alone, and one
`GET /sources` exposes.
