import json
import os

import tldextract

from src.crawler.fetchers.html_fetcher import HtmlFetcher
from src.crawler.fetchers.podcast_fetcher import PodcastFetcher
from src.crawler.fetchers.rss_fetcher import RssFetcher
from src.crawler.utils.logger import getLogger
from src.crawler.utils.sanitize import sanitize_string
from src.crawler.utils.source_analyzer import SourceAnalyzer

CONFIG_FILE = "config/sources.json"
DATA_DIR = "data/raw"

# Initialize logger
logger = getLogger(__name__)


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
        "rss+podcast": PodcastFetcher(source).fetch,
        "html": HtmlFetcher(source).fetch,
    }

    try:
        fetcher = fetcher_map.get(source_type)
        if fetcher:
            entries = fetcher()
            for entry in entries:
                entry.update({
                    "source_type": source_type,
                    "tld": tldextract.extract(url).registered_domain,
                })
                try:
                    save_entry(entry)
                except Exception as e:
                    raise SavingEntryFailed(entry, source) from e
            logger.info("Saved %s entries", len(entries))
        else:
            logger.warning("No fetcher available for source type: %s", source_type)
    except SavingEntryFailed as e:
        logger.critical("Saving entry failed: %s", str(e))
        raise e
    except Exception as e:
        logger.error("Error processing source '%s': %s", name, str(e))

class SavingEntryFailed(Exception):
    def __init__(self, entry, source):
        self.entry = entry
        self.source = source
    def __str__(self):
        return f"Saving entry '{self.entry}' from source '{self.source}' failed."

def save_entry(entry):
    """
    Saves an entry as a JSON file. If 'content_md' exists, saves it as a Markdown file.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Save JSON entry
    json_file_name = sanitize_string(f"{entry['id']}.json")
    json_file_path = os.path.join(DATA_DIR, json_file_name)
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(entry, json_file, indent=2)
    logger.debug(f"Saved JSON entry: {json_file_path}")

    # Save Markdown content if available
    if "content_md" in entry:
        md_file_name = sanitize_string(f"{entry['id']}.md")
        md_file_path = os.path.join(DATA_DIR, md_file_name)
        with open(md_file_path, "w", encoding="utf-8") as md_file:
            md_file.write(entry["content_md"])
        logger.debug(f"Saved Markdown content: {md_file_path}")


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
