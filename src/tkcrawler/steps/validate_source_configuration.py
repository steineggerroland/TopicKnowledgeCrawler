from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tkcrawler.enums import ConfigurationStatus, SourceStatus, SourceType
from tkcrawler.steps._runtime import StepError, ok, split_input
from tkcrawler.steps.list_candidates import list_candidates_items


def validate_source_configuration_item(
    row: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    source_type = str(row.get("type") or "").strip()
    now = str(context.get("now") or datetime.now(timezone.utc).isoformat())

    if source_type in {SourceType.RSS, SourceType.PODCAST}:
        return {
            **dict(row),
            "source_status": SourceStatus.READY,
            "configuration_status": None,
            "configuration_error": None,
            "configuration_checked_at": now,
        }
    if source_type != SourceType.HTML:
        return {
            **dict(row),
            "source_status": SourceStatus.ANALYSIS_FAILED,
            "configuration_status": ConfigurationStatus.INVALID,
            "configuration_error": f"Unsupported source type: {source_type or 'missing'}",
            "configuration_checked_at": now,
        }

    try:
        sample_row = _with_sample_limit(row, context)
        candidates = list_candidates_items(sample_row)
    except StepError as exc:
        return _invalid(row, now, exc.message)
    except Exception as exc:
        return _invalid(row, now, str(exc))

    sample_count = len(candidates)
    if sample_count <= 0:
        return _invalid(row, now, "HTML configuration did not find candidates", sample_count=0)

    return {
        **dict(row),
        "source_status": SourceStatus.READY,
        "configuration_status": ConfigurationStatus.VALID,
        "configuration_error": None,
        "configuration_checked_at": now,
        "sample_candidate_count": sample_count,
    }


def _with_sample_limit(row: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    sample_limit = int(context.get("sample_candidate_limit", 5))
    out = dict(row)
    policy = dict(out.get("effective_policy") or {})
    policy["max_candidates_per_run"] = sample_limit
    out["effective_policy"] = policy
    return out


def _invalid(row: Mapping[str, Any], now: str, error: str, *, sample_count: int | None = None) -> dict[str, Any]:
    out = {
        **dict(row),
        "source_status": SourceStatus.CONFIGURATION_INVALID,
        "configuration_status": ConfigurationStatus.INVALID,
        "configuration_error": error,
        "configuration_checked_at": now,
    }
    if sample_count is not None:
        out["sample_candidate_count"] = sample_count
    return out


def validate_source_configuration_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(validate_source_configuration_item(item, context))
