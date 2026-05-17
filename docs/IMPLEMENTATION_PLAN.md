# Implementation Plan

This plan describes the implementation path for a small Python step layer that can be used from n8n Code nodes and from plain Python or CLI scripts.

## Guiding Principle

Each domain step should provide:

1. a Python function with clear dict/JSON contracts,
2. optional CLI execution through stdin/stdout JSON,
3. a tiny n8n Code node snippet that forwards input and output,
4. tests for the actual function, not for n8n internals.

n8n remains the production orchestrator. The Python steps are the portable reference implementation.

## Python Guidelines

The existing `src/` layout is the right choice and should remain. It avoids accidental imports from the working directory and matches common packaging practice for installable Python libraries.

Guidelines for new Python changes:

- Package code lives under `src/tkcrawler`.
- Tests live under `tests/` and cover behavior.
- Step functions stay small, typed and JSON-friendly.
- Side effects stay at the edge: CLI reads stdin/stdout, n8n reads and writes items.
- Runtime context is passed explicitly through `context`.
- n8n-specific mapping belongs in thin wrappers, not deep parser or policy logic.
- Errors should be structured.
- Heavy imports should not happen at package import time unless unavoidable.
- Packaging stays in `pyproject.toml`.

When Python conventions and n8n convenience conflict, the library should follow Python conventions. n8n snippets may remain pragmatic, but should mostly call step functions.

## Code Structure

The canonical modules are:

```text
src/tkcrawler/
  steps/
    normalize_source.py
    analyze_source.py
    inspect_source_policy.py
    plan_dispatch.py
    list_candidates.py
    filter_candidates.py
    fetch_detail.py
    finalize_item.py
    limit_llm_items.py
    build_ingest_body.py
    finalize_crawl_run.py
    derive_source_health.py
    build_source_status_body.py
  cli/
    run_step.py
  pipeline.py
```

CLI examples:

```bash
python -m tkcrawler.cli.run_step normalize_source < input.json
python -m tkcrawler.cli.run_step list_candidates < input.json
python -m tkcrawler.cli.run_step filter_candidates < input.json
python -m tkcrawler.cli.run_step fetch_detail < input.json
python -m tkcrawler.cli.run_step finalize_item < input.json
python -m tkcrawler.cli.run_step limit_llm_items < input.json
python -m tkcrawler.cli.run_step build_ingest_body < input.json
```

## n8n Input vs. CLI Envelope

There are two intentional invocation levels:

1. n8n core functions receive one flat n8n item payload, the object visible as `$json` or `item["json"]`.
2. Step/CLI functions may receive a portable envelope so the same logic can run outside n8n with explicit context.

n8n Code nodes should usually call the `*_item(...)` function:

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

n8n input is flat:

```json
{
  "crawl_key": "https://example.com/feed",
  "type": "rss",
  "source_status": "ready"
}
```

The portable CLI envelope is:

```json
{
  "item": {
    "crawl_key": "https://example.com/feed",
    "type": "rss",
    "source_status": "ready"
  },
  "context": {
    "now": "2026-05-04T12:00:00+02:00",
    "dispatch_mode": "scheduled"
  }
}
```

## Completed Direction

The broad black-box fetch step has been replaced by explicit steps:

1. `list_candidates`
2. history lookup in n8n or another store
3. `filter_candidates`
4. `fetch_detail`
5. `finalize_item`
6. optional `segment_content` for long-form Markdown
7. optional LLM enrichment in n8n
8. `build_ingest_body`
9. `finalize_crawl_run`

A pure Python reference flow is available in `tkcrawler.pipeline` and demonstrated in `examples/python_step_flow.py`.

## Next Implementation Phases

### Dispatch and Policy

- Keep `plan_dispatch` as the single source for due checks.
- Use `effective_policy` from source policy and detected hints.
- Respect running state, invalid configuration and retry hints.
- Store `next_allowed_crawl_at` before starting the child workflow.

### Source Sync

- Keep source sync fast and robust.
- Analyze source type separately from HTML selector generation.
- Use n8n AI nodes for selector generation.
- Validate generated HTML configuration before marking a source ready.

### Candidate-First Crawl

- Keep candidate listing cheap.
- Perform history lookup before detail fetch.
- Fetch only candidates with `candidate_decision = fetch`.
- Count skipped, unchanged, processed and failed items for source health.

### Policy Inspection

- Inspect RSS TTL, skip hours and skip days.
- Capture HTTP `Cache-Control`, `Expires`, `ETag`, `Last-Modified` and `Retry-After`.
- Store raw detected hints in `detected_policy_json`.

### Item Model and New Source Families

- Keep generalizing from `article` to `item` while preserving compatibility.
- Add `episode` metadata for podcasts.
- Add future adapters for Mastodon, documents or research sources.
- Design `segment_content` for long sources.

## Open Questions

- Which default crawl interval should apply when a source has no explicit policy?
- Should crawl history live in the existing enrichment table or a dedicated technical table?
- How aggressively should old content be refreshed?
- Which new source family is the best next proof of concept after RSS, HTML and podcast?
