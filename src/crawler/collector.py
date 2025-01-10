import json
import os
import tldextract

from src.crawler.fetchers.html_fetcher import HtmlFetcher
from src.crawler.fetchers.rss_fetcher import RssFetcher  # Updated import
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
    """Processes a single source based on its type."""
    source_type = source.get("type")
    name = source["name"]
    url = source["url"]

    logger.info("Processing source: %s (%s)", name, source_type)

    fetcher_map = {
        "rss": RssFetcher(source).fetch,
        "rss+podcast": RssFetcher(source).fetch,
        "html": HtmlFetcher(source).fetch
    }

    try:
        fetcher = fetcher_map.get(source_type)
        if fetcher:
            entries = fetcher()
            for entry in entries:
                entry.update({
                    "source_type": source_type,
                    "tld": tldextract.extract(url).registered_domain
                })
                save_entry(entry)
            logger.info("Saved %s entries", len(entries))
        else:
            logger.warning("No fetcher available for source type: %s", source_type)
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
