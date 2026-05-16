"""RSS candidate builder."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import feedparser

from tkcrawler.candidates._common import (
    candidate_row,
    entry_get,
    max_candidates,
    source_basics,
)
from tkcrawler.enums import ItemKind
from tkcrawler.html import HtmlFetcher
from tkcrawler._runtime import StepError


def _rss_id(entry: Any, link: str | None = None) -> str:
    title = str(entry_get(entry, "title", "") or "")
    summary = str(entry_get(entry, "summary", "") or entry_get(entry, "description", "") or "")
    content = str(link or entry_get(entry, "link", "") or title or summary)
    return hashlib.sha256(content.encode()).hexdigest()


def _extract_feed_content(entry: Any) -> tuple[str | None, str | None]:
    content_fields = entry_get(entry, "content", [])
    if isinstance(content_fields, list):
        for content_type in ("text/html", "application/xhtml+xml", "text/plain"):
            for field in content_fields:
                if isinstance(field, Mapping) and field.get("type") == content_type:
                    return field.get("value"), content_type
                if hasattr(field, "get") and field.get("type") == content_type:
                    return field.get("value"), content_type
    return None, None


def build_rss_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build candidate rows from an RSS/Atom feed."""
    source_type, url, crawl_key, source_name = source_basics(row)
    max_entries = max_candidates(row)
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        raise StepError("feed_parse_failed", f"Failed to parse feed: {url}") from exc

    feed_entries = getattr(feed, "entries", None) or []
    if max_entries and max_entries > 0:
        feed_entries = feed_entries[:max_entries]

    seen_links: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in feed_entries:
        link = HtmlFetcher.sanitize_link(entry_get(entry, "link"))
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        feed_content, feed_content_type = _extract_feed_content(entry)
        summary = entry_get(entry, "summary", "") or entry_get(entry, "description", "") or ""
        candidate: dict[str, Any] = {
            "id": _rss_id(entry, link=link),
            "link": link,
            "title": entry_get(entry, "title"),
            "summary": summary,
            "author": entry_get(entry, "author"),
            "publishedAt": entry_get(entry, "published") or entry_get(entry, "updated"),
            "updatedAt": entry_get(entry, "updated"),
            "has_feed_content": bool(feed_content),
            "feed_content": feed_content,
            "feed_content_type": feed_content_type,
            "item_kind": ItemKind.ARTICLE,
        }
        out.append(candidate_row(
            row, crawl_key=crawl_key, source_name=source_name,
            source_type=source_type, candidate=candidate,
        ))

    return out
