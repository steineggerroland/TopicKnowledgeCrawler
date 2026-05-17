"""Source-family fetchers implementing the Fetcher port."""

from __future__ import annotations

from tkcrawler.enums import SourceType
from tkcrawler.fetchers.base import BaseFetcher
from tkcrawler.fetchers.html import HtmlListingFetcher
from tkcrawler.fetchers.podcast import PodcastFetcher
from tkcrawler.fetchers.rss import RssFetcher
from tkcrawler.protocols import Fetcher
from tkcrawler.steps._runtime import StepError

_RSS_FETCHER = RssFetcher()
_PODCAST_FETCHER = PodcastFetcher()
_HTML_FETCHER = HtmlListingFetcher()

_FETCHERS: dict[str, BaseFetcher] = {
    SourceType.RSS: _RSS_FETCHER,
    SourceType.PODCAST: _PODCAST_FETCHER,
    SourceType.HTML: _HTML_FETCHER,
}


def get_fetcher(source_type: str) -> Fetcher:
    """Return the fetcher adapter for a normalized source type string."""
    key = str(source_type or "").strip()
    fetcher = _FETCHERS.get(key)
    if fetcher is None:
        raise StepError(
            "unsupported_source_type",
            f"No fetcher for source type: {source_type!r}",
            {"source_type": source_type},
        )
    return fetcher


__all__ = [
    "BaseFetcher",
    "Fetcher",
    "HtmlListingFetcher",
    "PodcastFetcher",
    "RssFetcher",
    "get_fetcher",
]
