"""Unit tests for Slack message building and sending (no real webhook)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

import slack
from scrapers.base import Job


def make_job() -> Job:
    return Job(
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/jobs/1",
        source="test",
        experience="0-2 years",
    )


class TestBuildMessage:
    def test_contains_title_and_company(self):
        payload = slack.build_message(make_job())
        text = str(payload)
        assert "Python Developer" in text
        assert "Acme" in text
        assert "Remote" in text
        assert "0-2 years" in text

    def test_has_blocks_and_fallback_text(self):
        payload = slack.build_message(make_job())
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)
        assert payload["text"]  # fallback for notifications

    def test_link_included(self):
        payload = slack.build_message(make_job())
        assert "https://example.com/jobs/1" in str(payload)

    def test_missing_experience_defaults(self):
        job = make_job()
        job.experience = None
        assert "Not specified" in str(slack.build_message(job))


def _response(status_code=200, text="ok"):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


class TestSend:
    @patch("slack.httpx.post")
    def test_success_returns_true(self, post):
        post.return_value = _response()
        assert slack.send("https://hooks.example/x", {"text": "hi"}) is True
        post.assert_called_once()

    @patch("slack.time.sleep")  # don't actually wait
    @patch("slack.httpx.post")
    def test_retries_three_times_then_fails(self, post, _sleep):
        post.side_effect = httpx.ConnectError("boom")
        assert slack.send("https://hooks.example/x", {"text": "hi"}) is False
        assert post.call_count == 3

    @patch("slack.time.sleep")
    @patch("slack.httpx.post")
    def test_http_error_status_retries(self, post, _sleep):
        post.return_value = _response(status_code=500, text="server error")
        assert slack.send("https://hooks.example/x", {"text": "hi"}) is False
        assert post.call_count == 3

    @patch("slack.time.sleep")
    @patch("slack.httpx.post")
    def test_recovers_after_transient_failure(self, post, _sleep):
        post.side_effect = [httpx.ConnectError("boom"), _response()]
        assert slack.send("https://hooks.example/x", {"text": "hi"}) is True
        assert post.call_count == 2


class TestSendJob:
    @patch("slack.send")
    def test_sends_built_payload(self, send):
        send.return_value = True
        assert slack.send_job("https://hooks.example/x", make_job()) is True
        payload = send.call_args[0][1]
        assert "Python Developer" in str(payload)

    @patch("slack.send")
    def test_returns_false_on_failure(self, send):
        send.return_value = False
        assert slack.send_job("https://hooks.example/x", make_job()) is False
