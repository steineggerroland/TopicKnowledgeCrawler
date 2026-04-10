import unittest
from unittest.mock import patch, Mock
from crawler.fetchers.podcast_fetcher import PodcastFetcher


class TestPodcastFetcher(unittest.TestCase):

    def setUp(self):
        self.source_podcast = {
            "url": "https://example.com/podcast",
            "type": "rss+podcast",
            "name": "Test Podcast"
        }

    @patch("feedparser.parse")
    @patch("crawler.fetchers.podcast_fetcher.PodcastFetcher.extract_markdown_content", return_value="Markdown Content")
    def test_happy_path_all_entries_fetched(self, mock_markdown, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = [
            {"title": "Episode 1", "link": "https://example.com/1", "description": "HTML Content 1"},
            {"title": "Episode 2", "link": "https://example.com/2", "itunes:summary": "HTML Content 2"}
        ]
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["title"], "Episode 1")
        self.assertEqual(entries[1]["link"], "https://example.com/2")
        self.assertIn("Markdown Content", entries[0]["content_md"])

    @patch("feedparser.parse", side_effect=Exception("Failed to parse feed"))
    def test_feed_parsing_fails(self, mock_feedparser):
        # Given
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    def test_empty_feed(self, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = []
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)

    @patch("feedparser.parse")
    @patch("crawler.fetchers.podcast_fetcher.PodcastFetcher.extract_markdown_content", return_value="Markdown Content")
    def test_entry_without_content(self, mock_markdown, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = [
            {"title": "Episode 1", "link": "https://example.com/1", "description": ""}
        ]
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 0)  # Skipped due to missing content

    @patch("feedparser.parse")
    @patch("crawler.fetchers.podcast_fetcher.PodcastFetcher.extract_markdown_content",
           side_effect=[Exception("Markdown conversion failed"), "Markdown Content"])
    def test_markdown_conversion_fails(self, mock_markdown, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = [
            {"title": "Episode 1", "link": "https://example.com/1", "description": "HTML Content 1"},
            {"title": "Episode 2", "link": "https://example.com/2", "description": "HTML Content 2"}
        ]
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 1)  # Only one succeeds
        self.assertEqual(entries[0]["title"], "Episode 2")
        self.assertIn("Markdown Content", entries[0]["content_md"])

    @patch("feedparser.parse")
    def test_duplicate_entries(self, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = [
            {"title": "Episode 1", "link": "https://example.com/1?tracking=abc", "description": "HTML Content 1"},
            {"title": "Episode 1", "link": "https://example.com/1", "description": "HTML Content 1"}
        ]
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(1, len(entries))
        self.assertEqual(entries[0]["link"], "https://example.com/1")

    @patch("feedparser.parse")
    @patch("crawler.fetchers.podcast_fetcher.PodcastFetcher.extract_markdown_content", return_value="Markdown Content")
    def test_validate_required_fields(self, mock_markdown, mock_feedparser):
        # Given
        mock_feedparser.return_value.entries = [
            {"title": "Episode 1", "link": "https://example.com/1", "description": "HTML Content 1"}
        ]
        fetcher = PodcastFetcher(self.source_podcast)

        # When
        entries = fetcher.fetch()

        # Then
        self.assertEqual(len(entries), 1)
        self.assertIn("content_md", entries[0])
        self.assertIn("publishedAt", entries[0])
        self.assertIn("categories", entries[0])


if __name__ == "__main__":
    unittest.main()