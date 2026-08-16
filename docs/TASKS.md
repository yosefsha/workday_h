# Workday Tech Test

Source: [`WorkdayTechTest.pdf`](WorkdayTechTest.pdf)

## Objective

Design and implement a small application that retrieves and processes candidate
data from public endpoints.

## Data Sources

| Source | URL |
| --- | --- |
| Main candidate data (JSON) | https://recruiting-test-resume-data.hiredscore.com/allcands-full-api_hub_b1f6-acde48001122.json |
| Supplemental LinkedIn data (CSV) | https://recruiting-test-resume-data.hiredscore.com/linkedin_source_b1f6-acde48001122.csv |

## Requirements

- Fetch and parse candidate data. Extract and present each candidate's:
  - Full name
  - Work experience (role, start and end dates, location)
  - LinkedIn profile (if available)
- Detect and indicate any significant employment gaps between jobs.
- Present the information in:
  - A readable text format (e.g., printed or logged output) — see [`example-output.txt`](example-output.txt)
  - A structured JSON format — see [`example-output.json`](example-output.json)

Notes drawn from the examples: jobs are listed newest-first, and the `Gap` field
belongs to the *later* job — it describes the gap immediately preceding it.

## Interview Format

- The coding session is 1 hour.
- Questions and clarification of the task are welcome before starting.
- The interviewers stay on the call with mic and camera off during the coding
  period; reach out at any time for clarifications.
- At the end, walk them through the solution, focusing on the design choices
  made and how the problem was approached.

## Guidance

- Reasonable assumptions are fine for anything not explicitly defined.
- Any AI tooling may be used. The expectation is a working solution that is
  thoroughly understood and whose implementation decisions can be defended.
  The prompts used during the process will be reviewed together — how the
  candidate interacts with the AI matters.
- Any programming language and tooling may be chosen.
- They are looking for clean, well-structured, maintainable code reflecting good
  engineering practices.
- Prioritize readability, modularity, and extensibility in the design.
- They are interested in the candidate's interpretation of "production-ready"
  code — design decisions worth being proud of and comfortable maintaining.
