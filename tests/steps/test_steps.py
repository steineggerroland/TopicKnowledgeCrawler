import json
import os
import subprocess
import sys

from tkcrawler.steps.build_ingest_body import build_ingest_body_item, build_ingest_body_step
from tkcrawler.steps.normalize_source import normalize_source_item, normalize_source_step
from tkcrawler.steps.plan_dispatch import plan_dispatch_item, plan_dispatch_step


def test_normalize_source_accepts_infl0_fields():
    out = normalize_source_item(
        {
            "feedUrl": "HTTPS://Example.com/feed/",
            "crawlKey": "https://example.com/feed",
            "displayTitle": "Example",
            "subscriberCount": 2,
        }
    )

    assert out["crawl_key"] == "https://example.com/feed"
    assert out["url"] == "HTTPS://Example.com/feed/"
    assert out["name"] == "Example"
    assert out["subscriber_count"] == 2
    assert out["source_status"] == "needs_analysis"


def test_normalize_source_marks_configured_html_ready():
    out = normalize_source_item(
        {
            "url": "https://example.com/articles",
            "type": "html",
            "configuration_json": json.dumps(
                {"article_selector": "article", "main_page_anchor_selector": "a"}
            ),
        }
    )

    assert out["crawl_key"] == "https://example.com/articles"
    assert out["source_status"] == "ready"
    assert json.loads(out["configuration_json"])["article_selector"] == "article"


def test_normalize_source_step_returns_envelope():
    result = normalize_source_step({"item": {"url": "https://example.com/feed", "type": "rss"}})

    assert result["ok"] is True
    assert result["items"][0]["source_status"] == "ready"


def test_build_ingest_body_item_uses_flat_enrichment():
    out = build_ingest_body_item(
        {
            "crawl_key": "https://example.com/feed",
            "article": {"id": "a1", "title": "T", "content_md": "Body"},
            "teaser": "Short",
            "category": ["factual information"],
        }
    )

    body = out["infl0_ingest_body"]
    assert out["article_id"] == "a1"
    assert body["crawlKey"] == "https://example.com/feed"
    assert body["teaser"] == "Short"
    assert body["category"] == ["factual information"]


def test_build_ingest_body_step_accepts_legacy_output():
    result = build_ingest_body_step(
        {
            "item": {
                "crawl_key": "https://example.com/feed",
                "article": {"id": "a1", "title": "T", "content_md": "Body"},
                "output": {"teaser": "Short"},
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["infl0_ingest_body"]["teaser"] == "Short"


def test_plan_dispatch_dispatches_due_ready_source():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "active": True,
            "type": "rss",
            "source_status": "ready",
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is True
    assert out["dispatch_reason"] == "due"
    assert out["next_allowed_crawl_at"] == "2026-05-04T15:00:00+00:00"


def test_plan_dispatch_skips_not_due_source():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "next_allowed_crawl_at": "2026-05-04T13:00:00+00:00",
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "not_due"


def test_plan_dispatch_next_allowed_wins_over_stale_running_status():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "next_allowed_crawl_at": "2026-05-04T11:01:56.864904+00:00",
            "last_crawl_status": "running",
            "last_crawl_started_at": "2026-05-04T06:01:56.876Z",
        },
        {"now": "2026-05-04T08:06:17.193839+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "not_due"
    assert out["next_allowed_crawl_at"] == "2026-05-04T11:01:56.864904+00:00"


def test_plan_dispatch_skips_invalid_html_configuration():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "source_status": "ready",
            "configuration_status": "invalid",
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "html_configuration_invalid"


def test_plan_dispatch_skips_running_source():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "last_crawl_status": "running",
            "last_crawl_started_at": "2026-05-04T11:30:00+00:00",
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "already_running"


def test_plan_dispatch_force_ignores_interval():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "next_allowed_crawl_at": "2026-05-04T13:00:00+00:00",
        },
        {"now": "2026-05-04T12:00:00+00:00", "dispatch_mode": "force"},
    )

    assert out["should_dispatch"] is True
    assert out["dispatch_reason"] == "manual_force"


def test_plan_dispatch_step_returns_envelope():
    result = plan_dispatch_step(
        {
            "item": {"crawl_key": "https://example.com/feed", "type": "rss", "source_status": "ready"},
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["should_dispatch"] is True


def test_cli_run_step_smoke():
    payload = {"item": {"url": "https://example.com/feed", "type": "rss"}}
    env = {**os.environ, "PYTHONPATH": "src"}
    proc = subprocess.run(
        [sys.executable, "-m", "tkcrawler.cli.run_step", "normalize_source"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert proc.returncode == 0
    result = json.loads(proc.stdout)
    assert result["ok"] is True
    assert result["items"][0]["crawl_key"] == "https://example.com/feed"
