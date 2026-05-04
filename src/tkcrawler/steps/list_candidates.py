from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from crawler.fetchers.html_fetcher import HtmlFetcher
from tkcrawler.steps._runtime import StepError, ok, split_input


def _entry_get(entry: Any, name: str, default: Any = None) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(name, default)
    return getattr(entry, name, default)


def _rss_id(entry: Any, link: str | None = None) -> str:
    title = str(_entry_get(entry, "title", "") or "")
    summary = str(_entry_get(entry, "summary", "") or _entry_get(entry, "description", "") or "")
    content = str(link or _entry_get(entry, "link", "") or title or summary)
    return hashlib.sha256(content.encode()).hexdigest()


def _podcast_id(entry: Any, link: str | None = None, summary: str | None = None) -> str:
    content = (
        str(link or _entry_get(entry, "link", "") or "")
        + str(_entry_get(entry, "title", "") or "")
        + str(summary or _entry_get(entry, "summary", "") or _entry_get(entry, "description", "") or "")
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_feed_content(entry: Any) -> tuple[str | None, str | None]:
    content_fields = _entry_get(entry, "content", [])
    if isinstance(content_fields, list):
        for content_type in ("text/html", "application/xhtml+xml", "text/plain"):
            for field in content_fields:
                if isinstance(field, Mapping) and field.get("type") == content_type:
                    return field.get("value"), content_type
                if hasattr(field, "get") and field.get("type") == content_type:
                    return field.get("value"), content_type
    return None, None


def _podcast_best_content(entry: Any) -> tuple[str | None, str | None]:
    value, content_type = _extract_feed_content(entry)
    if value:
        return value, content_type
    return (
        _entry_get(entry, "description")
        or _entry_get(entry, "itunes:summary")
        or _entry_get(entry, "summary"),
        "description",
    )


def _policy_value(row: Mapping[str, Any], name: str, default: Any = None) -> Any:
    policy = row.get("effective_policy")
    if isinstance(policy, Mapping) and name in policy:
        return policy[name]
    return default


def _max_candidates(row: Mapping[str, Any]) -> int | None:
    max_entries = _policy_value(row, "max_candidates_per_run")
    if max_entries is None:
        max_entries = _policy_value(row, "max_entries_per_run")
    if max_entries is not None:
        try:
            return int(max_entries)
        except (TypeError, ValueError) as exc:
            raise StepError("invalid_policy", "max_candidates_per_run must be an integer") from exc
    return None


def _source_basics(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    source_type = str(row.get("type") or "").strip()
    url = str(row.get("url") or "").strip()
    if not url:
        raise StepError("missing_url", "Source needs url")
    crawl_key = str(row.get("crawl_key") or row.get("crawlKey") or url)
    source_name = str(row.get("name") or url)
    return source_type, url, crawl_key, source_name


def _candidate_row(
    row: Mapping[str, Any],
    *,
    crawl_key: str,
    source_name: str,
    source_type: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **dict(row),
        "crawl_key": crawl_key,
        "source_name": source_name,
        "source_type": source_type,
        "article_id": candidate["id"],
        "item_id": candidate["id"],
        "candidate": dict(candidate),
    }


def _list_feed_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_type, url, crawl_key, source_name = _source_basics(row)
    max_entries = _max_candidates(row)
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
        link = HtmlFetcher.sanitize_link(_entry_get(entry, "link"))
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        if source_type == "rss+podcast":
            feed_content, feed_content_type = _podcast_best_content(entry)
            candidate_id = _podcast_id(entry, link=link, summary=feed_content)
            categories = _entry_get(entry, "tags", []) or []
            candidate: dict[str, Any] = {
                "id": candidate_id,
                "link": link,
                "title": _entry_get(entry, "title"),
                "summary": feed_content or "",
                "author": (
                    _entry_get(entry, "itunes:author")
                    or _entry_get(entry, "author")
                    or _entry_get(entry, "dc:creator")
                ),
                "publishedAt": _entry_get(entry, "pubDate") or _entry_get(entry, "published"),
                "updatedAt": _entry_get(entry, "updated"),
                "categories": [tag.get("term") for tag in categories if hasattr(tag, "get") and tag.get("term")],
                "has_feed_content": bool(feed_content),
                "feed_content": feed_content,
                "feed_content_type": feed_content_type,
                "item_kind": "episode",
            }
        else:
            feed_content, feed_content_type = _extract_feed_content(entry)
            summary = _entry_get(entry, "summary", "") or _entry_get(entry, "description", "") or ""
            candidate = {
                "id": _rss_id(entry, link=link),
                "link": link,
                "title": _entry_get(entry, "title"),
                "summary": summary,
                "author": _entry_get(entry, "author"),
                "publishedAt": _entry_get(entry, "published") or _entry_get(entry, "updated"),
                "updatedAt": _entry_get(entry, "updated"),
                "has_feed_content": bool(feed_content),
                "feed_content": feed_content,
                "feed_content_type": feed_content_type,
                "item_kind": "article",
            }

        out.append(
            _candidate_row(
                row,
                crawl_key=crawl_key,
                source_name=source_name,
                source_type=source_type,
                candidate=candidate,
            )
        )

    return out


def _configuration(row: Mapping[str, Any]) -> dict[str, Any]:
    raw = row.get("configuration")
    if isinstance(raw, Mapping):
        return dict(raw)
    raw = row.get("configuration_json")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StepError("invalid_configuration", "configuration_json must be valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise StepError("invalid_configuration", "configuration_json must be a JSON object")
        return dict(parsed)
    raise StepError("missing_configuration", "HTML source needs configuration_json")


def _html_title(block: Any, anchor: Any) -> str | None:
    for selector in ("h1", "h2", "h3"):
        element = block.select_one(selector)
        if element and element.get_text(strip=True):
            return element.get_text(strip=True)
    if anchor and anchor.get_text(strip=True):
        return anchor.get_text(strip=True)
    return None


def _list_html_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_type, url, crawl_key, source_name = _source_basics(row)
    cfg = _configuration(row)
    article_selector = str(cfg.get("article_selector") or "").strip()
    anchor_selector = str(cfg.get("main_page_anchor_selector") or "").strip()
    if not article_selector or not anchor_selector:
        raise StepError(
            "invalid_configuration",
            "HTML configuration needs article_selector and main_page_anchor_selector",
        )

    html = HtmlFetcher._fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(article_selector)
    max_entries = _max_candidates(row)
    if max_entries and max_entries > 0:
        blocks = blocks[:max_entries]

    seen_links: set[str] = set()
    out: list[dict[str, Any]] = []
    for block in blocks:
        anchor = block.select_one(anchor_selector)
        if not anchor or not anchor.get("href"):
            continue
        link = HtmlFetcher.sanitize_link(urljoin(url, anchor.get("href")))
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        candidate = {
            "id": hashlib.sha256(link.encode("utf-8")).hexdigest(),
            "link": link,
            "title": _html_title(block, anchor),
            "summary": "",
            "author": None,
            "publishedAt": None,
            "updatedAt": None,
            "has_feed_content": False,
            "feed_content": None,
            "feed_content_type": None,
            "item_kind": "article",
        }
        out.append(
            _candidate_row(
                row,
                crawl_key=crawl_key,
                source_name=source_name,
                source_type=source_type,
                candidate=candidate,
            )
        )

    return out


def list_candidates_items(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_type = str(row.get("type") or "").strip()
    if source_type in {"rss", "rss+podcast"}:
        return _list_feed_candidates(row)
    if source_type == "html":
        return _list_html_candidates(row)
    raise StepError(
        "unsupported_source_type",
        f"list_candidates does not support source type: {source_type!r}",
        {"source_type": source_type},
    )


def list_candidates_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(list_candidates_items(item))
