import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

from tkcrawler.steps.build_ingest_body import build_ingest_body_item, build_ingest_body_step
from tkcrawler.steps.filter_candidates import filter_candidate_item, filter_candidates_step
from tkcrawler.steps.fetch_detail import fetch_detail_item, fetch_detail_step
from tkcrawler.steps.finalize_item import finalize_item, finalize_item_step
from tkcrawler.steps.limit_llm_items import limit_llm_items, limit_llm_items_step
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
