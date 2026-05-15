# n8n → Code → Python
# Builds the JSON body for POST /api/crawler/ingest.
#
# Prerequisite: `pip install -e` for this repo in the runner image.

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
