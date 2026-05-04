from __future__ import annotations

from typing import Any, Mapping

from tkcrawler.steps._runtime import StepError, ok, parse_json_object, split_input


def _max_llm_items(row: Mapping[str, Any], context: Mapping[str, Any]) -> int | None:
    if context.get("max_llm_items_per_run") is not None:
        return int(context["max_llm_items_per_run"])

    policy = row.get("effective_policy")
    if isinstance(policy, Mapping) and policy.get("max_llm_items_per_run") is not None:
        return int(policy["max_llm_items_per_run"])

    policy_json = parse_json_object(row.get("effective_policy_json"), field="effective_policy_json")
    if policy_json.get("max_llm_items_per_run") is not None:
        return int(policy_json["max_llm_items_per_run"])

    return None


def limit_llm_items(rows: list[Mapping[str, Any]], context: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    processed_by_source: dict[str, int] = {}
    out: list[dict[str, Any]] = []

    for row in rows:
        source_key = str(row.get("crawl_key") or row.get("source_key") or "default")
        limit = _max_llm_items(row, context)
        processed = processed_by_source.get(source_key, 0)

        if limit is None or limit < 0:
            decision = "process"
            reason = "no_run_limit"
            processed_by_source[source_key] = processed + 1
        elif processed < limit:
            decision = "process"
            reason = "within_run_limit"
            processed_by_source[source_key] = processed + 1
        else:
            decision = "skip_run_limit"
            reason = "max_llm_items_per_run_reached"

        out.append(
            {
                **dict(row),
                "llm_decision": decision,
                "llm_reason": reason,
                "llm_run_index": processed + 1 if decision == "process" else processed,
                "max_llm_items_per_run": limit,
            }
        )

    return out


def limit_llm_items_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    rows = item.get("items")
    if rows is None:
        rows = [item]
    if not isinstance(rows, list):
        raise StepError("invalid_input", "limit_llm_items expects item.items list or a single item")
    return ok(limit_llm_items(rows, context))
