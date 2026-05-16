from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from tkcrawler.steps.build_ingest_body import build_ingest_body_item
from tkcrawler.steps.fetch_detail import fetch_detail_item
from tkcrawler.steps.filter_candidates import filter_candidate_item
from tkcrawler.steps.finalize_item import finalize_item
from tkcrawler.steps.list_candidates import list_candidates_items

HistoryLookup = Callable[[str], Mapping[str, Any] | None]


def crawl_source_items(
    source: Mapping[str, Any],
    *,
    history_lookup: HistoryLookup | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run the canonical step-based crawl flow for one source.

    This mirrors the n8n workflow up to finalized content items:

    list candidates -> optional history lookup -> filter -> fetch detail ->
    finalize item.

    The function intentionally does not call an LLM and does not POST to infl0.
    Flow systems can insert those steps between `finalize_item` and
    `build_ingest_body_item`, just like n8n does.
    """
    context = dict(context or {})
    now = str(context.get("now") or datetime.now(UTC).isoformat())
    out: list[dict[str, Any]] = []

    for candidate_row in list_candidates_items(source):
        article_id = str(candidate_row.get("article_id") or candidate_row.get("item_id") or "")
        row = dict(candidate_row)
        if history_lookup and article_id:
            history = history_lookup(article_id)
            if history:
                row["history"] = dict(history)

        filtered = filter_candidate_item(row, {"now": now})
        if filtered["candidate_decision"] != "fetch":
            out.append(filtered)
            continue

        try:
            fetched = fetch_detail_item(filtered, context)
            out.append(finalize_item(fetched))
        except Exception as exc:
            failed = dict(filtered)
            failed["fetch_detail_error"] = str(exc)
            failed["candidate_decision"] = "fetch_failed"
            out.append(failed)

    return out


def crawl_source_ingest_bodies(
    source: Mapping[str, Any],
    *,
    history_lookup: HistoryLookup | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run the step flow and return infl0 ingest bodies for fetched items."""
    bodies: list[dict[str, Any]] = []
    for item in crawl_source_items(source, history_lookup=history_lookup, context=context):
        if item.get("article") and not item.get("fetch_detail_error"):
            bodies.append(build_ingest_body_item(item)["infl0_ingest_body"])
    return bodies
