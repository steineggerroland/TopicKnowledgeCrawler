"""Integration-style tests for candidate builders using synthetic fixtures.

These tests exercise real feedparser/BeautifulSoup parsing against synthetic
XML and HTML fixtures (no network, no copyrighted content).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import feedparser
import pytest

from tkcrawler.candidates.html import build_html_candidates
from tkcrawler.candidates.podcast import build_podcast_candidates
from tkcrawler.candidates.rss import build_rss_candidates
from tkcrawler.enums import ItemKind

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def rss_feed():
    xml = (FIXTURES / "synthetic_rss.xml").read_text()
    return feedparser.parse(xml)


@pytest.fixture
def podcast_feed():
    xml = (FIXTURES / "synthetic_podcast.xml").read_text()
    return feedparser.parse(xml)


@pytest.fixture
def listing_html():
    return (FIXTURES / "synthetic_listing.html").read_text()


def _rss_source():
    return {
        "crawl_key": "https://synthetic.example.com/feed",
        "type": "rss",
        "url": "https://synthetic.example.com/feed",
    }


def _podcast_source():
    return {
        "crawl_key": "https://synthetic.example.com/podcast",
        "type": "rss+podcast",
        "url": "https://synthetic.example.com/podcast",
    }


def _html_source():
    return {
        "crawl_key": "https://synthetic.example.com/articles",
        "type": "html",
        "url": "https://synthetic.example.com/articles",
        "configuration": {
            "article_selector": "article",
            "main_page_anchor_selector": "h2 > a",
        },
    }


class TestRssCandidatesFromFixture:
    def test_parses_all_entries(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        assert len(rows) == 3

    def test_extracts_titles(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        titles = [r["candidate"]["title"] for r in rows]
        assert "First Synthetic Article" in titles
        assert "Second Synthetic Article" in titles
        assert "Third Synthetic Article" in titles

    def test_extracts_links(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        links = [r["candidate"]["link"] for r in rows]
        assert "https://synthetic.example.com/articles/first" in links
        assert "https://synthetic.example.com/articles/second" in links

    def test_extracts_author(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        authors = {r["candidate"]["title"]: r["candidate"]["author"] for r in rows}
        assert authors["First Synthetic Article"] == "Ada Testwriter"
        assert authors["Second Synthetic Article"] == "Bob Testwriter"

    def test_all_items_are_articles(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        for row in rows:
            assert row["candidate"]["item_kind"] == ItemKind.ARTICLE

    def test_each_candidate_has_stable_id(self, rss_feed):
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(_rss_source())
        ids = [r["candidate"]["id"] for r in rows]
        assert len(ids) == len(set(ids))
        assert all(len(cid) == 64 for cid in ids)

    def test_respects_max_candidates(self, rss_feed):
        src = {**_rss_source(), "effective_policy": {"max_candidates_per_run": 2}}
        with patch("tkcrawler.candidates.rss.feedparser.parse", return_value=rss_feed):
            rows = build_rss_candidates(src)
        assert len(rows) == 2


class TestPodcastCandidatesFromFixture:
    def test_parses_all_episodes(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        assert len(rows) == 2

    def test_all_items_are_episodes(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        for row in rows:
            assert row["candidate"]["item_kind"] == ItemKind.EPISODE

    def test_extracts_media_url(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        media_urls = [r["candidate"].get("media_url") for r in rows]
        assert "https://synthetic.example.com/audio/ep1.mp3" in media_urls
        assert "https://synthetic.example.com/audio/ep2.mp3" in media_urls

    def test_extracts_duration(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        by_title = {r["candidate"]["title"]: r["candidate"] for r in rows}
        assert by_title["Episode 1: Getting Started"]["duration_seconds"] == 25 * 60 + 30
        assert by_title["Episode 2: Deep Dive"]["duration_seconds"] == 1 * 3600 + 2 * 60 + 15

    def test_extracts_episode_metadata(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        ep1 = next(r["candidate"] for r in rows if r["candidate"]["title"] == "Episode 1: Getting Started")
        assert ep1["episode_number"] == 1
        assert ep1["season_number"] == 1
        assert ep1["media_type"] == "audio/mpeg"

    def test_extracts_author(self, podcast_feed):
        with patch("tkcrawler.candidates.podcast.feedparser.parse", return_value=podcast_feed):
            rows = build_podcast_candidates(_podcast_source())
        by_title = {r["candidate"]["title"]: r["candidate"] for r in rows}
        assert by_title["Episode 1: Getting Started"]["author"] == "Ada Host"
        assert by_title["Episode 2: Deep Dive"]["author"] == "Bob Host"


class TestHtmlCandidatesFromFixture:
    def test_parses_unique_articles(self, listing_html):
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(_html_source())
        assert len(rows) == 3

    def test_deduplicates_links(self, listing_html):
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(_html_source())
        links = [r["candidate"]["link"] for r in rows]
        assert len(links) == len(set(links))

    def test_extracts_titles_from_headings(self, listing_html):
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(_html_source())
        titles = [r["candidate"]["title"] for r in rows]
        assert "Alpha Article" in titles
        assert "Beta Article" in titles
        assert "Gamma Article" in titles

    def test_resolves_relative_links(self, listing_html):
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(_html_source())
        for row in rows:
            assert row["candidate"]["link"].startswith("https://synthetic.example.com/")

    def test_all_items_are_articles(self, listing_html):
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(_html_source())
        for row in rows:
            assert row["candidate"]["item_kind"] == ItemKind.ARTICLE

    def test_respects_max_candidates(self, listing_html):
        src = {**_html_source(), "effective_policy": {"max_candidates_per_run": 1}}
        with patch("tkcrawler.candidates.html.HtmlFetcher._fetch_html", return_value=listing_html):
            rows = build_html_candidates(src)
        assert len(rows) == 1
