# n8n Data Tables (statt `data/summary_history.json`)

Die bisherige Datei `summary_history.json` hielt pro Artikel den letzten `content_hash` und die LLM-Felder. In n8n legst du dafür **eine oder zwei Tabellen** an und nutzt die Nodes **Data table → Get row** / **Insert or update row**.

## Tabelle `crawl_sources` (was gecrawlt wird)

| Spalte | Typ | Beschreibung |
|--------|-----|----------------|
| `name` | String | Anzeigename |
| `type` | String | `rss`, `html` oder `rss+podcast` (wie `config/sources.json`) |
| `url` | String | Feed-URL bzw. Listing-URL |
| `configuration_json` | String, optional | JSON-String mit `article_selector` und `main_page_anchor_selector` für `type: html` |
| `crawl_key` | String, optional | Wenn leer: im Workflow mit dem gleichen Algorithmus wie infl0 aus `url` berechnen (`normalize_feed_url`) |
| `active` | Boolean, optional | `true` = verarbeiten |
| `source_status` | String, optional | `new`, `ready`, `needs_analysis`, `analysis_failed`, `configuration_invalid`, `inactive` |
| `analysis_error` | String, optional | Letzter Fehler aus Typ-/Source-Analyse |
| `analysis_checked_at` | DateTime/String, optional | Wann die Quelle zuletzt analysiert wurde |
| `configuration_status` | String, optional | `missing`, `valid`, `invalid`, `generated` |
| `configuration_error` | String, optional | Letzter Fehler aus HTML-Selector-Validierung |
| `subscriber_count` | Number, optional | Anzahl Abonnenten aus infl0, falls geliefert |
| `last_seen_in_infl0_at` | DateTime/String, optional | Letzter erfolgreicher Sync aus infl0 |
| `effective_policy_json` | String, optional | Zusammengefuehrte Policy aus Defaults, manueller Policy und erkannten Hinweisen |
| `detected_policy_json` | String, optional | Automatisch erkannte Hinweise wie RSS `ttl`, HTTP Cache-Header, `Retry-After` |
| `next_allowed_crawl_at` | DateTime/String, optional | Fruehester Zeitpunkt fuer den naechsten Crawl |
| `last_crawl_started_at` | DateTime/String, optional | Startzeit des letzten Crawl-Laufs |
| `last_crawl_finished_at` | DateTime/String, optional | Endzeit des letzten Crawl-Laufs |
| `last_crawl_status` | String, optional | `running`, `success`, `failed`, `skipped` |
| `last_crawl_error` | String, optional | Letzter Crawl-Fehler |
| `last_dispatch_reason` | String, optional | Warum der Dispatcher die Quelle gestartet oder uebersprungen hat |

**Workflow:** Schedule / Webhook → **Get rows** (`active = true`) → ein Item pro Zeile → Python „Fetch & expand“.

Der **`crawl_key`** muss exakt zu `user_feeds.crawl_key` in infl0 passieren (Nutzer trägt dieselbe Feed-URL ein).

### Quellen aus infl0 synchronisieren

infl0 stellt **`GET /api/crawler/sources`** bereit (wie Ingest: **`X-Crawler-Key`** oder **`Authorization: Bearer`** mit `NUXT_CRAWLER_API_KEY`).

Antwort (Auszug): `sources[]` mit `crawlKey`, `feedUrl`, `displayTitle`, `subscriberCount`.

**Mapping in n8n** (Data Table `crawl_sources`):

| infl0-Feld | Tabellenspalte |
|------------|----------------|
| `crawlKey` | `crawl_key` |
| `feedUrl` | `url` |
| `displayTitle` | `name` (Fallback: `feedUrl` oder `crawlKey`) |
| — | `type` zunächst leer — siehe unten |
| — | `active` = `true` |

**RSS vs. HTML und LLM (wie `SourceAnalyzer`):** infl0 speichert nur die vom Nutzer eingetragene URL — kein MIME-Type. Wie im lokalen `collector.py` solltest du **vor dem Fetch** (oder einmal nach dem Sync) klassifizieren: Request an die URL, anhand von `Content-Type` / Inhalt **`rss`** vs. **`html`** setzen; bei **HTML** ggf. **`configuration_json`** per LLM ermitteln (`crawler.analyzer.source_analyzer.SourceAnalyzer`). Snippet: `n8n/python/code_analyze_source_row.py`.

Workflow-Idee: eigener Trigger (z. B. täglich oder nach Feed-Änderung) → **HTTP Request** GET → **Split out** / Schleife → **Data table → Insert or update row** mit eindeutiger Zeile pro `crawl_key` → **Code (Python)** Analyse für Zeilen ohne vollständigen `type`/`configuration` → erneut **Insert or update row**. Feeds, die Nutzer in infl0 deaktivieren (`active: false`), erscheinen nicht mehr in der Liste — bestehende Tabellenzeilen musst du ggf. separat auf `active = false` setzen oder löschen, wenn du die Tabelle strikt spiegeln willst.

Der aktuelle Source-Sync und die geplante robustere Aufteilung sind in [`SOURCE_SYNC_WORKFLOW.md`](SOURCE_SYNC_WORKFLOW.md) beschrieben. Wichtig: Quellen sollten erst nach einem erfolgreichen Sync-Lauf deaktiviert werden, nicht schon vor dem HTTP-Request, damit ein Teilfehler nicht versehentlich alle Quellen inaktiv setzt.

Der Crawl-Dispatch-Workflow, der aktive/faellige Quellen aus dieser Tabelle an den eigentlichen Crawl-Workflow uebergibt, ist in [`CRAWL_DISPATCH_WORKFLOW.md`](CRAWL_DISPATCH_WORKFLOW.md) beschrieben.

## Tabelle `article_enrichment` (ersetzt Summary-History)

| Spalte | Typ | Beschreibung |
|--------|-----|----------------|
| `article_id` | String, **unique** | Gleich wie `entry.id` aus dem Crawler (SHA256) |
| `content_hash` | String | Hash über `content_md` (wie bisher `content_hash` im JSON) |
| `teaser` | String | |
| `summary_long` | String/Text | |
| `category_json` | String | JSON-Array von Kategorien |
| `tags_json` | String | JSON-Array von Tags |
| `seriousness_rating` | String | `high` / `medium` / `low` |
| `updated_at` | String | ISO-Zeitstempel |

**Skip-Logik (wie alter Summarizer):** Vor dem AI-Node **Get row** mit `article_id`. Wenn Zeile existiert und `content_hash` = aktueller Hash → Branch „kein LLM“ und gespeicherte Felder an den HTTP-Request anreichern. Sonst → AI-Node → **Insert or update row**.

Rohartikel (`data/raw/…`) musst du in n8n **nicht** spiegeln, wenn du jeden Lauf nur über die Data Table und den HTTP-Body an infl0 führst. Optional kannst du zusätzlich eine Tabelle `crawl_runs` für Debugging pflegen.
