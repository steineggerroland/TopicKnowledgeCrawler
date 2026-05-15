from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from tkcrawler.enums import CandidateDecision
from tkcrawler.steps._runtime import StepError, ok, parse_json_object, split_input

DEFAULT_REFRESH_WINDOW_DAYS = 7


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError) as exc:
                raise StepError("invalid_datetime", f"Invalid datetime: {value}") from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _refresh_window_days(row: Mapping[str, Any]) -> int:
    policy = row.get("effective_policy")
    if isinstance(policy, Mapping) and policy.get("refresh_window_days") is not None:
        return int(policy["refresh_window_days"])
    policy_json = parse_json_object(row.get("effective_policy_json"), field="effective_policy_json")
    if policy_json.get("refresh_window_days") is not None:
        return int(policy_json["refresh_window_days"])
    return DEFAULT_REFRESH_WINDOW_DAYS


def _history_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    history = row.get("history")
    if isinstance(history, Mapping):
        return dict(history)

    # n8n Merge nodes commonly flatten history fields into the candidate item.
    if row.get("is_known") is not None:
        return {"exists": bool(row.get("is_known"))}
    if row.get("content_hash") or row.get("is_sent") is not None or row.get("article") is not None:
        return {"exists": True}
    if row.get("history_exists") is not None:
        return {"exists": bool(row.get("history_exists"))}
    return {"exists": False}


def filter_candidate_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    candidate = row.get("candidate")
    if not isinstance(candidate, Mapping):
        raise StepError("missing_candidate", "Item needs candidate object")

    now = _parse_dt(context.get("now")) or datetime.now(timezone.utc)
    refresh_window_days = _refresh_window_days(row)
    refresh_cutoff = now - timedelta(days=refresh_window_days)
    history = _history_from_row(row)
    history_exists = bool(history.get("exists"))

    candidate_dt = (
        _parse_dt(candidate.get("updatedAt"))
        or _parse_dt(candidate.get("publishedAt"))
    )

    decision = CandidateDecision.FETCH
    reason = "new_candidate"

    if history_exists:
        if candidate_dt and candidate_dt < refresh_cutoff:
            decision = CandidateDecision.SKIP_TOO_OLD
            reason = "known_candidate_outside_refresh_window"
        else:
            decision = CandidateDecision.FETCH
            reason = "known_candidate_within_refresh_window"

    return {
        **dict(row),
        "article_id": row.get("article_id") or candidate.get("id"),
        "item_id": row.get("item_id") or candidate.get("id"),
        "candidate": dict(candidate),
        "candidate_published_at": _iso(_parse_dt(candidate.get("publishedAt"))),
        "candidate_updated_at": _iso(_parse_dt(candidate.get("updatedAt"))),
        "candidate_decision": decision,
        "candidate_reason": reason,
        "candidate_history_exists": history_exists,
        "refresh_window_days": refresh_window_days,
        "refresh_cutoff_at": _iso(refresh_cutoff),
    }


def filter_candidates_items(rows: list[Mapping[str, Any]], context: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    return [filter_candidate_item(row, context) for row in rows]


def filter_candidates_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(filter_candidate_item(item, context))
