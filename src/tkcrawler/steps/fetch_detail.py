from __future__ import annotations

from typing import Any, Mapping

import requests

from crawler.fetchers.html_fetcher import HtmlFetcher
from crawler.utils import text_processor
from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError, ok, split_input


EPISODE_FIELDS = (
    "media_url",
    "media_type",
    "media_length_bytes",
    "duration_seconds",
    "episode_number",
    "season_number",
    "episode_type",
    "explicit",
    "subtitle",
    "image_url",
    "chapters_url",
    "chapters_type",
    "transcript_url",
    "transcript_type",
)


def _markdown_from_feed_content(candidate: Mapping[str, Any]) -> tuple[str, str]:
    title = candidate.get("title") or ""
    feed_content = candidate.get("feed_content") or candidate.get("summary") or ""
    if not feed_content:
        raise StepError("missing_feed_content", "Candidate has no feed content")

    markdown = text_processor.convert_from_html_to_markdown(f"<html><body>{feed_content}</body></html>")
    if not markdown:
        markdown = str(feed_content)
    if title:
        return f"# {title}\n\n{markdown}", markdown
    return markdown, markdown


def _podcast_content(candidate: Mapping[str, Any], link: str, *, verify: Any, headers: Mapping[str, str]) -> tuple[str, str | None]:
    if candidate.get("has_feed_content") or candidate.get("summary"):
        return _markdown_from_feed_content(candidate)
    try:
        return HtmlFetcher.generate_markdown_from_url(link, verify=verify, headers=dict(headers)), None
    except Exception:
        return _markdown_from_feed_content(candidate)


def _seconds(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return max(int(value), 0)
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


def _chapter_start(chapter: Mapping[str, Any]) -> int | None:
    for field in ("startTime", "start_time", "start", "time"):
        seconds = _seconds(chapter.get(field))
        if seconds is not None:
            return seconds
    return None


def _chapter_url(chapter: Mapping[str, Any]) -> str | None:
    for field in ("url", "href", "link"):
        value = chapter.get(field)
        if value:
            return str(value)
    return None


def _normalize_chapters(payload: Any) -> list[dict[str, Any]]:
    raw_chapters = payload.get("chapters") if isinstance(payload, Mapping) else payload
    if not isinstance(raw_chapters, list):
        return []
    chapters = []
    for raw in raw_chapters:
        if not isinstance(raw, Mapping):
            continue
        start_seconds = _chapter_start(raw)
        title = raw.get("title") or raw.get("name")
        if start_seconds is None or not title:
            continue
        chapter: dict[str, Any] = {
            "start_seconds": start_seconds,
            "title": str(title),
        }
        url = _chapter_url(raw)
        if url:
            chapter["url"] = url
        image_url = raw.get("img") or raw.get("image") or raw.get("imageUrl") or raw.get("image_url")
        if image_url:
            chapter["image_url"] = str(image_url)
        chapters.append(chapter)
    return chapters


def _fetch_chapters(candidate: Mapping[str, Any], *, verify: Any, headers: Mapping[str, str]) -> tuple[list[dict[str, Any]], str | None]:
    url = str(candidate.get("chapters_url") or "").strip()
    if not url:
        return [], None
    try:
        response = requests.get(url, timeout=20, verify=verify, headers=dict(headers))
        response.raise_for_status()
        chapters = _normalize_chapters(response.json())
        return chapters, None
    except Exception as exc:
        return [], str(exc)


def fetch_detail_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    candidate = row.get("candidate")
    if not isinstance(candidate, Mapping):
        raise StepError("missing_candidate", "Item needs candidate object")

    decision = row.get("candidate_decision")
    if decision and decision != "fetch":
        raise StepError(
            "candidate_not_fetchable",
            f"Candidate decision is not fetch: {decision}",
            {"candidate_decision": decision},
        )

    link = str(candidate.get("link") or "").strip()
    if not link:
        raise StepError("missing_link", "Candidate needs link")

    source_type = str(row.get("source_type") or row.get("type") or "").strip()
    item_kind = str(candidate.get("item_kind") or "article")
    verify = context.get("verify", row.get("verify", True))
    headers = request_headers(row, context)

    shownotes_md = None
    if source_type == "rss+podcast":
        content_md, shownotes_md = _podcast_content(candidate, link, verify=verify, headers=headers)
    elif candidate.get("has_feed_content") and row.get("prefer_feed_content"):
        content_md, _shownotes_md = _markdown_from_feed_content(candidate)
    else:
        content_md = HtmlFetcher.generate_markdown_from_url(link, verify=verify, headers=dict(headers))

    article = {
        "id": candidate.get("id") or row.get("article_id") or row.get("item_id"),
        "title": candidate.get("title"),
        "link": link,
        "summary": candidate.get("summary", ""),
        "author": candidate.get("author"),
        "publishedAt": candidate.get("publishedAt"),
        "updatedAt": candidate.get("updatedAt"),
        "content_md": content_md,
        "item_kind": item_kind,
    }
    if candidate.get("categories") is not None:
        article["categories"] = candidate.get("categories")
    if item_kind == "episode":
        for field in EPISODE_FIELDS:
            if candidate.get(field) is not None:
                article[field] = candidate.get(field)
        if shownotes_md:
            article["shownotes_md"] = shownotes_md
        chapters, chapters_error = _fetch_chapters(candidate, verify=verify, headers=headers)
        if chapters:
            article["chapters"] = chapters
        if chapters_error:
            article["chapters_fetch_error"] = chapters_error

    return {
        **dict(row),
        "article_id": article["id"],
        "item_id": article["id"],
        "article": article,
        "content_md": content_md,
        "fetch_detail_error": None,
    }


def fetch_detail_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(fetch_detail_item(item, context))
