"""Arbeitnow API source (free public job API, incl. India/remote)."""
from __future__ import annotations

import logging

import httpx

from scrapers.base import Job, Scraper

log = logging.getLogger(__name__)

API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(Scraper):
    name = "arbeitnow"

    def fetch(
        self,
        keywords: list[str],
        locations: list[str],
        max_experience: int | None = None,
    ) -> list[Job]:
        try:
            resp = httpx.get(API, timeout=20, headers={"User-Agent": "job-alert/1.0"})
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("arbeitnow fetch failed: %s", exc)
            return []

        jobs: list[Job] = []
        for item in data.get("data", []):
            jobs.append(
                Job(
                    title=(item.get("title") or "").strip(),
                    company=(item.get("company_name") or "").strip(),
                    location=(item.get("location") or "").strip() or "Remote",
                    url=item.get("url", ""),
                    source=self.name,
                    experience=None,
                    description=(item.get("description") or "")[:2000],
                )
            )
        return jobs
