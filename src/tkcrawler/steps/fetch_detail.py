from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.enums import CandidateDecision
from tkcrawler.fetchers import get_fetcher
from tkcrawler.fetchers._detail import EPISODE_FIELDS
from tkcrawler.models import Candidate, Source
from tkcrawler.steps._runtime import StepError, ok, split_input

__all__ = ["EPISODE_FIELDS", "fetch_detail_item", "fetch_detail_step"]


def fetch_detail_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    candidate_raw = row.get("candidate")
    if not isinstance(candidate_raw, Mapping):
        raise StepError("missing_candidate", "Item needs candidate object")

    decision = row.get("candidate_decision")
    if decision and decision != CandidateDecision.FETCH:
        raise StepError(
            "candidate_not_fetchable",
            f"Candidate decision is not fetch: {decision}",
            {"candidate_decision": decision},
        )

    candidate = Candidate.from_mapping(candidate_raw)
    source_type = str(row.get("source_type") or row.get("type") or "").strip()
    if not source_type:
        raise StepError("missing_source_type", "Item needs source_type or type")
    source = Source.from_mapping({**dict(row), "type": source_type})

    fetcher = get_fetcher(source_type)
    article = fetcher.fetch_detail(
        source,
        candidate,
        context,
        prefer_feed_content=row.get("prefer_feed_content") if "prefer_feed_content" in row else None,
    )
    article_data = article.to_dict()
    content_md = article_data.get("content_md") or ""

    return {
        **dict(row),
        "article_id": article_data.get("id"),
        "item_id": article_data.get("id"),
        "article": article_data,
        "content_md": content_md,
        "fetch_detail_error": None,
    }


def fetch_detail_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(fetch_detail_item(item, context))
