"""Shared detail-fetch helpers for source-family fetchers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

from tkcrawler import text
from tkcrawler.enums import ItemKind, SourceType
from tkcrawler.html import HtmlFetcher
from tkcrawler.models import Article, Candidate, Source
from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError

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


def _markdown_from_text(value: Any) -> str:
    markdown = text.convert_from_html_to_markdown(f"<html><body>{value}</body></html>")
    if not markdown:
        markdown = str(value)
    return markdown.strip()


def _with_title(title: Any, markdown: str) -> str:
    if title:
        return f"# {title}\n\n{markdown}"
    return markdown


def _candidate_mapping(candidate: Candidate | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(candidate, Candidate):
        return candidate.to_dict()
    return candidate


def _markdown_from_feed_content(candidate: Mapping[str, Any]) -> tuple[str, str]:
    title = candidate.get("title") or ""
    feed_content = candidate.get("feed_content") or candidate.get("summary") or ""
    if not feed_content:
        raise StepError("missing_feed_content", "Candidate has no feed content")

    markdown = _markdown_from_text(feed_content)
    if title:
        return f"# {title}\n\n{markdown}", markdown
    return markdown, markdown


def _meaningfully_distinct(left: str, right: str) -> bool:
    def normalized(value: str) -> str:
        return " ".join(value.casefold().split())

    return bool(normalized(left) and normalized(right) and normalized(left) != normalized(right))


def _podcast_feed_content(candidate: Mapping[str, Any]) -> tuple[str, str | None]:
    title = candidate.get("title") or ""
    rich_content = candidate.get("feed_content")
    if rich_content:
        markdown = _markdown_from_text(rich_content)
        return _with_title(title, markdown), markdown

    parts: list[str] = []
    shownotes_md = None
    shownotes = candidate.get("podcast_shownotes")
    if shownotes:
        shownotes_md = _markdown_from_text(shownotes)
        if shownotes_md:
            parts.append(shownotes_md)

    summary = candidate.get("podcast_summary") or candidate.get("summary")
    if summary:
        summary_md = _markdown_from_text(summary)
        if summary_md and all(_meaningfully_distinct(existing, summary_md) for existing in parts):
            parts.append(summary_md)

    if not parts:
        raise StepError("missing_feed_content", "Candidate has no feed content")

    body = "\n\n".join(parts)
    return _with_title(title, body), body if shownotes_md or len(parts) > 1 else parts[0]


def _podcast_content(
    candidate: Mapping[str, Any],
    link: str,
    *,
    verify: Any,
    headers: Mapping[str, str],
) -> tuple[str, str | None]:
    if (
        candidate.get("feed_content")
        or candidate.get("podcast_shownotes")
        or candidate.get("podcast_summary")
        or candidate.get("summary")
    ):
        return _podcast_feed_content(candidate)
    try:
        return HtmlFetcher.generate_markdown_from_url(link, verify=verify, headers=dict(headers)), None
    except Exception:
        return _podcast_feed_content(candidate)


def _seconds(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return max(int(value), 0)
    text_value = str(value).strip()
    if not text_value:
        return None
    if text_value.isdigit():
        return int(text_value)
    parts = text_value.split(":")
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


def _fetch_chapters(
    candidate: Mapping[str, Any],
    *,
    verify: Any,
    headers: Mapping[str, str],
) -> tuple[list[dict[str, Any]], str | None]:
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


def _plain_transcript(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT":
            continue
        if stripped.isdigit() or "-->" in stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


def _transcript_text_from_json(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        return "\n".join(
            part
            for item in payload
            if (part := _transcript_text_from_json(item))
        ).strip()
    if isinstance(payload, Mapping):
        for field in ("transcript", "text", "body"):
            value = payload.get(field)
            if isinstance(value, str):
                return value
        for field in ("segments", "items", "captions"):
            value = payload.get(field)
            if isinstance(value, list):
                return _transcript_text_from_json(value)
    return ""


def _transcript_markdown(response: requests.Response, transcript_type: str | None) -> str:
    media_type = (transcript_type or response.headers.get("content-type") or "").casefold()
    if "json" in media_type:
        markdown = _transcript_text_from_json(response.json())
        if not markdown:
            raise ValueError("Unsupported transcript JSON shape")
        return markdown.strip()

    raw = response.text
    if "html" in media_type:
        markdown = text.convert_from_html_to_markdown(raw)
        return (markdown or raw).strip()
    return _plain_transcript(raw)


def _fetch_transcript(
    candidate: Mapping[str, Any],
    *,
    verify: Any,
    headers: Mapping[str, str],
) -> tuple[str | None, str | None]:
    url = str(candidate.get("transcript_url") or "").strip()
    if not url:
        return None, None
    try:
        response = requests.get(url, timeout=20, verify=verify, headers=dict(headers))
        response.raise_for_status()
        transcript_md = _transcript_markdown(response, candidate.get("transcript_type"))
        return transcript_md or None, None
    except Exception as exc:
        return None, str(exc)


def _request_context(
    source: Source,
    context: Mapping[str, Any] | None,
    *,
    prefer_feed_content: bool | None = None,
) -> tuple[Any, Mapping[str, str], bool]:
    row = source.to_dict()
    if prefer_feed_content is not None:
        row = {**row, "prefer_feed_content": prefer_feed_content}
    ctx = dict(context or {})
    verify = ctx.get("verify", row.get("verify", True))
    headers = request_headers(row, ctx)
    return verify, headers, bool(row.get("prefer_feed_content"))


def fetch_article_detail(
    source: Source,
    candidate: Candidate,
    context: Mapping[str, Any] | None = None,
    *,
    prefer_feed_content: bool | None = None,
) -> Article:
    """Fetch full article/episode content for a candidate."""
    candidate_map = _candidate_mapping(candidate)
    link = str(candidate_map.get("link") or "").strip()
    if not link:
        raise StepError("missing_link", "Candidate needs link")

    source_type = str(source.type or "").strip()
    item_kind = str(candidate_map.get("item_kind") or ItemKind.ARTICLE)
    verify, headers, use_feed_content = _request_context(
        source,
        context,
        prefer_feed_content=prefer_feed_content,
    )

    shownotes_md = None
    if source_type == SourceType.PODCAST:
        content_md, shownotes_md = _podcast_content(candidate_map, link, verify=verify, headers=headers)
    elif candidate_map.get("has_feed_content") and use_feed_content:
        content_md, _shownotes_md = _markdown_from_feed_content(candidate_map)
    else:
        content_md = HtmlFetcher.generate_markdown_from_url(link, verify=verify, headers=dict(headers))

    article_data: dict[str, Any] = {
        "id": candidate_map.get("id") or candidate.id,
        "title": candidate_map.get("title"),
        "link": link,
        "summary": candidate_map.get("summary", ""),
        "author": candidate_map.get("author"),
        "publishedAt": candidate_map.get("publishedAt"),
        "updatedAt": candidate_map.get("updatedAt"),
        "content_md": content_md,
        "item_kind": item_kind,
    }
    if candidate_map.get("categories") is not None:
        article_data["categories"] = candidate_map.get("categories")
    if item_kind == ItemKind.EPISODE:
        for field in EPISODE_FIELDS:
            if candidate_map.get(field) is not None:
                article_data[field] = candidate_map.get(field)
        if shownotes_md:
            article_data["shownotes_md"] = shownotes_md
        chapters, chapters_error = _fetch_chapters(candidate_map, verify=verify, headers=headers)
        if chapters:
            article_data["chapters"] = chapters
        if chapters_error:
            article_data["chapters_fetch_error"] = chapters_error
        transcript_md, transcript_error = _fetch_transcript(candidate_map, verify=verify, headers=headers)
        if transcript_md:
            article_data["transcript_md"] = transcript_md
        if transcript_error:
            article_data["transcript_fetch_error"] = transcript_error

    return Article.from_mapping(article_data)
