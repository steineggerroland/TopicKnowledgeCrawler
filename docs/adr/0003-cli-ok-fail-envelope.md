# ADR 0003: Use ok/fail Envelope Format for CLI Steps

## Status

Accepted

## Context

The same step functions need to run in n8n, local scripts and subprocess-based tests. Raw Python exceptions are useful internally but awkward for shell callers and workflow nodes that need structured error handling.

The input side also needs to support both a raw item and an explicit `{ "item": ..., "context": ... }` envelope.

## Decision

Expose CLI step results as a JSON envelope:

```json
{
  "ok": true,
  "items": [],
  "meta": {}
}
```

Failures use the same top-level shape with an `error` object:

```json
{
  "ok": false,
  "items": [],
  "error": {
    "code": "invalid_input",
    "message": "Input item must be an object",
    "details": {}
  },
  "meta": {}
}
```

`StepError` is the structured exception type that maps internal step failures into this envelope.

## Consequences

- CLI callers can branch on `ok` and `error.code` without parsing stderr.
- Tests can assert stable error contracts.
- n8n can keep using item-level functions directly, while custom runners can use the envelope boundary.
- New steps should preserve this shape unless a future ADR replaces it.
