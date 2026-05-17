import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from tkcrawler._runtime import StepError
from tkcrawler.steps.analyze_source import analyze_source_item, analyze_source_step
from tkcrawler.steps.apply_html_analysis import (
    apply_html_analysis_item,
    apply_html_analysis_step,
)
from tkcrawler.steps.build_ingest_body import (
    build_ingest_body_item,
    build_ingest_body_step,
)
from tkcrawler.steps.build_source_status_body import (
    build_source_status_body_item,
    build_source_status_body_step,
)
from tkcrawler.steps.derive_source_health import (
    derive_source_health_item,
    derive_source_health_step,
)
from tkcrawler.steps.fetch_detail import fetch_detail_item, fetch_detail_step
from tkcrawler.steps.filter_candidates import (
    filter_candidate_item,
    filter_candidates_step,
)
from tkcrawler.steps.finalize_crawl_run import (
    finalize_crawl_run_item,
    finalize_crawl_run_step,
)
from tkcrawler.steps.finalize_item import finalize_item, finalize_item_step
from tkcrawler.steps.inspect_source_policy import (
    inspect_source_policy_item,
    inspect_source_policy_step,
)
from tkcrawler.steps.limit_llm_items import limit_llm_items, limit_llm_items_step
from tkcrawler.steps.list_candidates import list_candidates_items, list_candidates_step
from tkcrawler.steps.normalize_source import (
    normalize_source_item,
    normalize_source_step,
)
from tkcrawler.steps.plan_dispatch import plan_dispatch_item, plan_dispatch_step
from tkcrawler.steps.prepare_html_analysis import (
    prepare_html_analysis_item,
    prepare_html_analysis_step,
)
from tkcrawler.steps.segment_content import segment_content_item, segment_content_step
from tkcrawler.steps.validate_source_configuration import (
    validate_source_configuration_item,
    validate_source_configuration_step,
)


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


def test_normalize_source_accepts_split_out_source_wrapper():
    out = normalize_source_item(
        {
            "source": {
                "feedUrl": "https://example.com/feed.xml",
                "crawlKey": "https://example.com/feed.xml",
                "displayTitle": "Wrapped Feed",
                "subscriberCount": 1,
            }
        }
    )

    assert out["crawl_key"] == "https://example.com/feed.xml"
    assert out["url"] == "https://example.com/feed.xml"
    assert out["name"] == "Wrapped Feed"
    assert out["subscriber_count"] == 1


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


@patch("tkcrawler.steps.analyze_source.requests.get")
def test_analyze_source_detects_rss(mock_get):
    response = Mock()
    response.headers = {"content-type": "application/rss+xml; charset=utf-8"}
    response.text = "<rss><channel><item><title>One</title></item></channel></rss>"
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    out = analyze_source_item(
        {"url": "https://example.com/feed"},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["type"] == "rss"
    assert out["source_status"] == "ready"
    assert out["analysis_error"] is None


@patch("tkcrawler.steps.analyze_source.requests.get")
def test_analyze_source_detects_html_needing_configuration(mock_get):
    response = Mock()
    response.headers = {"content-type": "text/html"}
    response.text = "<!doctype html><html><body>Articles</body></html>"
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    out = analyze_source_item(
        {"url": "https://example.com/articles"},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["type"] == "html"
    assert out["source_status"] == "needs_analysis"
    assert out["configuration_status"] == "missing"


@patch("tkcrawler.steps.analyze_source.requests.get")
def test_analyze_source_reports_fetch_error(mock_get):
    mock_get.side_effect = Exception("boom")

    out = analyze_source_item(
        {"url": "https://example.com/articles"},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "analysis_failed"
    assert "boom" in out["analysis_error"]


@patch("tkcrawler.steps.analyze_source.requests.get")
def test_analyze_source_step_returns_envelope(mock_get):
    response = Mock()
    response.headers = {"content-type": "text/html"}
    response.text = "<html></html>"
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    result = analyze_source_step(
        {
            "item": {"url": "https://example.com/articles"},
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["type"] == "html"


@patch("tkcrawler.steps.inspect_source_policy.requests.get")
def test_inspect_source_policy_extracts_http_headers_and_rss_ttl(mock_get):
    response = Mock()
    response.status_code = 200
    response.headers = {
        "etag": '"abc"',
        "last-modified": "Sat, 09 May 2026 09:00:00 GMT",
        "cache-control": "public, max-age=600",
        "content-type": "application/rss+xml",
    }
    response.text = "<rss><channel><ttl>45</ttl><item><title>One</title></item></channel></rss>"
    mock_get.return_value = response

    out = inspect_source_policy_item(
        {"url": "https://example.com/feed.xml", "type": "rss"},
        {"now": "2026-05-09T12:00:00+00:00"},
    )

    detected = json.loads(out["detected_policy_json"])
    assert detected["http_status"] == 200
    assert detected["etag"] == '"abc"'
    assert detected["last_modified"] == "Sat, 09 May 2026 09:00:00 GMT"
    assert detected["cache_max_age_seconds"] == 600
    assert detected["rss_ttl_minutes"] == 45
    assert out["detected_policy_error"] is None


@patch("tkcrawler.steps.inspect_source_policy.requests.get")
def test_inspect_source_policy_extracts_retry_after_seconds(mock_get):
    response = Mock()
    response.status_code = 429
    response.headers = {
        "retry-after": "120",
        "content-type": "text/html",
    }
    response.text = "<html></html>"
    mock_get.return_value = response

    out = inspect_source_policy_item(
        {"url": "https://example.com/articles", "type": "html"},
        {"now": "2026-05-09T12:00:00+00:00"},
    )

    detected = json.loads(out["detected_policy_json"])
    assert detected["http_status"] == 429
    assert detected["retry_after_seconds"] == 120


@patch("tkcrawler.steps.inspect_source_policy.requests.get")
def test_inspect_source_policy_reports_fetch_error(mock_get):
    mock_get.side_effect = Exception("network down")

    out = inspect_source_policy_item(
        {"url": "https://example.com/feed.xml"},
        {"now": "2026-05-09T12:00:00+00:00"},
    )

    assert json.loads(out["detected_policy_json"]) == {}
    assert out["detected_policy_error"] == "network down"


@patch("tkcrawler.steps.inspect_source_policy.requests.get")
def test_inspect_source_policy_step_returns_envelope(mock_get):
    response = Mock()
    response.status_code = 200
    response.headers = {"content-type": "text/html"}
    response.text = "<html></html>"
    mock_get.return_value = response

    result = inspect_source_policy_step(
        {
            "item": {"url": "https://example.com/articles"},
            "context": {"now": "2026-05-09T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert json.loads(result["items"][0]["detected_policy_json"])["http_status"] == 200


@patch("tkcrawler.steps.prepare_html_analysis.requests.get")
def test_prepare_html_analysis_builds_prompt_and_compacts_html(mock_get):
    response = Mock()
    response.text = (
        "<html><head><script>bad()</script></head><body>"
        "<article><a href='/a1'><h2>Article 1</h2></a></article>"
        "</body></html>"
    )
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    out = prepare_html_analysis_item(
        {"url": "https://example.com/articles"},
        {"now": "2026-05-04T12:00:00+00:00", "max_html_chars": 200},
    )

    assert out["type"] == "html"
    assert out["source_status"] == "needs_analysis"
    assert "bad()" not in out["html_analysis_input"]
    assert "article_selector" in out["html_analysis_prompt"]
    assert "https://example.com/articles" in out["html_analysis_prompt"]


@patch("tkcrawler.steps.prepare_html_analysis.requests.get")
def test_prepare_html_analysis_reports_fetch_error(mock_get):
    mock_get.side_effect = Exception("blocked")

    out = prepare_html_analysis_item(
        {"url": "https://example.com/articles"},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "analysis_failed"
    assert "blocked" in out["analysis_error"]


@patch("tkcrawler.steps.prepare_html_analysis.requests.get")
def test_prepare_html_analysis_step_returns_envelope(mock_get):
    response = Mock()
    response.text = "<html><body><a href='/a1'><h2>A</h2></a></body></html>"
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    result = prepare_html_analysis_step(
        {
            "item": {"url": "https://example.com/articles"},
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["html_analysis_prompt"]


def test_apply_html_analysis_accepts_structured_output():
    out = apply_html_analysis_item(
        {
            "url": "https://example.com/articles",
            "output": {
                "article_selector": "article",
                "main_page_anchor_selector": "a:has(h2)",
                "confidence": "high",
                "notes": "Looks stable.",
            },
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "needs_validation"
    assert out["configuration_status"] == "generated"
    assert json.loads(out["configuration_json"]) == {
        "article_selector": "article",
        "main_page_anchor_selector": "a:has(h2)",
    }
    assert out["html_analysis_confidence"] == "high"


def test_apply_html_analysis_accepts_fenced_json_text():
    out = apply_html_analysis_item(
        {
            "html_analysis_result": (
                "```json\n"
                "{\"article_selector\":\"article\",\"anchor_selector\":\"a\"}"
                "\n```"
            )
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert json.loads(out["configuration_json"])["main_page_anchor_selector"] == "a"


def test_apply_html_analysis_marks_missing_selectors_invalid():
    out = apply_html_analysis_item(
        {"output": {"article_selector": "article"}},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "configuration_invalid"
    assert out["configuration_status"] == "invalid"
    assert "main_page_anchor_selector" in out["configuration_error"]


def test_apply_html_analysis_step_returns_envelope():
    result = apply_html_analysis_step(
        {
            "item": {
                "output": {
                    "article_selector": "article",
                    "main_page_anchor_selector": "a",
                },
            },
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["configuration_status"] == "generated"


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


def test_build_ingest_body_step_accepts_flat_enrichment_output():
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


def test_plan_dispatch_uses_detected_cache_max_age_for_interval():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "detected_policy_json": json.dumps({"cache_max_age_seconds": 14400}),
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is True
    assert out["effective_policy"]["crawl_interval_minutes"] == 240
    assert out["next_allowed_crawl_at"] == "2026-05-04T16:00:00+00:00"


def test_plan_dispatch_skips_when_cache_is_fresh():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "detected_policy_checked_at": "2026-05-04T11:30:00+00:00",
            "detected_policy_json": json.dumps({"cache_max_age_seconds": 3600}),
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "cache_fresh"


def test_plan_dispatch_skips_until_detected_expires():
    out = plan_dispatch_item(
        {
            "crawl_key": "https://example.com/feed",
            "type": "rss",
            "source_status": "ready",
            "detected_policy_json": json.dumps({"expires": "Mon, 04 May 2026 13:00:00 GMT"}),
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["should_dispatch"] is False
    assert out["dispatch_reason"] == "cache_fresh"


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


def test_list_candidates_rejects_unsupported_source_type():
    with pytest.raises(StepError) as exc:
        list_candidates_items(
            {
                "crawl_key": "https://example.com/feed",
                "type": "telegram",
                "url": "https://example.com/feed",
            }
        )

    assert exc.value.code == "unsupported_source_type"


@patch("tkcrawler.candidates.rss.feedparser.parse")
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


@patch("tkcrawler.candidates.rss.feedparser.parse")
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


@patch("tkcrawler.candidates.podcast.feedparser.parse")
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
    assert out[0]["candidate"]["feed_content"] is None
    assert out[0]["candidate"]["podcast_shownotes"] == "<p>Shownotes</p>"
    assert out[0]["candidate"]["summary"] == "<p>Shownotes</p>"
    assert out[0]["candidate"]["categories"] == ["architecture"]


@patch("tkcrawler.candidates.podcast.feedparser.parse")
def test_list_candidates_podcast_preserves_rich_content_and_summary(mock_parse):
    mock_parse.return_value.entries = [
        {
            "title": "Episode 1",
            "link": "https://example.com/e1",
            "content": [{"type": "text/html", "value": "<p>Rich content</p>"}],
            "description": "<p>Shownotes</p>",
            "itunes_summary": "<p>Summary</p>",
        }
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/podcast",
            "type": "rss+podcast",
            "url": "https://example.com/podcast",
        }
    )

    candidate = out[0]["candidate"]
    assert candidate["feed_content"] == "<p>Rich content</p>"
    assert candidate["feed_content_type"] == "text/html"
    assert candidate["podcast_shownotes"] == "<p>Shownotes</p>"
    assert candidate["podcast_summary"] == "<p>Summary</p>"
    assert candidate["summary"] == "<p>Rich content</p>"


@patch("tkcrawler.candidates.podcast.feedparser.parse")
def test_list_candidates_podcast_supports_colon_itunes_summary(mock_parse):
    mock_parse.return_value.entries = [
        {
            "title": "Episode 1",
            "link": "https://example.com/e1",
            "description": "<p>Shownotes</p>",
            "itunes:summary": "<p>iTunes summary</p>",
        }
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/podcast",
            "type": "rss+podcast",
            "url": "https://example.com/podcast",
        }
    )

    assert out[0]["candidate"]["podcast_summary"] == "<p>iTunes summary</p>"


@patch("tkcrawler.candidates.podcast.feedparser.parse")
def test_list_candidates_podcast_extracts_episode_metadata(mock_parse):
    mock_parse.return_value.entries = [
        {
            "title": "Episode 42",
            "link": "https://example.com/e42",
            "description": "<p>Shownotes</p>",
            "itunes_duration": "01:02:03",
            "itunes_episode": "42",
            "itunes_season": "3",
            "itunes_episodetype": "full",
            "itunes_explicit": "no",
            "itunes_subtitle": "A deep dive",
            "itunes_image": {"href": "https://example.com/cover.jpg"},
            "enclosures": [
                {
                    "href": "https://cdn.example.com/e42.mp3",
                    "type": "audio/mpeg",
                    "length": "123456",
                }
            ],
            "podcast_chapters": [
                {
                    "href": "https://example.com/e42.chapters.json",
                    "type": "application/json+chapters",
                }
            ],
            "podcast_transcript": [
                {
                    "href": "https://example.com/e42.txt",
                    "type": "text/plain",
                }
            ],
        }
    ]

    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/podcast",
            "type": "rss+podcast",
            "url": "https://example.com/podcast",
        }
    )

    candidate = out[0]["candidate"]
    assert candidate["item_kind"] == "episode"
    assert candidate["media_url"] == "https://cdn.example.com/e42.mp3"
    assert candidate["media_type"] == "audio/mpeg"
    assert candidate["media_length_bytes"] == 123456
    assert candidate["duration_seconds"] == 3723
    assert candidate["episode_number"] == 42
    assert candidate["season_number"] == 3
    assert candidate["episode_type"] == "full"
    assert candidate["subtitle"] == "A deep dive"
    assert candidate["image_url"] == "https://example.com/cover.jpg"
    assert candidate["chapters_url"] == "https://example.com/e42.chapters.json"
    assert candidate["transcript_url"] == "https://example.com/e42.txt"


@patch("tkcrawler.candidates.rss.feedparser.parse")
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


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="""
    <html><body>
      <article><a href="/a1"><h2>Article 1</h2></a></article>
      <article><a href="/a2"><h2>Article 2</h2></a></article>
    </body></html>
    """,
)
def test_list_candidates_html_from_listing(mock_fetch):
    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "name": "Example HTML",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration": {
                "article_selector": "article",
                "main_page_anchor_selector": "a",
            },
        }
    )

    assert len(out) == 2
    assert out[0]["source_type"] == "html"
    assert out[0]["candidate"]["link"] == "https://example.com/a1"
    assert out[0]["candidate"]["title"] == "Article 1"
    assert out[0]["candidate"]["item_kind"] == "article"


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="""
    <html><body>
      <article><a href="/a1?utm_source=x"><h2>Article 1</h2></a></article>
      <article><a href="/a1"><h2>Article duplicate</h2></a></article>
    </body></html>
    """,
)
def test_list_candidates_html_deduplicates_links(mock_fetch):
    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration_json": json.dumps(
                {
                    "article_selector": "article",
                    "main_page_anchor_selector": "a",
                }
            ),
        }
    )

    assert len(out) == 1
    assert out[0]["candidate"]["link"] == "https://example.com/a1"


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="""
    <html><body>
      <article><a href="/a1"><h2>Article 1</h2></a></article>
      <article><a href="/a2"><h2>Article 2</h2></a></article>
    </body></html>
    """,
)
def test_list_candidates_html_respects_max_candidates(mock_fetch):
    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration": {
                "article_selector": "article",
                "main_page_anchor_selector": "a",
            },
            "effective_policy": {"max_candidates_per_run": 1},
        }
    )

    assert len(out) == 1
    assert out[0]["candidate"]["title"] == "Article 1"


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="<html><body><article><a href='/a1'><h2>Article 1</h2></a></article></body></html>",
)
def test_list_candidates_html_passes_policy_user_agent(mock_fetch):
    list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration": {
                "article_selector": "article",
                "main_page_anchor_selector": "a",
            },
            "effective_policy": {"user_agent": "CustomAgent/1.0"},
        }
    )

    mock_fetch.assert_called_once_with(
        "https://example.com/articles",
        headers={"User-Agent": "CustomAgent/1.0"},
    )


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value=(
        "<html><body><div><a href='/a1'><h2>Article 1</h2></a></div>"
        "<div><a href='/a2'><h2>Article 2</h2></a></div></body></html>"
    ),
)
def test_list_candidates_html_accepts_anchor_as_article_block(mock_fetch):
    out = list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration": {
                "article_selector": "div > a:has(h2)",
                "main_page_anchor_selector": "div > a:has(h2)",
            },
        }
    )

    assert [item["candidate"]["title"] for item in out] == ["Article 1", "Article 2"]
    assert [item["candidate"]["link"] for item in out] == [
        "https://example.com/a1",
        "https://example.com/a2",
    ]


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="<html><body><article><a href='/a1'><h2>Article 1</h2></a></article></body></html>",
)
def test_list_candidates_html_passes_fair_contact_headers(mock_fetch):
    list_candidates_items(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration": {
                "article_selector": "article",
                "main_page_anchor_selector": "a",
            },
            "effective_policy": {
                "contact": "mailto:crawler@example.com",
                "crawler_name": "infl0",
            },
        }
    )

    mock_fetch.assert_called_once_with(
        "https://example.com/articles",
        headers={
            "From": "mailto:crawler@example.com",
            "X-Infl0-Contact": "mailto:crawler@example.com",
            "X-Infl0-Crawler": "infl0",
        },
    )


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="<html><body><article><a href='/a1'>Article 1</a></article></body></html>",
)
def test_list_candidates_html_rejects_invalid_article_selector(mock_fetch):
    with pytest.raises(StepError) as exc_info:
        list_candidates_items(
            {
                "crawl_key": "https://example.com/articles",
                "type": "html",
                "url": "https://example.com/articles",
                "configuration": {
                    "article_selector": "article[",
                    "main_page_anchor_selector": "a",
                },
            }
        )

    assert exc_info.value.code == "invalid_configuration"
    assert "Invalid HTML article selector" in exc_info.value.message


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="<html><body><article><a href='/a1'>Article 1</a></article></body></html>",
)
def test_list_candidates_html_rejects_invalid_anchor_selector(mock_fetch):
    with pytest.raises(StepError) as exc_info:
        list_candidates_items(
            {
                "crawl_key": "https://example.com/articles",
                "type": "html",
                "url": "https://example.com/articles",
                "configuration": {
                    "article_selector": "article",
                    "main_page_anchor_selector": "a[",
                },
            }
        )

    assert exc_info.value.code == "invalid_configuration"
    assert "Invalid HTML anchor selector" in exc_info.value.message


@patch(
    "tkcrawler.candidates.html.HtmlFetcher._fetch_html",
    return_value="<html><body><main><p>Layout changed.</p></main></body></html>",
)
def test_validate_source_configuration_marks_changed_html_structure_invalid(mock_fetch):
    out = validate_source_configuration_item(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration_json": json.dumps(
                {"article_selector": "article", "main_page_anchor_selector": "a"}
            ),
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "configuration_invalid"
    assert out["configuration_status"] == "invalid"
    assert out["sample_candidate_count"] == 0
    assert out["configuration_error"] == "HTML configuration did not find candidates"


@patch("tkcrawler.steps.validate_source_configuration.list_candidates_items")
def test_validate_source_configuration_marks_html_valid(mock_list):
    mock_list.return_value = [{"candidate": {"id": "a1"}}]

    out = validate_source_configuration_item(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration_json": json.dumps(
                {"article_selector": "article", "main_page_anchor_selector": "a"}
            ),
        },
        {"now": "2026-05-04T12:00:00+00:00", "sample_candidate_limit": 3},
    )

    assert out["source_status"] == "ready"
    assert out["configuration_status"] == "valid"
    assert out["sample_candidate_count"] == 1
    assert mock_list.call_args.args[0]["effective_policy"]["max_candidates_per_run"] == 3


@patch("tkcrawler.steps.validate_source_configuration.list_candidates_items", return_value=[])
def test_validate_source_configuration_marks_empty_html_invalid(mock_list):
    out = validate_source_configuration_item(
        {
            "crawl_key": "https://example.com/articles",
            "type": "html",
            "url": "https://example.com/articles",
            "configuration_json": json.dumps(
                {"article_selector": "article", "main_page_anchor_selector": "a"}
            ),
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "configuration_invalid"
    assert out["configuration_status"] == "invalid"
    assert out["sample_candidate_count"] == 0


def test_validate_source_configuration_accepts_rss():
    out = validate_source_configuration_item(
        {"crawl_key": "https://example.com/feed", "type": "rss"},
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["source_status"] == "ready"
    assert out["configuration_error"] is None


@patch("tkcrawler.steps.validate_source_configuration.list_candidates_items")
def test_validate_source_configuration_step_returns_envelope(mock_list):
    mock_list.return_value = [{"candidate": {"id": "a1"}}]

    result = validate_source_configuration_step(
        {
            "item": {
                "crawl_key": "https://example.com/articles",
                "type": "html",
                "url": "https://example.com/articles",
                "configuration_json": json.dumps(
                    {"article_selector": "article", "main_page_anchor_selector": "a"}
                ),
            },
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["configuration_status"] == "valid"


def test_filter_candidate_fetches_unknown_candidate():
    out = filter_candidate_item(
        {
            "article_id": "a1",
            "candidate": {
                "id": "a1",
                "publishedAt": "Thu, 22 May 2025 12:50:50 GMT",
            },
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["candidate_decision"] == "fetch"
    assert out["candidate_reason"] == "new_candidate"
    assert out["candidate_history_exists"] is False
    assert out["candidate_published_at"] == "2025-05-22T12:50:50+00:00"


def test_filter_candidate_skips_known_old_candidate():
    out = filter_candidate_item(
        {
            "article_id": "a1",
            "candidate": {
                "id": "a1",
                "publishedAt": "2026-04-20T12:00:00+00:00",
            },
            "history": {"exists": True},
            "effective_policy": {"refresh_window_days": 7},
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["candidate_decision"] == "skip_too_old"
    assert out["candidate_reason"] == "known_candidate_outside_refresh_window"


def test_filter_candidate_fetches_known_recent_candidate():
    out = filter_candidate_item(
        {
            "article_id": "a1",
            "candidate": {
                "id": "a1",
                "publishedAt": "2026-05-02T12:00:00+00:00",
            },
            "history": {"exists": True},
            "effective_policy": {"refresh_window_days": 7},
        },
        {"now": "2026-05-04T12:00:00+00:00"},
    )

    assert out["candidate_decision"] == "fetch"
    assert out["candidate_reason"] == "known_candidate_within_refresh_window"


def test_filter_candidate_step_returns_envelope():
    result = filter_candidates_step(
        {
            "item": {
                "article_id": "a1",
                "candidate": {"id": "a1", "publishedAt": "2026-05-02T12:00:00+00:00"},
            },
            "context": {"now": "2026-05-04T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["candidate_decision"] == "fetch"


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
def test_fetch_detail_rss_loads_detail_page(mock_markdown):
    out = fetch_detail_item(
        {
            "source_type": "rss",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "a1",
                "title": "Article",
                "link": "https://example.com/article",
                "summary": "Summary",
                "author": "Author",
                "publishedAt": "2026-05-04T09:00:00Z",
                "updatedAt": None,
                "item_kind": "article",
            },
        }
    )

    mock_markdown.assert_called_once_with("https://example.com/article", verify=True, headers={})
    assert out["article_id"] == "a1"
    assert out["article"]["content_md"] == "# Article\n\nBody"
    assert out["content_md"] == "# Article\n\nBody"


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
def test_fetch_detail_passes_verify_context(mock_markdown):
    fetch_detail_item(
        {
            "source_type": "rss",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "a1",
                "title": "Article",
                "link": "https://example.com/article",
            },
        },
        {"verify": "/etc/ssl/certs/ca-certificates.crt"},
    )

    mock_markdown.assert_called_once_with(
        "https://example.com/article",
        verify="/etc/ssl/certs/ca-certificates.crt",
        headers={},
    )


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
def test_fetch_detail_passes_policy_user_agent(mock_markdown):
    fetch_detail_item(
        {
            "source_type": "rss",
            "candidate_decision": "fetch",
            "effective_policy": {"user_agent": "CustomAgent/1.0"},
            "candidate": {
                "id": "a1",
                "title": "Article",
                "link": "https://example.com/article",
            },
        }
    )

    mock_markdown.assert_called_once_with(
        "https://example.com/article",
        verify=True,
        headers={"User-Agent": "CustomAgent/1.0"},
    )


@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown", return_value="Shownotes")
def test_fetch_detail_podcast_prefers_feed_content(mock_markdown):
    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "<p>Summary</p>",
                "publishedAt": "2026-05-04T09:00:00Z",
                "has_feed_content": True,
                "feed_content": "<p>Shownotes</p>",
                "item_kind": "episode",
                "categories": ["architecture"],
                "media_url": "https://cdn.example.com/e1.mp3",
                "media_type": "audio/mpeg",
                "media_length_bytes": 1234,
                "duration_seconds": 1800,
                "episode_number": 1,
                "season_number": 2,
                "episode_type": "full",
                "subtitle": "Episode subtitle",
                "image_url": "https://example.com/cover.jpg",
                "chapters_url": "https://example.com/chapters.json",
                "chapters_type": "application/json+chapters",
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nShownotes"
    assert out["article"]["categories"] == ["architecture"]
    assert out["article"]["item_kind"] == "episode"
    assert out["article"]["shownotes_md"] == "Shownotes"
    assert out["article"]["media_url"] == "https://cdn.example.com/e1.mp3"
    assert out["article"]["duration_seconds"] == 1800
    assert out["article"]["episode_number"] == 1
    assert out["article"]["season_number"] == 2
    assert out["article"]["chapters_url"] == "https://example.com/chapters.json"


@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown")
def test_fetch_detail_podcast_rich_content_wins(mock_markdown):
    mock_markdown.side_effect = ["Rich content"]

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "<p>Candidate summary</p>",
                "feed_content": "<p>Rich content</p>",
                "podcast_shownotes": "<p>Shownotes</p>",
                "podcast_summary": "<p>Summary</p>",
                "item_kind": "episode",
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nRich content"
    assert out["article"]["shownotes_md"] == "Rich content"
    assert mock_markdown.call_count == 1


@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown")
def test_fetch_detail_podcast_combines_shownotes_and_summary(mock_markdown):
    mock_markdown.side_effect = ["Shownotes", "Summary"]

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "podcast_shownotes": "<p>Shownotes</p>",
                "podcast_summary": "<p>Summary</p>",
                "item_kind": "episode",
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nShownotes\n\nSummary"
    assert out["article"]["shownotes_md"] == "Shownotes\n\nSummary"


@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown")
def test_fetch_detail_podcast_deduplicates_shownotes_and_summary(mock_markdown):
    mock_markdown.side_effect = ["Same text", "same text"]

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "podcast_shownotes": "<p>Same text</p>",
                "podcast_summary": "<p>same text</p>",
                "item_kind": "episode",
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nSame text"
    assert out["article"]["shownotes_md"] == "Same text"


@patch("tkcrawler.fetchers._detail.requests.get")
@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown", return_value="Shownotes")
def test_fetch_detail_podcast_fetches_chapters(mock_markdown, mock_get):
    response = Mock()
    response.json.return_value = {
        "version": "1.2.0",
        "chapters": [
            {
                "startTime": 0,
                "title": "Intro",
                "url": "https://example.com/intro",
                "img": "https://example.com/intro.jpg",
            },
            {"startTime": "00:05:12", "title": "Main Topic"},
        ],
    }
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "<p>Summary</p>",
                "has_feed_content": True,
                "feed_content": "<p>Shownotes</p>",
                "item_kind": "episode",
                "chapters_url": "https://example.com/chapters.json",
            },
        },
        {"verify": "/etc/ssl/certs/ca-certificates.crt"},
    )

    mock_get.assert_called_once_with(
        "https://example.com/chapters.json",
        timeout=20,
        verify="/etc/ssl/certs/ca-certificates.crt",
        headers={},
    )
    assert out["article"]["chapters"] == [
        {
            "start_seconds": 0,
            "title": "Intro",
            "url": "https://example.com/intro",
            "image_url": "https://example.com/intro.jpg",
        },
        {"start_seconds": 312, "title": "Main Topic"},
    ]


@patch("tkcrawler.fetchers._detail.requests.get")
@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown", return_value="Summary only")
def test_fetch_detail_podcast_keeps_chapter_fetch_error(mock_markdown, mock_get):
    mock_get.side_effect = RuntimeError("chapters unavailable")

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "Summary",
                "has_feed_content": False,
                "item_kind": "episode",
                "chapters_url": "https://example.com/chapters.json",
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nSummary only"
    assert out["article"]["shownotes_md"] == "Summary only"
    assert "chapters unavailable" in out["article"]["chapters_fetch_error"]


@patch("tkcrawler.fetchers._detail.requests.get")
@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown", return_value="Summary only")
def test_fetch_detail_podcast_fetches_plain_transcript(mock_markdown, mock_get):
    response = Mock()
    response.text = "WEBVTT\n\n00:00:00.000 --> 00:00:03.000\nWelcome.\n\n00:00:03.000 --> 00:00:05.000\nMain topic."
    response.headers = {"content-type": "text/vtt"}
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "Summary",
                "item_kind": "episode",
                "transcript_url": "https://example.com/e1.vtt",
                "transcript_type": "text/vtt",
            },
        },
        {"verify": "/etc/ssl/certs/ca-certificates.crt"},
    )

    mock_get.assert_called_once_with(
        "https://example.com/e1.vtt",
        timeout=20,
        verify="/etc/ssl/certs/ca-certificates.crt",
        headers={},
    )
    assert out["article"]["transcript_md"] == "Welcome.\nMain topic."
    assert out["article"]["transcript_url"] == "https://example.com/e1.vtt"


@patch("tkcrawler.fetchers._detail.requests.get")
@patch("tkcrawler.fetchers._detail.text.convert_from_html_to_markdown", return_value="Summary only")
def test_fetch_detail_podcast_keeps_transcript_fetch_error(mock_markdown, mock_get):
    mock_get.side_effect = RuntimeError("transcript unavailable")

    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "Summary",
                "item_kind": "episode",
                "transcript_url": "https://example.com/e1.txt",
                "transcript_type": "text/plain",
            },
        }
    )

    assert out["article"]["shownotes_md"] == "Summary only"
    assert "transcript unavailable" in out["article"]["transcript_fetch_error"]


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Detail\n\nBody")
def test_fetch_detail_podcast_uses_detail_page_when_no_feed_summary(mock_markdown):
    out = fetch_detail_item(
        {
            "source_type": "rss+podcast",
            "candidate_decision": "fetch",
            "candidate": {
                "id": "e1",
                "title": "Episode",
                "link": "https://example.com/e1",
                "summary": "",
                "has_feed_content": False,
                "item_kind": "episode",
            },
        }
    )

    mock_markdown.assert_called_once_with("https://example.com/e1", verify=True, headers={})
    assert out["article"]["content_md"] == "# Detail\n\nBody"
    assert "shownotes_md" not in out["article"]


def test_fetch_detail_rejects_skipped_candidate():
    try:
        fetch_detail_item(
            {
                "candidate_decision": "skip_too_old",
                "candidate": {"id": "a1", "link": "https://example.com/article"},
            }
        )
    except Exception as exc:
        assert "Candidate decision is not fetch" in str(exc)
    else:
        raise AssertionError("Expected exception")


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article")
def test_fetch_detail_step_returns_envelope(mock_markdown):
    result = fetch_detail_step(
        {
            "item": {
                "source_type": "rss",
                "candidate_decision": "fetch",
                "candidate": {"id": "a1", "title": "Article", "link": "https://example.com/article"},
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["article"]["id"] == "a1"


def test_segment_content_splits_markdown_headings():
    item = {
        "article": {
            "id": "long-1",
            "title": "Long Form",
            "link": "https://example.com/long",
            "summary": "A long item",
            "author": "Ada",
            "publishedAt": "2026-05-10T08:00:00+00:00",
            "updatedAt": None,
            "source_type": "html",
            "content_md": "# Intro\n\nOpening text.\n\n## Part One\n\nBody.\n\n## Part Two\n\nMore body.",
        }
    }

    out = segment_content_item(item)

    assert out["segment_count"] == 3
    assert [segment["title"] for segment in out["segments"]] == ["Intro", "Part One", "Part Two"]
    assert out["segments"][0]["item_kind"] == "section"
    assert out["segments"][0]["parent_item_id"] == "long-1"
    assert out["segments"][0]["position"] == 1
    assert out["segments"][0]["link"] == "https://example.com/long"
    assert out["segments"][1]["content_md"] == "## Part One\n\nBody."
    assert out["segments"][0]["id"] == segment_content_item(item)["segments"][0]["id"]


def test_segment_content_returns_single_segment_without_headings():
    out = segment_content_item(
        {
            "id": "plain-1",
            "title": "Plain Long Form",
            "link": "https://example.com/plain",
            "content_md": "No headings here, just one long text.",
        }
    )

    assert out["segment_count"] == 1
    assert out["segments"][0]["title"] == "Plain Long Form"
    assert out["segments"][0]["content_md"] == "No headings here, just one long text."


def test_segment_content_step_returns_envelope():
    result = segment_content_step(
        {
            "item": {
                "article": {
                    "id": "long-1",
                    "title": "Long Form",
                    "link": "https://example.com/long",
                    "content_md": "# Intro\n\nBody.",
                }
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["segment_count"] == 1


def test_finalize_crawl_run_marks_success_from_aggregates():
    out = finalize_crawl_run_item(
        {
            "crawl_key": "https://example.com/feed",
            "candidateCount": 4,
            "skipped": [{"id": "a4"}],
            "processed": [{"id": "a1"}, {"id": "a2"}],
            "unchanged": [{"id": "a3"}],
            "fetchErrorred": [],
            "llmFailed": [],
            "consecutive_error_count": 2,
        },
        {"now": "2026-05-08T12:00:00+00:00"},
    )

    assert out["last_crawl_status"] == "success"
    assert out["last_crawl_error"] is None
    assert out["last_successful_crawl_at"] == "2026-05-08T12:00:00+00:00"
    assert out["crawl_total_count"] == 4
    assert out["crawl_candidate_count"] == 4
    assert out["crawl_skipped_count"] == 1
    assert out["crawl_processed_count"] == 2
    assert out["crawl_unchanged_count"] == 1
    assert out["consecutive_error_count"] == 0


def test_finalize_crawl_run_marks_partial_failure():
    out = finalize_crawl_run_item(
        {
            "crawl_key": "https://example.com/feed",
            "processed": 2,
            "unchanged": 1,
            "fetchErrored": [{"id": "a4"}],
            "llmFailed": 1,
        },
        {"now": "2026-05-08T12:00:00+00:00"},
    )

    assert out["last_crawl_status"] == "partial_failed"
    assert out["crawl_fetch_error_count"] == 1
    assert out["crawl_llm_failed_count"] == 1
    assert out["last_crawl_error"] == "1 fetch error(s), 1 LLM failure(s)"


def test_finalize_crawl_run_marks_failed_without_successes():
    out = finalize_crawl_run_item(
        {
            "crawl_key": "https://example.com/feed",
            "fetchErrorred": [{"id": "a1"}],
            "consecutive_error_count": 2,
        },
        {"now": "2026-05-08T12:00:00+00:00"},
    )

    assert out["last_crawl_status"] == "failed"
    assert out["consecutive_error_count"] == 3
    assert out["last_crawl_error"] == "1 fetch error(s)"


def test_finalize_crawl_run_marks_no_candidates_as_success():
    out = finalize_crawl_run_item(
        {
            "crawl_key": "https://example.com/feed",
            "candidateCount": 0,
        },
        {"now": "2026-05-08T12:00:00+00:00"},
    )

    assert out["last_crawl_status"] == "success"
    assert out["crawl_total_count"] == 0
    assert out["crawl_candidate_count"] == 0
    assert out["last_crawl_error"] is None


def test_finalize_crawl_run_step_returns_envelope():
    result = finalize_crawl_run_step(
        {
            "item": {
                "crawl_key": "https://example.com/feed",
                "processed": 1,
            },
            "context": {"now": "2026-05-08T12:00:00+00:00"},
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["last_crawl_status"] == "success"


def test_derive_source_health_marks_pending_source():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/feed",
            "active": True,
            "source_status": "ready",
        }
    )

    assert out["source_health_status"] == "pending"
    assert out["source_health_reason"] == "never_crawled"
    assert out["operator_attention"] is False


def test_derive_source_health_marks_needs_setup():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/articles",
            "source_status": "needs_analysis",
            "type": "html",
        }
    )

    assert out["source_health_status"] == "needs_setup"
    assert out["source_health_reason"] == "needs_analysis"


def test_derive_source_health_marks_degraded_with_attention():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_status": "ready",
            "last_crawl_status": "partial_failed",
            "crawl_fetch_error_count": 3,
            "crawl_processed_count": 0,
        }
    )

    assert out["source_health_status"] == "degraded"
    assert out["operator_attention"] is True
    assert out["operator_attention_reason"] == "fetch_errors_without_processed_items"


def test_derive_source_health_marks_blocked_from_detected_policy():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_status": "ready",
            "last_crawl_status": "success",
            "detected_policy_json": json.dumps({"http_status": 403}),
        }
    )

    assert out["source_health_status"] == "blocked"
    assert out["source_health_reason"] == "http_403"
    assert out["operator_attention"] is True


def test_derive_source_health_ignores_invalid_detected_policy_json():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_status": "ready",
            "last_crawl_status": "success",
            "crawl_candidate_count": 1,
            "detected_policy_json": "not-json",
        }
    )

    assert out["source_health_status"] == "healthy"
    assert out["source_health_reason"] == "recent_success"
    assert json.loads(out["source_health_json"])["policy"]["detected"] == {}


def test_derive_source_health_marks_quiet_no_candidates():
    out = derive_source_health_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_status": "ready",
            "last_crawl_status": "success",
            "crawl_candidate_count": 0,
        }
    )

    assert out["source_health_status"] == "quiet"
    assert out["source_health_reason"] == "no_candidates"
    assert out["operator_attention"] is False


def test_derive_source_health_step_returns_envelope():
    result = derive_source_health_step(
        {
            "item": {
                "crawl_key": "https://example.com/feed",
                "source_status": "ready",
                "last_crawl_status": "success",
                "crawl_candidate_count": 1,
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["source_health_status"] == "healthy"


def test_build_source_status_body_includes_health_and_schedule():
    out = build_source_status_body_item(
        {
            "crawl_key": "https://example.com/feed",
            "name": "Example",
            "type": "rss",
            "url": "https://example.com/feed",
            "active": True,
            "source_status": "ready",
            "source_health_status": "healthy",
            "source_health_reason": "recent_success",
            "source_health_json": json.dumps({"status": "healthy"}),
            "operator_attention": False,
            "last_dispatch_reason": "due",
            "last_crawl_status": "success",
            "last_crawl_started_at": "2026-05-09T08:16:00Z",
            "last_crawl_finished_at": "2026-05-09T08:19:00Z",
            "last_successful_crawl_at": "2026-05-09T08:19:00Z",
            "next_allowed_crawl_at": "2026-05-09T11:16:00Z",
            "crawl_total_count": 12,
            "crawl_candidate_count": 10,
            "crawl_skipped_count": 7,
            "crawl_processed_count": 3,
            "crawl_fetch_error_count": 0,
            "crawl_unchanged_count": 0,
            "crawl_llm_failed_count": 0,
            "consecutive_error_count": 0,
            "effective_policy": {"crawl_interval_minutes": 180},
            "detected_policy_json": json.dumps({"http_status": 200, "cache_max_age_seconds": 600}),
            "detected_policy_checked_at": "2026-05-09T10:20:41Z",
            "last_crawl_result_json": json.dumps({"total_count": 12}),
        }
    )

    body = out["infl0_source_status_body"]
    assert body["crawlKey"] == "https://example.com/feed"
    assert body["sourceHealthStatus"] == "healthy"
    assert body["nextAllowedCrawlAt"] == "2026-05-09T11:16:00Z"
    assert body["crawlCandidateCount"] == 10
    assert body["effectivePolicy"] == {"crawl_interval_minutes": 180}
    assert body["detectedPolicy"]["cache_max_age_seconds"] == 600
    assert body["lastCrawlResult"] == {"total_count": 12}


def test_build_source_status_body_uses_documented_schema_fields():
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "docs",
        "schemas",
        "source-status.schema.json",
    )
    with open(schema_path, encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    out = build_source_status_body_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_health_status": "pending",
        }
    )

    assert set(out["infl0_source_status_body"]) == set(schema["properties"])


def test_build_source_status_body_step_returns_envelope():
    result = build_source_status_body_step(
        {
            "item": {
                "crawl_key": "https://example.com/feed",
                "source_health_status": "pending",
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["infl0_source_status_body"]["crawlKey"] == "https://example.com/feed"


def test_build_source_status_body_ignores_invalid_diagnostic_json():
    out = build_source_status_body_item(
        {
            "crawl_key": "https://example.com/feed",
            "last_crawl_result_json": "not-json",
            "detected_policy_json": "[1, 2]",
        }
    )

    body = out["infl0_source_status_body"]
    assert body["crawlKey"] == "https://example.com/feed"
    assert body["sourceHealthStatus"] == "pending"
    assert body["sourceHealthReason"] == "never_crawled"
    assert body["lastCrawlResult"] is None
    assert body["detectedPolicy"] is None


def test_build_source_status_body_keeps_explicit_health_when_never_crawled():
    out = build_source_status_body_item(
        {
            "crawl_key": "https://example.com/feed",
            "source_health_status": "needs_setup",
            "source_health_reason": "needs_analysis",
            "last_crawl_result_json": "not-json",
        }
    )

    body = out["infl0_source_status_body"]
    assert body["sourceHealthStatus"] == "needs_setup"
    assert body["sourceHealthReason"] == "needs_analysis"


@patch("tkcrawler.infl0_payload.tldextract.extract")
def test_finalize_item_sets_metadata(mock_extract):
    mock_extract.return_value.top_domain_under_public_suffix = "example.com"

    out = finalize_item(
        {
            "source_type": "rss",
            "url": "https://feeds.example.com/atom",
            "article": {
                "id": "a1",
                "title": "Article",
                "link": "https://example.com/article",
                "content_md": "Body",
            },
        }
    )

    assert out["article_id"] == "a1"
    assert out["item_id"] == "a1"
    assert out["content_hash"]
    assert out["article"]["content_hash"] == out["content_hash"]
    assert out["article"]["source_type"] == "rss"
    assert out["article"]["tld"] == "example.com"


@patch("tkcrawler.infl0_payload.tldextract.extract")
def test_finalize_item_step_returns_envelope(mock_extract):
    mock_extract.return_value.top_domain_under_public_suffix = "example.com"

    result = finalize_item_step(
        {
            "item": {
                "source_type": "rss",
                "url": "https://feeds.example.com/atom",
                "article": {
                    "id": "a1",
                    "title": "Article",
                    "link": "https://example.com/article",
                    "content_md": "Body",
                },
            }
        }
    )

    assert result["ok"] is True
    assert result["items"][0]["content_hash"]


def test_limit_llm_items_respects_policy_per_source():
    out = limit_llm_items(
        [
            {"crawl_key": "s1", "article_id": "a1", "effective_policy": {"max_llm_items_per_run": 2}},
            {"crawl_key": "s1", "article_id": "a2", "effective_policy": {"max_llm_items_per_run": 2}},
            {"crawl_key": "s1", "article_id": "a3", "effective_policy": {"max_llm_items_per_run": 2}},
        ]
    )

    assert [item["llm_decision"] for item in out] == ["process", "process", "skip_run_limit"]
    assert out[2]["llm_reason"] == "max_llm_items_per_run_reached"


def test_limit_llm_items_separates_sources():
    out = limit_llm_items(
        [
            {"crawl_key": "s1", "article_id": "a1", "effective_policy": {"max_llm_items_per_run": 1}},
            {"crawl_key": "s2", "article_id": "b1", "effective_policy": {"max_llm_items_per_run": 1}},
            {"crawl_key": "s1", "article_id": "a2", "effective_policy": {"max_llm_items_per_run": 1}},
        ]
    )

    assert [item["llm_decision"] for item in out] == ["process", "process", "skip_run_limit"]


def test_limit_llm_items_allows_unlimited_by_default():
    out = limit_llm_items(
        [
            {"crawl_key": "s1", "article_id": "a1"},
            {"crawl_key": "s1", "article_id": "a2"},
        ]
    )

    assert [item["llm_decision"] for item in out] == ["process", "process"]
    assert [item["llm_reason"] for item in out] == ["no_run_limit", "no_run_limit"]


def test_limit_llm_items_step_accepts_items_list():
    result = limit_llm_items_step(
        {
            "item": {
                "items": [
                    {"crawl_key": "s1", "article_id": "a1"},
                    {"crawl_key": "s1", "article_id": "a2"},
                ]
            },
            "context": {"max_llm_items_per_run": 1},
        }
    )

    assert result["ok"] is True
    assert [item["llm_decision"] for item in result["items"]] == ["process", "skip_run_limit"]


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
