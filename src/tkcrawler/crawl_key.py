"""
Gleiche Regeln wie infl0/server/utils/feed-url.ts (Trailing-Slash, kein Fragment, http/https).
"""

from urllib.parse import urlparse, urlunparse


def normalize_feed_url(raw: str) -> str:
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("empty")
    p = urlparse(trimmed)
    if p.scheme.lower() not in ("http", "https"):
        raise ValueError("protocol")
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunparse(
        (
            p.scheme.lower(),
            p.netloc.lower(),
            path,
            p.params,
            p.query,
            "",
        )
    )
