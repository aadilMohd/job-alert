"""Remotive API source (remote jobs, free public API)."""
from __future__ import annotations

import logging

import httpx

from scrapers.base import Job, Scraper

log = logging.getLogger(__name__)

API = "https://remotive.com/api/remote-jobs"


class RemotiveScraper(Scraper):
    name = "remotive"

    def fetch(
        self,
        keywords: list[str],
        locations: list[str],
        max_experience: int | None = None,
    ) -> list[Job]:
        try:
            resp = httpx.get(
                API,
                params={"search": keywords[0]} if keywords else {},
                timeout=20,
                headers={"User-Agent": "job-alert/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("remotive fetch failed: %s", exc)
            return []

        jobs: list[Job] = []
        for item in data.get("jobs", []):
            jobs.append(
                Job(
                    title=item.get("title", "").strip(),
                    company=item.get("company_name", "").strip(),
                    location=item.get("candidate_required_location", "").strip() or "Remote",
                    url=item.get("url", ""),
                    source=self.name,
                    experience=None,
                    description=(item.get("description") or "")[:2000],
                )
            )
        return jobs
