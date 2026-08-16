# Persist ingest snapshots; derive gaps on read

Supersedes the "no database" half of [ADR-0001](./0001-stateless-single-service.md).

The two upstream feeds are unversioned, mutable URLs: they can change without
notice and neither records that they did. What this application owns, and no
upstream holds, is what the feeds said at a given moment — so we persist each
ingest as a snapshot of normalized `candidate` and `employment` rows tied to an
`ingest_run`. Ingest writes; the API and CLI read only from the database and
never call the upstreams, which means the service serves correctly while both
feeds are down instead of returning 502.

Employment gaps are **not** stored. They are computed from the persisted dates
whenever a report is rendered, so `GAP_THRESHOLD_DAYS` stays a live policy knob
— raising it to 90 re-evaluates every historical snapshot rather than only
future ingests. Dates are stored as `DATE`, not as the `Jan/01/2008` wire
string, so `Sep/5/2016` and `Sep/05/2016` land on the same row and gap queries
are queries rather than a full re-parse.

Recorded because the volume involved — four candidates, 57 KB — makes a
database look like over-engineering at a glance. The justification is upstream
independence and history, not scale, and the next reader should not have to
guess which.
