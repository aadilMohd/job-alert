"""Unit tests for the Indeed HTML parser (fixture-based, no network)."""
from __future__ import annotations

from scrapers.indeed import IndeedScraper

FIXTURE = """
<html><body>
<div class="job_seen_beacon">
  <h2><a href="/rc/clk?jk=abc123">Python Developer</a></h2>
  <span class="companyName">Acme Corp</span>
  <div class="companyLocation">Bengaluru, India</div>
  <ul><li>Experience: 0-2 years</li></ul>
</div>
<div class="job_seen_beacon">
  <h2><a href="/rc/clk?jk=def456">Senior Python Developer</a></h2>
  <span class="companyName">Globex</span>
  <div class="companyLocation">Remote</div>
</div>
</body></html>
"""


def test_parses_jobs_from_fixture():
    jobs = IndeedScraper()._parse(FIXTURE)
    assert len(jobs) == 2


def test_job_fields():
    jobs = IndeedScraper()._parse(FIXTURE)
    first = jobs[0]
    assert first.title == "Python Developer"
    assert first.company == "Acme Corp"
    assert first.location == "Bengaluru, India"
    assert first.url == "https://www.indeed.com/rc/clk?jk=abc123"
    assert first.source == "indeed"
    assert first.experience == "0-2 years"


def test_experience_extracted_when_present():
    jobs = IndeedScraper()._parse(FIXTURE)
    assert jobs[0].experience is not None
    assert jobs[1].experience is None


def test_empty_html_returns_no_jobs():
    assert IndeedScraper()._parse("<html><body>blocked</body></html>") == []
