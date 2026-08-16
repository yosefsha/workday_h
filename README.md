# Candidate Résumé Reporting

Joins a résumé feed with supplemental LinkedIn data and reports each
candidate's employment history — including significant gaps between jobs — as
readable text and as structured JSON.

## Run it

```bash
docker compose up --build
```

The API applies its migrations on start and, finding an empty database, runs
one ingest. Then:

```bash
curl localhost:8000/candidates       # structured JSON
curl localhost:8000/candidates.txt   # readable text
curl localhost:8000/sources          # registered sources + what each did last run
```

The CLI runs the same code in-process, against the same database, without the
API container. It runs from the repository root:

```bash
python -m app ingest          # read both feeds, store a snapshot
python -m app report          # readable text
python -m app report --json   # structured JSON
```

The virtualenv lives at the repository root, so VS Code activates it in every
new terminal. To build it on a fresh clone:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt ruff==0.16.2
```

`.vscode/settings.json` puts `backend/` on `PYTHONPATH`, which is what makes
`python -m app` work from the root. Outside VS Code, either export it —
`export PYTHONPATH=backend` — or run the CLI from `backend/`.

## How it fits together

```
feeds ──▶ IngestService ──▶ Postgres ──▶ renderers ──▶ text / JSON
                                             ▲
                              CLI and API both read here
```

- `app/domain/` — the vocabulary and the gap rule. Knows nothing about HTTP,
  CSV or SQL.
- `app/sources/` — the source protocols and their implementations.
- `app/ingest/` — the one implementation of "go and read the sources". Both the
  CLI and `POST /ingest` call this same object.
- `app/store/` — the only code that talks SQL.
- `app/render/` — text and JSON renderers over the same domain objects.

Ingest writes; the API and CLI only read. The service serves its last snapshot
correctly while both upstream feeds are down.

## Adding a data source

`IngestService` names no feed. It is handed one `CandidateSource` — which
produces candidates — and any number of `EnrichmentSource`s, and loops over
them. Both protocols are in `app/sources/protocols.py`.

```python
class GitHubProfileSource:                     # app/sources/github_source.py
    name = "github"
    required = False                           # its failure degrades, not fails

    def load(self) -> Enrichment:
        ...                                    # raise SourceUnavailableError if it can't
```

Then register it — this is the only other edit:

```python
def build_enrichments() -> list[EnrichmentSource]:   # app/wiring.py
    return [
        LinkedInFeedSource(client=build_feed_client(), url=settings.linkedin_feed_url),
        GitHubProfileSource(...),
    ]
```

Nothing in the pipeline, the store or the renderers changes. `GET /sources`
walks the same registry, so the new source appears there automatically, and its
per-run outcome is recorded in `ingest_source_status` without a migration.

`Enrichment.apply()` receives the whole candidate list rather than one at a
time, so a source backed by a database or an API can do one bulk lookup
instead of N.

## Decisions worth knowing

| | |
| --- | --- |
| **The join** | The feeds share no ID and the CSV has no name column. Rows are indexed by normalized email *and* phone (digits only, lowercased email); email wins. Neither key alone resolves all four candidates. |
| **Gaps** | Derived on read, never stored, so `GAP_THRESHOLD_DAYS` stays a live policy knob. Default 30 days. |
| **Gap arithmetic** | Plain subtraction, matching the specification's worked example — which is off by one against true days unemployed. Deliberate; see `docs/FUTURE-TASKS.md`. |
| **Ordering** | Derived by sorting on dates. The feed is not reliably sorted. |
| **`current_job`** | Contradicts its own `end_date` in the sample data. The date wins; `Present` appears only when there is no end date. |
| **`duration_in_month`, `last_job`** | Ignored — both contradict the dates they accompany. |
| **Absence** | Always stated, never blank: `LinkedIn: not available`, `No employment history on record.` In JSON, `Gap` is omitted when absent; `Linkedin_url` is null, not missing. |
| **Bad dates** | The employment is kept and rendered with the missing field named; that candidate's gap reporting is suppressed rather than guessed at. |

Longer form: `CONTEXT.md` for the vocabulary, `docs/adr/` for the two
architectural decisions, `docs/FUTURE-TASKS.md` for what was deferred.

## Configuration

Every value has a working default. Set via environment:

| Variable | Default | |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5433/app` | 5433, because a native Postgres usually owns 5432 |
| `GAP_THRESHOLD_DAYS` | `30` | Below this, a gap is month-boundary noise |
| `RESUME_FEED_URL` | the exercise's URL | |
| `LINKEDIN_FEED_URL` | the exercise's URL | |
| `INGEST_TOKEN` | unset | Unset means `POST /ingest` is **not registered at all** |
| `FEED_CONNECT_TIMEOUT_SECONDS` | `5.0` | |
| `FEED_READ_TIMEOUT_SECONDS` | `10.0` | |
| `FEED_RETRIES` | `1` | |

## Tests

There are none yet — deliberately deferred, with the intended suite specified
in `docs/FUTURE-TASKS.md`. `ci.yml` runs lint, the migration and the image
build; the `pytest` gate is restored along with the suite.
