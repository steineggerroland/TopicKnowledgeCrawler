"""Candidate builders for RSS, podcast and HTML sources."""

from tkcrawler.candidates.html import build_html_candidates
from tkcrawler.candidates.podcast import build_podcast_candidates
from tkcrawler.candidates.rss import build_rss_candidates

__all__ = [
    "build_html_candidates",
    "build_podcast_candidates",
    "build_rss_candidates",
]
