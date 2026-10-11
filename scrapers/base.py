"""Scraper interface and Job data model."""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:
    """A normalized job listing from any source."""

    title: str
    company: str
    location: str
    url: str
    source: str
    experience: str | None = None  # raw text, e.g. "0-2 years"
    posted_at: datetime | None = None
    description: str = ""
    raw_years: tuple[float, float] | None = None  # parsed (min, max) years

    @property
    def id(self) -> str:
        """Stable dedupe key based on source + url."""
        return hashlib.sha1(f"{self.source}|{self.url}".encode()).hexdigest()


class Scraper(ABC):
    """Base class for job sources."""

    name: str = "base"

    @abstractmethod
    def fetch(
        self,
        keywords: list[str],
        locations: list[str],
        max_experience: int | None = None,
    ) -> list[Job]:
        """Fetch jobs matching the given criteria."""
        raise NotImplementedError
