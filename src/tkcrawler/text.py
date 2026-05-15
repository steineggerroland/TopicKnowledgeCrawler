from __future__ import annotations

import hashlib
import re

import trafilatura


def sanitize_string(value: str) -> str:
    """Return a filename-safe representation of a string."""
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)


def clean_json_response(raw_content: str) -> str:
    """Remove common Markdown code fences around JSON model output."""
    return re.sub(r"^(.(?<!```))*```(?:json)?\n?|\n?```((?!```).)*$", "", raw_content.strip(), flags=re.S)


def calculate_hash(text: str) -> str:
    """Return a SHA256 hash for text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def analyze_meta(html: str) -> str | None:
    return trafilatura.extract(
        html,
        favor_precision=True,
        with_metadata=True,
        include_links=True,
        include_images=True,
        include_formatting=True,
        output_format="json",
    )


def convert_from_html_to_markdown(html_content: str) -> str | None:
    return trafilatura.extract(
        html_content,
        include_formatting=True,
        include_links=True,
        include_images=True,
        output_format="markdown",
    )
