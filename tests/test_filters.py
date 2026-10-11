"""Unit tests for filters: experience parsing and job matching."""
from __future__ import annotations

import pytest

from filters import (
    filter_jobs,
    matches_experience,
    matches_keywords,
    matches_location,
    parse_experience,
)
from scrapers.base import Job


def make_job(**kwargs) -> Job:
    defaults = dict(
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/jobs/1",
        source="test",
    )
    defaults.update(kwargs)
    return Job(**defaults)


class TestParseExperience:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("0-2 years", (0.0, 2.0)),
            ("2 to 5 years", (2.0, 5.0)),
            ("1–3 yrs", (1.0, 3.0)),
            ("3 years", (0.0, 3.0)),
            ("fresher", (0.0, 1.0)),
            ("Entry level", (0.0, 1.0)),
            (None, None),
            ("", None),
            ("No experience listed", None),
        ],
    )
    def test_parse(self, text, expected):
        assert parse_experience(text) == expected


class TestMatchesExperience:
    def test_within_limit(self):
        assert matches_experience(make_job(experience="0-2 years"), 2)

    def test_exceeds_limit(self):
        assert not matches_experience(make_job(experience="5-8 years"), 2)

    def test_unknown_included_by_default(self):
        assert matches_experience(make_job(experience=None), 2)

    def test_unknown_excluded_when_strict(self):
        assert not matches_experience(make_job(experience=None), 2, strict=True)

    def test_no_filter_passes_everything(self):
        assert matches_experience(make_job(experience="10+ years"), None)

    def test_senior_title_excluded_when_no_experience_stated(self):
        assert not matches_experience(
            make_job(title="Senior Software Engineer", experience=None), 2
        )

    def test_junior_title_included_when_no_experience_stated(self):
        assert matches_experience(
            make_job(title="Junior Python Developer", experience=None), 2
        )

    def test_junior_title_wins_over_senior_stated_limit(self):
        # Stated requirement wins over title when parseable
        assert matches_experience(
            make_job(title="Senior Engineer", experience="0-2 years"), 2
        )


class TestMatchesKeywords:
    def test_match_in_title(self):
        assert matches_keywords(make_job(title="Python Developer"), ["python"])

    def test_match_in_description(self):
        assert matches_keywords(make_job(description="We need a python dev"), ["python"])

    def test_case_insensitive(self):
        assert matches_keywords(make_job(title="PYTHON DEVELOPER"), ["python"])

    def test_no_match(self):
        assert not matches_keywords(make_job(title="Java Developer"), ["python"])

    def test_empty_keywords_pass(self):
        assert matches_keywords(make_job(title="Anything"), [])

    def test_multiple_keywords_any_match(self):
        assert matches_keywords(make_job(title="Java Developer"), ["python", "java"])


class TestMatchesLocation:
    def test_remote_matches(self):
        assert matches_location(make_job(location="Remote"), ["remote"])

    def test_india_matches(self):
        assert matches_location(make_job(location="Bengaluru, India"), ["India"])

    def test_any_match_with_multiple_locations(self):
        assert matches_location(make_job(location="Mumbai, India"), ["remote", "India"])

    def test_no_match(self):
        assert not matches_location(make_job(location="Berlin, Germany"), ["remote", "India"])

    def test_empty_locations_pass(self):
        assert matches_location(make_job(location="Anywhere"), [])


class TestFilterJobs:
    def test_all_filters_combined_with_and(self):
        jobs = [
            make_job(url="j1", title="Python Developer", location="Remote", experience="0-2 years"),
            make_job(url="j2", title="Python Developer", location="Remote", experience="5-8 years"),
            make_job(url="j3", title="Java Developer", location="Remote", experience="0-2 years"),
            make_job(url="j4", title="Python Developer", location="Berlin", experience="0-2 years"),
        ]
        result = filter_jobs(jobs, ["python"], ["remote"], max_experience=2)
        assert [j.url for j in result] == ["j1"]

    def test_no_filters_returns_all(self):
        jobs = [make_job(url="j1"), make_job(url="j2", title="Java Developer")]
        assert len(filter_jobs(jobs, [], [], None)) == 2
