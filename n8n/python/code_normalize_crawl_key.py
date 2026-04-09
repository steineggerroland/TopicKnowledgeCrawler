# n8n → Code → Python
# Ein Item pro Data-Table-Zeile (crawl_sources). Setzt crawl_key falls leer.
#
# Env: TOPIC_CRAWLER_ROOT = Repo-Root (Ordner mit src/). Alternativ PYTHONPATH setzen.

import os
import sys

_ROOT = os.environ.get("TOPIC_CRAWLER_ROOT", "/data/TopicKnowledgeCrawler")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.crawler.n8n_compat.crawl_key import normalize_feed_url

out = []
for item in items:
    row = dict(item["json"])
    url = (row.get("url") or "").strip()
    if not row.get("crawl_key") and url:
        row["crawl_key"] = normalize_feed_url(url)
    out.append({"json": row})
return out
