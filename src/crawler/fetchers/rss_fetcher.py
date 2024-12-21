import hashlib

import feedparser


def generate_id(entry):
    """
    Generates a unique hash ID for the entry using its link, title, or summary.
    """
    link = str(getattr(entry, "link", "") or "")
    title = str(getattr(entry, "title", "") or "")
    summary = str(getattr(entry, "summary", "") or "")
    content = link or title or summary or ""
    return hashlib.sha256(content.encode()).hexdigest()


def extract_summary(entry):
    """
    Extracts the summary of an entry, handling both content as string and content arrays.
    """
    if hasattr(entry, "summary") and entry.summary:
        return entry.summary
    elif hasattr(entry, "content") and entry.content:
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
        entry_data = {
            "title": getattr(entry, "title", None),
            "link": getattr(entry, "link", None),
            "summary": extract_summary(entry),
            "publishedAt": getattr(entry, "published", None) or getattr(entry, "updated", None),
            "updatedAt": getattr(entry, "updated", None),
            "id": generate_id(entry)
        }
        entries.append(entry_data)
    return entries
