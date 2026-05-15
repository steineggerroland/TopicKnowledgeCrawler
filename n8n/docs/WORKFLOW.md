# n8n Workflow Overview

## Goals

- Read sources from a n8n Data Table or from infl0.
- Store intermediate state in Data Tables instead of local JSON files.
- Run LLM enrichment in n8n AI Nodes.
- Run crawler logic through portable `tkcrawler.steps` functions.
- Send items to infl0 through `POST /api/crawler/ingest`.

## Source Sync

infl0 can provide sources through `GET {{$env.INFL0_BASE_URL}}/api/crawler/sources`. Store the result in the `crawl_sources` Data Table keyed by `crawl_key`.

For new or incomplete rows, run the source-analysis steps:

- `analyze_source`
- `prepare_html_analysis`
- n8n AI selector generation for HTML sources
- `apply_html_analysis`
- `validate_source_configuration`

The detailed source-sync workflow is documented in `SOURCE_SYNC_WORKFLOW.md`.

## Crawl Dispatch

The dispatch workflow reads active sources, runs `plan_dispatch`, updates source state and only starts the child crawl workflow for due sources. Details are documented in `CRAWL_DISPATCH_WORKFLOW.md`.

## Child Crawl Workflow

Recommended node chain for one source:

1. Trigger from the dispatch workflow or manual test input.
2. `List Candidates` Python Code node.
3. History lookup by `article_id`.
4. Merge candidate and history result.
5. `Filter Candidates` Python Code node.
6. IF `candidate_decision == "fetch"`.
7. `Fetch Detail` Python Code node.
8. `Finalize Item` Python Code node.
9. Existing history/content-hash check.
10. `Limit LLM Items` Python Code node.
11. AI enrichment in n8n.
12. `build_ingest_body` Python Code node.
13. `POST /api/crawler/ingest`.
14. Aggregate all ending paths.
15. `finalize_crawl_run`.
16. Update source table.
17. Send source health to infl0.

## Python in n8n

Prefer installing the package in the runner image with `pip install -e`. If that is not possible during development, set `PYTHONPATH` to the repository root and `src/` directory.

The implementation path is `src/tkcrawler/steps/*`. The plain Python reference flow is `tkcrawler.pipeline`.
