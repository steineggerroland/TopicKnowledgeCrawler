"""Step: list candidates for a source without fetching detail pages.

Candidate building is implemented by source-family fetchers in ``tkcrawler.fetchers``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tkcrawler.fetchers import get_fetcher
from tkcrawler.models import Source
from tkcrawler.steps._runtime import ok, split_input


def list_candidates_items(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = Source.from_mapping(row)
    source_type = str(row.get("type") or source.type or "").strip()
    return get_fetcher(source_type).list_candidate_rows(source)


def list_candidates_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, _context = split_input(payload)
    return ok(list_candidates_items(item))
