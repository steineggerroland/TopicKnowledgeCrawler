from unittest.mock import Mock

import pytest

from src.crawler.fetchers.rss_fetcher import fetch_rss_feed


@pytest.fixture
def mock_feed_with_entries():
    """Returns a mocked FeedParserDict with valid entries."""
    mock_feed = Mock()
    mock_feed.entries = [
        Mock(
            title="Test Article 1",
            link="https://example.com/test-1",
            content="This is a summary.",
            published="2024-06-06T10:00:00Z",
        )
    ]
    return mock_feed


@pytest.fixture
def mock_feed_with_missing_fields():
    """Returns a mocked FeedParserDict with missing fields."""
    mock_feed = Mock()
    mock_entry = Mock(spec=dict, spec_set=None)
    mock_entry.content = "Fallback content for missing summary"  # Single String
    mock_feed.entries = [mock_entry]
    return mock_feed


@pytest.fixture
def mock_feed_with_content_array():
    """Returns a mocked FeedParserDict where content is an array."""
    mock_feed = Mock()
    mock_entry = Mock(spec=dict, spec_set=None)
    mock_entry.title = "Test with Content Array"
    mock_entry.link = "https://example.com/test-content-array"
    mock_entry.content = [{"value": "This is a content array example."}]
    mock_entry.published = "2024-06-06T10:00:00Z"
    mock_feed.entries = [mock_entry]
    return mock_feed


@pytest.fixture
def mock_feed_empty():
    """Returns a mocked empty FeedParserDict."""
    mock_feed = Mock()
    mock_feed.entries = []
    return mock_feed


def test_fetch_rss_valid_feed(mock_feed_with_entries, mocker):
    """Test RSS fetcher with valid entries."""
    mocker.patch("feedparser.parse", return_value=mock_feed_with_entries)

    url = "https://example.com/feed"
    result = fetch_rss_feed(url)

    assert len(result) == 1
    assert result[0]["title"] == "Test Article 1"
    assert result[0]["link"] == "https://example.com/test-1"
    assert result[0]["summary"] == "This is a summary."
    assert result[0]["publishedAt"] == "2024-06-06T10:00:00Z"
    assert result[0]["id"] is not None


def test_fetch_rss_missing_fields(mock_feed_with_missing_fields, mocker):
    """Test RSS fetcher with missing fields."""
    mocker.patch("feedparser.parse", return_value=mock_feed_with_missing_fields)

    url = "https://example.com/feed"
    result = fetch_rss_feed(url)

    assert len(result) == 1
    assert result[0]["title"] is None
    assert result[0]["link"] is None
    assert result[0]["summary"] == "Fallback content for missing summary"
    assert result[0]["publishedAt"] is None
    assert result[0]["id"] is not None


def test_fetch_rss_content_array(mock_feed_with_content_array, mocker):
    """Test RSS fetcher where content is provided as an array."""
    mocker.patch("feedparser.parse", return_value=mock_feed_with_content_array)

    url = "https://example.com/feed"
    result = fetch_rss_feed(url)

    assert len(result) == 1
    assert result[0]["title"] == "Test with Content Array"
    assert result[0]["link"] == "https://example.com/test-content-array"
    assert result[0]["summary"] == "This is a content array example."
    assert result[0]["publishedAt"] == "2024-06-06T10:00:00Z"
    assert result[0]["id"] is not None


def test_fetch_rss_empty_feed(mock_feed_empty, mocker):
    """Test RSS fetcher with an empty feed."""
    mocker.patch("feedparser.parse", return_value=mock_feed_empty)

    url = "https://example.com/feed"
    result = fetch_rss_feed(url)

    assert len(result) == 0
