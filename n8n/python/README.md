# Python Snippets for n8n Code Nodes

Each file in this directory is meant to be copied into a n8n Python Code node, or used as a reference for writing the node inline.

## Paths

Prefer installing the repository in the Python runner image:

```bash
pip install -e /opt/TopicKnowledgeCrawler
```

If you mount the repository during development, set `TOPIC_CRAWLER_ROOT` to the repository root and add `src/` to `PYTHONPATH` if needed.

```yaml
environment:
  TOPIC_CRAWLER_ROOT: /data/TopicKnowledgeCrawler
volumes:
  - /opt/TopicKnowledgeCrawler:/data/TopicKnowledgeCrawler:ro
```

## Snippet Files

| File | Role |
|------|------|
| `code_normalize_crawl_key.py` | Compute `crawl_key` from `url` when missing. |
| `code_merge_enrichment_for_infl0.py` | Merge `article` and LLM fields into `infl0_ingest_body`. |

The actual crawler flow uses portable steps under `tkcrawler.steps`. The same data flow is shown in plain Python in `../../examples/python_step_flow.py`.

## Portable Steps

All steps can be used from n8n or from the CLI:

```bash
python -m tkcrawler.cli.run_step normalize_source < input.json
python -m tkcrawler.cli.run_step plan_dispatch < input.json
python -m tkcrawler.cli.run_step list_candidates < input.json
python -m tkcrawler.cli.run_step filter_candidates < input.json
python -m tkcrawler.cli.run_step fetch_detail < input.json
python -m tkcrawler.cli.run_step finalize_item < input.json
python -m tkcrawler.cli.run_step limit_llm_items < input.json
python -m tkcrawler.cli.run_step build_ingest_body < input.json
```

In n8n, call the `*_item(...)` functions with `item["json"]`, which is the same object as `$json`. The portable `{ "item": ..., "context": ... }` envelope is for CLI and custom runners.

## `normalize_source`

```python
from tkcrawler.steps.normalize_source import normalize_source_item

out = []
for item in _items:
    out.append({"json": normalize_source_item(item["json"])})
return out
```

## `plan_dispatch`

```python
from datetime import datetime, timezone

from tkcrawler.steps.plan_dispatch import plan_dispatch_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    planned = plan_dispatch_item(
        item["json"],
        {"now": now, "dispatch_mode": "scheduled"},
    )
    out.append({"json": planned})
return out
```

Then branch in n8n on `{{ $json.should_dispatch }}`.

## `list_candidates`

```python
from tkcrawler.steps.list_candidates import list_candidates_items

out = []
for item in _items:
    for candidate in list_candidates_items(item["json"]):
        out.append({"json": candidate})
return out
```

This step reads RSS, podcast RSS or HTML listing pages and returns candidates without fetching detail pages.

For sources that block plain Python requests, set a user agent in `policy_json`:

```json
{
  "user_agent": "Mozilla/5.0 (compatible; TopicKnowledgeCrawler/0.1; +https://github.com/steineggerroland/TopicKnowledgeCrawler)"
}
```

## `filter_candidates`

```python
from datetime import datetime, timezone

from tkcrawler.steps.filter_candidates import filter_candidate_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    filtered = filter_candidate_item(item["json"], {"now": now})
    out.append({"json": filtered})
return out
```

Then branch on `{{ $json.candidate_decision === "fetch" }}`.

## `fetch_detail`

```python
from tkcrawler.steps.fetch_detail import fetch_detail_item

verify = "/etc/ssl/certs/ca-certificates.crt"
out = []
for item in _items:
    try:
        out.append({"json": fetch_detail_item(item["json"], {"verify": verify})})
    except Exception as exc:
        j = dict(item["json"])
        j["fetch_detail_error"] = str(exc)
        j["candidate_decision"] = "fetch_failed"
        out.append({"json": j})
return out
```

RSS articles fetch detail pages and create `article.content_md`. Podcast RSS prefers existing feed content and shownotes.

## `finalize_item`

```python
from tkcrawler.steps.finalize_item import finalize_item

out = []
for item in _items:
    out.append({"json": finalize_item(item["json"])})
return out
```

This adds `content_hash`, `source_type` and `tld` to the item.

## `limit_llm_items`

```python
from tkcrawler.steps.limit_llm_items import limit_llm_items

out = []
for limited in limit_llm_items([item["json"] for item in _items]):
    out.append({"json": limited})
return out
```

The step reads `effective_policy.max_llm_items_per_run`. Items over the limit receive `llm_decision = "skip_run_limit"`.

## `build_ingest_body`

```python
from tkcrawler.steps.build_ingest_body import build_ingest_body_item

out = []
for item in _items:
    out.append({"json": build_ingest_body_item(item["json"])})
return out
```

Set the following HTTP node body to `{{ $json.infl0_ingest_body }}`.

## Dependencies

See `../requirements-n8n.txt` and the root `pyproject.toml`.
