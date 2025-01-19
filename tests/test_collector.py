from unittest.mock import patch

import pytest

from src.crawler.collector import process_source, SavingEntryFailed

DATA_DIR = "data/raw"


@pytest.fixture
def source_rss():
    return {"type": "rss", "name": "Test RSS", "url": "https://example.com/rss"}


@pytest.fixture
def source_podcast():
    return {"type": "rss+podcast", "name": "Test Podcast", "url": "https://example.com/podcast"}


@pytest.fixture
def source_html():
    return {
        "type": "html",
        "name": "Test HTML",
        "url": "https://example.com/articles",
        "configuration": {"article_selector": "article", "main_page_anchor_selector": "a"},
    }


@pytest.fixture
def mock_entry():
    return {"id": "test_id", "content_md": "##Content as markdown", "title": "Test Title", "link": "https://example.com/article"}


# Grouping tests by test class
class TestRssFetcher:
    def test_happy_path(self, source_rss, mock_entry):
        with patch("src.crawler.collector.RssFetcher") as MockRssFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockRssFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]

            # When
            process_source(source_rss)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)

    def test_fetcher_failure(self, source_rss):
        with patch("src.crawler.collector.RssFetcher") as MockRssFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockRssFetcher.return_value
            mock_fetcher.fetch.side_effect = Exception("Fetching failed")

            # When
            process_source(source_rss)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_not_called()

    def test_save_failure(self, source_rss, mock_entry):
        with patch("src.crawler.collector.RssFetcher") as MockRssFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockRssFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]
            mock_save_entry.side_effect = Exception("Saving failed")

            # When
            with pytest.raises(SavingEntryFailed, match="Saving.* failed"):
                process_source(source_rss)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)


class TestPodcastFetcher:
    def test_happy_path(self, source_podcast, mock_entry):
        with patch("src.crawler.collector.PodcastFetcher") as MockPodcastFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockPodcastFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]

            # When
            process_source(source_podcast)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)

    def test_fetcher_failure(self, source_podcast):
        with patch("src.crawler.collector.PodcastFetcher") as MockPodcastFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockPodcastFetcher.return_value
            mock_fetcher.fetch.side_effect = Exception("Fetching failed")

            # When
            process_source(source_podcast)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_not_called()

    def test_save_failure(self, source_podcast, mock_entry):
        with patch("src.crawler.collector.PodcastFetcher") as MockPodcastFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockPodcastFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]
            mock_save_entry.side_effect = Exception("Saving failed")

            # When
            with pytest.raises(Exception, match="Saving.* failed"):
                process_source(source_podcast)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)


class TestHtmlFetcher:
    def test_happy_path(self, source_html, mock_entry):
        with patch("src.crawler.collector.HtmlFetcher") as MockHtmlFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockHtmlFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]

            # When
            process_source(source_html)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)

    def test_fetcher_failure(self, source_html):
        with patch("src.crawler.collector.HtmlFetcher") as MockHtmlFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockHtmlFetcher.return_value
            mock_fetcher.fetch.side_effect = Exception("Fetching failed")

            # When
            process_source(source_html)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_not_called()

    def test_save_failure(self, source_html, mock_entry):
        with patch("src.crawler.collector.HtmlFetcher") as MockHtmlFetcher, patch(
                "src.crawler.collector.save_entry"
        ) as mock_save_entry:
            # Given
            mock_fetcher = MockHtmlFetcher.return_value
            mock_fetcher.fetch.return_value = [mock_entry]
            mock_save_entry.side_effect = Exception("Saving failed")

            # When
            with pytest.raises(Exception, match="Saving.* failed"):
                process_source(source_html)

            # Then
            mock_fetcher.fetch.assert_called_once()
            mock_save_entry.assert_called_once_with(mock_entry)
