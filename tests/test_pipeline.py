from unittest.mock import patch

from tkcrawler.fetch import fetch_entries_for_source
from tkcrawler.pipeline import crawl_source_ingest_bodies, crawl_source_items


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_crawl_source_items_runs_step_flow(mock_parse, mock_markdown):
    mock_parse.return_value.entries = [
        {
            "title": "Article",
            "link": "https://example.com/article",
            "summary": "Summary",
            "published": "2026-05-10T08:00:00+00:00",
        }
    ]

    items = crawl_source_items(
        {
            "crawl_key": "https://example.com/feed.xml",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "source_status": "ready",
        },
        context={"now": "2026-05-13T10:00:00+00:00"},
    )

    assert len(items) == 1
    assert items[0]["article"]["content_md"] == "# Article\n\nBody"
    assert items[0]["article"]["item_kind"] == "article"
    assert items[0]["content_hash"]
    mock_markdown.assert_called_once()


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_crawl_source_items_uses_history_lookup(mock_parse, mock_markdown):
    mock_parse.return_value.entries = [
        {
            "title": "Old Article",
            "link": "https://example.com/old",
            "summary": "Summary",
            "published": "2020-01-01T08:00:00+00:00",
        }
    ]

    items = crawl_source_items(
        {
            "crawl_key": "https://example.com/feed.xml",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "source_status": "ready",
        },
        history_lookup=lambda _article_id: {"exists": True},
        context={"now": "2026-05-13T10:00:00+00:00"},
    )

    assert len(items) == 1
    assert items[0]["candidate_decision"] == "skip_too_old"
    assert "article" not in items[0]
    mock_markdown.assert_not_called()


@patch("tkcrawler.steps.fetch_detail.HtmlFetcher.generate_markdown_from_url", return_value="# Article\n\nBody")
@patch("tkcrawler.steps.list_candidates.feedparser.parse")
def test_crawl_source_ingest_bodies_returns_flat_infl0_payload(mock_parse, _mock_markdown):
    mock_parse.return_value.entries = [
        {
            "title": "Article",
            "link": "https://example.com/article",
            "summary": "Summary",
            "published": "2026-05-10T08:00:00+00:00",
        }
    ]

    bodies = crawl_source_ingest_bodies(
        {
            "crawl_key": "https://example.com/feed.xml",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "source_status": "ready",
        },
        context={"now": "2026-05-13T10:00:00+00:00"},
    )

    assert len(bodies) == 1
    assert bodies[0]["crawlKey"] == "https://example.com/feed.xml"
    assert bodies[0]["item_kind"] == "article"
    assert bodies[0]["content_md"] == "# Article\n\nBody"


@patch("tkcrawler.fetch.crawl_source_items")
def test_fetch_entries_for_source_delegates_to_step_pipeline(mock_crawl_source_items):
    mock_crawl_source_items.return_value = [
        {"article": {"id": "a1", "title": "Article"}},
        {"candidate_decision": "fetch_failed", "fetch_detail_error": "boom"},
    ]

    entries = fetch_entries_for_source({"type": "rss", "url": "https://example.com/feed.xml"})

    assert entries == [{"id": "a1", "title": "Article"}]
    mock_crawl_source_items.assert_called_once()
