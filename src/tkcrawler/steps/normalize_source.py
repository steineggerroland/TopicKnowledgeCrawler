from __future__ import annotations

import json
from typing import Any, Mapping

from tkcrawler.crawl_key import normalize_feed_url
from tkcrawler.steps._runtime import StepError, ok, parse_json_object, split_input


def _first_str(row: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_source_item(row: Mapping[str, Any]) -> dict[str, Any]:
    row = _source_row(row)
    url = _first_str(row, "url", "feedUrl")
    if not url:
        raise StepError("missing_url", "Source needs url or feedUrl")

    crawl_key = _first_str(row, "crawl_key", "crawlKey")
    if not crawl_key:
        try:
            crawl_key = normalize_feed_url(url)
        except ValueError as exc:
            raise StepError("invalid_url", f"Cannot normalize crawl key: {exc}") from exc

    name = _first_str(row, "name", "displayTitle") or url
    source_type = _first_str(row, "type")

    out: dict[str, Any] = {
        "crawl_key": crawl_key,
        "url": url,
        "name": name,
        "active": row.get("active", True),
    }

    subscriber_count = row.get("subscriber_count", row.get("subscriberCount"))
    if subscriber_count is not None:
        out["subscriber_count"] = subscriber_count

    configuration = parse_json_object(row.get("configuration_json", row.get("configuration")), field="configuration_json")
    if configuration:
        out["configuration_json"] = json.dumps(configuration, ensure_ascii=False)

    if source_type:
        out["type"] = source_type

    source_status = _first_str(row, "source_status")
    if not source_status:
        if not source_type:
            source_status = "needs_analysis"
        elif source_type == "html" and not configuration:
            source_status = "needs_analysis"
        else:
            source_status = "ready"
    out["source_status"] = source_status

    return out


def _source_row(row: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = row.get("source")
    if isinstance(nested, Mapping):
        return nested
    return row


def normalize_source_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(normalize_source_item(item))
