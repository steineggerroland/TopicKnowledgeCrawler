"""RSS/Atom source fetcher."""

from __future__ import annotations

from tkcrawler.candidates.rss import build_rss_candidates
from tkcrawler.fetchers.base import BaseFetcher


class RssFetcher(BaseFetcher):
    build_candidates = staticmethod(build_rss_candidates)
