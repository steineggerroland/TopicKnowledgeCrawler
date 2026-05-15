"""Tests for tkcrawler.datatable – Data Table row conversion."""

from __future__ import annotations

import json

import pytest

from tkcrawler.datatable import row_to_source, row_with_crawl_key


class TestRowToSource:
    def test_basic_rss_row(self):
        row = {"name": "Feed", "type": "rss", "url": "https://example.com/feed"}
        src = row_to_source(row)
        assert src == {"name": "Feed", "type": "rss", "url": "https://example.com/feed"}

    def test_html_with_configuration_json_string(self):
        cfg = {"article_selector": "article", "main_page_anchor_selector": "a"}
        row = {"name": "HTML", "type": "html", "url": "https://x.com", "configuration_json": json.dumps(cfg)}
        src = row_to_source(row)
        assert src["configuration"] == cfg

    def test_html_with_configuration_dict(self):
        cfg = {"article_selector": "div.post", "main_page_anchor_selector": "a.title"}
        row = {"name": "HTML", "type": "html", "url": "https://x.com", "configuration": cfg}
        src = row_to_source(row)
        assert src["configuration"] == cfg

    def test_configuration_json_takes_precedence_over_configuration(self):
        json_cfg = {"article_selector": "from_json"}
        dict_cfg = {"article_selector": "from_dict"}
        row = {
            "name": "X",
            "type": "html",
            "url": "https://x.com",
            "configuration_json": json.dumps(json_cfg),
            "configuration": dict_cfg,
        }
        src = row_to_source(row)
        assert src["configuration"]["article_selector"] == "from_json"

    def test_raises_on_missing_name(self):
        with pytest.raises(ValueError, match="name"):
            row_to_source({"name": "", "type": "rss", "url": "https://x.com"})

    def test_raises_on_missing_type(self):
        with pytest.raises(ValueError, match="type"):
            row_to_source({"name": "X", "type": "", "url": "https://x.com"})

    def test_raises_on_missing_url(self):
        with pytest.raises(ValueError, match="url"):
            row_to_source({"name": "X", "type": "rss", "url": ""})

    def test_strips_whitespace(self):
        row = {"name": "  Feed  ", "type": "  rss  ", "url": "  https://x.com  "}
        src = row_to_source(row)
        assert src["name"] == "Feed"
        assert src["type"] == "rss"
        assert src["url"] == "https://x.com"

    def test_ignores_empty_configuration_json(self):
        row = {"name": "X", "type": "rss", "url": "https://x.com", "configuration_json": ""}
        src = row_to_source(row)
        assert "configuration" not in src

    def test_ignores_none_configuration(self):
        row = {"name": "X", "type": "rss", "url": "https://x.com", "configuration_json": None}
        src = row_to_source(row)
        assert "configuration" not in src


class TestRowWithCrawlKey:
    def test_adds_crawl_key_from_url(self):
        row = {"url": "https://example.com/feed/"}
        out = row_with_crawl_key(row)
        assert out["crawl_key"] == "https://example.com/feed"

    def test_preserves_existing_crawl_key(self):
        row = {"url": "https://example.com/feed/", "crawl_key": "https://custom.key/feed"}
        out = row_with_crawl_key(row)
        assert out["crawl_key"] == "https://custom.key/feed"

    def test_strips_whitespace_from_crawl_key(self):
        row = {"url": "https://example.com/feed", "crawl_key": "  "}
        out = row_with_crawl_key(row)
        assert out["crawl_key"] == "https://example.com/feed"

    def test_does_not_mutate_original(self):
        row = {"url": "https://example.com/feed"}
        out = row_with_crawl_key(row)
        assert "crawl_key" not in row
        assert "crawl_key" in out
