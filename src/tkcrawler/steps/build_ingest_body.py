from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.infl0_payload import build_ingest_body
from tkcrawler.steps._runtime import StepError, ok, split_input
from tkcrawler.types import BuildIngestBodyItem

ENRICHMENT_FIELDS = ("teaser", "summary_long", "category", "tags", "seriousness_rating")


def build_ingest_body_item(row: Mapping[str, Any]) -> BuildIngestBodyItem:
    crawl_key = row.get("crawl_key") or row.get("crawlKey")
    if not crawl_key:
        raise StepError("missing_crawl_key", "Item needs crawl_key")

    article = row.get("article")
    if not isinstance(article, Mapping):
        raise StepError("missing_article", "Item needs article object")

    enrichment = {
        key: row[key]
        for key in ENRICHMENT_FIELDS
        if key in row and row[key] is not None
    }
    # Compatibility for older n8n AI-agent output. The canonical input is flat.
    output = row.get("output")
    if not enrichment and isinstance(output, Mapping):
        enrichment = {
            key: output[key]
            for key in ENRICHMENT_FIELDS
            if key in output and output[key] is not None
        }

    body = build_ingest_body(
        crawl_key=str(crawl_key),
        entry=article,
        enrichment=enrichment or None,
    )

    return {
        "crawl_key": str(crawl_key),
        "article_id": article.get("id") or row.get("article_id"),
        "infl0_ingest_body": body,
    }


def build_ingest_body_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(build_ingest_body_item(item))
