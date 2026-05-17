from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    RSS = "rss"
    PODCAST = "rss+podcast"
    HTML = "html"
    UNKNOWN = "unknown"


class SourceStatus(StrEnum):
    READY = "ready"
    NEEDS_ANALYSIS = "needs_analysis"
    NEEDS_VALIDATION = "needs_validation"
    ANALYSIS_FAILED = "analysis_failed"
    CONFIGURATION_INVALID = "configuration_invalid"


class ConfigurationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    GENERATED = "generated"


class SourceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    PENDING = "pending"
    QUIET = "quiet"
    DEGRADED = "degraded"
    FAILING = "failing"
    BLOCKED = "blocked"
    PAUSED = "paused"
    NEEDS_SETUP = "needs_setup"


class CandidateDecision(StrEnum):
    FETCH = "fetch"
    SKIP_TOO_OLD = "skip_too_old"
    FETCH_FAILED = "fetch_failed"


class CrawlStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_FAILED = "partial_failed"
    RUNNING = "running"


class ItemKind(StrEnum):
    ARTICLE = "article"
    EPISODE = "episode"
    SECTION = "section"
