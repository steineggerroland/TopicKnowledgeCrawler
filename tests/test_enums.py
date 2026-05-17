"""Tests for tkcrawler.enums – domain enums are StrEnum and JSON-safe."""

from __future__ import annotations

import json

from tkcrawler.enums import (
    CandidateDecision,
    ConfigurationStatus,
    CrawlStatus,
    ItemKind,
    SourceHealthStatus,
    SourceStatus,
    SourceType,
)


class TestStrEnumBehavior:
    """All enums are StrEnum, so they must compare equal to their string value
    and serialize to JSON without conversion."""

    def test_source_type_is_string(self):
        assert SourceType.RSS == "rss"
        assert SourceType.PODCAST == "rss+podcast"
        assert SourceType.HTML == "html"
        assert SourceType.UNKNOWN == "unknown"

    def test_source_status_is_string(self):
        assert SourceStatus.READY == "ready"
        assert SourceStatus.NEEDS_ANALYSIS == "needs_analysis"
        assert SourceStatus.ANALYSIS_FAILED == "analysis_failed"
        assert SourceStatus.CONFIGURATION_INVALID == "configuration_invalid"
        assert SourceStatus.NEEDS_VALIDATION == "needs_validation"

    def test_configuration_status_is_string(self):
        assert ConfigurationStatus.VALID == "valid"
        assert ConfigurationStatus.INVALID == "invalid"
        assert ConfigurationStatus.MISSING == "missing"
        assert ConfigurationStatus.GENERATED == "generated"

    def test_source_health_status_is_string(self):
        assert SourceHealthStatus.HEALTHY == "healthy"
        assert SourceHealthStatus.PENDING == "pending"
        assert SourceHealthStatus.FAILING == "failing"
        assert SourceHealthStatus.BLOCKED == "blocked"
        assert SourceHealthStatus.PAUSED == "paused"
        assert SourceHealthStatus.DEGRADED == "degraded"
        assert SourceHealthStatus.QUIET == "quiet"
        assert SourceHealthStatus.NEEDS_SETUP == "needs_setup"

    def test_candidate_decision_is_string(self):
        assert CandidateDecision.FETCH == "fetch"
        assert CandidateDecision.SKIP_TOO_OLD == "skip_too_old"
        assert CandidateDecision.FETCH_FAILED == "fetch_failed"

    def test_crawl_status_is_string(self):
        assert CrawlStatus.SUCCESS == "success"
        assert CrawlStatus.FAILED == "failed"
        assert CrawlStatus.PARTIAL_FAILED == "partial_failed"
        assert CrawlStatus.RUNNING == "running"

    def test_item_kind_is_string(self):
        assert ItemKind.ARTICLE == "article"
        assert ItemKind.EPISODE == "episode"
        assert ItemKind.SECTION == "section"


class TestJsonSerialization:
    """Enum values must survive JSON round-trips since the step pipeline
    communicates through JSON dicts."""

    def test_enum_in_dict_serializes_to_plain_string(self):
        data = {
            "source_status": SourceStatus.READY,
            "type": SourceType.RSS,
            "item_kind": ItemKind.ARTICLE,
        }
        serialized = json.dumps(data)
        deserialized = json.loads(serialized)
        assert deserialized["source_status"] == "ready"
        assert deserialized["type"] == "rss"
        assert deserialized["item_kind"] == "article"

    def test_enum_in_set_membership(self):
        assert "rss" in {SourceType.RSS, SourceType.PODCAST}
        assert SourceType.RSS in {"rss", "rss+podcast"}

    def test_enum_in_f_string(self):
        assert f"status: {SourceStatus.READY}" == "status: ready"
