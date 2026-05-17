# Target Architecture

This note defines the target direction for TopicKnowledgeCrawler. The project is no longer meant to become a standalone crawler product. Its role is to provide a robust, observable ingestion and preparation pipeline for infl0.

n8n is currently the production orchestrator, and that is fine. The Python layer should therefore not pretend to be a full application. It should either be:

1. a small, well-tested library for parsing, normalization and decision logic, or
2. disappear for parts where n8n can own the logic cleanly.

Both options are acceptable as long as the domain workflow is documented independently from n8n JSON exports.

## Goal

We want a pipeline that processes sources intelligently, respectfully and transparently:

- Synchronize sources from infl0.
- Classify sources as RSS, podcast RSS, HTML or unknown.
- Validate HTML source configuration.
- Respect crawl intervals and rate limits per source.
- Decide before expensive detail fetches whether an item is relevant.
- Process only new or meaningfully refreshable content.
- Split long sources into stable learning and timeline items.
- Keep enrichment and ingest transparent through n8n.

## Product Context

infl0 should be the reading and learning app for users: a compact inflow where all relevant information sources for their topics are prepared, learnable and easy to process.

The pipeline should not merely fetch articles. It should turn knowledge sources into consumable infl0 items:

- current articles from RSS/Atom and HTML sources,
- podcast episodes,
- social posts or threads,
- chapters or sections from PDFs and EPUBs,
- new scientific papers or paper references,
- later, additional personal or curated knowledge sources.

The common denominator is not the technical source format. The goal is that users can understand, revisit and learn from new information efficiently.

## Non-Goals

- No separate crawler backend unless the workflow clearly outgrows n8n.
- No hidden persistence in the Python package.
- No second source of truth for infl0 timeline ranking. Feed scoring belongs to infl0 because it uses user behavior.
- No hard dependency on one LLM provider in Python.

## Abstract Workflow

The workflow should be described in domain steps that can be implemented in n8n or another orchestration system:

1. `sync_sources`: fetch sources from infl0 or another source registry.
2. `normalize_source`: normalize URL, crawl key, display name and source shape.
3. `analyze_source`: detect content type and source type.
4. `prepare_html_analysis`: prepare HTML pages for LLM-assisted selector detection.
5. `apply_html_analysis`: persist generated selector configuration.
6. `validate_source_configuration`: verify that the source can produce candidates.
7. `inspect_source_policy`: inspect cache headers, RSS TTL and retry hints.
8. `plan_dispatch`: decide whether a source may run now.
9. `list_candidates`: cheaply list article or episode candidates.
10. `filter_candidates`: compare candidates with history and policy.
11. `fetch_detail`: fetch and extract exactly one article or episode.
12. `finalize_item`: add metadata, content hash and source metadata.
13. `segment_content`: optionally split long-form Markdown into stable sections.
14. `limit_llm_items`: cap expensive enrichment work per run.
15. `enrich_item`: run LLM enrichment in n8n.
16. `build_ingest_body`: build the infl0 ingest body.
17. `send_to_infl0`: call infl0.
18. `finalize_crawl_run`: aggregate run counters and health state.
19. `send_source_status`: publish source status to infl0.

n8n is one concrete implementation of these steps. Another system should be able to implement the same steps and data contracts.

## Source Families

### Articles

Articles are the current baseline. They come from RSS, Atom or HTML listing pages. Important assumptions:

- candidates are cheap to list,
- detail pages are often expensive,
- old items can usually be ignored after a refresh window,
- content changes are detected through `content_hash`.

### Podcast Episodes

Podcast episodes are timeline items, not merely article variants. The existing `episode` item kind extends the shared item model with fields such as audio URL, duration, MIME type, shownotes and chapters.

Preferred extraction order:

1. rich feed content or shownotes,
2. episode description or iTunes summary,
3. linked detail page,
4. title and metadata fallback for a minimal teaser.

### Social Sources

Social sources such as Mastodon should be modeled as source adapters that produce normalized candidates. Threads may become parent/child item groups. This should remain an adapter concern, not a change to the whole workflow.

### Documents

PDF and EPUB sources are long-form knowledge sources. They should be segmented into stable items, for example by chapter, heading or semantic section. Each segment needs a stable ID, position and parent document metadata.

### Research Sources

Paper sources should produce item types such as paper references, abstracts, sections or method/result summaries. They need careful metadata handling and conservative summarization.

## Item Model

The target model is an infl0 item, not only an article.

Common fields:

- `item_id`: stable item id.
- `source_key`: stable source id.
- `source_type`: source family or concrete source type.
- `item_kind`: article, episode, post, chapter, section, paper and so on.
- `title`.
- `link`.
- `published_at`.
- `updated_at`.
- `author`.
- `content_md`.
- `summary`.
- `content_hash`.
- `position`, optional for long sources.
- `parent_item_id`, optional for chapters, sections or threads.

The field name `article` may still appear inside n8n for compatibility, but the documented contract should move toward `item` semantics.

## Python Layer

The Python layer should contain reusable logic:

- normalization,
- source analysis,
- policy and dispatch decisions,
- candidate listing,
- detail extraction,
- finalization,
- payload construction,
- source health derivation,
- parser and adapter helpers.

It should not contain workflow state persistence, n8n Data Table persistence, LLM provider orchestration, or infl0 feed ranking logic.

## n8n Layer

n8n remains responsible for scheduling, table access, branching, LLM nodes, batching, retries, HTTP calls to infl0 and operational visibility.

## Success Criteria

- The dispatcher starts only due sources.
- Known old RSS or podcast episodes do not trigger detail fetches.
- HTML sources with valid configuration can run productively.
- Long documents can be split into stable infl0 items.
- New source families can be added through adapters.
- infl0 receives source health data for user and operator views.
- n8n remains debuggable through small, explicit steps.
- The workflow is documented well enough to be ported to another orchestrator later.
