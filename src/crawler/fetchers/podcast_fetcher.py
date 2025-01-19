import hashlib
import logging

import feedparser

from src.crawler.fetchers.html_fetcher import HtmlFetcher
from src.crawler.utils import text_processor

# Initialize logger
logger = logging.getLogger(__name__)


class PodcastFetcher:
    def __init__(self, source):
        self.source = source
        self.url = source["url"]

    def generate_id(self, entry):
        """
        Generates a unique hash ID for the entry using its link, title, or summary.
        """
        content = (
                str(entry.get("link", "")) +
                str(entry.get("title", "")) +
                str(entry.get("summary", ""))
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def extract_markdown_content(self, html_content):
        """
        Converts HTML content to Markdown using trafilatura.
        """
        markdown = text_processor.convert_from_html_to_markdown(html_content)
        return markdown if markdown else ""

    def get_best_content(self, item):
        """
        Extract the most suitable content from an RSS entry.
        Priority:
        1. HTML content (text/html)
        2. XHTML content (application/xhtml+xml)
        3. Plain text content (text/plain)
        4. Description or iTunes summary
        """
        content_fields = item.get("content", [])
        if isinstance(content_fields, list):
            for content_type in ["text/html", "application/xhtml+xml", "text/plain"]:
                for field in content_fields:
                    if field.get("type") == content_type:
                        return field.get("value")

        # Fallback to description or iTunes summary
        return item.get("description") or item.get("itunes:summary")

    def fetch(self):
        """
        Fetches entries from the RSS feed, processes them into standardized entries with Markdown content.
        """
        try:
            feed = feedparser.parse(self.url)
        except Exception:
            logger.error("Failed to parse feed '%s'", self.url)
            return []

        feed_entries = getattr(feed, "entries", None) or []
        if len(feed_entries) == 0:
            logger.warning("No entries found in the feed '%s'.", self.url)
            return []

        entries = []

        for item in feed_entries:
            # Extract relevant fields
            title = item.get("title")
            published_at = item.get("pubDate") or item.get("published", None)
            author = (
                    item.get("itunes:author") or
                    item.get("author") or
                    item.get("dc:creator")
            )
            categories = item.get("tags", [])
            link = HtmlFetcher.sanitize_link(item.get("link"))

            if link in (a["link"] for a in entries):
                logger.warning(f"Skipping duplicate entry '{item}'.")
                continue

            # Extract the best content
            html_content = self.get_best_content(item)
            if not html_content:
                logger.warning(f"No content found for podcast entry: {title} ({link})")
                continue

            # Convert HTML to Markdown
            try:
                markdown_content = self.extract_markdown_content(f"<html><body>{html_content}</body></html>")
            except Exception as e:
                logger.error("Failed to convert entry '%s' to Markdown: %s", item, str(e))
                continue

            # Build the entry
            entry = {
                "title": title,
                "link": link,
                "author": author,
                "publishedAt": published_at,
                "categories": [tag["term"] for tag in categories] if categories else [],
                "id": self.generate_id({"link": link, "title": title, "summary": html_content}),
                "content_md": f"# {title}\n\n{markdown_content}"
            }
            entries.append(entry)

        return entries
