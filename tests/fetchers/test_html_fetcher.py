from unittest.mock import patch

import pytest

from src.crawler.fetchers.html_fetcher import fetch_html_articles


@pytest.fixture
def mock_html_page():
    """Mock HTML content with multiple articles."""
    return """
    <html>
        <body>
            <div><div>
            <article>
                <h2><a href="https://example.com/article-1">Test Article 1</a></h2>
                <h3>Summary of Article 1.</h3>
            </article>
            <article>
                <a href="https://example.com/article-2"><h2>Test Article 2</h2></a>
            </article>
            <article>
                <h2>Invalid Article</h2>
            </article>
            </div></div>
        </body>
    </html>
    """


@patch("requests.get")
def test_fetch_html_articles(mock_get, mock_html_page):
    """Test the fetch_html_articles function."""
    # Mock the response from requests.get
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = mock_html_page

    # Call the function
    url = "https://example.com/mock-html"
    articles = fetch_html_articles(url)

    # Assertions
    assert len(articles) == 2  # Only two valid articles
    assert articles[0]["title"] == "Test Article 1"
    assert articles[0]["link"] == "https://example.com/article-1"
    assert articles[0]["summary"] == "Summary of Article 1."
    assert articles[1]["title"] == "Test Article 2"
    assert articles[1]["link"] == "https://example.com/article-2"
    assert articles[1]["summary"] is None


@pytest.fixture
def mock_invalid_html():
    """Mock HTML with invalid structure."""
    return """
    <html>
        <body>
            <div><div>
            <div>Not an article</div>
            <section>
                <h2>Section without link</h2>
            </section>
            </div></div>
        </body>
    </html>
    """


@patch("requests.get")
def test_fetch_html_invalid_structure(mock_get, mock_invalid_html):
    """Test the fetch_html_articles function with invalid HTML structure."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = mock_invalid_html

    url = "https://example.com/mock-html"
    articles = fetch_html_articles(url)

    assert len(articles) == 0  # No valid articles


@pytest.fixture
def mock_empty_html():
    """Mock HTML page with no articles."""
    return """
    <html>
        <body>
            <div>No articles here!</div>
        </body>
    </html>
    """


@patch("requests.get")
def test_fetch_html_no_articles(mock_get, mock_empty_html):
    """Test the fetch_html_articles function with no articles."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = mock_empty_html

    url = "https://example.com/mock-html"
    articles = fetch_html_articles(url)

    assert len(articles) == 0  # No articles should be found


@patch("requests.get")
def test_fetch_html_http_error(mock_get):
    """Test the fetch_html_articles function with an HTTP error."""
    mock_get.return_value.status_code = 404

    url = "https://example.com/mock-html"
    with pytest.raises(Exception, match="Failed to fetch HTML content. Status code: 404"):
        fetch_html_articles(url)
