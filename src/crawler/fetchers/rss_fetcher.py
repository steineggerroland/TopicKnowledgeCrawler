import hashlib
import feedparser

from src.crawler.utils.logger import getLogger
from src.crawler.fetchers.html_fetcher import HtmlFetcher  # For the static markdown generation

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
        feed = feedparser.parse(self.url)
        entries = []

        for entry in feed.entries:
            # Standardize entry data
            entry_data = {
                "title": getattr(entry, "title", None),
                "link": getattr(entry, "link", None),
                "summary": getattr(entry, "summary", None),
                "content": self.extract_content(entry),
                "author": getattr(entry, "author", None),
                "publishedAt": getattr(entry, "published", None) or getattr(entry, "updated", None),
                "updatedAt": getattr(entry, "updated", None),
                "id": self.generate_id(entry),
            }

            # Add Markdown content if the link exists
            if entry_data["link"]:
                logger.debug(f"Generating Markdown for RSS entry: {entry_data['link']}")
                entry_data["content_md"] = HtmlFetcher.generate_markdown_from_url(entry_data["link"])

            entries.append(entry_data)

        return entries