import json
from pathlib import Path

EXAMPLE_DIR = Path(__file__).parents[2] / "docs" / "examples" / "source-status"
SCHEMA_PATH = Path(__file__).parents[2] / "docs" / "schemas" / "source-status.schema.json"
HEALTH_STATUSES = {
    "pending",
    "needs_setup",
    "healthy",
    "quiet",
    "degraded",
    "failing",
    "blocked",
    "paused",
}
SCHEMA_TOP_LEVEL_PROPERTIES = {
    "crawlKey",
    "name",
    "type",
    "url",
    "active",
    "sourceStatus",
    "configurationStatus",
    "sourceHealthStatus",
    "sourceHealthReason",
    "sourceHealth",
    "operatorAttention",
    "operatorAttentionReason",
    "detectedContentType",
    "analysisCheckedAt",
    "analysisError",
    "configurationError",
    "lastDispatchReason",
    "lastCrawlStatus",
    "lastCrawlStartedAt",
    "lastCrawlFinishedAt",
    "lastSuccessfulCrawlAt",
    "lastCrawlError",
    "nextAllowedCrawlAt",
    "crawlTotalCount",
    "crawlCandidateCount",
    "crawlSkippedCount",
    "crawlProcessedCount",
    "crawlFetchErrorCount",
    "crawlUnchangedCount",
    "crawlLlmFailedCount",
    "consecutiveErrorCount",
    "lastCrawlResult",
    "effectivePolicy",
    "detectedPolicy",
    "detectedPolicyCheckedAt",
    "detectedPolicyError",
}


def test_source_status_examples_cover_all_health_statuses():
    files = {path.stem: path for path in EXAMPLE_DIR.glob("*.json")}

    assert set(files) == HEALTH_STATUSES
    for status, path in files.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["crawlKey"]
        assert payload["sourceHealthStatus"] == status
        assert "sourceHealthReason" in payload
        assert "operatorAttention" in payload
        assert "nextAllowedCrawlAt" in payload
        assert "effectivePolicy" in payload
        assert "detectedPolicy" in payload


def test_source_status_examples_have_matching_nested_health_status():
    for path in EXAMPLE_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        nested_health = payload.get("sourceHealth")
        if nested_health is not None:
            assert nested_health["status"] == payload["sourceHealthStatus"]
            assert nested_health["reason"] == payload["sourceHealthReason"]


def test_source_status_schema_matches_example_contract():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == SCHEMA_TOP_LEVEL_PROPERTIES
    assert set(schema["properties"]["sourceHealthStatus"]["enum"]) == HEALTH_STATUSES
    assert set(schema["required"]) == {"crawlKey", "sourceHealthStatus"}

    for path in EXAMPLE_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert set(payload) <= set(schema["properties"]), path.name
