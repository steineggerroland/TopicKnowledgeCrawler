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
8. Python-Runner-Allowlist & `pip install -e` → [`docs/PYTHON_RUNNER_ALLOWLIST.md`](docs/PYTHON_RUNNER_ALLOWLIST.md).

## Python-Module im Repo

Paket **`tkcrawler`** unter `src/tkcrawler/` (installiert mit Root-`pyproject.toml`):

- `tkcrawler.crawl_key.normalize_feed_url` – analog infl0 `feed-url.ts`
- `tkcrawler.datatable.row_to_source` – Data-Table-Zeile → Dict wie `sources.json`
- `tkcrawler.fetch.fetch_entries_for_source` – nutzt Paket **`crawler`** (`src/crawler/…`)
- `tkcrawler.infl0_payload` – `POST /api/crawler/ingest`

Tests: `pytest tests/test_tkcrawler.py`

## Lokaler Legacy-Pfad

`python src/crawler/collector.py` und `summarizer.py` bleiben für lokale Läufe ohne n8n; für reine n8n-Betriebsweise entfällt die Nutzung von `summary_history.json`, wenn die Data Table `article_enrichment` die gleiche Rolle übernimmt.
