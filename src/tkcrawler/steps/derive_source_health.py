from __future__ import annotations

import json
from typing import Any, Mapping

from tkcrawler.steps._runtime import ok, parse_json_object, split_input


def derive_source_health_item(row: Mapping[str, Any]) -> dict[str, Any]:
    detected = parse_json_object(row.get("detected_policy_json", row.get("detected_policy")), field="detected_policy_json")
    status, reason = _health(row, detected)
    attention, attention_reason = _operator_attention(row, detected, status, reason)
    health = {
        "status": status,
        "reason": reason,
        "operator_attention": attention,
        "operator_attention_reason": attention_reason,
        "crawl": {
            "last_status": row.get("last_crawl_status"),
            "candidate_count": _int(row.get("crawl_candidate_count")),
            "skipped_count": _int(row.get("crawl_skipped_count")),
            "processed_count": _int(row.get("crawl_processed_count")),
            "unchanged_count": _int(row.get("crawl_unchanged_count")),
            "fetch_error_count": _int(row.get("crawl_fetch_error_count")),
            "llm_failed_count": _int(row.get("crawl_llm_failed_count")),
            "consecutive_error_count": _int(row.get("consecutive_error_count")),
        },
        "policy": {
            "next_allowed_crawl_at": row.get("next_allowed_crawl_at"),
            "detected": detected,
        },
    }
    return {
        **dict(row),
        "source_health_status": status,
        "source_health_reason": reason,
        "source_health_json": json.dumps(health, ensure_ascii=False),
        "operator_attention": attention,
        "operator_attention_reason": attention_reason,
    }


def _health(row: Mapping[str, Any], detected: Mapping[str, Any]) -> tuple[str, str]:
    active = row.get("active", True)
    if active is False or str(active).lower() in {"false", "0", "no"}:
        return "paused", "inactive"

    source_status = str(row.get("source_status") or "").strip()
    configuration_status = str(row.get("configuration_status") or "").strip()
    if source_status in {"needs_analysis", "configuration_invalid"}:
        return "needs_setup", source_status
    if configuration_status in {"missing", "invalid"}:
        return "needs_setup", f"configuration_{configuration_status}"
    if source_status == "analysis_failed":
        return "failing", "analysis_failed"

    http_status = _int(detected.get("http_status"))
    if http_status in {403, 429}:
        return "blocked", f"http_{http_status}"
    if http_status >= 500:
        return "degraded", f"http_{http_status}"
    if detected.get("retry_after_seconds") or detected.get("retry_after_until"):
        return "paused", "retry_after_active"

    last_status = str(row.get("last_crawl_status") or "").strip()
    if not last_status:
        return "pending", "never_crawled"
    if last_status == "failed":
        return "failing", "last_crawl_failed"
    if last_status == "partial_failed":
        return "degraded", "last_crawl_partial_failed"

    candidate_count = _int(row.get("crawl_candidate_count"))
    processed_count = _int(row.get("crawl_processed_count"))
    unchanged_count = _int(row.get("crawl_unchanged_count"))
    skipped_count = _int(row.get("crawl_skipped_count"))
    if candidate_count == 0:
        return "quiet", "no_candidates"
    if skipped_count >= candidate_count and processed_count == 0 and unchanged_count == 0:
        return "quiet", "all_candidates_skipped"
    return "healthy", "recent_success"


def _operator_attention(
    row: Mapping[str, Any],
    detected: Mapping[str, Any],
    status: str,
    reason: str,
) -> tuple[bool, str | None]:
    if status in {"failing", "blocked"}:
        return True, reason
    if _int(row.get("consecutive_error_count")) >= 2:
        return True, "repeated_errors"
    if _int(row.get("crawl_fetch_error_count")) > 0 and _int(row.get("crawl_processed_count")) == 0:
        return True, "fetch_errors_without_processed_items"
    if row.get("detected_policy_error"):
        return True, "policy_detection_failed"
    http_status = _int(detected.get("http_status"))
    if http_status in {403, 429} or http_status >= 500:
        return True, f"http_{http_status}"
    return False, None


def _int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def derive_source_health_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(derive_source_health_item(item))
