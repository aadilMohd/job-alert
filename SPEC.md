# Job Alert — Specification

**Version:** 1.0
**Date:** 2026-10-11
**Location:** `D:\job-alert`

---

## 1. Overview

A Python service that periodically scans job sites for listings matching user-supplied
criteria (keywords, experience level, location) and sends an alert to a Slack channel
via an Incoming Webhook. Only new (previously unseen) jobs are alerted.

## 2. Goals

- Accept search criteria via command-line arguments.
- Poll one or more job sources on a fixed interval.
- Filter results by experience, keywords, and location.
- Post formatted job alerts to Slack.
- Avoid duplicate alerts across runs.
- Support adding new job sources without changing core logic.

### Non-Goals (v1)

- Scraping *every* job site / company career portal worldwide. v1 ships with a small
  set of major sources; the scraper interface is designed for incremental addition.
- Authentication (OAuth, multi-user, database-backed config).
- A web UI or REST API.

## 3. Tech Stack

| Concern            | Choice                          |
|--------------------|---------------------------------|
| Language           | Python 3.11+                    |
| HTTP / scraping    | `httpx` (or `requests`) + `beautifulsoup4` |
| CLI parsing        | `argparse`                      |
| Scheduling         | `schedule` (or simple sleep loop) |
| Slack delivery     | Incoming Webhook                |
| Dedupe persistence | SQLite (stdlib `sqlite3`)       |
| Secrets            | `python-dotenv` (`.env`)        |

## 4. Project Structure

```
D:\job-alert\
├── main.py              # entry point: parses args, runs the polling loop
├── config.py            # loads Slack webhook URL and defaults from .env
├── filters.py           # experience / keyword / location filtering
├── storage.py           # SQLite seen-jobs tracking (dedupe)
├── slack.py             # builds and sends Slack messages
├── scrapers/
│   ├── __init__.py
│   ├── base.py          # Job dataclass + Scraper interface
│   ├── indeed.py        # first concrete scraper
│   └── <source>.py      # additional sources over time
├── requirements.txt
├── .env                 # SLACK_WEBHOOK_URL (gitignored)
├── .gitignore
└── SPEC.md              # this document
```

## 5. Command-Line Interface

```
python main.py --keywords "python developer" \
               --max-experience 2 \
               --location remote --location India \
               --interval 60
```

### Arguments

| Argument           | Required | Repeatable | Description                                              |
|--------------------|----------|------------|----------------------------------------------------------|
| `--keywords`       | yes      | yes        | Job title/skill keywords to search for. Multiple values are OR-ed. |
| `--max-experience` | no       | no         | Maximum years of experience (e.g. `2` → 0–2 years eligible). Default: no experience filter. |
| `--location`       | no       | yes        | Accepted locations, e.g. `remote`, `India`. A job matching **any** value passes. If omitted, no location filter. |
| `--interval`       | no       | no         | Minutes between scans. Default: `60`.                    |
| `--slack-webhook`  | no       | no         | Webhook URL override. Otherwise read from `.env`.         |
| `--once`           | no       | no         | Run a single scan and exit (useful for testing).         |

### Semantics

- **Keywords:** a job matches if it satisfies *any* `--keywords` value (case-insensitive
  substring/token match on title + description).
- **Locations:** a job matches if it satisfies *any* `--location` value. `remote` matches
  listings flagged as remote.
- **Experience:** a job matches if its stated experience requirement is ≤
  `--max-experience`. Listings with no stated requirement are **included** (assumed entry-friendly)
  unless `--strict-experience` is passed.
- All three filters are combined with **AND** (keywords AND location AND experience).

## 6. Architecture

### 6.1 Data model

```python
@dataclass
class Job:
    id: str          # stable hash of (source + url) — used for dedupe
    title: str
    company: str
    location: str
    experience: str | None   # raw text, e.g. "0-2 years"
    url: str
    source: str               # e.g. "indeed"
    posted_at: datetime | None
    description: str
```

### 6.2 Scraper interface

```python
class Scraper(ABC):
    name: str
    @abstractmethod
    def fetch(self, keywords: list[str], locations: list[str],
              max_experience: int | None) -> list[Job]: ...
```

- Each source implements `fetch()` and returns normalized `Job` objects.
- `main.py` discovers enabled scrapers from a registry and iterates them.
- A failing source is logged and skipped; it never crashes the loop.

### 6.3 Processing pipeline

```
CLI args
  → for each enabled scraper: fetch jobs
  → normalize
  → filters.py (experience, keywords, location)
  → storage.py: drop already-seen job IDs
  → slack.py: send one message per job (or batched digest)
  → storage.py: mark new IDs as seen
```

## 7. Slack Integration

- Uses an **Incoming Webhook** URL stored in `.env` as `SLACK_WEBHOOK_URL`.
- Message format (Block Kit):

```
:briefcase: *{title}*
🏢 {company}  |  📍 {location}  |  📅 {experience}
🔗 <{url}|View listing>
_Source: {source}_
```

- Failure handling: on webhook error, retry up to 3 times with backoff, then log and
  continue (jobs are marked seen only after a successful send, so they alert on the next run).

## 8. Deduplication

- Table `seen_jobs(job_id TEXT PRIMARY KEY, first_seen TIMESTAMP)`.
- `job_id` = SHA-1 of `source + url`.
- Pruned periodically (default: rows older than 30 days) to keep the DB small.

## 9. Configuration

`.env` (not committed):

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
DEFAULT_INTERVAL_MINUTES=60
```

## 10. Error Handling & Logging

- Structured logging to stdout (`logging` module), levels: INFO / WARNING / ERROR.
- Network errors per-source: logged as WARNING, loop continues.
- Slack errors: retried ×3, then logged as ERROR.
- Missing webhook URL: fail fast with a clear message before scanning.

## 11. Testing

- **Unit:** filters (experience/keyword/location edge cases), dedupe logic, job ID stability.
- **Scraper:** parsing tests against saved HTML fixtures (no live network in CI).
- **Slack:** mock webhook, verify payload shape.
- **Manual:** `python main.py --once --keywords "python" --location remote --interval 0`

## 12. Milestones

1. Scaffold project, venv, requirements, `.env` handling.
2. `storage.py` + `filters.py` with unit tests.
3. `slack.py` with message formatting and retries.
4. Scraper interface + first concrete source (Indeed).
5. `main.py` CLI + polling loop + `--once`.
6. Add remaining sources incrementally.

## 13. Risks & Notes

- **Scraping fragility:** sites change markup and deploy anti-bot measures (CAPTCHA, rate
  limits, IP blocks). Sources may break without notice; the pluggable design isolates failures.
- **Legal / ToS:** many job sites prohibit scraping in their Terms of Service. Prefer official
  APIs where available (Adzuna, Arbeitnow, JSearch/RapidAPI). The scraper interface supports
  both scraping and API-backed sources.
- **Coverage:** v1 does not cover all job sites worldwide; coverage grows by adding sources.
