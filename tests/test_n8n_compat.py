import json

import pytest

from src.crawler.n8n_compat.crawl_key import normalize_feed_url
from src.crawler.n8n_compat.datatable import row_to_source
from src.crawler.n8n_compat.infl0_payload import build_ingest_body, finalize_entry_metadata


def test_normalize_feed_url_trailing_slash_and_hash():
    assert normalize_feed_url("HTTPS://Example.com/feed/") == "https://example.com/feed"
    assert normalize_feed_url("https://example.com/path#frag") == "https://example.com/path"


def test_normalize_feed_url_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        normalize_feed_url("  ")


def test_row_to_source_with_configuration_json_string():
    row = {
        "name": "Reddit",
        "type": "html",
        "url": "https://reddit.com/r/x",
        "configuration_json": json.dumps(
            {"article_selector": "main article", "main_page_anchor_selector": "a"}
        ),
    }
    s = row_to_source(row)
    assert s["configuration"]["article_selector"] == "main article"


def test_build_ingest_body_includes_crawl_key_and_enrichment():
    entry = {"id": "a1", "title": "T", "link": "https://x", "content_md": "# hi"}
    body = build_ingest_body(
        crawl_key="https://feed.example/atom",
        entry=entry,
        enrichment={
            "teaser": "short",
            "summary_long": "long",
            "category": ["factual information"],
            "tags": ["a"],
            "seriousness_rating": "high",
        },
    )
    assert body["crawlKey"] == "https://feed.example/atom"
    assert body["teaser"] == "short"
    assert body["category"] == ["factual information"]


def test_finalize_entry_metadata_sets_tld_and_hash():
    e = {"id": "x", "title": "t", "link": "https://a.com", "content_md": "body"}
    out = finalize_entry_metadata(e, source_type="rss", source_feed_url="https://feeds.site/atom")
    assert out["source_type"] == "rss"
    assert out["content_hash"]
    assert out["tld"]
