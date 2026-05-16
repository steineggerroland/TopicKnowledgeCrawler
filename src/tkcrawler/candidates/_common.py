"""Shared helpers for candidate builders."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.steps._runtime import StepError


def entry_get(entry: Any, name: str, default: Any = None) -> Any:
    """Read a field from a feedparser entry or plain mapping."""
    if isinstance(entry, Mapping):
        return entry.get(name, default)
    return getattr(entry, name, default)


def source_basics(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Extract (source_type, url, crawl_key, source_name) from a row."""
    source_type = str(row.get("type") or "").strip()
    url = str(row.get("url") or "").strip()
    if not url:
        raise StepError("missing_url", "Source needs url")
    crawl_key = str(row.get("crawl_key") or row.get("crawlKey") or url)
    source_name = str(row.get("name") or url)
    return source_type, url, crawl_key, source_name


def max_candidates(row: Mapping[str, Any]) -> int | None:
    """Read the optional candidate cap from the effective policy."""
    max_entries = policy_value(row, "max_candidates_per_run")
    if max_entries is None:
        max_entries = policy_value(row, "max_entries_per_run")
    if max_entries is not None:
        try:
            return int(max_entries)
        except (TypeError, ValueError) as exc:
            raise StepError("invalid_policy", "max_candidates_per_run must be an integer") from exc
    return None


def policy_value(row: Mapping[str, Any], name: str, default: Any = None) -> Any:
    """Read a single value from the effective_policy mapping."""
    policy = row.get("effective_policy")
    if isinstance(policy, Mapping) and name in policy:
        return policy[name]
    return default


def candidate_row(
    row: Mapping[str, Any],
    *,
    crawl_key: str,
    source_name: str,
    source_type: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    """Wrap a candidate into a full pipeline row."""
    return {
        **dict(row),
        "crawl_key": crawl_key,
        "source_name": source_name,
        "source_type": source_type,
        "article_id": candidate["id"],
        "item_id": candidate["id"],
        "candidate": dict(candidate),
    }
