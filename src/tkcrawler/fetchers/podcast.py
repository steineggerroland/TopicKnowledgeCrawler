"""Podcast RSS source fetcher."""

from __future__ import annotations

from tkcrawler.candidates.podcast import build_podcast_candidates
from tkcrawler.fetchers.base import BaseFetcher


class PodcastFetcher(BaseFetcher):
    build_candidates = staticmethod(build_podcast_candidates)
