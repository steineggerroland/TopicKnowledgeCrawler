import pytest
from unittest.mock import patch, MagicMock
from crawler.fetchers.html_fetcher import HtmlFetcher

@pytest.fixture
def source_html():
    return {
        "type": "html",
        "name": "Test HTML",
        "url": "https://example.com/articles/overview",
        "configuration": {"article_selector": "article", "main_page_anchor_selector": "a"},
    }


def mock_fetch_html(url, **kwargs):
    """
    Mock function to simulate fetching HTML content.
    """
    if "overview" in url:
        return "<html><body><article><a href='/article1'>Article 1</a></article><article><a href='/article2'>Article 2</a></article></body></html>"
    elif "article1" in url:
        return "<html><body><h1>Title 1</h1><p>Content for article 1</p></body></html>"
    elif "article2" in url:
        return "<html><body><h1>Title 2</h1><p>Content for article 2</p></body></html>"
    elif "tracking=123" in url:
        return "<html><body><article><a href='/article1?source=123'>Article 1</a></article><article><a href='/article1?source=123'>Article 1 again</a></article></body></html>"
    else:
        raise Exception("Page not found")

class TestHtmlFetcher:
    @patch("crawler.fetchers.html_fetcher.text_processor.convert_from_html_to_markdown", return_value="Markdown Content")
    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", side_effect=mock_fetch_html)
    def test_happy_case(self, mock_fetch, mock_markdown, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 2
        assert entries[0]["title"] == "Title 1"
        assert entries[1]["title"] == "Title 2"

    @patch("crawler.fetchers.html_fetcher.text_processor.convert_from_html_to_markdown", side_effect=[Exception("Failed"), "Markdown Content"])
    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", side_effect=mock_fetch_html)
    def test_first_article_fails(self, mock_fetch, mock_markdown, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 1
        assert entries[0]["title"] == "Title 2"

    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", return_value="<html><body>No articles here</body></html>")
    def test_no_articles_found(self, mock_fetch, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 0

    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", return_value="<html><body><article><a href='/article1'></a></article></body></html>")
    def test_no_header_found(self, mock_fetch, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 0

    @patch("crawler.fetchers.html_fetcher.text_processor.convert_from_html_to_markdown", side_effect=[Exception("Failed"), "Markdown Content"])
    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", side_effect=mock_fetch_html)
    def test_markdown_extraction_fails(self, mock_fetch, mock_markdown, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 1
        assert entries[0]["title"] == "Title 2"

    @patch("crawler.fetchers.html_fetcher.text_processor.convert_from_html_to_markdown", side_effect=["Markdown Content", "Markdown Content"])
    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", side_effect=mock_fetch_html)
    def test_deduplicate_articles(self, mock_fetch, mock_markdown, source_html):
        # Given
        source_html["url"] = "https://example.com/articles?tracking=123"
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 1  # Ensure only one article for duplicate URLs
        assert entries[0]["title"] == "Title 1"

    @patch("crawler.fetchers.html_fetcher.HtmlFetcher._fetch_html", side_effect=Exception("Timeout"))
    def test_overview_page_load_fails(self, mock_fetch, source_html):
        # Given
        fetcher = HtmlFetcher(source_html)

        # When
        entries = fetcher.fetch()

        # Then
        assert len(entries) == 0
