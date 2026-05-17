"""Minimal Python example for the canonical TopicKnowledgeCrawler step flow.

Run from the repository root after `pip install -e .`:

    python examples/python_step_flow.py

The example uses mocked step data so it does not access the network. Real
applications can call `tkcrawler.pipeline.crawl_source_items(...)` directly with
their source rows and optional history lookup.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

os.environ.setdefault("TLDEXTRACT_CACHE", "/tmp/tkcrawler-tldextract-cache")

from tkcrawler.pipeline import crawl_source_ingest_bodies


SOURCE = {
    "crawl_key": "https://example.com/feed.xml",
    "name": "Example Feed",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "source_status": "ready",
    "effective_policy": {
        "refresh_window_days": 7,
        "max_llm_items_per_run": 3,
    },
}


def history_lookup(article_id: str) -> dict | None:
    """Replace this with a database/Data-Table lookup in real systems."""
    return None


def main() -> None:
    with patch("tkcrawler.candidates.rss.feedparser.parse") as parse_feed, patch(
        "tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url",
        return_value="# Example Article\n\nThis is the fetched article body.",
    ):
        parse_feed.return_value.entries = [
            {
                "title": "Example Article",
                "link": "https://example.com/articles/1",
                "summary": "Short source summary",
                "author": "Ada Example",
                "published": "2026-05-10T08:00:00+00:00",
            }
        ]

        ingest_bodies = crawl_source_ingest_bodies(
            SOURCE,
            history_lookup=history_lookup,
            context={"now": "2026-05-13T10:00:00+00:00"},
        )

    print(json.dumps(ingest_bodies, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
