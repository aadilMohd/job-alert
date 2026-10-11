"""Slack Incoming Webhook delivery with retries."""
from __future__ import annotations

import logging
import time

import httpx

from scrapers.base import Job

log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_SECONDS = 2  # doubled each retry: 2, 4, 8


def build_message(job: Job) -> dict:
    """Build a Slack Block Kit payload for a single job."""
    experience = job.experience or "Not specified"
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":briefcase: *{job.title}*",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"🏢 {job.company}  |  📍 {job.location}  |  📅 {experience}"
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔗 <{job.url}|View listing>",
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_Source: {job.source}_"}],
        },
    ]
    return {"blocks": blocks, "text": f"{job.title} at {job.company}"}


def send(webhook_url: str, payload: dict) -> bool:
    """Post a payload to the webhook. Retries 3 times with backoff."""
    delay = _BACKOFF_SECONDS
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = httpx.post(webhook_url, json=payload, timeout=10)
            if resp.status_code == 200:
                return True
            log.error("Slack returned %s: %s", resp.status_code, resp.text)
        except httpx.HTTPError as exc:
            log.error("Slack request failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)
        if attempt < _MAX_RETRIES:
            time.sleep(delay)
            delay *= 2
    return False


def send_job(webhook_url: str, job: Job) -> bool:
    """Send a single job alert. Returns True on success."""
    ok = send(webhook_url, build_message(job))
    if ok:
        log.info("Alerted: %s @ %s", job.title, job.company)
    else:
        log.error("Failed to alert: %s @ %s (will retry next run)", job.title, job.company)
    return ok
