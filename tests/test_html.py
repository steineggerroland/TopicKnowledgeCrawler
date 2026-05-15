"""Tests for tkcrawler.html – HtmlFetcher utilities."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from tkcrawler.html import HtmlFetcher


class TestSanitizeLink:
    def test_removes_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social&id=42"
        result = HtmlFetcher.sanitize_link(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "id=42" in result

    def test_removes_tracking_params(self):
        url = "https://example.com/p?tracking=abc&source=rss&referrer=feed"
        result = HtmlFetcher.sanitize_link(url)
        assert "tracking" not in result
        assert "source" not in result
        assert "referrer" not in result

    def test_preserves_clean_url(self):
        url = "https://example.com/article/hello-world"
        assert HtmlFetcher.sanitize_link(url) == url

    def test_preserves_non_tracking_params(self):
        url = "https://example.com/search?page=2&lang=en"
        result = HtmlFetcher.sanitize_link(url)
        assert "page=2" in result
        assert "lang=en" in result

    def test_returns_none_for_none(self):
        assert HtmlFetcher.sanitize_link(None) is None

    def test_returns_none_for_empty_string(self):
        assert HtmlFetcher.sanitize_link("") is None

    def test_handles_url_without_query(self):
        url = "https://example.com/path"
        assert HtmlFetcher.sanitize_link(url) == url

    def test_handles_url_with_fragment(self):
        url = "https://example.com/path#section"
        result = HtmlFetcher.sanitize_link(url)
        assert result == url

    def test_handles_malformed_url_gracefully(self):
        result = HtmlFetcher.sanitize_link("not-a-url")
        assert result is not None

    def test_removes_utm_campaign(self):
        url = "https://x.com/a?utm_campaign=launch&keep=1"
        result = HtmlFetcher.sanitize_link(url)
        assert "utm_campaign" not in result
        assert "keep=1" in result


class TestGenerateMarkdownFromUrl:
    @patch("tkcrawler.html.HtmlFetcher._fetch_html")
    @patch("tkcrawler.html.text.convert_from_html_to_markdown")
    def test_happy_path(self, mock_convert, mock_fetch):
        mock_fetch.return_value = "<html><body><p>Content</p></body></html>"
        mock_convert.return_value = "# Title\n\nContent"

        result = HtmlFetcher.generate_markdown_from_url("https://example.com/article")

        assert result == "# Title\n\nContent"
        mock_fetch.assert_called_once_with("https://example.com/article", verify=True, headers=None)

    @patch("tkcrawler.html.HtmlFetcher._fetch_html")
    @patch("tkcrawler.html.text.convert_from_html_to_markdown")
    def test_raises_when_markdown_is_empty(self, mock_convert, mock_fetch):
        mock_fetch.return_value = "<html></html>"
        mock_convert.return_value = None

        with pytest.raises(ValueError, match="Failed to extract"):
            HtmlFetcher.generate_markdown_from_url("https://example.com/empty")

    @patch("tkcrawler.html.HtmlFetcher._fetch_html")
    @patch("tkcrawler.html.text.convert_from_html_to_markdown")
    def test_passes_verify_and_headers(self, mock_convert, mock_fetch):
        mock_fetch.return_value = "<html><body>text</body></html>"
        mock_convert.return_value = "text"

        HtmlFetcher.generate_markdown_from_url(
            "https://example.com/a",
            verify=False,
            headers={"Authorization": "Bearer x"},
        )

        mock_fetch.assert_called_once_with(
            "https://example.com/a",
            verify=False,
            headers={"Authorization": "Bearer x"},
        )


class TestFetchHtml:
    @patch("tkcrawler.html.requests.get")
    def test_returns_response_text(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html>OK</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = HtmlFetcher._fetch_html("https://example.com")

        assert result == "<html>OK</html>"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["timeout"] == 10
        assert "User-Agent" in call_kwargs.kwargs["headers"]

    @patch("tkcrawler.html.requests.get")
    def test_merges_custom_headers(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        HtmlFetcher._fetch_html("https://example.com", headers={"X-Custom": "val"})

        headers = mock_get.call_args.kwargs["headers"]
        assert headers["X-Custom"] == "val"
        assert "User-Agent" in headers

    @patch("tkcrawler.html.requests.get")
    def test_passes_verify_flag(self, mock_get):
        mock_response = Mock()
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        HtmlFetcher._fetch_html("https://example.com", verify=False)

        assert mock_get.call_args.kwargs["verify"] is False
