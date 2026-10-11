"""Experience, keyword, and location filtering."""
from __future__ import annotations

import re

from scrapers.base import Job

# Matches patterns like "0-2 years", "2 yrs", "fresher", "<= 3 years"
_EXPERIENCE_RE = re.compile(
    r"(?P<min>\d+)\s*(?:-|to|–)\s*(?P<max>\d+)\s*(?:years|yrs?)",
    re.IGNORECASE,
)
_SINGLE_YEAR_RE = re.compile(r"(?P<max>\d+)\s*(?:years|yrs?)", re.IGNORECASE)
_FRESHER_RE = re.compile(r"\b(fresher|entry[\s-]?level|0\s*years)\b", re.IGNORECASE)
# Titles implying more experience than an entry-level (0-2) role
_SENIOR_TITLE_RE = re.compile(
    r"\b(senior|sr\.?|lead|staff|principal|architect|manager|head of|director|chief)\b",
    re.IGNORECASE,
)
_JUNIOR_TITLE_RE = re.compile(
    r"\b(junior|jr\.?|intern|trainee|graduate|associate|fresher|entry)\b",
    re.IGNORECASE,
)


def parse_experience(text: str | None) -> tuple[float, float] | None:
    """Parse experience text into (min, max) years. Returns None if unparseable."""
    if not text:
        return None
    m = _EXPERIENCE_RE.search(text)
    if m:
        return float(m.group("min")), float(m.group("max"))
    if _FRESHER_RE.search(text):
        return 0.0, 1.0
    m = _SINGLE_YEAR_RE.search(text)
    if m:
        return 0.0, float(m.group("max"))
    return None


def matches_experience(job: Job, max_experience: int | None, strict: bool = False) -> bool:
    """True if the job's experience requirement is within max_experience.

    Jobs with no stated requirement pass unless strict=True or the title
    clearly signals a senior-level role.
    """
    if max_experience is None:
        return True
    years = job.raw_years or parse_experience(job.experience)
    if years is None:
        # No stated requirement: still exclude obviously senior titles
        # (but junior/fresher titles always pass).
        if _JUNIOR_TITLE_RE.search(job.title):
            return True
        return not strict and not _SENIOR_TITLE_RE.search(job.title)
    return years[1] <= max_experience


def matches_keywords(job: Job, keywords: list[str]) -> bool:
    """True if any keyword appears in title, company, or description (case-insensitive)."""
    if not keywords:
        return True
    haystack = f"{job.title} {job.company} {job.description}".lower()
    return any(k.lower() in haystack for k in keywords)


def matches_location(job: Job, locations: list[str]) -> bool:
    """True if any requested location matches the job's location."""
    if not locations:
        return True
    loc = job.location.lower()
    return any(l.lower() in loc or loc in l.lower() for l in locations)


def filter_jobs(
    jobs: list[Job],
    keywords: list[str],
    locations: list[str],
    max_experience: int | None = None,
    strict_experience: bool = False,
) -> list[Job]:
    """Apply all filters (AND)."""
    return [
        j
        for j in jobs
        if matches_keywords(j, keywords)
        and matches_location(j, locations)
        and matches_experience(j, max_experience, strict_experience)
    ]
