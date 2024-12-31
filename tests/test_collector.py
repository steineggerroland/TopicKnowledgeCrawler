import json
import logging
import os
from unittest.mock import patch, Mock, ANY

import pytest

from src.crawler.collector import load_sources, process_source

TEST_CONFIG_FILE = "tests/fixtures/mock_sources.json"
TEST_OUTPUT_DIR = "tests/output/raw"


@pytest.fixture
def setup_test_environment():
    """Sets up and cleans up the test environment."""
    if os.path.exists(TEST_OUTPUT_DIR):
        for file in os.listdir(TEST_OUTPUT_DIR):
            os.remove(os.path.join(TEST_OUTPUT_DIR, file))
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

    sources = [{"name": "Test RSS Source", "type": "rss", "url": "https://example.com/mock-rss"},
               {"name": "Test HTML Source", "type": "html", "url": "https://example.com/mock-html"}]
    with open(TEST_CONFIG_FILE, "w") as f:
        json.dump({"sources": sources}, f)

    yield  # Tests run here

    for file in os.listdir(TEST_OUTPUT_DIR):
        os.remove(os.path.join(TEST_OUTPUT_DIR, file))


@patch("src.crawler.collector.fetch_rss_feed")
@patch("src.crawler.collector.HtmlFetcher")
def test_process_source(html_fetcher_patch, fetch_rss_feed, setup_test_environment):
    """Test that sources are processed and saved correctly."""
    fetch_rss_feed.return_value = [
        {"id": "rss_1", "title": "RSS Article 1", "link": "https://example.com/rss-1", "summary": "Summary of RSS 1"}]
    html_fetcher_patch.return_value = Mock(fetch=Mock(
        return_value=[{"id": "html_1", "title": "HTML Article 1", "link": "https://example.com/html-1",
                       "summary": "Summary of HTML 1"}]))
    with patch("src.crawler.collector.CONFIG_FILE", TEST_CONFIG_FILE), patch("src.crawler.collector.DATA_DIR",
                                                                             TEST_OUTPUT_DIR):
        sources = load_sources()
        for source in sources:
            process_source(source)

    saved_files = os.listdir(TEST_OUTPUT_DIR)
    assert 'rss_1.json' in saved_files
    assert 'html_1.json' in saved_files

    rss_file = os.path.join(TEST_OUTPUT_DIR, "rss_1.json")
    with open(rss_file, "r") as f:
        rss_content = json.load(f)
        assert rss_content["title"] == "RSS Article 1"
        assert rss_content["link"] == "https://example.com/rss-1"
        assert rss_content["summary"] == "Summary of RSS 1"

    html_file = os.path.join(TEST_OUTPUT_DIR, "html_1.json")
    with open(html_file, "r") as f:
        html_content = json.load(f)
        assert html_content["title"] == "HTML Article 1"
        assert html_content["link"] == "https://example.com/html-1"
        assert html_content["summary"] == "Summary of HTML 1"

    fetch_rss_feed.assert_called_once_with("https://example.com/mock-rss")
    html_fetcher_patch.assert_called_once_with({'name': ANY, 'type': ANY, 'url':"https://example.com/mock-html"})


@patch("src.crawler.collector.fetch_rss_feed")
@patch("src.crawler.collector.HtmlFetcher")
def test_process_source_with_exceptions(mock_html_fetcher, mock_rss_fetch, caplog):
    """Test that process_source handles exceptions gracefully."""
    # Configure caplog to listen to the specific logger
    caplog.set_level(logging.ERROR, logger="src.crawler.utils.logger")
    caplog.set_level(logging.INFO, logger="src.crawler.utils.logger")

    # Simulate exception by RSS fetcher
    mock_rss_fetch.side_effect = Exception("RSS fetcher failed!")
    # Simulate successful processing by HTML fetcher
    mock_html_fetcher.return_value = Mock(return_value=[{"id": "html_1", "title": "HTML Article 1", "link": "https://example.com/html-1"}])

    # Define sources
    rss_source = {"name": "Test RSS Source", "type": "rss", "url": "https://example.com/mock-rss"}
    html_source = {"name": "Test HTML Source", "type": "html", "url": "https://example.com/mock-html"}

    # Test source with exception
    process_source(rss_source)
    assert "Error processing source 'Test RSS Source': RSS fetcher failed!" in caplog.text

    # Test successful source
    process_source(html_source)
    assert "Processing source: Test HTML Source (html)" in caplog.text
