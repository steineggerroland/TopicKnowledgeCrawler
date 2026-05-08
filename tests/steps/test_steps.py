import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

from tkcrawler.steps.analyze_source import analyze_source_item, analyze_source_step
from tkcrawler.steps.apply_html_analysis import apply_html_analysis_item, apply_html_analysis_step
from tkcrawler.steps.build_ingest_body import build_ingest_body_item, build_ingest_body_step
from tkcrawler.steps.filter_candidates import filter_candidate_item, filter_candidates_step
from tkcrawler.steps.fetch_detail import fetch_detail_item, fetch_detail_step
from tkcrawler.steps.finalize_crawl_run import finalize_crawl_run_item, finalize_crawl_run_step
from tkcrawler.steps.finalize_item import finalize_item, finalize_item_step
from tkcrawler.steps.limit_llm_items import limit_llm_items, limit_llm_items_step
from tkcrawler.steps.list_candidates import list_candidates_items, list_candidates_step
from tkcrawler.steps.normalize_source import normalize_source_item, normalize_source_step
from tkcrawler.steps.plan_dispatch import plan_dispatch_item, plan_dispatch_step
from tkcrawler.steps.prepare_html_analysis import prepare_html_analysis_item, prepare_html_analysis_step
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


@patch(
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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
    "tkcrawler.steps.list_candidates.HtmlFetcher._fetch_html",
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


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
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


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
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


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
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


@patch("tkcrawler.steps.fetch_detail.text_processor.convert_from_html_to_markdown", return_value="Shownotes")
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
            },
        }
    )

    assert out["article"]["content_md"] == "# Episode\n\nShownotes"
    assert out["article"]["categories"] == ["architecture"]


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


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article")
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


def test_finalize_crawl_run_marks_success_from_aggregates():
    out = finalize_crawl_run_item(
        {
            "crawl_key": "https://example.com/feed",
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
    assert out["crawl_total_count"] == 3
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


@patch("tkcrawler.infl0_payload.tldextract.extract")
def test_finalize_item_sets_metadata(mock_extract):
    mock_extract.return_value.registered_domain = "example.com"

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
    mock_extract.return_value.registered_domain = "example.com"

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
