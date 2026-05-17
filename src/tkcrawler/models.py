"""Typed domain models that remain compatible with step dictionaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from tkcrawler.enums import ItemKind, SourceStatus, SourceType


def _without_known(data: Mapping[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key not in known}


def _parse_source_type(value: Any) -> SourceType | str:
    """Parse a known source type; keep unknown values as str for step-level errors."""
    raw = str(value or "").strip()
    if not raw:
        return SourceType.UNKNOWN
    try:
        return SourceType(raw)
    except ValueError:
        return raw


@dataclass(slots=True)
class Source:
    crawl_key: str
    type: SourceType | str
    url: str
    name: str | None = None
    source_status: SourceStatus | str | None = None
    configuration: dict[str, Any] | None = None
    effective_policy: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Source:
        crawl_key = str(row.get("crawl_key") or row.get("crawlKey") or row.get("url") or "")
        url = str(row.get("url") or row.get("feedUrl") or "")
        return cls(
            crawl_key=crawl_key,
            type=_parse_source_type(row.get("type")),
            url=url,
            name=str(row["name"]) if row.get("name") is not None else None,
            source_status=SourceStatus(str(row["source_status"])) if row.get("source_status") else None,
            configuration=dict(row["configuration"]) if isinstance(row.get("configuration"), Mapping) else None,
            effective_policy=dict(row["effective_policy"]) if isinstance(row.get("effective_policy"), Mapping) else None,
            extra=_without_known(
                row,
                {
                    "crawl_key",
                    "crawlKey",
                    "type",
                    "url",
                    "feedUrl",
                    "name",
                    "source_status",
                    "configuration",
                    "effective_policy",
                },
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.extra)
        out.update({
            "crawl_key": self.crawl_key,
            "type": str(self.type),
            "url": self.url,
        })
        if self.name is not None:
            out["name"] = self.name
        if self.source_status is not None:
            out["source_status"] = str(self.source_status)
        if self.configuration is not None:
            out["configuration"] = dict(self.configuration)
        if self.effective_policy is not None:
            out["effective_policy"] = dict(self.effective_policy)
        return out


@dataclass(slots=True)
class Candidate:
    id: str
    link: str
    title: str | None = None
    item_kind: ItemKind | str = ItemKind.ARTICLE
    summary: str = ""
    author: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Candidate:
        return cls(
            id=str(row.get("id") or row.get("item_id") or row.get("article_id") or ""),
            link=str(row.get("link") or ""),
            title=str(row["title"]) if row.get("title") is not None else None,
            item_kind=ItemKind(str(row.get("item_kind") or ItemKind.ARTICLE)),
            summary=str(row.get("summary") or ""),
            author=str(row["author"]) if row.get("author") is not None else None,
            published_at=str(row["publishedAt"]) if row.get("publishedAt") is not None else None,
            updated_at=str(row["updatedAt"]) if row.get("updatedAt") is not None else None,
            extra=_without_known(
                row,
                {"id", "item_id", "article_id", "link", "title", "item_kind", "summary", "author", "publishedAt", "updatedAt"},
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.extra)
        out.update({
            "id": self.id,
            "link": self.link,
            "title": self.title,
            "summary": self.summary,
            "author": self.author,
            "publishedAt": self.published_at,
            "updatedAt": self.updated_at,
            "item_kind": str(self.item_kind),
        })
        return out


@dataclass(slots=True)
class Article:
    id: str
    link: str
    content_md: str
    title: str | None = None
    item_kind: ItemKind | str = ItemKind.ARTICLE
    summary: str = ""
    author: str | None = None
    published_at: str | None = None
    updated_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> Article:
        return cls(
            id=str(row.get("id") or row.get("item_id") or row.get("article_id") or ""),
            link=str(row.get("link") or ""),
            content_md=str(row.get("content_md") or ""),
            title=str(row["title"]) if row.get("title") is not None else None,
            item_kind=ItemKind(str(row.get("item_kind") or ItemKind.ARTICLE)),
            summary=str(row.get("summary") or ""),
            author=str(row["author"]) if row.get("author") is not None else None,
            published_at=str(row["publishedAt"]) if row.get("publishedAt") is not None else None,
            updated_at=str(row["updatedAt"]) if row.get("updatedAt") is not None else None,
            extra=_without_known(
                row,
                {"id", "item_id", "article_id", "link", "content_md", "title", "item_kind", "summary", "author", "publishedAt", "updatedAt"},
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.extra)
        out.update({
            "id": self.id,
            "link": self.link,
            "title": self.title,
            "summary": self.summary,
            "author": self.author,
            "publishedAt": self.published_at,
            "updatedAt": self.updated_at,
            "content_md": self.content_md,
            "item_kind": str(self.item_kind),
        })
        return out
