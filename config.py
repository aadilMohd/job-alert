"""Loads configuration from .env and environment."""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def slack_webhook_url(override: str | None = None) -> str:
    """Return the webhook URL: CLI override > .env > error."""
    url = override or os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not url:
        raise SystemExit(
            "Missing Slack webhook URL. Set SLACK_WEBHOOK_URL in .env "
            "or pass --slack-webhook."
        )
    return url


def default_interval() -> int:
    try:
        return int(os.getenv("DEFAULT_INTERVAL_MINUTES", "60"))
    except ValueError:
        return 60
