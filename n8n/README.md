# TopicKnowledgeCrawler for n8n

n8n orchestrates the crawler flow: sources live in a Data Table, intermediate state lives in Data Tables, AI Nodes create summaries and categories, and Python Code nodes call the portable `tkcrawler.steps` functions.

## Quick Start

1. Create Data Tables, see `docs/DATA_TABLES.md`.
2. Review the workflow overview, see `docs/WORKFLOW.md`.
3. Configure AI prompts, see `docs/AI_PROMPTS.md`.
4. Use Python snippets from `python/README.md` where useful.
5. Build or configure the Python runner, see `DOCKER_CRAWLER.md` and `docker-compose.server.example.yaml`.
6. Install `requirements-n8n.txt` in the Python runner image.
7. Configure the runner allowlist and `pip install -e`, see `docs/PYTHON_RUNNER_ALLOWLIST.md`.

## Python Modules

The installable package is `tkcrawler` under `src/tkcrawler/`.

Useful entry points:

- `tkcrawler.crawl_key.normalize_feed_url`: normalize feed URLs like infl0 does.
- `tkcrawler.datatable.row_to_source`: convert a Data Table row into a source dict.
- `tkcrawler.steps.*`: portable steps for analysis, dispatch, candidate listing, detail fetch and finalization.
- `tkcrawler.pipeline`: the same data flow as a plain Python reference pipeline.
- `tkcrawler.fetch.fetch_entries_for_source`: small compatibility helper backed by `tkcrawler.pipeline`.
- `tkcrawler.infl0_payload`: helpers for `POST /api/crawler/ingest`.

Run focused tests with:

```bash
pytest tests/test_tkcrawler.py tests/steps/test_steps.py
```

## Local Python Path

The canonical implementation is `tkcrawler.steps`. n8n orchestrates these steps, but the same pipeline can run from plain Python or another flow system. See `../examples/python_step_flow.py` for a runnable example.
