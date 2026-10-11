"""Job Alert — CLI entry point.

Scans job sources on an interval and sends new matches to Slack.

Example:
    python main.py --keywords "python developer" --max-experience 2 \
                   --location remote --location India --interval 60 --once
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

import schedule

import config
import slack as slack_mod
from filters import filter_jobs
from scrapers import ALL_SCRAPERS, Job
from storage import SeenStore

log = logging.getLogger("job_alert")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Scan job sites and alert on Slack.")
    p.add_argument(
        "--keywords",
        action="append",
        required=True,
        help="Job title/skill keywords (repeat for multiple, OR-ed).",
    )
    p.add_argument(
        "--max-experience",
        type=int,
        default=None,
        help="Maximum years of experience, e.g. 2 for 0-2 years.",
    )
    p.add_argument(
        "--location",
        action="append",
        default=[],
        help='Accepted location, e.g. "remote" or "India" (repeatable, any-match).',
    )
    p.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Minutes between scans (default: env DEFAULT_INTERVAL_MINUTES or 60).",
    )
    p.add_argument("--slack-webhook", default=None, help="Webhook URL override.")
    p.add_argument(
        "--sources",
        default=None,
        help=f"Comma-separated source names. Default: all ({', '.join(ALL_SCRAPERS)}).",
    )
    p.add_argument("--strict-experience", action="store_true",
                   help="Exclude jobs with no stated experience requirement.")
    p.add_argument("--once", action="store_true", help="Run a single scan and exit.")
    p.add_argument("--log-file", default=None, help="Also write logs to this file (for scheduled runs).")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    return p


def collect_jobs(args: argparse.Namespace, store: SeenStore, webhook: str) -> int:
    """Fetch, filter, dedupe, and alert. Returns number of new alerts sent."""
    names = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources
        else list(ALL_SCRAPERS)
    )

    raw: list[Job] = []
    for name in names:
        cls = ALL_SCRAPERS.get(name)
        if cls is None:
            log.warning("Unknown source '%s', skipping", name)
            continue
        try:
            found = cls().fetch(args.keywords, args.location, args.max_experience)
            log.info("%s: %d jobs fetched", name, len(found))
            raw.extend(found)
        except Exception as exc:  # never let one source kill the loop
            log.error("Source '%s' failed: %s", name, exc)

    matches = filter_jobs(
        raw,
        args.keywords,
        args.location,
        args.max_experience,
        args.strict_experience,
    )
    log.info("%d total, %d after filters", len(raw), len(matches))

    sent = 0
    for job in matches:
        if store.is_seen(job.id):
            continue
        if slack_mod.send_job(webhook, job):
            store.mark_seen(job.id)
            sent += 1
    if sent:
        log.info("Sent %d new alert(s)", sent)
    return sent


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers: list[logging.Handler] = []
    if sys.stderr is not None:  # not running under pythonw
        handlers.append(logging.StreamHandler())
    if args.log_file:
        os.makedirs(os.path.dirname(args.log_file) or ".", exist_ok=True)
        handlers.append(logging.FileHandler(args.log_file, encoding="utf-8"))
    if not handlers:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
    )

    webhook = config.slack_webhook_url(args.slack_webhook)
    interval = args.interval if args.interval is not None else config.default_interval()
    store = SeenStore()

    if args.once:
        collect_jobs(args, store, webhook)
        store.close()
        return 0

    log.info("Polling every %d minute(s). Ctrl+C to stop.", interval)
    store.prune()
    job = lambda: collect_jobs(args, store, webhook)  # noqa: E731
    schedule.every(interval).minutes.do(job)
    job()  # first run immediately
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Stopped.")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
