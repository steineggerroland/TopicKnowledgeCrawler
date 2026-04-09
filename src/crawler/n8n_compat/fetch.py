"""
Ruft bestehende Fetcher auf (keine Duplikation der HTML/RSS-Logik).
"""

from __future__ import annotations

from typing import Any


def fetch_entries_for_source(source: dict) -> list[dict[str, Any]]:
    source_type = source.get("type")
    if source_type == "rss":
        from src.crawler.fetchers.rss_fetcher import RssFetcher

        return RssFetcher(source).fetch()
    if source_type == "rss+podcast":
        from src.crawler.fetchers.podcast_fetcher import PodcastFetcher

        return PodcastFetcher(source).fetch()
    if source_type == "html":
        from src.crawler.fetchers.html_fetcher import HtmlFetcher

        return HtmlFetcher(source).fetch()
    raise ValueError(f"Unsupported source type: {source_type!r}")
