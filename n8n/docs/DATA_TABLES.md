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

**Workflow:** Schedule / Webhook → **Get rows** (`active = true`) → ein Item pro Zeile → Python „Fetch & expand“.

Der **`crawl_key`** muss exakt zu `user_feeds.crawl_key` in infl0 passieren (Nutzer trägt dieselbe Feed-URL ein).

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
