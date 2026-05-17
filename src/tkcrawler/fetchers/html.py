"""HTML listing page source fetcher."""

from __future__ import annotations

from tkcrawler.candidates.html import build_html_candidates
from tkcrawler.fetchers.base import BaseFetcher


class HtmlListingFetcher(BaseFetcher):
    build_candidates = staticmethod(build_html_candidates)
