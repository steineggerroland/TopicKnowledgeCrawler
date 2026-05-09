from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from tkcrawler.steps._runtime import StepError, ok, split_input


COUNT_FIELDS = {
    "candidate_count": ("candidateCount", "candidate_count", "candidates"),
    "skipped_count": ("skipped", "skippedCandidates", "skipped_candidates", "notFetched", "not_fetched"),
    "fetch_error_count": ("fetchErrorred", "fetchErrored", "fetch_failed", "fetch_errors"),
    "unchanged_count": ("unchanged", "unchanged_items"),
    "processed_count": ("processed", "processed_items"),
    "llm_failed_count": ("llmFailed", "llm_failed", "llm_errors"),
}


def finalize_crawl_run_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    now = str(context.get("now") or datetime.now(timezone.utc).isoformat())
    crawl_key = row.get("crawl_key") or row.get("crawlKey") or context.get("crawl_key")
    if not crawl_key:
        raise StepError("missing_crawl_key", "Crawl run summary needs crawl_key")

    counts = {name: _count_first(row, *aliases) for name, aliases in COUNT_FIELDS.items()}
    error_count = counts["fetch_error_count"] + counts["llm_failed_count"]
    success_count = counts["unchanged_count"] + counts["processed_count"] + counts["skipped_count"]
    terminal_count = error_count + success_count
    total_count = counts["candidate_count"] if counts["candidate_count"] > 0 else terminal_count

    if error_count == 0:
        status = "success"
        error = None
    elif success_count > 0:
        status = "partial_failed"
        error = _summary_error(counts)
    else:
        status = "failed"
        error = _summary_error(counts)

    result = {
        "total_count": total_count,
        **counts,
    }

    previous_errors = _int_or_zero(row.get("consecutive_error_count"))
    consecutive_errors = 0 if status == "success" else previous_errors + 1

    out = {
        **dict(row),
        "crawl_key": str(crawl_key),
        "last_crawl_finished_at": now,
        "last_crawl_status": status,
        "last_crawl_error": error,
        "last_crawl_result_json": json.dumps(result, ensure_ascii=False),
        "crawl_total_count": total_count,
        "crawl_candidate_count": counts["candidate_count"],
        "crawl_skipped_count": counts["skipped_count"],
        "crawl_fetch_error_count": counts["fetch_error_count"],
        "crawl_unchanged_count": counts["unchanged_count"],
        "crawl_processed_count": counts["processed_count"],
        "crawl_llm_failed_count": counts["llm_failed_count"],
        "consecutive_error_count": consecutive_errors,
    }
    if status == "success":
        out["last_successful_crawl_at"] = now
    return out


def _count_first(row: Mapping[str, Any], *names: str) -> int:
    for name in names:
        if name in row:
            return _count(row.get(name))
    return 0


def _count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    if isinstance(value, float):
        return max(int(value), 0)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    if isinstance(value, Mapping):
        return len(value)
    text = str(value).strip()
    if not text:
        return 0
    try:
        return max(int(text), 0)
    except ValueError:
        return 1


def _int_or_zero(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _summary_error(counts: Mapping[str, int]) -> str:
    parts = []
    if counts["fetch_error_count"]:
        parts.append(f"{counts['fetch_error_count']} fetch error(s)")
    if counts["llm_failed_count"]:
        parts.append(f"{counts['llm_failed_count']} LLM failure(s)")
    return ", ".join(parts) or "Crawl failed"


def finalize_crawl_run_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(finalize_crawl_run_item(item, context))
