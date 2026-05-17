from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from typing import Any

from tkcrawler.enums import ItemKind
from tkcrawler.steps._runtime import StepError, ok, split_input

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _article(row: Mapping[str, Any]) -> Mapping[str, Any]:
    article = row.get("article")
    if isinstance(article, Mapping):
        return article
    return row


def _segment_id(parent_id: str, position: int, title: str | None, content_md: str) -> str:
    payload = f"{parent_id}\0{position}\0{title or ''}\0{content_md}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _clean_heading(value: str) -> str:
    return value.strip().strip("#").strip()


def _split_sections(content_md: str, fallback_title: str | None) -> list[tuple[str | None, str]]:
    matches = list(HEADING_RE.finditer(content_md))
    if not matches:
        return [(fallback_title, content_md.strip())]

    sections: list[tuple[str | None, str]] = []
    intro = content_md[:matches[0].start()].strip()
    if intro:
        sections.append((fallback_title or "Introduction", intro))

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content_md)
        section_md = content_md[match.start():end].strip()
        if section_md:
            sections.append((_clean_heading(match.group(2)), section_md))
    return sections


def _segment_article(parent: Mapping[str, Any], *, position: int, title: str | None, content_md: str) -> dict[str, Any]:
    parent_id = str(parent.get("id") or "").strip()
    if not parent_id:
        raise StepError("missing_parent_id", "Item needs id to build content segments")

    segment: dict[str, Any] = {
        "id": _segment_id(parent_id, position, title, content_md),
        "item_kind": ItemKind.SECTION,
        "parent_item_id": parent_id,
        "position": position,
        "title": title or parent.get("title"),
        "link": parent.get("link"),
        "summary": parent.get("summary"),
        "author": parent.get("author"),
        "publishedAt": parent.get("publishedAt"),
        "updatedAt": parent.get("updatedAt"),
        "content_md": content_md,
    }
    for field in ("source_type", "tld", "categories"):
        if parent.get(field) is not None:
            segment[field] = parent.get(field)
    return segment


def segment_content_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    _context = context or {}
    parent = _article(row)
    content_md = str(parent.get("content_md") or row.get("content_md") or "").strip()
    if not content_md:
        raise StepError("missing_content", "Item needs article.content_md or content_md")

    parts = _split_sections(content_md, parent.get("title"))
    segments = [
        _segment_article(parent, position=index + 1, title=title, content_md=section_md)
        for index, (title, section_md) in enumerate(parts)
        if section_md
    ]

    return {
        **dict(row),
        "segments": segments,
        "segment_count": len(segments),
    }


def segment_content_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(segment_content_item(item, context))
