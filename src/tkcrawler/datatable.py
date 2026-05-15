"""Convert n8n Data Table rows into source dictionaries."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def row_to_source(row: Mapping[str, Any]) -> dict:
    """
    Expected columns, see n8n/docs/DATA_TABLES.md:
    name, type, url and optional configuration_json for HTML sources.
    """
    name = (row.get("name") or "").strip()
    typ = (row.get("type") or "").strip()
    url = (row.get("url") or "").strip()
    if not name or not typ or not url:
        raise ValueError("Data table row needs name, type, url")

    src: dict = {"name": name, "type": typ, "url": url}

    cfg = row.get("configuration_json")
    if cfg is None:
        cfg = row.get("configuration")
    if isinstance(cfg, str) and cfg.strip():
        src["configuration"] = json.loads(cfg)
    elif isinstance(cfg, dict):
        src["configuration"] = cfg

    return src


def row_with_crawl_key(row: Mapping[str, Any]) -> dict:
    """Add crawl_key from url when missing so rows match infl0 user_feeds."""
    from tkcrawler.crawl_key import normalize_feed_url

    out = dict(row)
    ck = (out.get("crawl_key") or "").strip()
    if not ck:
        out["crawl_key"] = normalize_feed_url(out.get("url") or "")
    return out
