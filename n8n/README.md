# TopicKnowledgeCrawler → n8n

Orchestrierung mit **n8n**: Quellen in einer **Data Table**, Zwischenstände in einer zweiten Tabelle (statt `data/summary_history.json`), **AI Nodes** für Zusammenfassung/Kategorien, **Python Code Nodes** für Fetch und infl0-Payload.

## Kurzstart

1. Data Tables anlegen → [`docs/DATA_TABLES.md`](docs/DATA_TABLES.md)
2. Workflow skizzieren → [`docs/WORKFLOW.md`](docs/WORKFLOW.md)
3. AI-Prompts → [`docs/AI_PROMPTS.md`](docs/AI_PROMPTS.md)
4. Python-Skripte → [`python/README.md`](python/README.md)
5. Workflow-Template importieren → [`workflows/crawl_to_infl0.template.json`](workflows/crawl_to_infl0.template.json)
6. Docker/n8n: Crawler einbinden → [`DOCKER_CRAWLER.md`](DOCKER_CRAWLER.md) und [`docker-compose.server.example.yaml`](docker-compose.server.example.yaml)
7. `requirements-n8n.txt` im **Python-Runner-Image** installieren (siehe `DOCKER_CRAWLER.md`).

## Python-Module im Repo

`src/crawler/n8n_compat/` (Untermodule importieren, kein schwerer Import über `__init__`):

- `crawl_key.normalize_feed_url` – analog infl0 `feed-url.ts`
- `datatable.row_to_source` – Data-Table-Zeile → Dict wie `sources.json`
- `fetch.fetch_entries_for_source` – `RssFetcher` / `HtmlFetcher` / `PodcastFetcher`
- `infl0_payload.finalize_entry_metadata` / `build_ingest_body` – `POST /api/crawler/ingest`

Tests: `pytest tests/test_n8n_compat.py`

## Lokaler Legacy-Pfad

`python src/crawler/collector.py` und `summarizer.py` bleiben für lokale Läufe ohne n8n; für reine n8n-Betriebsweise entfällt die Nutzung von `summary_history.json`, wenn die Data Table `article_enrichment` die gleiche Rolle übernimmt.
