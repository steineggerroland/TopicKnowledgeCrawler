from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass
class StepError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None


def split_input(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (item, context), tolerating a raw item without an envelope."""
    if "item" in payload or "context" in payload:
        item = payload.get("item") or {}
        context = payload.get("context") or {}
    else:
        item = payload
        context = {}
    if not isinstance(item, Mapping):
        raise StepError("invalid_input", "Input item must be an object")
    if not isinstance(context, Mapping):
        raise StepError("invalid_input", "Input context must be an object")
    return dict(item), dict(context)


def ok(items: list[dict[str, Any]] | dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(items, dict):
        out_items = [items]
    else:
        out_items = items
    return {"ok": True, "items": out_items, "meta": meta or {}}


def fail(error: StepError, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "items": [],
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details or {},
        },
        "meta": meta or {},
    }


def parse_json_object(value: Any, *, field: str) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise StepError("invalid_json", f"{field} must be valid JSON", {"field": field}) from exc
        if not isinstance(parsed, Mapping):
            raise StepError("invalid_json", f"{field} must be a JSON object", {"field": field})
        return dict(parsed)
    raise StepError("invalid_json", f"{field} must be an object or JSON string", {"field": field})


def run_safely(step, payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return step(payload)
    except StepError as exc:
        return fail(exc)
