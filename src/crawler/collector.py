import json
import os

from src.crawler.fetchers.html_fetcher import fetch_html_content
from src.crawler.fetchers.rss_fetcher import fetch_rss_feed
from src.crawler.utils.logger import logger
from src.crawler.utils.sanitize import sanitize_string

CONFIG_FILE = "config/sources.json"
DATA_DIR = "data/raw"


def load_sources():
    """Loads the sources configuration."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)["sources"]


def process_source(source):
    """
    Processes a single source based on its type.
    """
    source_type = source["type"]
    name = source["name"]
    url = source["url"]

    logger.info("Processing source: %s (%s)", name, source_type)

    try:
        if source_type == "rss" or source_type == "rss+podcast":
            entries = fetch_rss_feed(url)
        elif source_type == "html":
            entries = fetch_html_content(url)
        else:
            logger.warning("No fetcher available for source type: %s", source_type)

        for entry in entries:
            entry["source_type"] = source_type
            save_entry(name, entry)
        logger.info("Saved %s entries", len(entries))

    except Exception as e:
        logger.error("Error processing source '%s': %s", name, str(e))


def save_entry(source_name, entry):
    """Saves an entry as a JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_name = sanitize_string(f"{source_name}_{entry['id']}.json")
    file_path = os.path.join(DATA_DIR, file_name)
    with open(file_path, "w") as file:
        json.dump(entry, file, indent=4)
    logger.debug("Saved entry: %s", file_path)


if __name__ == "__main__":
    sources = load_sources()
    for source in sources:
        process_source(source)
