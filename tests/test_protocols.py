from __future__ import annotations

from tkcrawler.models import Article, Candidate, Source
from tkcrawler.protocols import Fetcher


class DummyFetcher:
    def list_candidates(self, source: Source) -> list[Candidate]:
        return [Candidate(id="a1", link=source.url)]

    def fetch_detail(self, source: Source, candidate: Candidate) -> Article:
        return Article(id=candidate.id, link=candidate.link, content_md="# Body")


def test_fetcher_protocol_accepts_structural_adapter():
    fetcher: Fetcher = DummyFetcher()
    source = Source.from_mapping({"type": "rss", "url": "https://example.com/feed"})

    candidate = fetcher.list_candidates(source)[0]
    article = fetcher.fetch_detail(source, candidate)

    assert candidate.id == "a1"
    assert article.content_md == "# Body"
