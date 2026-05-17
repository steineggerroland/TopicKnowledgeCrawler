"""Base fetcher: typed boundary over candidate builders and detail fetch."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from tkcrawler.fetchers._detail import fetch_article_detail
from tkcrawler.models import Article, Candidate, Source


class BaseFetcher:
    """Adapter that lists candidates and fetches detail for one source family."""

    build_candidates: Callable[[Mapping[str, Any]], list[dict[str, Any]]]

    def list_candidates(self, source: Source) -> list[Candidate]:
        return [
            Candidate.from_mapping(row["candidate"])
            for row in self.list_candidate_rows(source)
        ]

    def list_candidate_rows(self, source: Source) -> list[dict[str, Any]]:
        return self.build_candidates(source.to_dict())

    def fetch_detail(
        self,
        source: Source,
        candidate: Candidate,
        context: Mapping[str, Any] | None = None,
        *,
        prefer_feed_content: bool | None = None,
    ) -> Article:
        return fetch_article_detail(
            source,
            candidate,
            context,
            prefer_feed_content=prefer_feed_content,
        )
