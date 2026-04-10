"""
Payload für POST /api/crawler/ingest (infl0), flaches JSON wie server/api/crawler/ingest.post.ts.
"""

from __future__ import annotations

from typing import Any, Mapping

import tldextract

from crawler.utils.text_processor import calculate_hash


def finalize_entry_metadata(entry: Mapping[str, Any], *, source_type: str, source_feed_url: str) -> dict[str, Any]:
    """Ergänzt source_type, tld, content_hash wie der klassische collector."""
    out = dict(entry)
    md = out.get("content_md")
    if md:
        out["content_hash"] = calculate_hash(md)
    else:
        out["content_hash"] = None
    out["source_type"] = source_type
    out["tld"] = tldextract.extract(source_feed_url).registered_domain
    return out


def build_ingest_body(
    *,
    crawl_key: str,
    entry: Mapping[str, Any],
    enrichment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    enrichment: teaser, summary_long, category (list), tags (list), seriousness_rating
    """
    e = dict(entry)
    if enrichment:
        for k in ("teaser", "summary_long", "category", "tags", "seriousness_rating"):
            if k in enrichment and enrichment[k] is not None:
                e[k] = enrichment[k]

    body: dict[str, Any] = {"crawlKey": crawl_key, **e}
    return body
