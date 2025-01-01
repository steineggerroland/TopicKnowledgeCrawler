import json
import os
import urllib.parse

import tldextract

from src.crawler.fetchers.html_fetcher import HtmlFetcher
from src.crawler.fetchers.rss_fetcher import fetch_rss_feed
from src.crawler.utils.logger import logger
from src.crawler.utils.sanitize import sanitize_string
from src.crawler.utils.source_analyzer import SourceAnalyzer

CONFIG_FILE = "config/sources.json"
DATA_DIR = "data/raw"


def load_sources():
    """Loads the sources configuration."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)["sources"]


def save_sources(sources):
    """Saves the updated sources configuration."""
    with open(CONFIG_FILE, "w") as file:
        json.dump({"sources": sources}, file, indent=2)


def process_source(source):
    """
    Processes a single source based on its type.
    """
    source_type = str(source.get("type"))
    name = str(source["name"])
    url = str(source["url"])

    logger.info("Processing source: %s (%s)", name, source_type)

    try:
        if source_type == "rss" or source_type == "rss+podcast":
            entries = fetch_rss_feed(url)
        elif source_type == "html":
            entries = HtmlFetcher(source).fetch()
        else:
            logger.warning("No fetcher available for source type: %s", source_type)
            return

        for entry in entries:
            entry["source_type"] = source_type
            entry["tld"] = tldextract.extract(url).registered_domain
            save_entry(entry)
        logger.info("Saved %s entries", len(entries))
    except Exception as e:
        logger.error("Error processing source '%s': %s", name, str(e))


def save_entry(entry):
    """Saves an entry as a JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_name = sanitize_string(f"{entry['id']}.json")
    file_path = os.path.join(DATA_DIR, file_name)
    with open(file_path, "w") as file:
        json.dump(entry, file, indent=2)
    logger.debug("Saved entry: %s", file_path)


if __name__ == "__main__":
    sources = load_sources()
    analyzer = SourceAnalyzer()

    for source in sources:
        if "type" not in source or (source["type"] == "html" and "configuration" not in source):
            logger.info("Analyzing new source: %s", source["url"])
            updated_source = analyzer.analyze_source(source)
            sources[sources.index(source)] = updated_source
            save_sources(sources)
        process_source(source)