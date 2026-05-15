# n8n Data Tables

n8n Data Tables hold source state and item enrichment history. They replace old local JSON history files.

## Table `crawl_sources`

| Column | Type | Description |
|--------|------|-------------|
| `name` | String | Display name. |
| `type` | String | `rss`, `html`, `rss+podcast` or another supported source type. |
| `url` | String | Feed URL or listing URL. |
| `configuration_json` | String, optional | JSON string with HTML selectors for `type: html`. |
| `crawl_key` | String | Stable key matching infl0 `user_feeds.crawl_key`. |
| `active` | Boolean | `true` means the source may be processed. |
| `source_status` | String | `new`, `ready`, `needs_analysis`, `analysis_failed`, `configuration_invalid`, `inactive`. |
| `analysis_error` | String, optional | Last source-analysis error. |
| `analysis_checked_at` | DateTime/String, optional | Last source-analysis timestamp. |
| `configuration_status` | String, optional | `missing`, `valid`, `invalid`, `generated`. |
| `configuration_error` | String, optional | Last HTML configuration validation error. |
| `subscriber_count` | Number, optional | Subscriber count from infl0, if available. |
| `last_seen_in_infl0_at` | DateTime/String, optional | Last successful source sync timestamp. |
| `policy_json` | String, optional | Manual policy JSON. |
| `effective_policy_json` | String, optional | Effective policy after defaults and detected hints. |
| `detected_policy_json` | String, optional | Detected hints such as RSS TTL and HTTP cache headers. |
| `next_allowed_crawl_at` | DateTime/String, optional | Earliest next crawl time. |
| `last_crawl_started_at` | DateTime/String, optional | Last crawl start time. |
| `last_crawl_finished_at` | DateTime/String, optional | Last crawl finish time. |
| `last_crawl_status` | String, optional | `running`, `success`, `partial_failed`, `failed`, `skipped`. |
| `last_crawl_error` | String, optional | Last crawl error summary. |
| `last_dispatch_reason` | String, optional | Why the dispatcher started or skipped the source. |
| `crawl_total_count` | Number, optional | Total terminal items in the last run. |
| `crawl_candidate_count` | Number, optional | Listed candidates in the last run. |
| `crawl_skipped_count` | Number, optional | Candidates skipped before fetch or LLM. |
| `crawl_fetch_error_count` | Number, optional | Detail fetch errors. |
| `crawl_unchanged_count` | Number, optional | Known unchanged items. |
| `crawl_processed_count` | Number, optional | Successfully processed or sent items. |
| `crawl_llm_failed_count` | Number, optional | LLM failures. |
| `consecutive_error_count` | Number, optional | Consecutive failing crawl runs. |
| `last_successful_crawl_at` | DateTime/String, optional | Last fully successful crawl. |
| `last_crawl_result_json` | String, optional | JSON summary of the latest counts. |
| `source_health_status` | String, optional | `pending`, `needs_setup`, `healthy`, `quiet`, `degraded`, `failing`, `blocked`, `paused`. |
| `source_health_reason` | String, optional | Machine-readable health reason. |
| `source_health_json` | String, optional | Detailed source health object for infl0. |
| `operator_attention` | Boolean, optional | `true` when an operator should investigate. |
| `operator_attention_reason` | String, optional | Machine-readable operator attention reason. |

## `policy_json`

Manual source policy as JSON string:

```json
{
  "crawl_interval_minutes": 180,
  "refresh_window_days": 7,
  "max_candidates_per_run": 20,
  "max_llm_items_per_run": 5,
  "user_agent": "Mozilla/5.0 (compatible; TopicKnowledgeCrawler/0.1; +https://github.com/steineggerroland/TopicKnowledgeCrawler)",
  "contact": "mailto:hello@example.com",
  "crawler_name": "infl0"
}
```

Header semantics:

- `user_agent`: explicit `User-Agent`.
- `request_headers`: optional object with additional header overrides.
- `contact`: sent as `From` and `X-Infl0-Contact`.
- `crawler_name`: sent as `X-Infl0-Crawler`.

## Source Sync from infl0

infl0 exposes `GET /api/crawler/sources`. Map response fields into `crawl_sources`:

| infl0 field | Table column |
|-------------|--------------|
| `crawlKey` | `crawl_key` |
| `feedUrl` | `url` |
| `displayTitle` | `name`, fallback to `feedUrl` or `crawlKey` |
| `subscriberCount` | `subscriber_count` |
| missing | `type` initially empty or `unknown` |
| missing | `active = true` |

Analyze source type with `tkcrawler.steps.analyze_source`. For HTML sources, generate and validate `configuration_json` with the HTML analysis steps and n8n AI.

## Table `article_enrichment`

| Column | Type | Description |
|--------|------|-------------|
| `article_id` | String, unique | Same as the crawler item id. |
| `content_hash` | String | Hash over `content_md`. |
| `teaser` | String | Short teaser. |
| `summary_long` | String/Text | Longer summary. |
| `category_json` | String | JSON array of categories. |
| `tags_json` | String | JSON array of tags. |
| `seriousness_rating` | String | `high`, `medium` or `low`. |
| `updated_at` | String | ISO timestamp. |
| `article` | String, optional | Serialized article/item object for re-sending. |
| `is_sent` | Boolean, optional | Whether the item has already been sent to infl0. |

Skip logic: look up by `article_id`. If the stored `content_hash` matches the current one, reuse enrichment and skip the AI node. Otherwise run AI and upsert the enrichment row.
