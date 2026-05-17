# Planned Changes

> **Archive.** For current architecture and workflow, use [`TARGET_ARCHITECTURE.md`](TARGET_ARCHITECTURE.md) and [`WORKFLOW_DIAGRAM.md`](WORKFLOW_DIAGRAM.md). This file records earlier migration rationale only.

This is a historical planning document. The current implementation lives under `src/tkcrawler`, production n8n orchestration uses `tkcrawler.steps`, and the plain Python reference flow is `tkcrawler.pipeline`.

## Current State

TopicKnowledgeCrawler started as a standalone crawler and was then turned into a Python library that n8n workflows can reuse.

Current layers:

- `tkcrawler`: portable steps and helpers for n8n, infl0 and local Python flows.
- `n8n`: workflow documentation and Code node snippets for crawl -> LLM enrichment -> infl0 ingest.

Important decisions now happen earlier in the workflow. Candidate listing happens before detail fetching, and history/policy filtering decides whether a detail page is worth loading.

## Observed Problems

- RSS sources are fast when entries contain enough content.
- RSS sources become slow when every entry requires a detail-page fetch.
- Podcast feeds may contain many old episodes and long descriptions.
- Skipping LLM enrichment saves cost but does not automatically save fetch time.
- Source policies need to be explicit and observable.
- infl0 needs source status and health information for users and operators.

## Goals

1. Crawl sources intelligently and respectfully.
2. Avoid expensive detail fetches for known or old entries.
3. Make feed and item processing measurable.
4. Keep n8n as orchestration while documenting a portable workflow.
5. Use one shared Python step layer for n8n and local execution.
6. Make HTML sources a supported production path.
7. Keep control decisions visible in n8n.

## Candidate-First Processing

The old broad fetch step was convenient but too coarse. The current flow is split into:

1. `list_candidates`
2. history lookup
3. `filter_candidates`
4. `fetch_detail`
5. `finalize_item`
6. LLM enrichment in n8n
7. `build_ingest_body`

This reduces unnecessary detail fetches and makes each decision visible.

## RSS and Podcast Sources

RSS and podcast feeds should be cheap to inspect. Candidate IDs, links, titles, authors and timestamps are extracted first. Detail pages are fetched only after filtering.

Podcast episodes use feed content and shownotes first. Detail pages are a fallback. The item model includes episode-specific metadata such as audio URL, duration, MIME type, shownotes and chapters.

## HTML Sources

HTML sources need explicit configuration because listing pages have no standard structure. A production HTML path needs:

1. detection: is the source HTML or a feed?
2. configuration: which selectors identify candidate blocks and links?
3. validation: does the configuration still produce candidates?

For HTML sources, `configuration_json` should contain at least:

```json
{
  "article_selector": "article",
  "main_page_anchor_selector": "a:has(h2)"
}
```

Invalid selectors should set `configuration_status = invalid` and expose an error instead of silently producing an empty crawl.

## Data Tables

The source table should store operational state:

- `crawl_key`
- `type`
- `configuration_json`
- `policy_json`
- `detected_policy_json`
- `next_allowed_crawl_at`
- `last_crawl_status`
- run counters such as processed, skipped, unchanged and failed counts
- source health fields for infl0

The article/enrichment table can store content hashes and LLM output. A dedicated crawl history table may be cleaner later if technical history grows.

## infl0 Integration

infl0 provides sources through `GET /api/crawler/sources` and receives content through `POST /api/crawler/ingest`.

TopicKnowledgeCrawler additionally sends source health through `POST /api/crawler/source-status`. This lets infl0 show users which sources are pending, healthy, quiet, degraded, failing, blocked or paused.

## Next Useful Steps

- Keep source health publishing stable.
- Improve podcast episode support and infl0 rendering.
- Add tests and examples for HTML configuration edge cases.
- Decide which new source family should be the next adapter proof of concept.
- Keep documentation aligned with the current step names and API contracts.
