# Job Alert

Scans job sites for listings matching your criteria and posts alerts to Slack via an
Incoming Webhook. New (unseen) jobs only — no duplicates across runs.

## Setup

```powershell
cd D:\job-alert
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env   # paste your SLACK_WEBHOOK_URL
```

Create a webhook at https://api.slack.com/messaging/webhooks (add an "Incoming
Webhooks" app to your workspace) and paste the URL into `.env`.

## Usage

```powershell
# Single scan
python main.py --keywords "python developer" --max-experience 2 --location remote --location India --once

# Continuous polling every 30 minutes
python main.py --keywords "python developer" --max-experience 2 --location remote --location India --interval 30
```

### Arguments

| Argument            | Repeatable | Description                                                     |
|---------------------|------------|-----------------------------------------------------------------|
| `--keywords`        | yes        | Job title/skill keywords (required, OR-ed)                       |
| `--max-experience`  | no         | Max years of experience (e.g. `2` → 0–2 years)                   |
| `--location`        | yes        | e.g. `remote`, `India` — a job matching **any** value passes     |
| `--interval`        | no         | Minutes between scans (default 60)                               |
| `--slack-webhook`   | no         | Override the `.env` webhook URL                                  |
| `--sources`         | no         | Comma-separated subset, e.g. `remotive,arbeitnow`                |
| `--strict-experience` | no       | Exclude jobs with no stated experience requirement               |
| `--once`            | no         | Scan once and exit                                               |
| `-v`                | no         | Debug logging                                                    |

## Sources

| Source      | Type              | Notes                                          |
|-------------|-------------------|------------------------------------------------|
| `indeed`    | HTML scraping     | Fragile; often blocked by bot protection       |
| `remotive`  | Public API        | Remote jobs worldwide                          |
| `arbeitnow` | Public API        | Includes India/remote listings                |

Add a new source: create `scrapers/<name>.py` implementing `Scraper.fetch()`,
then register it in `scrapers/__init__.py`.

## How it works

```
CLI args → fetch from sources → filter (keywords AND location AND experience)
        → drop already-seen jobs (SQLite) → send Slack alert → mark seen
```

- `job_id` = SHA-1 of `source + url`, stored in `jobs.db` (pruned after 30 days).
- Slack failures retry 3× with backoff; the job is marked seen only on success.
- A failing source is logged and skipped — it never crashes the loop.

## Files

- `main.py` — CLI + polling loop
- `filters.py` — experience/keyword/location matching
- `storage.py` — SQLite dedupe
- `slack.py` — Block Kit message + retries
- `config.py` — `.env` loading
- `scrapers/` — pluggable job sources
- `smoke_test.py` — fetch + filter without Slack
- `SPEC.md` — full specification

## Notes

- Many job sites prohibit scraping in their Terms of Service; prefer official APIs
  where possible. Sources are pluggable so you can swap as needed.
- Coverage is not "all job sites worldwide" — extend `scrapers/` incrementally.
