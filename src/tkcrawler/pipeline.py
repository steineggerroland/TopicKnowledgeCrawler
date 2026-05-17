from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from tkcrawler.steps.build_ingest_body import build_ingest_body_item
from tkcrawler.steps.fetch_detail import fetch_detail_item
from tkcrawler.steps.filter_candidates import filter_candidate_item
from tkcrawler.steps.finalize_item import finalize_item
from tkcrawler.steps.list_candidates import list_candidates_items
from tkcrawler.steps.segment_content import segment_content_item
from tkcrawler.types import Infl0IngestBody

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


def _ingest_bodies_from_finalized(
    items: list[dict[str, Any]],
    *,
    segment_longform: bool = False,
    min_sections: int = 2,
) -> list[Infl0IngestBody]:
    bodies: list[Infl0IngestBody] = []
    for item in items:
        if not item.get("article") or item.get("fetch_detail_error"):
            continue

        if segment_longform:
            segmented = segment_content_item(item)
            segment_count = int(segmented.get("segment_count") or 0)
            if segment_count >= min_sections:
                for segment in segmented.get("segments") or []:
                    segment_row = {**item, "article": dict(segment)}
                    finalized = finalize_item(segment_row)
                    bodies.append(build_ingest_body_item(finalized)["infl0_ingest_body"])
                continue

        bodies.append(build_ingest_body_item(item)["infl0_ingest_body"])
    return bodies


def crawl_source_ingest_bodies(
    source: Mapping[str, Any],
    *,
    history_lookup: HistoryLookup | None = None,
    context: Mapping[str, Any] | None = None,
    segment_longform: bool = False,
    min_sections: int = 2,
) -> list[Infl0IngestBody]:
    """Run the step flow and return infl0 ingest bodies for fetched items.

    When ``segment_longform`` is true and Markdown splits into at least
    ``min_sections`` headings, each section is finalized and emitted as its own
    ingest body (``item_kind: section``). Otherwise one body is built per item.
    """
    items = crawl_source_items(source, history_lookup=history_lookup, context=context)
    return _ingest_bodies_from_finalized(
        items,
        segment_longform=segment_longform,
        min_sections=min_sections,
    )
