"""Shared pytest fixtures for TopicKnowledgeCrawler tests."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def source_rss():
    return {
        "crawl_key": "https://example.com/feed.xml",
        "name": "Example RSS",
        "type": "rss",
        "url": "https://example.com/feed.xml",
        "source_status": "ready",
    }


@pytest.fixture
def source_podcast():
    return {
        "crawl_key": "https://example.com/podcast",
        "name": "Example Podcast",
        "type": "rss+podcast",
        "url": "https://example.com/podcast",
        "source_status": "ready",
    }


@pytest.fixture
def source_html():
    return {
        "crawl_key": "https://example.com/articles",
        "name": "Example HTML",
        "type": "html",
        "url": "https://example.com/articles",
        "source_status": "ready",
        "configuration": {
            "article_selector": "article",
            "main_page_anchor_selector": "a:has(h2)",
        },
        "configuration_json": json.dumps({
            "article_selector": "article",
            "main_page_anchor_selector": "a:has(h2)",
        }),
    }


@pytest.fixture
def minimal_candidate():
    return {
        "crawl_key": "https://example.com/feed.xml",
        "type": "rss",
        "url": "https://example.com/feed.xml",
        "source_status": "ready",
        "article_id": "abc123",
        "candidate": {
            "title": "Test Article",
            "link": "https://example.com/article/1",
            "summary": "A test summary",
            "publishedAt": "2026-05-10T08:00:00+00:00",
        },
        "candidate_decision": "fetch",
    }


@pytest.fixture
def minimal_article():
    return {
        "id": "abc123",
        "title": "Test Article",
        "link": "https://example.com/article/1",
        "summary": "A test summary",
        "content_md": "# Test Article\n\nThis is the body.",
        "item_kind": "article",
        "publishedAt": "2026-05-10T08:00:00+00:00",
    }
