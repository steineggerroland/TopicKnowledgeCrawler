"""Protocols for source-family adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from tkcrawler.models import Article, Candidate, Source


@runtime_checkable
class Fetcher(Protocol):
    """Adapter contract for source families that can list and fetch items."""

    def list_candidates(self, source: Source) -> list[Candidate]:
        """Return cheap candidate metadata without fetching full detail content."""

    def fetch_detail(self, source: Source, candidate: Candidate) -> Article:
        """Fetch or assemble the full content item for a candidate."""
