"""Indeed scraper (HTML parsing — best-effort, sites change markup often)."""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from scrapers.base import Job, Scraper

log = logging.getLogger(__name__)

BASE = "https://www.indeed.com/jobs"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class IndeedScraper(Scraper):
    name = "indeed"

    def fetch(
        self,
        keywords: list[str],
        locations: list[str],
        max_experience: int | None = None,
    ) -> list[Job]:
        query = " ".join(keywords) if keywords else ""
        location = locations[0] if locations else ""
        params = {"q": query}
        if location and location.lower() != "remote":
            params["l"] = location
        if location.lower() == "remote":
            params["remotepos"] = "0"

        try:
            resp = httpx.get(BASE, params=params, headers=_HEADERS, timeout=20, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("indeed fetch failed: %s", exc)
            return []

        return self._parse(resp.text)

    def _parse(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[Job] = []
        # Indeed markup changes frequently; match common card selectors.
        cards = soup.select("div.job_seen_beacon, li.css-5lf3ms, div[data-jk]")
        for card in cards:
            link = card.select_one("a[href*='/rc/clk'], a[href*='/viewjob'], h2 a, a.jtJobInfo")
            title_el = card.select_one("h2, span[data-testid='jobTitle'], a[data-testid='jobTitle']")
            company_el = card.select_one("span[data-testid='companyName'], span.companyName")
            loc_el = card.select_one(
                "div[data-testid='text-location'], span.companyLocation, div.companyLocation"
            )
            if not (link and title_el):
                continue
            url = urljoin("https://www.indeed.com", link.get("href", ""))
            jobs.append(
                Job(
                    title=title_el.get_text(strip=True),
                    company=(company_el.get_text(strip=True) if company_el else ""),
                    location=(loc_el.get_text(strip=True) if loc_el else ""),
                    url=url,
                    source=self.name,
                    experience=self._extract_experience(card.get_text(" ", strip=True)),
                )
            )
        if not jobs:
            log.warning("indeed: parsed 0 jobs (markup may have changed or blocked)")
        return jobs

    @staticmethod
    def _extract_experience(text: str) -> str | None:
        m = re.search(r"\d+\s*(?:-|to)\s*\d+\s*(?:years|yrs?)", text, re.IGNORECASE)
        return m.group(0) if m else None
