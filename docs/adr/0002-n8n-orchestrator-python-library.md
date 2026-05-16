# ADR 0002: Use n8n as Orchestrator and Python as Library

## Status

Accepted

## Context

The production workflow needs scheduling, table access, branching, batching, retries, LLM nodes, HTTP calls to infl0 and operational visibility. n8n already provides those orchestration features.

Python is strongest here as a deterministic crawler library: URL normalization, policy inspection, candidate extraction, detail fetching, payload construction and testable business rules.

## Decision

Keep n8n as the production orchestrator. Keep Python as an installable library and CLI surface that exposes portable crawler steps.

LLM enrichment remains in n8n AI nodes. The Python package does not depend on an LLM provider to run tests or crawler steps.

## Consequences

- n8n workflows remain debuggable through explicit small nodes.
- Python code remains easy to test without n8n internals.
- Provider-specific AI behavior does not leak into the crawler package.
- The abstract workflow must stay documented so another orchestrator could implement the same contracts later.
