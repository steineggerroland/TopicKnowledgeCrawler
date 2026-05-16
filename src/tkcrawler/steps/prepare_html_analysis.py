from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from tkcrawler.enums import ConfigurationStatus, SourceStatus, SourceType
from tkcrawler.steps._headers import request_headers
from tkcrawler.steps._runtime import StepError, ok, split_input

DEFAULT_MAX_HTML_CHARS = 30000


def prepare_html_analysis_item(
    row: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    url = str(row.get("url") or row.get("feedUrl") or "").strip()
    if not url:
        raise StepError("missing_url", "Source needs url or feedUrl")

    timeout = float(context.get("timeout_seconds", row.get("timeout_seconds", 10)))
    verify = context.get("verify", row.get("verify", True))
    max_chars = int(context.get("max_html_chars", DEFAULT_MAX_HTML_CHARS))
    now = str(context.get("now") or datetime.now(UTC).isoformat())

    try:
        response = requests.get(
            url,
            timeout=timeout,
            verify=verify,
            headers=request_headers(row, context),
        )
        response.raise_for_status()
    except Exception as exc:
        return {
            **dict(row),
            "source_status": SourceStatus.ANALYSIS_FAILED,
            "analysis_error": str(exc),
            "analysis_checked_at": now,
        }

    compact_html = _compact_html(response.text, max_chars=max_chars)
    return {
        **dict(row),
        "type": SourceType.HTML,
        "source_status": SourceStatus.NEEDS_ANALYSIS,
        "configuration_status": ConfigurationStatus.MISSING,
        "analysis_error": None,
        "analysis_checked_at": now,
        "html_analysis_url": url,
        "html_analysis_input": compact_html,
        "html_analysis_prompt": _prompt(url, compact_html),
    }


def _compact_html(html: str, *, max_chars: int) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    compact = re.sub(r"\s+", " ", str(soup)).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars]


def _prompt(url: str, html: str) -> str:
    return f"""Analyze this HTML listing page and identify CSS selectors for article discovery.

Return valid JSON only, without markdown fences, in exactly this shape:
{{
  "article_selector": "CSS selector matching each repeated article/listing item",
  "main_page_anchor_selector": "CSS selector, relative to each article item, matching the <a> element for the article detail page",
  "confidence": "high|medium|low",
  "notes": "short explanation"
}}

Rules:
- Prefer short structural selectors.
- The anchor selector must match an <a> element, not a child heading.
- You may use :has(...) when it makes the selector simpler.
- Do not rely on tracking query parameters or unique article URLs.
- If no articles are found, return empty selector strings and confidence "low".

URL: {url}

HTML:
```html
{html}
```"""


def prepare_html_analysis_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(prepare_html_analysis_item(item, context))
