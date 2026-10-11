"""Unit tests for Job model and scraper base (no network)."""
from __future__ import annotations

import pytest

from scrapers.base import Job, Scraper


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


class TestJobId:
    def test_stable_for_same_source_and_url(self):
        assert make_job().id == make_job().id

    def test_differs_by_url(self):
        assert make_job().id != make_job(url="https://example.com/jobs/2").id

    def test_differs_by_source(self):
        assert make_job().id != make_job(source="other").id

    def test_is_hex_digest(self):
        assert len(make_job().id) == 40
        int(make_job().id, 16)  # valid hex


class TestScraperInterface:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Scraper()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_fetch(self):
        class Partial(Scraper):
            name = "partial"

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]
