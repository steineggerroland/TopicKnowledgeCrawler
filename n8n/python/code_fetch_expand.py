# n8n → Code → Python
# Pro Eingabe-Item (eine Quellen-Zeile): holt Einträge per RSS/HTML/Podcast-Fetcher,
# gibt viele Items zurück (je ein Artikel).
#
# Erwartetes Input-JSON pro Item: name, type, url, optional configuration_json, crawl_key.
# Env: TOPIC_CRAWLER_ROOT = Repo-Root (Ordner mit src/).

import os
import sys

_ROOT = os.environ.get("TOPIC_CRAWLER_ROOT", "/data/TopicKnowledgeCrawler")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.crawler.n8n_compat.datatable import row_to_source, row_with_crawl_key
from src.crawler.n8n_compat.fetch import fetch_entries_for_source
from src.crawler.n8n_compat.infl0_payload import finalize_entry_metadata

out = []
for item in items:
    row = row_with_crawl_key(item["json"])
    source = row_to_source(row)
    crawl_key = row["crawl_key"]
    try:
        entries = fetch_entries_for_source(source)
    except Exception as exc:
        out.append(
            {
                "json": {
                    "crawl_key": crawl_key,
                    "source_name": source.get("name"),
                    "fetch_error": str(exc),
                }
            }
        )
        continue

    for entry in entries:
        full = finalize_entry_metadata(
            entry,
            source_type=source["type"],
            source_feed_url=source["url"],
        )
        aid = full.get("id")
        ch = full.get("content_hash")
        out.append(
            {
                "json": {
                    "crawl_key": crawl_key,
                    "source_name": source.get("name"),
                    "article_id": aid,
                    "content_hash": ch,
                    "article": full,
                    "content_md": full.get("content_md"),
                }
            }
        )
return out
