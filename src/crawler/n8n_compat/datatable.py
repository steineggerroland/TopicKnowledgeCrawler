"""
n8n Data Table Zeile → Quellen-Dict wie in config/sources.json.
"""

from __future__ import annotations

import json
from typing import Any, Mapping


def row_to_source(row: Mapping[str, Any]) -> dict:
    """
    Erwartete Spalten (siehe n8n/docs/DATA_TABLES.md):
    name, type, url, optional configuration_json (String mit JSON-Object für html-Quellen).
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
    """Ergänzt crawl_key aus url, falls nicht gesetzt (für Abgleich mit infl0 user_feeds)."""
    from src.crawler.n8n_compat.crawl_key import normalize_feed_url

    out = dict(row)
    ck = (out.get("crawl_key") or "").strip()
    if not ck:
        out["crawl_key"] = normalize_feed_url(out.get("url") or "")
    return out
