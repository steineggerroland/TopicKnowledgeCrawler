# n8n → Code → Python
# Baut den JSON-Body für POST /api/crawler/ingest.
#
# Erwartet im Item-JSON:
#   crawl_key, article (dict mit id, title, link, …, content_md)
# Optional enrichment (von AI + Data Table): teaser, summary_long, category, tags, seriousness_rating
# Env: TOPIC_CRAWLER_ROOT = Repo-Root (Ordner mit src/).

import os
import sys

_ROOT = os.environ.get("TOPIC_CRAWLER_ROOT", "/data/TopicKnowledgeCrawler")
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.crawler.n8n_compat.infl0_payload import build_ingest_body

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
