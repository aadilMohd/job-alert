"""Unit tests for the main pipeline: fetch → filter → dedupe → alert."""
from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import httpx

import main
from scrapers.base import Job
from storage import SeenStore


def make_args(**kwargs) -> argparse.Namespace:
    defaults = dict(
        keywords=["python"],
        location=["remote"],
        max_experience=2,
        sources="fake",
        strict_experience=False,
        slack_webhook="https://hooks.example/x",
        interval=60,
        once=False,
        verbose=False,
    )
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def make_job(url: str = "j1", title: str = "Python Developer", **kwargs) -> Job:
    defaults = dict(
        title=title,
        company="Acme",
        location="Remote",
        url=f"https://example.com/{url}",
        source="fake",
        experience="0-2 years",
    )
    defaults.update(kwargs)
    return Job(**defaults)


class _FakeScraper:
    name = "fake"
    jobs: list[Job] = []

    def fetch(self, keywords, locations, max_experience=None):
        return list(self.jobs)


@patch.dict(main.ALL_SCRAPERS, {"fake": _FakeScraper})
class TestCollectJobs:
    def test_sends_and_marks_new_jobs(self):
        _FakeScraper.jobs = [make_job("j1")]
        store = SeenStore(":memory:")
        with patch("slack.httpx.post") as post:
            post.return_value = MagicMock(status_code=200, text="ok")
            sent = main.collect_jobs(make_args(), store, "https://hooks.example/x")
        assert sent == 1
        assert store.is_seen(_FakeScraper.jobs[0].id)

    def test_does_not_resend_seen_jobs(self):
        _FakeScraper.jobs = [make_job("j1")]
        store = SeenStore(":memory:")
        with patch("slack.httpx.post") as post:
            post.return_value = MagicMock(status_code=200, text="ok")
            main.collect_jobs(make_args(), store, "https://hooks.example/x")
            sent = main.collect_jobs(make_args(), store, "https://hooks.example/x")
        assert sent == 0
        assert post.call_count == 1  # only first run posted

    def test_failed_send_is_retried_next_run(self):
        _FakeScraper.jobs = [make_job("j1")]
        store = SeenStore(":memory:")
        with patch("slack.time.sleep"), patch("slack.httpx.post") as post:
            post.side_effect = httpx.ConnectError("down")  # all retries fail
            assert main.collect_jobs(make_args(), store, "https://hooks.example/x") == 0
        assert not store.is_seen(_FakeScraper.jobs[0].id)  # not marked seen

        with patch("slack.httpx.post") as post:
            post.return_value = MagicMock(status_code=200, text="ok")
            assert main.collect_jobs(make_args(), store, "https://hooks.example/x") == 1

    def test_filtered_jobs_are_not_sent(self):
        _FakeScraper.jobs = [
            make_job("j1", title="Senior Python Architect", experience=None),  # fails title heuristic
            make_job("j2", title="Java Developer"),           # fails keyword
            make_job("j3", title="Junior Python Developer"),  # passes
        ]
        store = SeenStore(":memory:")
        with patch("slack.httpx.post") as post:
            post.return_value = MagicMock(status_code=200, text="ok")
            sent = main.collect_jobs(make_args(), store, "https://hooks.example/x")
        assert sent == 1
        assert store.is_seen(_FakeScraper.jobs[2].id)

    def test_broken_source_does_not_crash_run(self):
        class BrokenScraper(_FakeScraper):
            name = "broken"

            def fetch(self, *a, **kw):
                raise RuntimeError("site down")

        _FakeScraper.jobs = [make_job("j1")]
        with patch.dict(main.ALL_SCRAPERS, {"broken": BrokenScraper}):
            store = SeenStore(":memory:")
            with patch("slack.httpx.post") as post:
                post.return_value = MagicMock(status_code=200, text="ok")
                sent = main.collect_jobs(
                    make_args(sources="broken,fake"), store, "https://hooks.example/x"
                )
        assert sent == 1  # healthy source still processed

    def test_unknown_source_is_skipped(self):
        _FakeScraper.jobs = []
        store = SeenStore(":memory:")
        sent = main.collect_jobs(make_args(sources="nope"), store, "https://hooks.example/x")
        assert sent == 0


class TestCliParser:
    def test_keywords_required(self):
        import pytest

        with pytest.raises(SystemExit):
            main.build_parser().parse_args([])

    def test_repeatable_location(self):
        args = main.build_parser().parse_args(
            ["--keywords", "python", "--location", "remote", "--location", "India"]
        )
        assert args.location == ["remote", "India"]

    def test_defaults(self):
        args = main.build_parser().parse_args(["--keywords", "python"])
        assert args.max_experience is None
        assert args.interval is None
        assert args.once is False
        assert args.location == []


class TestMissingWebhook:
    def test_fails_fast(self):
        import pytest

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": ""}, clear=False):
            with pytest.raises(SystemExit):
                main.main(["--keywords", "python", "--once"])
