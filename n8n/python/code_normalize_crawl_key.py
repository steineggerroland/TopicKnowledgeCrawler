# n8n → Code → Python
# Ein Item pro Data-Table-Zeile (crawl_sources). Setzt crawl_key falls leer.
#
# Voraussetzung: TopicKnowledgeCrawler im Runner-Image per `pip install -e` (siehe Dockerfile-Beispiel).

from tkcrawler.crawl_key import normalize_feed_url

out = []
for item in items:
    row = dict(item["json"])
    url = (row.get("url") or "").strip()
    if not row.get("crawl_key") and url:
        row["crawl_key"] = normalize_feed_url(url)
    out.append({"json": row})
return out
