# Single service, no SPA

> **Amended.** The "no database" part of this decision was reversed by
> [ADR-0002](./0002-ingest-snapshots-derive-gaps.md): ingest snapshots are
> persisted to Postgres. The single-service shape and the removal of the
> frontend, Redis and the SPA build still stand.

`docs/coding-instructions.md` describes a two-service repository with Postgres,
Redis, alembic migrations and a React frontend, and the original `ci.yml`
enforced all of it. This application fetches two static upstream endpoints,
joins them and renders the result; it owns no state anyone can write to, so a
database would store nothing the upstream doesn't already hold, and a cache
would be an optimisation for a load we don't have. The frontend is not part of
the exercise at all.

We therefore ship one service — a domain core with a CLI and a thin FastAPI
layer over it — and removed the `frontend` job, the Postgres and Redis service
containers, and the `alembic upgrade head` step from CI.

Recorded because the coding instructions say the opposite, and unused
scaffolding that is present but dead is harder to explain than infrastructure
that was never added. If the application later acquires state it owns — stored
candidate annotations, ingest history, anything written rather than derived —
this decision is the one to revisit.
