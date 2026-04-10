# n8n → Code → Python
# Ein Item pro Data-Table-Zeile (crawl_sources). Setzt crawl_key falls leer.
#
# Env: TOPIC_CRAWLER_ROOT = Repo-Root (Ordner mit Unterordner `src/`).
# Ohne pip install: sys.path enthält …/src für `import tkcrawler`.

import os
import sys

_ROOT = os.environ.get("TOPIC_CRAWLER_ROOT", "/data/TopicKnowledgeCrawler")
_SRC = os.path.join(_ROOT, "src")
for p in (_SRC, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from tkcrawler.crawl_key import normalize_feed_url

out = []
for item in items:
    row = dict(item["json"])
    url = (row.get("url") or "").strip()
    if not row.get("crawl_key") and url:
        row["crawl_key"] = normalize_feed_url(url)
    out.append({"json": row})
return out
