import hashlib

import feedparser

from crawler.fetchers.html_fetcher import HtmlFetcher  # For the static markdown generation
from crawler.utils.logger import getLogger

# Initialize logger
logger = getLogger(__name__)


class RssFetcher:
    def __init__(self, source):
        self.source = source
        self.url = source["url"]

    def generate_id(self, entry):
        """
        Generates a unique hash ID for the entry using its link, title, or summary.
        """
        link = str(getattr(entry, "link", "") or "")
        title = str(getattr(entry, "title", "") or "")
        summary = str(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
        content = link or title or summary
        return hashlib.sha256(content.encode()).hexdigest()

    def extract_content(self, entry):
        """
        Extracts the 'content' of an entry, if available.
        """
        if hasattr(entry, "content") and entry.content:
            if isinstance(entry.content, list) and "value" in entry.content[0]:
                return entry.content[0]["value"]
            elif isinstance(entry.content, str):
                return entry.content
        return None

    def fetch(self):
        """
        Fetches entries from the RSS feed and processes them into a standardized format.
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

        for entry in feed_entries:
            # Standardize entry data
            entry_data = {
                "title": getattr(entry, "title", None),
                "link": HtmlFetcher.sanitize_link(getattr(entry, "link", None)),
                "summary": getattr(entry, "summary", ""),
                "author": getattr(entry, "author", None),
                "publishedAt": getattr(entry, "published", None) or getattr(entry, "updated", None),
                "updatedAt": getattr(entry, "updated", None),
                "id": self.generate_id(entry),
            }

            # Add Markdown content if the link exists
            try:
                if not entry_data["link"]:
                    logger.warning(f"Skipping entry '{entry_data}' without link.")
                    continue
                elif entry_data["link"] in (a["link"] for a in entries):
                    logger.warning(f"Skipping duplicate entry '{entry_data}'.")
                    continue

                logger.debug(f"Generating Markdown for RSS entry: {entry_data['link']}")
                entry_data["content_md"] = HtmlFetcher.generate_markdown_from_url(entry_data["link"])
                entries.append(entry_data)
            except Exception as e:
                logger.warning(f"Markdown generation failed for article {entry_data}: {e}")

        return entries
