import re


def sanitize_string(value: str):
    """
    Escapes and sanitizes a string to make it safe for filenames.
    Removes invalid characters and replaces spaces or separators with '_'.
    """
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
