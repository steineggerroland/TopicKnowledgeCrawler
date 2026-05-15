# Historical Crawl Workflow Migration Notes

This document records the migration from the old broad fetch step to the current explicit step chain. It is kept for context; current workflows should use `tkcrawler.steps` directly.

## Old Shape

The previous productive workflow used one broad Python fetch step, then history lookup, AI enrichment, article saving, ingest body building and `POST /api/crawler/ingest`.

That worked, but the fetch step did too much:

- source parsing,
- candidate listing,
- detail fetching,
- markdown extraction,
- final article shaping.

Errors were harder to route, and old known feed entries could still trigger expensive detail fetches.

## Current Direction

The broad step is replaced by smaller nodes:

1. `List Candidates`
2. history lookup
3. merge candidate and history
4. `Filter Candidates`
5. IF `candidate_decision == "fetch"`
6. `Fetch Detail`
7. IF fetch succeeded
8. `Finalize Item`
9. content-hash comparison
10. `Limit LLM Items`
11. AI enrichment
12. `build_ingest_body`
13. `POST /api/crawler/ingest`
14. aggregate endings
15. `finalize_crawl_run`

## Compatibility Notes

The n8n field name `article` is still used in several nodes for compatibility with existing enrichment and ingest logic. The domain model is moving toward a more general item model with `item_kind` values such as `article` and `episode`.

The ingest builder should accept the flat enrichment format:

```json
{
  "article": { "id": "...", "content_md": "..." },
  "teaser": "...",
  "summary_long": "...",
  "category": ["..."],
  "tags": ["..."],
  "seriousness_rating": "medium"
}
```

It should output:

```json
{
  "infl0_ingest_body": { "crawlKey": "...", "id": "..." }
}
```

## Migration Outcome

The current step chain provides better observability:

- skipped candidates are visible,
- detail fetch errors are counted,
- unchanged items are counted,
- LLM failures are separated from fetch failures,
- source-level result counters can be sent back to infl0.

This document can be deleted once all active workflows and screenshots refer only to the current step names.
