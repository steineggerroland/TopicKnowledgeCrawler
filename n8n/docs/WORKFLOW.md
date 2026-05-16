# n8n Workflow Overview

## Goals

- Read sources from a n8n Data Table or from infl0.
- Store intermediate state in Data Tables instead of local JSON files.
- Run LLM enrichment in n8n AI Nodes.
- Run crawler logic through portable `tkcrawler.steps` functions.
- Send items to infl0 through `POST /api/crawler/ingest`.

## Workflow 1: Process Sources

Runs manually or every 15 minutes.

infl0 can provide sources through `GET {{$env.INFL0_BASE_URL}}/api/crawler/sources`. Store the result in the `crawl_sources` Data Table keyed by `crawl_key`.

For new or incomplete rows, run the source-analysis steps:

- `normalize_source`
- `analyze_source`
- `prepare_html_analysis`
- n8n AI selector generation for HTML sources
- `apply_html_analysis`
- `validate_source_configuration`

The detailed source-sync workflow is documented in `SOURCE_SYNC_WORKFLOW.md`.

## Workflow 2: Dispatch

Runs manually or every 15 minutes.

The dispatch workflow reads active sources, runs `inspect_source_policy`, persists detected policy fields, runs `plan_dispatch`, updates source state to `running` for due sources and starts the child crawl workflow for each due source. Details are documented in `CRAWL_DISPATCH_WORKFLOW.md`.

## Workflow 3: Crawl Source

Triggered by the dispatch workflow, with manual test inputs available during development.

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
14. Save article history and sent state.
15. Aggregate all ending paths: processed, unchanged, skipped, fetch errors, LLM failures and candidate counts.
16. `finalize_crawl_run`.
17. Update source table with crawl counters and result.

## Workflow 4: Send Health Status

Runs manually or on an hourly schedule.

The health workflow reads active sources, derives operator/source health, writes health fields back to the source Data Table and posts the public source-status body to infl0:

1. Read active sources.
2. `derive_source_health`.
3. Update source health fields in the source table.
4. `build_source_status_body`.
5. `POST /api/crawler/source-status`.

## Diagrams

The four-workflow topology and LLM call sites are diagrammed in `../../docs/WORKFLOW_DIAGRAM.md`.

That diagram also labels which nodes are `tkcrawler` calls and which nodes are pure n8n/platform orchestration. As a rule of thumb, crawler decisions and payload shaping belong in TKC calls; scheduling, branching, table persistence, child workflow execution, AI nodes and HTTP calls belong to n8n.

## Python in n8n

Prefer installing the package in the runner image with `pip install -e`. If that is not possible during development, set `PYTHONPATH` to the repository root and `src/` directory.

The implementation path is `src/tkcrawler/steps/*`. The plain Python reference flow is `tkcrawler.pipeline`.
