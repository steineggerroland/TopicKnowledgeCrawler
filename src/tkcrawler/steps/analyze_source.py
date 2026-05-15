from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

from tkcrawler.enums import ConfigurationStatus, SourceStatus, SourceType
from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError, ok, split_input


def analyze_source_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    url = str(row.get("url") or row.get("feedUrl") or "").strip()
    if not url:
        raise StepError("missing_url", "Source needs url or feedUrl")

    timeout = float(context.get("timeout_seconds", row.get("timeout_seconds", 10)))
    verify = context.get("verify", row.get("verify", True))
    now = str(context.get("now") or datetime.now(timezone.utc).isoformat())

    try:
        response = requests.get(
            url,
            timeout=timeout,
            verify=verify,
            headers=request_headers(row, context),
        )
        response.raise_for_status()
    except Exception as exc:
        return {
            **dict(row),
            "source_status": SourceStatus.ANALYSIS_FAILED,
            "analysis_error": str(exc),
            "analysis_checked_at": now,
        }

    content_type = response.headers.get("content-type", "")
    source_type = _detect_source_type(content_type, response.text)
    out = {
        **dict(row),
        "type": source_type,
        "detected_content_type": content_type,
        "analysis_checked_at": now,
        "analysis_error": None,
    }

    if source_type in {SourceType.RSS, SourceType.PODCAST}:
        out["source_status"] = SourceStatus.READY
        out.setdefault("configuration_status", None)
    elif source_type == SourceType.HTML:
        out["source_status"] = SourceStatus.READY if _has_html_configuration(row) else SourceStatus.NEEDS_ANALYSIS
        out["configuration_status"] = row.get("configuration_status") or (ConfigurationStatus.VALID if _has_html_configuration(row) else ConfigurationStatus.MISSING)
    else:
        out["source_status"] = SourceStatus.ANALYSIS_FAILED
        out["analysis_error"] = f"Unknown content type: {content_type or 'not provided'}"

    return out


def _detect_source_type(content_type: str, body: str) -> str:
    lower_content_type = content_type.lower()
    if any(marker in lower_content_type for marker in ("rss", "atom", "xml")):
        return _feed_type(body)
    if "html" in lower_content_type:
        return SourceType.HTML

    stripped = body.lstrip()[:300].lower()
    if stripped.startswith("<?xml") or "<rss" in stripped or "<feed" in stripped:
        return _feed_type(body)
    if "<html" in stripped or "<!doctype html" in stripped:
        return SourceType.HTML
    return SourceType.UNKNOWN


def _feed_type(body: str) -> str:
    feed = feedparser.parse(body)
    for entry in getattr(feed, "entries", None) or []:
        if _entry_get(entry, "itunes_duration") or _entry_get(entry, "enclosures"):
            return SourceType.PODCAST
    return SourceType.RSS


def _entry_get(entry: Any, name: str) -> Any:
    if isinstance(entry, Mapping):
        return entry.get(name)
    return getattr(entry, name, None)


def _has_html_configuration(row: Mapping[str, Any]) -> bool:
    raw = row.get("configuration")
    if isinstance(raw, Mapping):
        return bool(raw.get("article_selector") and raw.get("main_page_anchor_selector"))
    return bool(str(row.get("configuration_json") or "").strip())


def analyze_source_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(analyze_source_item(item, context))
