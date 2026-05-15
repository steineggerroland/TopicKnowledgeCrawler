"""Compatibility wrapper around the canonical step-based crawl flow."""

from __future__ import annotations

from typing import Any

from tkcrawler.pipeline import crawl_source_items


def fetch_entries_for_source(source: dict) -> list[dict[str, Any]]:
    """Return finalized content items for a source.

    Older callers imported this helper to get a list of fetched entries. The
    implementation now delegates to `tkcrawler.pipeline`.
    """
    return [
        item["article"]
        for item in crawl_source_items(source)
        if item.get("article") and not item.get("fetch_detail_error")
    ]
