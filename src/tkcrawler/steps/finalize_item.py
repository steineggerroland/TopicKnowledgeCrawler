from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.infl0_payload import finalize_entry_metadata
from tkcrawler.steps._runtime import StepError, ok, split_input


def finalize_item(row: Mapping[str, Any]) -> dict[str, Any]:
    article = row.get("article")
    if not isinstance(article, Mapping):
        raise StepError("missing_article", "Item needs article object")

    source_type = str(row.get("source_type") or row.get("type") or "").strip()
    if not source_type:
        raise StepError("missing_source_type", "Item needs source_type or type")

    source_feed_url = str(row.get("url") or row.get("source_url") or "").strip()
    if not source_feed_url:
        raise StepError("missing_source_url", "Item needs url or source_url")

    full_article = finalize_entry_metadata(
        article,
        source_type=source_type,
        source_feed_url=source_feed_url,
    )

    item_id = full_article.get("id") or row.get("item_id") or row.get("article_id")
    return {
        **dict(row),
        "article_id": item_id,
        "item_id": item_id,
        "article": full_article,
        "content_hash": full_article.get("content_hash"),
        "content_md": full_article.get("content_md"),
    }


def finalize_item_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(finalize_item(item))
