"""Step: list candidates for a source without fetching detail pages.

The actual candidate building logic lives in ``tkcrawler.candidates``.
This module is the thin step/CLI entry point.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.enums import SourceType
from tkcrawler.steps._runtime import StepError, ok, split_input


def list_candidates_items(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_type = str(row.get("type") or "").strip()
    if source_type in {SourceType.RSS, SourceType.PODCAST}:
        if source_type == SourceType.PODCAST:
            from tkcrawler.candidates.podcast import build_podcast_candidates

            return build_podcast_candidates(row)

        from tkcrawler.candidates.rss import build_rss_candidates

        return build_rss_candidates(row)
    if source_type == SourceType.HTML:
        from tkcrawler.candidates.html import build_html_candidates

        return build_html_candidates(row)
    raise StepError(
        "unsupported_source_type",
        f"list_candidates does not support source type: {source_type!r}",
        {"source_type": source_type},
    )


def list_candidates_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(list_candidates_items(item))
