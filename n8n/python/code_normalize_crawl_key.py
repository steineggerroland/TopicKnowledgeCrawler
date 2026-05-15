# n8n → Code → Python
# One item per Data Table row (crawl_sources). Sets crawl_key when it is empty.
#
# Prerequisite: TopicKnowledgeCrawler installed in the runner image via
# `pip install -e`, see the Dockerfile example.

from tkcrawler.crawl_key import normalize_feed_url

out = []
for item in items:
    row = dict(item["json"])
    url = (row.get("url") or "").strip()
    if not row.get("crawl_key") and url:
        row["crawl_key"] = normalize_feed_url(url)
    out.append({"json": row})
return out
