# n8n → Code → Python
# Pro Item: Data-Table-Zeile (`url`, `name`, …) oder infl0 `GET /api/crawler/sources`
# (`feedUrl`, `crawlKey`, `displayTitle`). Wie collector.py: RSS vs. HTML, bei HTML LLM (SourceAnalyzer).
#
# Voraussetzung: pip install -e des Repos im Runner; LLM-Env wie LlmPrompter (lokal).

import json

from crawler.analyzer.source_analyzer import SourceAnalyzer
from tkcrawler.crawl_key import normalize_feed_url


def _row_url(row: dict) -> str:
    """Data Table (`url`) oder infl0 GET `/api/crawler/sources` (`feedUrl`)."""
    return (row.get("url") or row.get("feedUrl") or "").strip()


def _row_name(row: dict) -> str:
    return (row.get("name") or row.get("displayTitle") or "").strip()


def _row_to_source_dict(row: dict) -> dict:
    url = _row_url(row)
    if not url:
        raise ValueError("row needs url or feedUrl")
    s: dict = {"url": url}
    name = _row_name(row)
    if name:
        s["name"] = name
    t = (row.get("type") or "").strip()
    if t:
        s["type"] = t
    cfg = row.get("configuration_json")
    if isinstance(cfg, str) and cfg.strip():
        s["configuration"] = json.loads(cfg)
    elif isinstance(cfg, dict) and cfg:
        s["configuration"] = cfg
    return s


def _needs_analyze(source: dict) -> bool:
    t = (source.get("type") or "").strip()
    if not t:
        return True
    if t == "html" and "configuration" not in source:
        return True
    return False


def _ensure_fetch_fields(row: dict) -> None:
    """Damit `row_to_source` / Fetch später `name`, `type`, `url` haben."""
    u = _row_url(row)
    if u:
        row["url"] = u
    n = _row_name(row)
    if n:
        row["name"] = n
    elif u:
        row["name"] = u
    ck = (row.get("crawl_key") or row.get("crawlKey") or "").strip()
    if ck:
        row["crawl_key"] = ck
    elif u:
        try:
            row["crawl_key"] = normalize_feed_url(u)
        except Exception:
            pass


out = []
for item in items:
    row = dict(item.get("json") or {})
    try:
        source = _row_to_source_dict(row)
        if not _needs_analyze(source):
            _ensure_fetch_fields(row)
            if not (row.get("crawl_key") or "").strip() and _row_url(row):
                try:
                    row["crawl_key"] = normalize_feed_url(_row_url(row))
                except Exception:
                    pass
            out.append({"json": row})
            continue

        analyzer = SourceAnalyzer()
        updated = analyzer.analyze_source(dict(source))

        merged = {**row}
        new_type = (updated.get("type") or "").strip()
        if new_type:
            merged["type"] = new_type
        if updated.get("configuration") is not None:
            merged["configuration_json"] = json.dumps(
                updated["configuration"], ensure_ascii=False
            )
        if (updated.get("url") or "").strip():
            merged["url"] = updated["url"].strip()
        _ensure_fetch_fields(merged)
        try:
            merged["crawl_key"] = normalize_feed_url(_row_url(merged))
        except Exception:
            if not (merged.get("crawl_key") or "").strip():
                merged["crawl_key"] = row.get("crawl_key") or row.get("crawlKey", "")

        if not (merged.get("type") or "").strip():
            merged["analyze_error"] = "SourceAnalyzer did not set type (see runner logs)"
        out.append({"json": merged})
    except Exception as exc:
        out.append({"json": {**row, "analyze_error": str(exc)}})

return out
