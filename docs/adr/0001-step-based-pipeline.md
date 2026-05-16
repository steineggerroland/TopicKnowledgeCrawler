# ADR 0001: Replace Standalone Crawler With Step-Based Pipeline

## Status

Accepted

## Context

TopicKnowledgeCrawler started as a standalone crawler. infl0 now needs a crawler layer that can be orchestrated by n8n, tested locally and reused from plain Python without duplicating parser and policy logic.

The old standalone mode also encouraged local filesystem state such as `data/raw` and `data/processed`. The current system sends normalized payloads to infl0 APIs instead.

## Decision

Use a step-based pipeline under `tkcrawler.steps` as the canonical implementation. Each step owns one explicit part of the crawl flow, accepts plain dictionaries at the boundary and returns a portable result envelope for CLI use.

The reference Python composition lives in `tkcrawler.pipeline`. Production orchestration can run the same steps from n8n Python Code nodes.

## Consequences

- Steps are small enough to test with mocked network and filesystem side effects.
- The same behavior can run from n8n, the CLI or plain Python.
- Workflow state and scheduling stay outside the parser/extraction modules.
- Adding a source family means adding focused candidate/fetch behavior rather than rebuilding the whole crawler.
