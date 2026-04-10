# n8n → Code → Python
# Baut den JSON-Body für POST /api/crawler/ingest.
#
# Env: TOPIC_CRAWLER_ROOT = Repo-Root (mit `src/tkcrawler`).

import os
import sys

_ROOT = os.environ.get("TOPIC_CRAWLER_ROOT", "/data/TopicKnowledgeCrawler")
_SRC = os.path.join(_ROOT, "src")
for p in (_SRC, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from tkcrawler.infl0_payload import build_ingest_body

out = []
for item in items:
    j = item["json"]
    crawl_key = j["crawl_key"]
    article = j["article"]
    enrichment = {
        k: j[k]
        for k in ("teaser", "summary_long", "category", "tags", "seriousness_rating")
        if k in j and j[k] is not None
    }
    body = build_ingest_body(
        crawl_key=crawl_key,
        entry=article,
        enrichment=enrichment or None,
    )
    out.append({"json": {"infl0_ingest_body": body}})
return out
