import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

from tkcrawler.steps.build_ingest_body import build_ingest_body_item, build_ingest_body_step
from tkcrawler.steps.list_candidates import list_candidates_items, list_candidates_step
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


@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_list_candidates_rss_without_detail_fetch(mock_parse):
    mock_parse.return_value.entries = [
        Mock(
            title="Article 1",
            link="https://example.com/1?utm_source=x",
            summary="Summary 1",
            author="Author",
            published="2026-05-04T09:00:00Z",
            updated="2026-05-04T10:00:00Z",
        ),
        Mock(title="Article duplicate", link="https://example.com/1", summary="Duplicate"),
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/feed",
            "name": "Example",
            "type": "rss",
            "url": "https://example.com/feed",
        }
    )

    assert len(out) == 1
    assert out[0]["source_type"] == "rss"
    assert out[0]["article_id"]
    assert out[0]["candidate"]["link"] == "https://example.com/1"
    assert out[0]["candidate"]["item_kind"] == "article"
    assert out[0]["candidate"]["has_feed_content"] is False


@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_list_candidates_respects_max_entries(mock_parse):
    mock_parse.return_value.entries = [
        Mock(title="Article 1", link="https://example.com/1", summary="Summary 1"),
        Mock(title="Article 2", link="https://example.com/2", summary="Summary 2"),
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "url": "https://example.com/feed",
            "effective_policy": {"max_entries_per_run": 1},
        }
    )

    assert len(out) == 1
    assert out[0]["candidate"]["title"] == "Article 1"


@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_list_candidates_podcast_uses_feed_description(mock_parse):
    mock_parse.return_value.entries = [
        {
            "title": "Episode 1",
            "link": "https://example.com/e1",
            "description": "<p>Shownotes</p>",
            "published": "2026-05-04T09:00:00Z",
            "tags": [{"term": "architecture"}],
        }
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/podcast",
            "type": "rss+podcast",
            "url": "https://example.com/podcast",
        }
    )

    assert len(out) == 1
    assert out[0]["candidate"]["item_kind"] == "episode"
    assert out[0]["candidate"]["has_feed_content"] is True
    assert out[0]["candidate"]["feed_content"] == "<p>Shownotes</p>"
    assert out[0]["candidate"]["categories"] == ["architecture"]


@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_list_candidates_step_returns_envelope(mock_parse):
    mock_parse.return_value.entries = [
        Mock(title="Article 1", link="https://example.com/1", summary="Summary 1"),
    ]

    result = list_candidates_step(
        {
            "item": {
                "crawl_key": "https://example.com/feed",
                "type": "rss",
                "url": "https://example.com/feed",
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["candidate"]["title"] == "Article 1"


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
