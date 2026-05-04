from __future__ import annotations

from typing import Any, Mapping

from crawler.fetchers.html_fetcher import HtmlFetcher
from crawler.utils import text_processor
from tkcrawler.steps._runtime import StepError, ok, split_input


def _markdown_from_feed_content(candidate: Mapping[str, Any]) -> str:
    title = candidate.get("title") or ""
    feed_content = candidate.get("feed_content") or candidate.get("summary") or ""
    if not feed_content:
        raise StepError("missing_feed_content", "Candidate has no feed content")

    markdown = text_processor.convert_from_html_to_markdown(f"<html><body>{feed_content}</body></html>")
    if not markdown:
        markdown = str(feed_content)
    if title:
        return f"# {title}\n\n{markdown}"
    return markdown


def fetch_detail_item(row: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    candidate = row.get("candidate")
    if not isinstance(candidate, Mapping):
        raise StepError("missing_candidate", "Item needs candidate object")

    decision = row.get("candidate_decision")
    if decision and decision != "fetch":
        raise StepError(
            "candidate_not_fetchable",
            f"Candidate decision is not fetch: {decision}",
            {"candidate_decision": decision},
        )

    link = str(candidate.get("link") or "").strip()
    if not link:
        raise StepError("missing_link", "Candidate needs link")

    source_type = str(row.get("source_type") or row.get("type") or "").strip()
    item_kind = str(candidate.get("item_kind") or "article")
    verify = context.get("verify", row.get("verify", True))
    headers = context.get("headers")
    if not isinstance(headers, Mapping):
        headers = {}
    policy = row.get("effective_policy")
    if isinstance(policy, Mapping):
        policy_headers = policy.get("request_headers")
        if isinstance(policy_headers, Mapping):
            headers = {**{str(k): str(v) for k, v in policy_headers.items()}, **dict(headers)}
        user_agent = policy.get("user_agent")
        if user_agent and "User-Agent" not in headers:
            headers = {**dict(headers), "User-Agent": str(user_agent)}

    if source_type == "rss+podcast" and candidate.get("has_feed_content"):
        content_md = _markdown_from_feed_content(candidate)
    elif candidate.get("has_feed_content") and row.get("prefer_feed_content"):
        content_md = _markdown_from_feed_content(candidate)
    else:
        content_md = HtmlFetcher.generate_markdown_from_url(link, verify=verify, headers=dict(headers))

    article = {
        "id": candidate.get("id") or row.get("article_id") or row.get("item_id"),
        "title": candidate.get("title"),
        "link": link,
        "summary": candidate.get("summary", ""),
        "author": candidate.get("author"),
        "publishedAt": candidate.get("publishedAt"),
        "updatedAt": candidate.get("updatedAt"),
        "content_md": content_md,
        "item_kind": item_kind,
    }
    if candidate.get("categories") is not None:
        article["categories"] = candidate.get("categories")

    return {
        **dict(row),
        "article_id": article["id"],
        "item_id": article["id"],
        "article": article,
        "content_md": content_md,
        "fetch_detail_error": None,
    }


def fetch_detail_step(payload: Mapping[str, Any]) -> dict[str, Any]:
    item, context = split_input(payload)
    return ok(fetch_detail_item(item, context))
