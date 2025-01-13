import hashlib
import logging

import feedparser
import trafilatura

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
        try:
            markdown = trafilatura.extract(
                html_content,
                include_formatting=True,
                include_images=True,
                include_links=True,
                output_format="markdown"
            )
            return markdown if markdown else "No content available."
        except Exception as e:
            logger.error("Failed to convert HTML to Markdown: %s", str(e))
            return "No content available."

    def fetch(self):
        """
        Fetches entries from the RSS feed, processes them into standardized entries with Markdown content.
        """
        feed = feedparser.parse(self.url)
        entries = []

        for item in feed.entries:
            # Extract relevant fields
            title = item.get("title")
            link = item.get("link")
            published_at = item.get("pubDate") or item.get("published", None)
            author = (
                    item.get("itunes:author") or
                    item.get("author") or
                    item.get("dc:creator")
            )
            categories = item.get("tags", [])
            description = item.get("description")
            itunes_summary = item.get("itunes:summary")

            # Determine the best content field
            html_content = "".join(
                [i["value"] for i in item.get("content", []) if i["type"] == "text/html"]) or "".join(
                [i["value"] for i in item.get("content", []) if i["type"] == "application/xhtml+xml"]) or "".join(
                [i["value"] for i in item.get("content", []) if
                 i["type"] == "text/plain"]) or description or itunes_summary
            if not html_content:
                logger.warning(f"No content found for podcast entry: {title} ({link})")

            # Convert HTML to Markdown
            markdown_content = (
                self.extract_markdown_content(f"<html><body>{html_content}</body></html>")
                if html_content else "No content available."
            )

            # Build the entry
            entry = {
                "title": title,
                "link": link,
                "author": author,
                "publishedAt": published_at,
                "categories": [tag["term"] for tag in categories] if categories else [],
                "id": self.generate_id({"link": link, "title": title, "summary": description}),
                "content_md": f"# {title}\n\n{markdown_content}"
            }
            entries.append(entry)

        return entries
