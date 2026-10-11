"""Scraper registry. Add new sources here."""
from __future__ import annotations

from scrapers.base import Job, Scraper
from scrapers.indeed import IndeedScraper
from scrapers.remotive import RemotiveScraper
from scrapers.arbeitnow import ArbeitnowScraper

ALL_SCRAPERS: dict[str, type[Scraper]] = {
    IndeedScraper.name: IndeedScraper,
    RemotiveScraper.name: RemotiveScraper,
    ArbeitnowScraper.name: ArbeitnowScraper,
}

__all__ = ["Job", "Scraper", "ALL_SCRAPERS"]
