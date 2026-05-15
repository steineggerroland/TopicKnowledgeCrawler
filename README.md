# TopicKnowledgeCrawler

TopicKnowledgeCrawler is the crawler and preparation layer behind infl0. It
discovers content from sources such as RSS feeds, HTML listings and podcast
feeds, turns them into normalized content items and prepares payloads for infl0.

The canonical implementation is the portable step layer in `tkcrawler.steps`.
n8n uses these steps in Python Code nodes, but the same steps can be composed
from plain Python or another workflow system.

## What This Project Does

- Normalize source rows from infl0 or local tables.
- Inspect source policies such as HTTP cache headers, RSS TTL and retry hints.
- Plan crawl dispatch based on source status and policy.
- List candidates without fetching every detail page.
- Filter candidates against history and refresh windows.
- Fetch and finalize articles or podcast episodes.
- Build `POST /api/crawler/ingest` payloads for infl0.
- Build `POST /api/crawler/source-status` payloads for infl0 operator/source
  health views.

All crawler implementation lives under `tkcrawler`. New integrations should use
`tkcrawler.steps` for explicit orchestration or `tkcrawler.pipeline` for the
reference Python flow.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

Run tests:

```bash
TLDEXTRACT_CACHE=/private/tmp/tkcrawler-tldextract-cache .venv/bin/python3.13 -m pytest
```

Use the Python version available in your environment if it differs from
`.venv/bin/python3.13`.

## Step CLI

Every portable step can be called through the CLI runner:

```bash
python -m tkcrawler.cli.run_step normalize_source < input.json
python -m tkcrawler.cli.run_step plan_dispatch < input.json
python -m tkcrawler.cli.run_step list_candidates < input.json
python -m tkcrawler.cli.run_step fetch_detail < input.json
python -m tkcrawler.cli.run_step finalize_item < input.json
python -m tkcrawler.cli.run_step build_ingest_body < input.json
```

CLI input accepts either a raw item object or an envelope:

```json
{
  "item": {
    "crawl_key": "https://example.com/feed.xml",
    "type": "rss",
    "url": "https://example.com/feed.xml"
  },
  "context": {
    "now": "2026-05-13T10:00:00+00:00"
  }
}
```

## Python Flow Example

For simple Python usage, compose the step flow through `tkcrawler.pipeline`:

```python
from tkcrawler.pipeline import crawl_source_ingest_bodies

source = {
    "crawl_key": "https://example.com/feed.xml",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "source_status": "ready",
}

payloads = crawl_source_ingest_bodies(source)
```

A runnable no-network example is available at
[`examples/python_step_flow.py`](examples/python_step_flow.py).

## n8n

n8n orchestration is documented in [`n8n/README.md`](n8n/README.md). The n8n
workflows use the same `*_item(...)` functions from `tkcrawler.steps` that a
plain Python flow would use.

## infl0 Contracts

- Ingest payload: [`docs/INGEST_API.md`](docs/INGEST_API.md)
- Source health payload: [`docs/SOURCE_STATUS_API.md`](docs/SOURCE_STATUS_API.md)
- Content item model: [`docs/CONTENT_ITEM_MODEL.md`](docs/CONTENT_ITEM_MODEL.md)

## Architecture Notes

- Target architecture: [`docs/TARGET_ARCHITECTURE.md`](docs/TARGET_ARCHITECTURE.md)
- Current migration notes: [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)
- Planned changes: [`docs/PLANNED_CHANGES.md`](docs/PLANNED_CHANGES.md)
