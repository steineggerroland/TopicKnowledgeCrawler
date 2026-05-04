from __future__ import annotations

import hashlib
from typing import Any, Mapping


def request_headers(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, str]:
    context = context or {}
    headers: dict[str, str] = {}

    policy = row.get("effective_policy")
    if isinstance(policy, Mapping):
        headers.update(_string_mapping(policy.get("request_headers")))
        user_agent = _select_user_agent(policy, row)
        if user_agent:
            headers["User-Agent"] = user_agent
        contact = policy.get("contact")
        if contact:
            headers.setdefault("From", str(contact))
            headers.setdefault("X-Infl0-Contact", str(contact))
        crawler_name = policy.get("crawler_name")
        if crawler_name:
            headers.setdefault("X-Infl0-Crawler", str(crawler_name))

    headers.update(_string_mapping(context.get("headers")))
    return headers


def _string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def _select_user_agent(policy: Mapping[str, Any], row: Mapping[str, Any]) -> str | None:
    user_agent = policy.get("user_agent")
    if user_agent:
        return str(user_agent)

    user_agents = policy.get("user_agents")
    if not isinstance(user_agents, list):
        return None

    candidates = [str(agent) for agent in user_agents if agent]
    if not candidates:
        return None

    key = str(row.get("crawl_key") or row.get("url") or "")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(candidates)
    return candidates[index]
