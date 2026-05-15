from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests

from tkcrawler import text

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TopicKnowledgeCrawler/0.1; "
        "+https://github.com/steineggerroland/TopicKnowledgeCrawler)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en,de;q=0.8",
}


class HtmlFetcher:
    """Small HTML utility used by the step-based crawler pipeline."""

    @staticmethod
    def generate_markdown_from_url(url: str, *, verify=True, headers=None) -> str:
        html_content = HtmlFetcher._fetch_html(url, verify=verify, headers=headers)
        markdown = text.convert_from_html_to_markdown(html_content)
        if markdown:
            return markdown
        logger.warning("Failed to extract content as Markdown for URL: %s", url)
        raise ValueError("Failed to extract content as Markdown")

    @staticmethod
    def _fetch_html(url: str, *, verify=True, headers=None) -> str:
        request_headers = {**DEFAULT_HEADERS, **(headers or {})}
        response = requests.get(url, timeout=10, verify=verify, headers=request_headers)
        response.raise_for_status()
        return response.text

    @staticmethod
    def sanitize_link(url: str | None) -> str | None:
        if not url:
            return None
        try:
            parsed_url = urlparse(url)
            query = parse_qs(parsed_url.query)
            filtered_query = {
                key: value
                for key, value in query.items()
                if key
                not in {
                    "q",
                    "query",
                    "source",
                    "referrer",
                    "tracking",
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                }
            }
            return urlunparse(parsed_url._replace(query=urlencode(filtered_query, doseq=True)))
        except Exception:
            logger.warning("Failed to sanitize URL %s", url)
            return url
