# Candidate Résumé Reporting

Retrieves candidate résumés and supplemental LinkedIn data from two public
feeds, joins them, and renders each candidate's employment history — including
gaps between jobs — as human-readable text and as structured JSON.

## Language

**Candidate**:
A person whose résumé appears in the Résumé Feed. The unit of reporting: one
candidate produces one text block and one JSON object.

**Résumé Feed**:
The upstream JSON array of candidate résumés. Authoritative for names and
employment history.
_Avoid_: main source, allcands, the API

**LinkedIn Feed**:
The upstream CSV of contact details and LinkedIn URLs. Supplemental only — it
adds a LinkedIn Profile to a Candidate and nothing else, and carries no name.
_Avoid_: supplemental source, the CSV

**Candidate Source**:
A source that produces Candidates. Exactly one takes part in an Ingest Run,
and without it there is no report, so its failure fails the run.
_Avoid_: primary source, main feed

**Enrichment Source**:
A source that adds data to Candidates another source produced. Any number may
take part in an Ingest Run, and by default the failure of one degrades the
report rather than failing it.
_Avoid_: secondary source, supplemental feed, side source

**Ingest Run**:
One attempt to read both feeds and record what they contained. Every Candidate
belongs to exactly one Ingest Run, so a run is a snapshot of the feeds at a
moment rather than an update to a running total.
_Avoid_: import, sync, refresh, job

**Contact Key**:
A normalized email address or phone number used to attach a LinkedIn Feed row
to a Candidate. Email keys are trimmed and lowercased; phone keys are reduced
to their digits. The two feeds share no identifier, so a Contact Key is the
only thing that links them.
_Avoid_: match key, join key, identifier

**LinkedIn Profile**:
The URL identifying a Candidate on LinkedIn. Optional — a Candidate with no
matching Contact Key simply has none.
_Avoid_: LinkedIn handle, social profile

## Employment History

**Employment**:
One position a Candidate held: a role, a location, and the dates it ran
between. Reported newest first.
_Avoid_: experience, job, work experience, position

**Employment Gap**:
The stretch between one Employment ending and the next beginning, measured
against the Candidate's Employments in date order. A Gap belongs to the
Employment that follows it — it describes how long the Candidate was out of
work before starting that role.
_Avoid_: unemployment period, break in service

**Significant**:
Of an Employment Gap: longer than the configured threshold, 30 days by
default. Only significant Gaps are reported; shorter ones are treated as
month-boundary noise.
