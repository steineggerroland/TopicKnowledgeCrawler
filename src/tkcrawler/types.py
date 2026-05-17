"""TypedDict contracts for portable step item payloads (IDE and documentation)."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class NormalizedSourceItem(TypedDict, total=False):
    crawl_key: str
    url: str
    name: str
    type: str
    active: bool
    source_status: str
    subscriber_count: int
    configuration_json: str


class PlanDispatchItem(TypedDict, total=False):
    crawl_key: str
    should_dispatch: bool
    dispatch_reason: str
    next_allowed_crawl_at: str | None
    effective_policy: dict[str, Any]


class SourceHealthItem(TypedDict, total=False):
    source_health_status: str
    source_health_reason: str
    source_health_json: str
    operator_attention: bool
    operator_attention_reason: str | None


class CandidatePayload(TypedDict, total=False):
    id: str
    link: str
    title: str | None
    summary: str
    author: str | None
    publishedAt: str | None
    updatedAt: str | None
    item_kind: str
    has_feed_content: bool
    feed_content: str | None


class ArticlePayload(TypedDict, total=False):
    id: str
    link: str
    title: str | None
    summary: str
    author: str | None
    publishedAt: str | None
    updatedAt: str | None
    content_md: str
    item_kind: str
    content_hash: str | None
    source_type: str
    tld: str
    categories: list[str]


class FinalizedItem(TypedDict, total=False):
    crawl_key: str
    source_type: str
    url: str
    article_id: str
    item_id: str
    article: ArticlePayload
    content_hash: str | None
    content_md: str


class Infl0IngestBody(TypedDict):
    crawlKey: str
    id: NotRequired[str]
    title: NotRequired[str | None]
    link: NotRequired[str]
    item_kind: NotRequired[str]
    content_md: NotRequired[str]
    content_hash: NotRequired[str | None]
    source_type: NotRequired[str]
    tld: NotRequired[str]
    teaser: NotRequired[str]
    summary_long: NotRequired[str]
    category: NotRequired[list[str]]
    tags: NotRequired[list[str]]
    seriousness_rating: NotRequired[str]


class BuildIngestBodyItem(TypedDict, total=False):
    crawl_key: str
    article_id: str
    infl0_ingest_body: Infl0IngestBody


class Infl0SourceStatusBody(TypedDict, total=False):
    crawlKey: str
    sourceHealthStatus: str
    sourceHealthReason: str
    name: str
    type: str
    url: str
