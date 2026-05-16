"""HTML listing page candidate builder."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from tkcrawler.candidates._common import (
    candidate_row,
    max_candidates,
    source_basics,
)
from tkcrawler.enums import ItemKind
from tkcrawler.html import HtmlFetcher
from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError


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


def _html_anchor(block: Any, anchor_selector: str) -> Any:
    if block.name == "a" and block.get("href"):
        if not anchor_selector or block.select(anchor_selector) or _matches_selector(block, anchor_selector):
            return block
    return block.select_one(anchor_selector)


def _matches_selector(element: Any, selector: str) -> bool:
    try:
        return bool(element.parent and element in element.parent.select(selector))
    except Exception:
        return False


def build_html_candidates(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build candidate rows from an HTML listing page."""
    source_type, url, crawl_key, source_name = source_basics(row)
    cfg = _configuration(row)
    article_selector = str(cfg.get("article_selector") or "").strip()
    anchor_selector = str(cfg.get("main_page_anchor_selector") or "").strip()
    if not article_selector or not anchor_selector:
        raise StepError(
            "invalid_configuration",
            "HTML configuration needs article_selector and main_page_anchor_selector",
        )

    html = HtmlFetcher._fetch_html(url, headers=request_headers(row))
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(article_selector)
    max_entries = max_candidates(row)
    if max_entries and max_entries > 0:
        blocks = blocks[:max_entries]

    seen_links: set[str] = set()
    out: list[dict[str, Any]] = []
    for block in blocks:
        anchor = _html_anchor(block, anchor_selector)
        if not anchor or not anchor.get("href"):
            continue
        link = HtmlFetcher.sanitize_link(urljoin(url, anchor.get("href")))
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        candidate: dict[str, Any] = {
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
            "item_kind": ItemKind.ARTICLE,
        }
        out.append(candidate_row(
            row, crawl_key=crawl_key, source_name=source_name,
            source_type=source_type, candidate=candidate,
        ))

    return out
