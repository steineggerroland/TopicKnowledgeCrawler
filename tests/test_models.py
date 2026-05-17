from __future__ import annotations

from tkcrawler.enums import ItemKind, SourceStatus, SourceType
from tkcrawler.models import Article, Candidate, Source


def test_source_round_trips_known_fields_and_extra():
    source = Source.from_mapping({
        "crawlKey": "https://example.com/feed",
        "type": "rss",
        "feedUrl": "https://example.com/feed",
        "source_status": "ready",
        "effective_policy": {"crawl_interval_minutes": 30},
        "custom": "kept",
    })

    assert source.type == SourceType.RSS
    assert source.source_status == SourceStatus.READY
    assert source.to_dict()["custom"] == "kept"
    assert source.to_dict()["crawl_key"] == "https://example.com/feed"


def test_candidate_round_trips_episode_metadata():
    candidate = Candidate.from_mapping({
        "id": "e1",
        "link": "https://example.com/e1",
        "item_kind": "episode",
        "duration_seconds": 123,
    })

    out = candidate.to_dict()
    assert candidate.item_kind == ItemKind.EPISODE
    assert out["duration_seconds"] == 123
    assert out["item_kind"] == "episode"


def test_article_round_trips_content_and_extra():
    article = Article.from_mapping({
        "id": "a1",
        "link": "https://example.com/a1",
        "content_md": "# Title",
        "chapters": [{"start_seconds": 0, "title": "Intro"}],
    })

    out = article.to_dict()
    assert out["content_md"] == "# Title"
    assert out["chapters"] == [{"start_seconds": 0, "title": "Intro"}]
