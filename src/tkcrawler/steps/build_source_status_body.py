from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.enums import SourceHealthStatus
from tkcrawler.steps._runtime import StepError, ok, parse_json_object, split_input

COUNT_FIELDS = {
    "crawlTotalCount": "crawl_total_count",
    "crawlCandidateCount": "crawl_candidate_count",
    "crawlSkippedCount": "crawl_skipped_count",
    "crawlProcessedCount": "crawl_processed_count",
    "crawlFetchErrorCount": "crawl_fetch_error_count",
    "crawlUnchangedCount": "crawl_unchanged_count",
    "crawlLlmFailedCount": "crawl_llm_failed_count",
    "consecutiveErrorCount": "consecutive_error_count",
}


def build_source_status_body_item(row: Mapping[str, Any]) -> dict[str, Any]:
    crawl_key = row.get("crawl_key") or row.get("crawlKey")
    if not crawl_key:
        raise StepError("missing_crawl_key", "Source status needs crawl_key")

    detected_policy = _parse_optional_json_object(
        row.get("detected_policy_json", row.get("detected_policy")),
        field="detected_policy_json",
    )
    effective_policy = _parse_optional_json_object(
        row.get("effective_policy", row.get("effective_policy_json")),
        field="effective_policy",
    )
    source_health = _parse_optional_json_object(
        row.get("source_health_json", row.get("source_health")),
        field="source_health_json",
    )
    crawl_result = _parse_optional_json_object(
        row.get("last_crawl_result_json", row.get("last_crawl_result")),
        field="last_crawl_result_json",
    )
    source_health_status = _optional_str(row.get("source_health_status"))
    source_health_reason = _optional_str(row.get("source_health_reason"))
    if _looks_never_crawled(row, crawl_result):
        source_health_status = source_health_status or SourceHealthStatus.PENDING
        source_health_reason = source_health_reason or "never_crawled"

    body: dict[str, Any] = {
        "crawlKey": str(crawl_key),
        "name": _optional_str(row.get("name")),
        "type": _optional_str(row.get("type")),
        "url": _optional_str(row.get("url") or row.get("feedUrl")),
        "active": _optional_bool(row.get("active")),
        "sourceStatus": _optional_str(row.get("source_status")),
        "configurationStatus": _optional_str(row.get("configuration_status")),
        "sourceHealthStatus": source_health_status,
        "sourceHealthReason": source_health_reason,
        "sourceHealth": source_health or None,
        "operatorAttention": _optional_bool(row.get("operator_attention")),
        "operatorAttentionReason": _optional_str(row.get("operator_attention_reason")),
        "detectedContentType": _optional_str(row.get("detected_content_type")),
        "analysisCheckedAt": _optional_str(row.get("analysis_checked_at")),
        "analysisError": _optional_str(row.get("analysis_error")),
        "configurationError": _optional_str(row.get("configuration_error")),
        "lastDispatchReason": _optional_str(row.get("last_dispatch_reason")),
        "lastCrawlStatus": _optional_str(row.get("last_crawl_status")),
        "lastCrawlStartedAt": _optional_str(row.get("last_crawl_started_at")),
        "lastCrawlFinishedAt": _optional_str(row.get("last_crawl_finished_at")),
        "lastSuccessfulCrawlAt": _optional_str(row.get("last_successful_crawl_at")),
        "lastCrawlError": _optional_str(row.get("last_crawl_error")),
        "nextAllowedCrawlAt": _optional_str(row.get("next_allowed_crawl_at")),
        "lastCrawlResult": crawl_result or None,
        "effectivePolicy": effective_policy or None,
        "detectedPolicy": detected_policy or None,
        "detectedPolicyCheckedAt": _optional_str(row.get("detected_policy_checked_at")),
        "detectedPolicyError": _optional_str(row.get("detected_policy_error")),
    }
    for payload_name, row_name in COUNT_FIELDS.items():
        body[payload_name] = _optional_int(row.get(row_name))

    return {
        **dict(row),
        "infl0_source_status_body": body,
    }


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_optional_json_object(value: Any, *, field: str) -> dict[str, Any]:
    try:
        return parse_json_object(value, field=field)
    except StepError:
        return {}


def _looks_never_crawled(row: Mapping[str, Any], crawl_result: Mapping[str, Any]) -> bool:
    return not any(
        _optional_str(row.get(field))
        for field in (
            "last_crawl_status",
            "last_crawl_started_at",
            "last_crawl_finished_at",
            "last_successful_crawl_at",
            "last_crawl_error",
        )
    ) and not crawl_result


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return None


def build_source_status_body_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(build_source_status_body_item(item))
