import json
from pathlib import Path

EXAMPLE_DIR = Path(__file__).parents[2] / "docs" / "examples" / "ingest"
SCHEMA_PATH = Path(__file__).parents[2] / "docs" / "schemas" / "ingest-item.schema.json"
COMMON_FIELDS = {
    "crawlKey",
    "id",
    "item_kind",
    "title",
    "link",
    "summary",
    "author",
    "publishedAt",
    "updatedAt",
    "content_md",
    "source_type",
    "tld",
    "content_hash",
    "parent_item_id",
    "position",
    "teaser",
    "summary_long",
    "category",
    "tags",
    "seriousness_rating",
}
EPISODE_FIELDS = {
    "categories",
    "media_url",
    "media_type",
    "media_length_bytes",
    "duration_seconds",
    "episode_number",
    "season_number",
    "episode_type",
    "explicit",
    "subtitle",
    "image_url",
    "shownotes_md",
    "chapters_url",
    "chapters_type",
    "chapters",
    "chapters_fetch_error",
    "transcript_url",
    "transcript_type",
    "transcript_md",
    "transcript_fetch_error",
}


def _load(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text(encoding="utf-8"))


def test_ingest_examples_are_documented_item_kinds():
    article = _load("article.json")
    episode = _load("episode.json")
    section = _load("section.json")

    assert article["item_kind"] == "article"
    assert episode["item_kind"] == "episode"
    assert section["item_kind"] == "section"
    assert set(article) <= COMMON_FIELDS
    assert set(episode) >= EPISODE_FIELDS
    assert set(section) <= COMMON_FIELDS
    assert section["parent_item_id"]
    assert section["position"] > 0
    assert episode["media_url"]
    assert episode["duration_seconds"] > 0
    assert episode["chapters"][0]["start_seconds"] == 0
    assert episode["chapters"][0]["title"]


def test_ingest_schema_matches_example_contract():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"crawlKey", "id", "title", "link", "item_kind"}
    assert set(schema["properties"]["item_kind"]["enum"]) == {"article", "episode", "section"}

    for path in EXAMPLE_DIR.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert set(payload) <= set(schema["properties"]), path.name
