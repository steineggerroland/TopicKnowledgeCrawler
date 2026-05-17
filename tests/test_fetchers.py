"""Tests for source-family fetcher adapters."""

from unittest.mock import patch

from tkcrawler.enums import SourceType
from tkcrawler.fetchers import PodcastFetcher, RssFetcher, get_fetcher
from tkcrawler.models import Candidate, Source


def test_get_fetcher_returns_rss_and_podcast_adapters():
    assert isinstance(get_fetcher(SourceType.RSS), RssFetcher)
    assert isinstance(get_fetcher(SourceType.PODCAST), PodcastFetcher)


@patch("tkcrawler.candidates.rss.feedparser.parse")
def test_rss_fetcher_list_candidates_returns_typed_candidates(mock_parse):
    mock_parse.return_value.entries = [
        {
            "title": "Article",
            "link": "https://example.com/article",
            "summary": "Summary",
            "published": "2026-05-10T08:00:00+00:00",
        }
    ]
    source = Source.from_mapping(
        {
            "crawl_key": "https://example.com/feed.xml",
            "type": "rss",
            "url": "https://example.com/feed.xml",
        }
    )
    candidates = RssFetcher().list_candidates(source)
    assert len(candidates) == 1
    assert candidates[0].link == "https://example.com/article"
    assert str(candidates[0].item_kind) == "article"


@patch("tkcrawler.fetchers._detail.HtmlFetcher.generate_markdown_from_url", return_value="# Body")
def test_rss_fetcher_fetch_detail_returns_article(mock_markdown):
    source = Source.from_mapping(
        {
            "crawl_key": "https://example.com/feed.xml",
            "type": "rss",
            "url": "https://example.com/feed.xml",
        }
    )
    candidate = Candidate.from_mapping(
        {
            "id": "abc",
            "link": "https://example.com/article",
            "title": "Article",
            "summary": "Summary",
            "item_kind": "article",
        }
    )
    article = RssFetcher().fetch_detail(source, candidate)
    assert article.content_md == "# Body"
    assert article.id == "abc"
    mock_markdown.assert_called_once()
