from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import requests

from tkcrawler import text
from tkcrawler.enums import CandidateDecision, ItemKind, SourceType
from tkcrawler.html import HtmlFetcher
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


def _markdown_from_text(value: Any) -> str:
    markdown = text.convert_from_html_to_markdown(f"<html><body>{value}</body></html>")
    if not markdown:
        markdown = str(value)
    return markdown.strip()


def _with_title(title: Any, markdown: str) -> str:
    if title:
        return f"# {title}\n\n{markdown}"
    return markdown


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


def _podcast_content(candidate: Mapping[str, Any], link: str, *, verify: Any, headers: Mapping[str, str]) -> tuple[str, str | None]:
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
    if decision and decision != CandidateDecision.FETCH:
        raise StepError(
            "candidate_not_fetchable",
            f"Candidate decision is not fetch: {decision}",
            {"candidate_decision": decision},
        )

    link = str(candidate.get("link") or "").strip()
    if not link:
        raise StepError("missing_link", "Candidate needs link")

    source_type = str(row.get("source_type") or row.get("type") or "").strip()
    item_kind = str(candidate.get("item_kind") or ItemKind.ARTICLE)
    verify = context.get("verify", row.get("verify", True))
    headers = request_headers(row, context)

    shownotes_md = None
    if source_type == SourceType.PODCAST:
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
    if item_kind == ItemKind.EPISODE:
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
