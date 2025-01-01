import hashlib
import json
import logging

import feedparser
import requests
import trafilatura

from src.crawler.fetchers.html_fetcher import extract_article_content

# Initialize logger
logger = logging.getLogger(__name__)


def generate_id(entry):
    """
    Generates a unique hash ID for the entry using its link, title, or summary.
    """
    link = str(getattr(entry, "link", "") or "")
    title = str(getattr(entry, "title", "") or "")
    summary = str(getattr(entry, "summary", "") or getattr(entry, "content", "") or getattr(entry, "description", "") or "")
    content = link or title or summary or ""
    return hashlib.sha256(content.encode()).hexdigest()


def extract_content(entry):
    """
    Extracts the summary of an entry, handling both content as string and content arrays.
    """
    if hasattr(entry, "content") and entry.content:
        # Handle content as array or string
        if isinstance(entry.content, list) and "value" in entry.content[0]:
            return entry.content[0]["value"]
        elif isinstance(entry.content, str):
            return entry.content
    return None


def fetch_rss_feed(url):
    """
    Fetches entries from an RSS feed and processes them into a standardized format.
    """
    feed = feedparser.parse(url)
    entries = []

    for entry in feed.entries:
        # Extract summary or description
        content = extract_content(entry)
        link = getattr(entry, "link", None)

        if not content and link:
            entry_data = extract_article_content(link)
            if entry_data:
                entries.append(entry_data)
                continue
        elif not content:
            content = getattr(entry, "summary", None) or getattr(entry, "description", None)

        # Default case if full article fetch is not needed
        entry_data = {
            "title": getattr(entry, "title", None),
            "link": link,
            "summary": content,
            "author": extract_author(entry),
            "publishedAt": getattr(entry, "published", None) or getattr(entry, "updated", None) or getattr(entry, "pubDate", None),
            "updatedAt": getattr(entry, "updated", None),
            "id": generate_id(entry)
        }
        entries.append(entry_data)

    return entries


def extract_author(entry):
    if hasattr(entry, "author"):
        auth_tag = getattr(entry, "author", None)
        return auth_tag if type(auth_tag) is str else getattr(auth_tag, "name", None) if hasattr(auth_tag, "name") else str(auth_tag)
    return  getattr(entry, "creator", None) or getattr(entry, "itunes:author", None)

