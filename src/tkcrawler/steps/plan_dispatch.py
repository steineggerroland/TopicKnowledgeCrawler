from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from tkcrawler.steps._runtime import StepError, ok, parse_json_object, split_input

DEFAULT_POLICY = {
    "crawl_interval_minutes": 180,
    "rate_limit_per_minute": 10,
    "refresh_window_days": 7,
    "stale_running_minutes": 120,
}


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
        except ValueError as exc:
            raise StepError("invalid_datetime", f"Invalid datetime: {value}") from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _merge_policy(row: Mapping[str, Any]) -> dict[str, Any]:
    policy = dict(DEFAULT_POLICY)
    detected = parse_json_object(row.get("detected_policy_json", row.get("detected_policy")), field="detected_policy_json")
    manual = parse_json_object(row.get("policy_json", row.get("policy")), field="policy_json")
    effective = parse_json_object(row.get("effective_policy_json", row.get("effective_policy")), field="effective_policy_json")

    ttl = detected.get("rss_ttl_minutes")
    if isinstance(ttl, (int, float)) and ttl > 0:
        policy["crawl_interval_minutes"] = max(policy["crawl_interval_minutes"], int(ttl))

    policy.update(manual)
    policy.update(effective)
    return policy


def _retry_after_until(row: Mapping[str, Any], now: datetime) -> datetime | None:
    detected = parse_json_object(row.get("detected_policy_json", row.get("detected_policy")), field="detected_policy_json")
    explicit = _parse_dt(detected.get("retry_after_until"))
    if explicit:
        return explicit

    seconds = detected.get("retry_after_seconds")
    if isinstance(seconds, (int, float)) and seconds > 0:
        base = _parse_dt(row.get("last_crawl_finished_at")) or now
        return base + timedelta(seconds=float(seconds))
    return None


def plan_dispatch_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    now = _parse_dt(context.get("now")) or datetime.now(timezone.utc)
    dispatch_mode = str(context.get("dispatch_mode") or "scheduled")
    force = dispatch_mode == "force" or bool(context.get("force"))

    crawl_key = row.get("crawl_key") or row.get("crawlKey") or row.get("url")
    if not crawl_key:
        raise StepError("missing_crawl_key", "Source needs crawl_key")

    policy = _merge_policy(row)
    source_type = str(row.get("type") or "").strip()
    source_status = str(row.get("source_status") or ("ready" if source_type else "needs_analysis")).strip()
    configuration_status = str(row.get("configuration_status") or "").strip()

    reason = "due"
    should = True

    active = row.get("active", True)
    if active is False or str(active).lower() in {"false", "0", "no"}:
        should, reason = False, "inactive"
    elif source_status != "ready":
        should, reason = False, "source_not_ready"
    elif source_type == "html" and configuration_status not in {"valid", "generated"}:
        should, reason = False, "html_configuration_invalid"
    else:
        retry_until = _retry_after_until(row, now)
        next_allowed = _parse_dt(row.get("next_allowed_crawl_at"))
        if not force:
            if next_allowed and next_allowed > now:
                should, reason = False, "not_due"
            elif retry_until and retry_until > now:
                should, reason = False, "retry_after_active"
            elif str(row.get("last_crawl_status") or "").strip() == "running":
                started = _parse_dt(row.get("last_crawl_started_at"))
                stale_after = timedelta(minutes=float(policy.get("stale_running_minutes", 120)))
                if started and started + stale_after <= now:
                    should, reason = True, "due"
                else:
                    should, reason = False, "already_running"
        elif retry_until and retry_until > now:
            should, reason = False, "retry_after_active"

    interval = float(policy.get("crawl_interval_minutes", DEFAULT_POLICY["crawl_interval_minutes"]))
    current_next_allowed = _parse_dt(row.get("next_allowed_crawl_at"))
    next_allowed_out = current_next_allowed
    if should:
        if force:
            reason = "manual_force"
        next_allowed_out = now + timedelta(minutes=interval)

    return {
        **dict(row),
        "crawl_key": str(crawl_key),
        "should_dispatch": should,
        "dispatch_reason": reason,
        "next_allowed_crawl_at": _iso(next_allowed_out),
        "effective_policy": policy,
    }


def plan_dispatch_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(plan_dispatch_item(item, context))
