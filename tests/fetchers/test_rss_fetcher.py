import unittest
from unittest.mock import patch, Mock

from src.crawler.fetchers.rss_fetcher import RssFetcher


class TestRssFetcher(unittest.TestCase):

    def setUp(self):
        self.source_rss = {
            "url": "https://example.com/rss",
            "type": "rss",
            "name": "Test RSS"
        }

    @patch("feedparser.parse")
    def test_happy_path_all_entries_fetched(self, mock_parse):
        # Given
        mock_parse.return_value.entries = [
            Mock(title= "Article 1", link= "https://example.com/1", summary= "Summary 1", author= "Author 1"),
            Mock(title= "Article 2", link= "https://example.com/2", summary= "Summary 2", author= "Author 2")
        ]
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "Article 1")
        self.assertEqual(entries[1]["link"], "https://example.com/2")

    @patch("feedparser.parse", side_effect=Exception("Failed to fetch feed"))
    def test_feed_fetching_fails(self, mock_parse):
        # Given
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    def test_malformed_rss_feed(self, mock_parse):
        # Given
        mock_parse.return_value.entries = None  # Malformed feed
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    def test_missing_link_field(self, mock_parse):
        # Given
        mock_parse.return_value.entries = [
            Mock(title= "Article 1", link=None, summary= "Summary 1", author= "Author 1")
        ]
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    @patch("src.crawler.fetchers.html_fetcher.HtmlFetcher.generate_markdown_from_url",
           side_effect=[Exception("Failed"), "Markdown Content"])
    def test_one_entry_fails_during_content_extraction(self, mock_markdown, mock_parse):
        # Given
        mock_parse.return_value.entries = [
            Mock(title= "Article 1", link= "https://example.com/1", summary= "Summary 1", author= "Author 1"),
            Mock(title= "Article 2", link= "https://example.com/2", summary= "Summary 2", author= "Author 2")
        ]
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Article 2")

    @patch("feedparser.parse")
    def test_duplicate_entries_in_rss_feed(self, mock_parse):
        # Given
        mock_parse.return_value.entries = [
            Mock(title= "Article 1", link= "https://example.com/1?tracking=abc", summary= "Summary 1"),
            Mock(title= "Article 2", link= "https://example.com/1", summary= "Summary 2")
        ]
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["link"], "https://example.com/1")

    @patch("feedparser.parse")
    def test_empty_rss_feed(self, mock_parse):
        # Given
        mock_parse.return_value.entries = []
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    def test_validate_required_fields(self, mock_parse):
        # Given
        mock_parse.return_value.entries = [
            Mock(title= "Article 1", link= "https://example.com/1")
        ]
        fetcher = RssFetcher(self.source_rss)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 1)
        self.assertIn("summary", entries[0])
        self.assertIn("publishedAt", entries[0])
        self.assertIn("author", entries[0])


if __name__ == "__main__":
    unittest.main()
