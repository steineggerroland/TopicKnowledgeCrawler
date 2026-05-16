"""Podcast candidate builder."""

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


def _podcast_id(entry: Any, link: str | None = None, summary: str | None = None) -> str:
    content = (
        str(link or entry_get(entry, "link", "") or "")
        + str(entry_get(entry, "title", "") or "")
        + str(summary or entry_get(entry, "summary", "") or entry_get(entry, "description", "") or "")
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _podcast_best_content(entry: Any) -> tuple[str | None, str | None]:
    content_fields = entry_get(entry, "content", [])
    if isinstance(content_fields, list):
        for content_type in ("text/html", "application/xhtml+xml", "text/plain"):
            for field in content_fields:
                if isinstance(field, Mapping) and field.get("type") == content_type:
                    return field.get("value"), content_type
                if hasattr(field, "get") and field.get("type") == content_type:
                    return field.get("value"), content_type
    return (
        entry_get(entry, "description")
        or entry_get(entry, "itunes:summary")
        or entry_get(entry, "summary"),
        "description",
    )


def _duration_seconds(value: Any) -> int | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    if len(parts) == 2:
        minutes, seconds = (int(part) for part in parts)
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = (int(part) for part in parts)
        return hours * 3600 + minutes * 60 + seconds
    return None


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mapping_get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    if hasattr(value, "get"):
        return value.get(name, default)
    return getattr(value, name, default)


def _first_mapping(value: Any) -> Any | None:
    if isinstance(value, list | tuple) and value:
        return value[0]
    if isinstance(value, Mapping):
        return value
    return None


def _podcast_enclosure(entry: Any) -> dict[str, Any]:
    enclosures = entry_get(entry, "enclosures", []) or []
    enclosure = _first_mapping(enclosures)
    if not enclosure:
        links = entry_get(entry, "links", []) or []
        for link in links:
            if _mapping_get(link, "rel") == "enclosure":
                enclosure = link
                break
    if not enclosure:
        return {}
    href = _mapping_get(enclosure, "href") or _mapping_get(enclosure, "url")
    return {
        "media_url": HtmlFetcher.sanitize_link(href) if href else None,
        "media_type": _mapping_get(enclosure, "type"),
        "media_length_bytes": _int_or_none(_mapping_get(enclosure, "length")),
    }


def _podcast_image_url(entry: Any) -> str | None:
    image = entry_get(entry, "itunes_image") or entry_get(entry, "image")
    if isinstance(image, str):
        return HtmlFetcher.sanitize_link(image)
    if image:
        href = _mapping_get(image, "href") or _mapping_get(image, "url")
        if href:
            return HtmlFetcher.sanitize_link(href)
    return None


def _podcast_link_object(entry: Any, *names: str) -> Any | None:
    for name in names:
        value = entry_get(entry, name)
        if value:
            return _first_mapping(value) or value
    return None


def _podcast_url_from_object(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return HtmlFetcher.sanitize_link(value)
    href = _mapping_get(value, "href") or _mapping_get(value, "url")
    return HtmlFetcher.sanitize_link(href) if href else None


def _podcast_episode_fields(entry: Any) -> dict[str, Any]:
    enclosure = _podcast_enclosure(entry)
    chapters = _podcast_link_object(entry, "podcast_chapters", "chapters")
    transcript = _podcast_link_object(entry, "podcast_transcript", "transcript")
    fields = {
        **enclosure,
        "duration_seconds": _duration_seconds(entry_get(entry, "itunes_duration")),
        "episode_number": _int_or_none(entry_get(entry, "itunes_episode") or entry_get(entry, "episode")),
        "season_number": _int_or_none(entry_get(entry, "itunes_season") or entry_get(entry, "season")),
        "episode_type": entry_get(entry, "itunes_episodetype") or entry_get(entry, "itunes_episode_type"),
        "explicit": entry_get(entry, "itunes_explicit"),
        "subtitle": entry_get(entry, "itunes_subtitle") or entry_get(entry, "subtitle"),
        "image_url": _podcast_image_url(entry),
        "chapters_url": _podcast_url_from_object(chapters),
        "chapters_type": _mapping_get(chapters, "type") if chapters else None,
        "transcript_url": _podcast_url_from_object(transcript),
        "transcript_type": _mapping_get(transcript, "type") if transcript else None,
    }
    return {key: value for key, value in fields.items() if value not in (None, "")}


def build_podcast_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build candidate rows from a podcast RSS feed."""
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

        feed_content, feed_content_type = _podcast_best_content(entry)
        candidate_id = _podcast_id(entry, link=link, summary=feed_content)
        categories = entry_get(entry, "tags", []) or []
        candidate: dict[str, Any] = {
            "id": candidate_id,
            "link": link,
            "title": entry_get(entry, "title"),
            "summary": feed_content or "",
            "author": (
                entry_get(entry, "itunes:author")
                or entry_get(entry, "author")
                or entry_get(entry, "dc:creator")
            ),
            "publishedAt": entry_get(entry, "pubDate") or entry_get(entry, "published"),
            "updatedAt": entry_get(entry, "updated"),
            "categories": [tag.get("term") for tag in categories if hasattr(tag, "get") and tag.get("term")],
            "has_feed_content": bool(feed_content),
            "feed_content": feed_content,
            "feed_content_type": feed_content_type,
            "item_kind": ItemKind.EPISODE,
            **_podcast_episode_fields(entry),
        }
        out.append(candidate_row(
            row, crawl_key=crawl_key, source_name=source_name,
            source_type=source_type, candidate=candidate,
        ))

    return out
