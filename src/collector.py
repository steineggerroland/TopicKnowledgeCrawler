import json
import os
from fetchers.rss_fetcher import fetch_rss_feed
from utils.logger import logger

DATA_DIR = "data/raw/"
CONFIG_FILE = "config/sources.json"


def load_sources():
    """Lädt die Quellen aus der Konfigurationsdatei."""
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)["sources"]


def escape_filename(name: str):
    """Bereitet Dateinamen auf, indem ungültige Zeichen entfernt werden."""
    import re
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)


def save_entry(source_name, entry):
    """
    Speichert einen einzelnen Artikel als JSON-Datei.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    safe_source_name = escape_filename(source_name)
    file_name = f"{safe_source_name}_{entry['id']}.json"
    file_path = os.path.join(DATA_DIR, file_name)

    with open(file_path, "w") as file:
        json.dump(entry, file, indent=4)
    logger.info(f"Saved entry: {file_path}")


if __name__ == "__main__":
    sources = load_sources()
    for source in sources:
        logger.info(f"Processing source: {source['name']} ({source['type']})")

        if source["type"] == "rss":
            entries = fetch_rss_feed(source["url"])
            for entry in entries:
                save_entry(source["name"], entry)
        else:
            logger.warn(f"No crawler found for source type: {source['type']}")