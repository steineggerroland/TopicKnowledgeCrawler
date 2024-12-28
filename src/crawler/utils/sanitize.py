import re


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
    cleaned_content = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw_content.strip())
    return cleaned_content