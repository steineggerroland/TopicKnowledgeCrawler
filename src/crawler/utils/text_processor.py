import hashlib
import re

import trafilatura


def sanitize_string(value: str):
    """
    Escapes and sanitizes a string to make it safe for filenames.
    Removes invalid characters and replaces spaces or separators with '_'.
    """
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)


def clean_json_response(raw_content):
    """
    Cleans the raw content of a response to ensure it's a valid JSON string.
    Handles cases where the response is encapsulated in a code block.
    """
    # Remove triple backticks or any surrounding code block markers
    cleaned_content = re.sub(r"^(.(?<!```))*```(?:json)?\n?|\n?```((?!```).)*$", "", raw_content.strip(), flags=re.S)
    return cleaned_content


def calculate_hash(text):
    """Generates a SHA256 hash for the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def analyze_meta(html):
    return trafilatura.extract(
        html,
        favor_precision=True,
        with_metadata=True,
        include_links=True,
        include_images=True,
        include_formatting=True,
        output_format="json",
    )


def convert_from_html_to_markdown(html_content):
    return trafilatura.extract(
        html_content,
        include_formatting=True,
        include_links=True,
        include_images=True,
        output_format="markdown",
    )
