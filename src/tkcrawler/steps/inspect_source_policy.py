from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping

import feedparser
import requests

from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError, ok, split_input


def inspect_source_policy_item(
    row: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    url = str(row.get("url") or row.get("feedUrl") or "").strip()
    if not url:
        raise StepError("missing_url", "Source needs url or feedUrl")

    now = str(context.get("now") or datetime.now(timezone.utc).isoformat())
    timeout = float(context.get("timeout_seconds", row.get("timeout_seconds", 10)))
    verify = context.get("verify", row.get("verify", True))

    try:
        response = requests.get(
            url,
            timeout=timeout,
            verify=verify,
            headers=request_headers(row, context),
        )
    except Exception as exc:
        return {
            **dict(row),
            "detected_policy_json": json.dumps({}, ensure_ascii=False),
            "detected_policy_checked_at": now,
            "detected_policy_error": str(exc),
        }

    detected = _detected_from_headers(response.headers, response.status_code, now)
    source_type = str(row.get("type") or "").strip()
    content_type = response.headers.get("content-type", "")
    if _looks_like_feed(source_type, content_type, response.text):
        detected.update(_detected_from_feed(response.text))

    return {
        **dict(row),
        "detected_policy_json": json.dumps(detected, ensure_ascii=False),
        "detected_policy_checked_at": now,
        "detected_policy_error": None,
    }


def _detected_from_headers(headers: Mapping[str, Any], status_code: int, now: str) -> dict[str, Any]:
    detected: dict[str, Any] = {
        "http_status": status_code,
    }

    etag = _header(headers, "etag")
    if etag:
        detected["etag"] = etag
    last_modified = _header(headers, "last-modified")
    if last_modified:
        detected["last_modified"] = last_modified

    cache_control = _header(headers, "cache-control")
    if cache_control:
        detected["cache_control"] = cache_control
        max_age = _cache_max_age(cache_control)
        if max_age is not None:
            detected["cache_max_age_seconds"] = max_age

    expires = _header(headers, "expires")
    if expires:
        detected["expires"] = expires

    retry_after = _header(headers, "retry-after")
    if retry_after:
        detected["retry_after"] = retry_after
        retry_seconds = _retry_after_seconds(retry_after, now)
        if retry_seconds is not None:
            detected["retry_after_seconds"] = retry_seconds

    return detected


def _detected_from_feed(body: str) -> dict[str, Any]:
    feed = feedparser.parse(body)
    ttl = _feed_value(feed.feed, "ttl")
    detected: dict[str, Any] = {}
    if ttl is not None:
        try:
            ttl_minutes = int(str(ttl).strip())
        except ValueError:
            ttl_minutes = 0
        if ttl_minutes > 0:
            detected["rss_ttl_minutes"] = ttl_minutes
    return detected


def _header(headers: Mapping[str, Any], name: str) -> str | None:
    if hasattr(headers, "get"):
        value = headers.get(name) or headers.get(name.title())
    else:
        value = None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _cache_max_age(cache_control: str) -> int | None:
    match = re.search(r"(?:^|,)\s*max-age\s*=\s*(\d+)", cache_control, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _retry_after_seconds(value: str, now: str) -> int | None:
    text = value.strip()
    if text.isdigit():
        return int(text)
    try:
        retry_at = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    return max(int((retry_at - now_dt).total_seconds()), 0)


def _looks_like_feed(source_type: str, content_type: str, body: str) -> bool:
    if source_type in {"rss", "rss+podcast"}:
        return True
    lowered = content_type.lower()
    if any(marker in lowered for marker in ("rss", "atom", "xml")):
        return True
    sample = body.lstrip()[:300].lower()
    return sample.startswith("<?xml") or "<rss" in sample or "<feed" in sample


def _feed_value(feed: Any, name: str) -> Any:
    if isinstance(feed, Mapping):
        return feed.get(name)
    return getattr(feed, name, None)


def inspect_source_policy_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(inspect_source_policy_item(item, context))
