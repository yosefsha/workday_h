# Future Tasks

Work deliberately deferred, with the reasoning. Each entry names what was
decided against so a reader can tell a conscious omission from an oversight.

## 1. Test suite — deferred, highest priority

Nothing is tested. There is no `backend/tests/`, and `ci.yml` has no `pytest`
step because an empty run exits 5 and would leave the workflow permanently red.

The design decided on before deferring:

- **Real payloads, checked in verbatim** as `tests/fixtures/resume_feed.json`
  (57 KB) and `tests/fixtures/linkedin_feed.csv` (266 B). They already carry
  the interesting cases: Walter White's empty `experience`, the unpadded
  `Sep/5/2016`, the null phone, the out-of-order entries, the 9-digit phone.
- **Small hand-written payloads** for what the real feed lacks: overlapping
  employments, a null `end_date` with `current_job: true`, an unparseable
  date, two candidates sharing a phone number.
- **No test reaches the network.** The suite must pass offline and keep passing
  after those upstream URLs are retired.

Cases worth naming explicitly:

| Area | Case |
| --- | --- |
| Join | email match, phone match, neither, blank CSV email, digit-normalized phone |
| Join | duplicate contact key across two rows — first wins, warning logged |
| Gaps | 366 / 125 / 69-day gaps reported; 0 and 1-day boundaries not |
| Gaps | exactly `GAP_THRESHOLD_DAYS` is not significant; one more is |
| Gaps | suppressed entirely when any employment has an unparseable date |
| Ordering | unsorted feed input renders newest-first |
| Render | `Sep/5/2016` normalizes to `Sep/05/2016` |
| Render | `Gap` key omitted, never null; `Linkedin_url` null, never omitted |
| Render | candidate with no employments |
| Ingest | LinkedIn feed down → run succeeds, `linkedin_feed_ok` false |
| Ingest | résumé feed down → run fails, failed row recorded, no partial data |
| API | 503 with a useful message when no snapshot exists |

Restore the `pytest` step in `ci.yml` with the suite, including the
skip-is-a-failure guard.

## 2. Overlapping employments produce a phantom gap

`build_history` compares sorted consecutive pairs. A candidate holding two
concurrent roles — a long one with a short one inside it — can show a gap that
the overlapping job actually covered. The sample data has no true overlaps,
only same-day handovers, so this is latent rather than live.

The fix is a merged coverage timeline: collapse overlapping and touching
employments into continuous blocks of "employed" and report gaps between
blocks. Considered and deliberately not built — see the note in
`app/domain/history.py`.

## 3. The spec's gap arithmetic is off by one

`Dec/31/2012 → Jan/20/2013` is reported as 20 days, matching the exercise's
worked example. The candidate was actually out of work for 19 days. We match
the specification rather than correct it, on purpose. If this ever becomes a
real report rather than an exercise, decide which one is wanted.

## 4. Ingest has no schedule

`POST /ingest` and `python -m app ingest` are the only triggers, plus a
first-boot ingest when the database is empty. Nothing refreshes the snapshot on
an interval. That is an operational decision — a cron entry or a Kubernetes
CronJob calling the CLI — deliberately left outside the application.

## 5. Snapshots are never pruned

Every ingest writes a new run and a full set of candidates; nothing deletes old
ones. At four candidates per run this is irrelevant, but it grows without
bound. A retention policy belongs here before anyone runs this on a schedule.

## 6. Not addressed, and out of scope as specified

- No authentication on the read endpoints. `INGEST_TOKEN` guards the one write
  endpoint; `GET /candidates` is open.
- No pagination. Four candidates fit in one response; a real feed would not.
- The résumé feed carries education, skills and certificates that are parsed
  away. Reporting them is a schema change, not a rework.
