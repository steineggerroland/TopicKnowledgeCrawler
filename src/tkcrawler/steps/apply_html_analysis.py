from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping

from tkcrawler.steps._runtime import StepError, ok, split_input


def apply_html_analysis_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    now = str(context.get("now") or datetime.now(timezone.utc).isoformat())

    try:
        analysis = _analysis_object(row)
        configuration = _configuration_from_analysis(analysis)
    except StepError as exc:
        return {
            **dict(row),
            "source_status": "configuration_invalid",
            "configuration_status": "invalid",
            "configuration_error": exc.message,
            "configuration_checked_at": now,
        }

    return {
        **dict(row),
        "type": "html",
        "source_status": "needs_validation",
        "configuration_json": json.dumps(configuration, ensure_ascii=False),
        "configuration_status": "generated",
        "configuration_error": None,
        "configuration_checked_at": now,
        "html_analysis_confidence": analysis.get("confidence"),
        "html_analysis_notes": analysis.get("notes"),
    }


def _analysis_object(row: Mapping[str, Any]) -> dict[str, Any]:
    for name in ("html_analysis_result", "output", "text", "response"):
        value = row.get(name)
        if value is None or value == "":
            continue
        if isinstance(value, Mapping):
            return dict(value)
        if isinstance(value, str):
            return _parse_json_text(value)
    raise StepError("missing_html_analysis_result", "Item needs html_analysis_result or LLM output")


def _parse_json_text(value: str) -> dict[str, Any]:
    text = value.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise StepError("invalid_html_analysis_json", "LLM output must be valid JSON") from exc
    if not isinstance(parsed, Mapping):
        raise StepError("invalid_html_analysis_json", "LLM output must be a JSON object")
    return dict(parsed)


def _configuration_from_analysis(analysis: Mapping[str, Any]) -> dict[str, str]:
    article_selector = str(analysis.get("article_selector") or "").strip()
    anchor_selector = str(
        analysis.get("main_page_anchor_selector")
        or analysis.get("anchor_selector")
        or ""
    ).strip()
    if not article_selector or not anchor_selector:
        raise StepError(
            "invalid_html_analysis_selectors",
            "LLM output needs article_selector and main_page_anchor_selector",
        )
    return {
        "article_selector": article_selector,
        "main_page_anchor_selector": anchor_selector,
    }


def apply_html_analysis_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(apply_html_analysis_item(item, context))
