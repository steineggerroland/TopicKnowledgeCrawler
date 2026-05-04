# n8n-Workflow (Überblick)

## Ziele

- **Quellen** aus einer n8n **Data Table** (oder manuell/Webhook) statt nur `sources.json`.
- **Zwischenstände** in Data Tables statt `summary_history.json`.
- **Sprachmodell** in n8n **AI Nodes**, nicht mehr `summarizer.py` / `LlmPrompter` zur Laufzeit.
- **Auslieferung** an infl0 mit `POST /api/crawler/ingest` und Header `X-Crawler-Key` / `Authorization: Bearer`.

## Quellen aus infl0 (optional, vor dem Crawl)

- **HTTP Request** – `GET {{$env.INFL0_BASE_URL}}/api/crawler/sources`, Header wie bei Ingest (`X-Crawler-Key`).
- Ergebnis in die Data Table **`crawl_sources`** schreiben (Insert or update pro `crawl_key`), siehe `DATA_TABLES.md` → Abschnitt „Quellen aus infl0 synchronisieren“.
- **Anschließend** (oder für jede neue Zeile): wie lokal `SourceAnalyzer` — **`type`** (`rss` / `html`) und bei HTML **`configuration_json`** setzen (`n8n/python/code_analyze_source_row.py`), damit `code_fetch_expand.py` / `row_to_source` zuverlässig arbeiten.

Der konkrete Source-Sync-/SourceAnalyzer-Workflow ist in [`SOURCE_SYNC_WORKFLOW.md`](SOURCE_SYNC_WORKFLOW.md) als Ist-Zustand und Zielstruktur dokumentiert.

## Empfohlene Node-Kette

Die aktuelle produktive Variante und die geplante Zerlegung des grossen `Python: Fetch + Expand`-Schritts sind in [`CURRENT_WORKFLOW_MIGRATION.md`](CURRENT_WORKFLOW_MIGRATION.md) dokumentiert.

Der vorgelagerte Workflow, der aktive Quellen aus `crawl_sources` liest und den Crawl-Workflow pro Quelle triggert, ist in [`CRAWL_DISPATCH_WORKFLOW.md`](CRAWL_DISPATCH_WORKFLOW.md) dokumentiert. Dort gehoert die Intervall- und Rate-Limit-Entscheidung hin.

1. **Trigger** – Schedule (z. B. stündlich) oder Webhook „Run crawl“.
2. **Data table → Get rows** – Tabelle `crawl_sources`, Filter `active` (wie von dir definiert).
3. **Code (Python)** – `code_normalize_crawl_key.py` oder direkt `code_fetch_expand.py` (siehe `n8n/python/`).
4. **Split in Batches** – optional, um Speicher/Timeouts zu begrenzen.
5. **Data table → Get row** – Lookup in `article_enrichment` mit `article_id` (= `json.article.id`).
6. **IF** – `exists($json.content_hash_match)` bzw. Vergleich Hash aus DB mit aktuellem Artikel-Hash.
   - **true:** Enrichment aus der Zeile übernehmen, AI überspringen.
   - **false:** Weiter zu AI.
7. **AI** – Prompts siehe `AI_PROMPTS.md`.
8. **Code** – JSON parsen, mit Artikel mergen (siehe `code_parse_ai_json.py`).
9. **Data table → Insert or update row** – `article_enrichment` aktualisieren.
10. **HTTP Request** – `POST {{$env.INFL0_BASE_URL}}/api/crawler/ingest`, Body aus `build_ingest_body`, Header mit API-Key.

## Python in n8n

- Repo **auf den n8n-Host mounten** (z. B. `/data/TopicKnowledgeCrawler`).
- **`PYTHONPATH`** = Projektroot (Ordner, der `src/` enthält).
- Im Code-Node: `sys.path.insert(0, "/data/TopicKnowledgeCrawler")` falls keine globale Env-Variable gesetzt ist.
- Im **Docker-Image** von n8n die Pakete aus `n8n/requirements-n8n.txt` installieren.

## Bestehendes Repo

- Crawl-Implementierung: weiterhin `src/crawler/fetchers/*`.
- Paket `tkcrawler` (`src/tkcrawler/`): crawlKey, Data-Table-Zeile → Source, Fetch, infl0-Body; Crawl-Logik bleibt in `crawler` (`src/crawler/`).
- `collector.py` / `summarizer.py` bleiben für **lokale** Läufe nutzbar; n8n ersetzt den Orchestrierungs- und LLM-Teil.
