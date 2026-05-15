# Crawl Dispatch Workflow

This document describes the n8n workflow that reads active sources from `Infl0-crawl-sources` and starts the child crawl workflow for each due source.

## Responsibility

The dispatch workflow decides which sources may run now. The child crawl workflow processes one source.

Recommended separation:

- Source sync workflow: keeps `crawl_sources` current and analyzes sources.
- Crawl dispatch workflow: selects due sources and starts child crawls.
- Child crawl workflow: lists candidates, fetches details, enriches and sends items to infl0.
- Source health workflow or final dispatch step: sends source health to infl0.

## Why Dispatch Matters

Filtering only on `active = true` is not enough once sources have policies and observed state.

The dispatcher should prevent:

- crawling sources before their interval elapsed,
- retrying sources that returned `Retry-After`,
- starting sources with invalid HTML configuration,
- starting already running sources too early,
- overloading operators with repeated failing runs.

## Recommended Node Chain

1. Manual or Schedule trigger.
2. Merge triggers.
3. Data Table `Get rows`: active sources, sorted by `updatedAt ASC`.
4. Optional `inspect_source_policy` for due or stale policy data.
5. Python Code node `plan_dispatch`.
6. Update source row with `last_crawl_status = running`, `last_crawl_started_at`, `next_allowed_crawl_at`, `last_dispatch_reason`.
7. IF `should_dispatch = true`.
8. Execute child crawl workflow in `each` mode.
9. Aggregate child workflow endings.
10. `finalize_crawl_run`.
11. Update source row with result counters.
12. `derive_source_health` and `build_source_status_body`.
13. `POST /api/crawler/source-status`.

The child workflow should receive the planned item from the true branch, not the Data Table update output, because update nodes may drop fields such as `dispatch_reason` or `effective_policy`.

## Dispatch Step

n8n Code node:

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

Manual force can be implemented by passing `dispatch_mode = "force"` only from an explicit manual-force branch.

## Important Fields

Input fields:

- `active`
- `source_status`
- `type`
- `configuration_status`
- `policy_json`
- `detected_policy_json`
- `next_allowed_crawl_at`
- `last_crawl_status`
- `last_crawl_started_at`

Output fields:

- `should_dispatch`
- `dispatch_reason`
- `next_allowed_crawl_at`
- `effective_policy`

Common dispatch reasons:

- `due`
- `not_due`
- `inactive`
- `source_not_ready`
- `html_configuration_invalid`
- `already_running`
- `stale_running`
- `manual_force`

## Policy

Default policy values should be conservative:

```json
{
  "crawl_interval_minutes": 180,
  "rate_limit_per_minute": 10,
  "refresh_window_days": 7,
  "stale_running_minutes": 120,
  "max_llm_items_per_run": 3
}
```

Source-level `policy_json` may override defaults. Detected hints from `inspect_source_policy` may influence timing, for example RSS TTL or HTTP cache headers.

## Child Crawl Contract

The child workflow receives a single planned source item. If `should_dispatch = true` is already present, the child should start directly with `list_candidates` and should not run `plan_dispatch` again.

The child workflow should aggregate ending paths into fields such as:

- `fetchErrored`
- `unchanged`
- `processed`
- `llmFailed`
- `skipped`
- `candidateCount`

Then `finalize_crawl_run` computes:

- `last_crawl_status`
- `last_crawl_finished_at`
- `last_crawl_error`
- `crawl_total_count`
- `crawl_candidate_count`
- `crawl_skipped_count`
- `crawl_fetch_error_count`
- `crawl_unchanged_count`
- `crawl_processed_count`
- `crawl_llm_failed_count`
- `consecutive_error_count`
- `last_successful_crawl_at`
- `last_crawl_result_json`

## Source Health

After the source row has current crawl counters, run `derive_source_health` and `build_source_status_body`. Send the resulting body to infl0 via `POST /api/crawler/source-status`.

`nextAllowedCrawlAt` is important for user-facing source status. Error counters and operator attention fields are mainly for operator views.

## Status Semantics

- `success`: no fetch or LLM failures.
- `partial_failed`: at least one success or unchanged item and at least one error.
- `failed`: errors without successful items.
- `skipped`: source was not due or not crawlable.

## Minimal First Step

1. Add `next_allowed_crawl_at` to the source table.
2. Add a Python dispatch filter that sets `should_dispatch`.
3. Send only `should_dispatch = true` rows to the child workflow.

Then add policy inspection, detected hints and backoff behavior incrementally.
