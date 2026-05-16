"""Tests for tkcrawler.cli.run_step – CLI entry point coverage."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


def _run_step(step_name: str, payload: dict | None = None, *, stdin_text: str | None = None) -> subprocess.CompletedProcess:
    """Helper to invoke run_step as a subprocess."""
    args = [sys.executable, "-m", "tkcrawler.cli.run_step"]
    if step_name is not None:
        args.append(step_name)
    env = {**os.environ, "PYTHONPATH": "src"}
    return subprocess.run(
        args,
        input=stdin_text if stdin_text is not None else (json.dumps(payload) if payload else ""),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class TestCLINormalizeSource:
    def test_normalize_source_happy_path(self):
        proc = _run_step("normalize_source", {"item": {"url": "https://example.com/feed", "type": "rss"}})
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["crawl_key"] == "https://example.com/feed"

    def test_normalize_source_with_raw_item(self):
        proc = _run_step("normalize_source", {"url": "https://example.com/rss", "type": "rss"})
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["source_status"] == "ready"


class TestCLIPlanDispatch:
    def test_plan_dispatch_due_source(self):
        payload = {
            "item": {
                "crawl_key": "https://example.com/feed",
                "type": "rss",
                "source_status": "ready",
            },
            "context": {
                "now": "2026-05-15T12:00:00+00:00",
            },
        }
        proc = _run_step("plan_dispatch", payload)
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["should_dispatch"] is True


class TestCLIDeriveSourceHealth:
    def test_derive_source_health_pending(self):
        payload = {"item": {"crawl_key": "https://example.com/feed", "source_status": "ready"}}
        proc = _run_step("derive_source_health", payload)
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["source_health_status"] == "pending"


class TestCLIBuildIngestBody:
    def test_build_ingest_body_happy_path(self):
        payload = {
            "item": {
                "crawl_key": "https://example.com/feed",
                "article": {
                    "id": "a1",
                    "title": "Test",
                    "link": "https://example.com/article",
                    "content_md": "# Test",
                    "item_kind": "article",
                },
            },
        }
        proc = _run_step("build_ingest_body", payload)
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["infl0_ingest_body"]["crawlKey"] == "https://example.com/feed"


class TestCLIFinalizeItem:
    def test_finalize_item_adds_metadata(self):
        payload = {
            "item": {
                "type": "rss",
                "url": "https://example.com/feed",
                "article": {
                    "id": "a1",
                    "title": "Test",
                    "link": "https://example.com/a",
                    "content_md": "body text",
                },
            },
        }
        proc = _run_step("finalize_item", payload)
        assert proc.returncode == 0
        result = json.loads(proc.stdout)
        assert result["ok"] is True
        assert result["items"][0]["content_hash"]


class TestCLIErrorHandling:
    def test_unknown_step_returns_error_envelope(self):
        proc = _run_step("nonexistent_step", {"item": {}})
        assert proc.returncode == 1
        result = json.loads(proc.stdout)
        assert result["ok"] is False
        assert result["error"]["code"] == "unknown_step"
        assert "available" in result["error"]["details"]

    def test_invalid_json_returns_error_envelope(self):
        proc = _run_step("normalize_source", stdin_text="{bad json")
        assert proc.returncode == 1
        result = json.loads(proc.stdout)
        assert result["ok"] is False
        assert result["error"]["code"] == "invalid_json"

    def test_missing_step_name_returns_usage(self):
        proc = subprocess.run(
            [sys.executable, "-m", "tkcrawler.cli.run_step"],
            input="",
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "PYTHONPATH": "src"},
        )
        assert proc.returncode == 2
        assert "Usage:" in proc.stderr

    def test_help_flag_returns_usage(self):
        proc = _run_step("--help")
        assert proc.returncode == 2
        assert "Usage:" in proc.stderr

    def test_step_error_returns_fail_envelope(self):
        proc = _run_step("normalize_source", {"item": {}})
        assert proc.returncode == 1
        result = json.loads(proc.stdout)
        assert result["ok"] is False
        assert result["error"]["code"] == "missing_url"
