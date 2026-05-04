# Migration des aktuellen n8n-Workflows

Diese Notiz bezieht sich auf den aktuell produktiven Workflow mit `Python: Fetch + Expand`, `Find in history`, AI-Enrichment, `Save article`, `Python: Build infl0 body` und `POST /api/crawler/ingest`.

## Was heute gut funktioniert

- Der Workflow trennt Enrichment und Ingest bereits sauber vom Python-Crawler.
- `infl0-articles` speichert `article_id`, `content_hash`, LLM-Felder, das serialisierte `article` und `is_sent`.
- `Find in history` plus `If nothing changed` spart LLM-Aufrufe, wenn der `content_hash` unveraendert ist.
- `is_sent` verhindert erneutes Senden bereits verarbeiteter unveraenderter Artikel.
- Fehler aus `Python: Fetch + Expand` werden nicht komplett verschluckt, sondern ueber `IF fetch_error` / `Log Fetch Errors` sichtbar.

## Zentrales Problem

`Python: Fetch + Expand` ist derzeit der lange Black-Box-Schritt:

1. Source-Zeile normalisieren.
2. Fetcher auswaehlen.
3. Feed oder HTML-Listing lesen.
4. Fuer viele Eintraege Detailseiten laden.
5. Markdown erzeugen.
6. `content_hash` berechnen.
7. Ein n8n-Item pro Artikel zurueckgeben.

Die spaetere History-Pruefung spart LLM-Zeit, aber nicht die teuren Detailabrufe. Bei RSS-Feeds, die fuer jeden Eintrag eine Detailseite laden, oder bei langen Podcast-Feeds kostet das viel Laufzeit.

## Zielstruktur

Der Workflow sollte den bestehenden Enrichment-/Ingest-Teil behalten, aber den Fetch-Teil davor in kleinere Schritte zerlegen.

Neue Crawl-Vorstufe:

1. `Python: Analyze Source`
2. `Python: Inspect Source Policy`
3. `Python: Plan Crawl`
4. `IF should_crawl`
5. `Python: List Candidates`
6. `Data Table: Find Candidate History`
7. `Python: Filter Candidates`
8. `Split in Batches`
9. `Python: Fetch Detail`
10. `Python: Finalize Article`

Bestehende Enrichment-/Ingest-Stufe:

1. `Find in history`
2. `Merge`
3. `If history entry exists`
4. `If nothing changed`
5. `AI Agent`
6. `Set previous fields`
7. `Save article`
8. `If is_sent`
9. `Python: Build infl0 body`
10. `POST /api/crawler/ingest`
11. optional `Set sent`

Der aktuelle korrigierte Ingest-Pfad nutzt einen kleinen Python-Step zwischen `If is_sent` und `POST /api/crawler/ingest`, weil die Felder je nach Pfad unterschiedlich strukturiert sind. Nach dem AI-Pfad liegen Enrichment-Felder zuerst unter `output.*`; nach `Set previous fields` bzw. aus der Historie liegen `teaser`, `summary_long`, `category`, `tags` und `seriousness_rating` flach auf dem Item. Der Ingest-Builder sollte deshalb das flache Format als kanonischen Input erwarten.

Input fuer `Python: Build infl0 body`:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "article": {
    "id": "sha256...",
    "title": "Article title",
    "content_md": "# Article title\n\n..."
  },
  "teaser": "...",
  "summary_long": "...",
  "category": ["factual information"],
  "tags": ["architecture"],
  "seriousness_rating": "medium"
}
```

Output:

```json
{
  "infl0_ingest_body": {
    "crawlKey": "https://example.com/feed.xml",
    "id": "sha256...",
    "title": "Article title"
  }
}
```

Der Python-Code liest die Enrichment-Felder deshalb direkt aus `j[k]`, nicht aus `j["output"][k]`:

```python
enrichment = {
    k: j[k]
    for k in ("teaser", "summary_long", "category", "tags", "seriousness_rating")
    if k in j and j[k] is not None
}
```

Diese Normalisierung ist wichtig, damit unveraenderte, aber noch nicht gesendete Artikel aus der Historie denselben Ingest-Pfad nutzen koennen wie frisch angereicherte Artikel.

## Neue Python-Node-Vertraege

### `Python: Analyze Source`

Input: eine Source-Zeile aus `crawl_sources` oder ein infl0-Source-Item.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "source": {
    "name": "Example",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "configuration": null
  },
  "source_status": "ready",
  "source_error": null
}
```

Bei HTML sollte `configuration_json` validiert oder erzeugt werden. Fehlt eine gueltige Konfiguration, sollte der Status nicht stillschweigend `ready` sein.

### `Python: Inspect Source Policy`

Input: analysierte Source.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "detected_policy": {
    "rss_ttl_minutes": 60,
    "skip_hours": [],
    "skip_days": [],
    "cache_control": "max-age=3600",
    "etag": "\"abc123\"",
    "last_modified": "Mon, 04 May 2026 08:00:00 GMT",
    "robots_crawl_delay_seconds": null,
    "retry_after_seconds": null
  },
  "policy_detection_error": null
}
```

Dieser Schritt soll guenstig sein. Er darf Feed-/Header-Metadaten lesen, aber keine Artikel-Detailseiten crawlen.

### `Python: Plan Crawl`

Input: Source-Zeile, `policy_json`, `detected_policy_json`, letzte Laufzeiten.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "should_crawl": true,
  "reason": "crawl_allowed",
  "next_allowed_at": "2026-05-04T13:00:00+02:00",
  "effective_policy": {
    "crawl_interval_minutes": 60,
    "rate_limit_per_minute": 10,
    "max_entries_per_run": 20,
    "refresh_window_days": 7,
    "prefer_feed_content": true
  }
}
```

Wenn `should_crawl` false ist, kann n8n den Lauf fuer diese Quelle beenden und `next_allowed_at` speichern.

### `Python: List Candidates`

Input: Source und `effective_policy`.

Output: ein Item pro Kandidat, noch ohne teuren Markdown-Detailinhalt.

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "source_name": "Example",
  "source_type": "rss",
  "candidate": {
    "id": "sha256...",
    "link": "https://example.com/article",
    "title": "Article title",
    "summary": "Feed summary",
    "publishedAt": "2026-05-04T09:00:00+02:00",
    "updatedAt": null,
    "has_feed_content": true,
    "feed_content_html": "<p>...</p>"
  },
  "http_cache": {
    "etag": "\"new-etag\"",
    "last_modified": "Mon, 04 May 2026 09:00:00 GMT"
  }
}
```

Bei HTML entspricht der Kandidat einem Link aus dem Listing. Wichtig: Die Detailseite wird hier noch nicht geladen.

### `Python: Filter Candidates`

Input: Kandidat plus gespeicherte Historie aus `infl0-articles` oder einer neuen `crawl_articles`-Tabelle.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "article_id": "sha256...",
  "candidate": {},
  "candidate_decision": "fetch",
  "candidate_reason": "new_article"
}
```

Moegliche Entscheidungen:

- `fetch`
- `skip_known`
- `skip_too_old`
- `skip_not_modified`
- `skip_policy`
- `skip_rate_limited`

Nur `fetch` geht weiter zu `Python: Fetch Detail`.

### `Python: Fetch Detail`

Input: genau ein Kandidat.

Output: ein Artikel mit `content_md`.

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "source_name": "Example",
  "article_id": "sha256...",
  "article": {
    "id": "sha256...",
    "title": "Article title",
    "link": "https://example.com/article",
    "publishedAt": "2026-05-04T09:00:00+02:00",
    "updatedAt": null,
    "author": null,
    "content_md": "# Article title\n\n..."
  },
  "fetch_detail_error": null
}
```

Dieser Schritt kann in n8n mit `Split in Batches`, Wait-Nodes und Retry-Logik kontrolliert werden.

### `Python: Finalize Article`

Input: Artikel mit `content_md`.

Output: kompatibel zum bisherigen Output von `Python: Fetch + Expand`.

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "source_name": "Example",
  "article_id": "sha256...",
  "content_hash": "sha256...",
  "article": {},
  "content_md": "# Article title\n\n..."
}
```

Ab hier kann der bestehende Workflow fast unveraendert weiterlaufen.

## Empfohlene Zwischenmigration

Die Migration muss nicht in einem grossen Schritt passieren.

1. `Python: Fetch + Expand` behalten, aber intern auf neue Bibliotheksfunktionen umstellen.
2. Als ersten sichtbaren Split `Python: List Candidates` vorziehen und nur Kandidaten ausgeben.
3. Danach History-Lookup vor den Detailfetch schieben.
4. `Python: Fetch Detail` einfuehren und nur fuer Kandidaten mit Entscheidung `fetch` ausfuehren.
5. Den bestehenden Enrichment-/Ingest-Pfad ab `Find in history` weiterverwenden.

Damit entsteht frueh ein Performancegewinn, ohne AI-Agent, Save/Ingest und `is_sent`-Logik gleichzeitig anzufassen.

## Hinweise zum aktuellen Workflow

- `Find in history` passiert aktuell nach dem Detailfetch. Fuer die Performance sollte ein technischer History-Lookup bereits auf Kandidatenebene passieren.
- Die Tabelle `infl0-articles` speichert bereits `article` als JSON-String. Fuer Kandidaten-Skip reicht langfristig eine schlankere Crawl-Historie mit `article_id`, `crawl_key`, `link`, `published_at`, `updated_at`, `content_hash`, `last_seen_at`, `last_fetched_at`.
- Der Ingest-Builder sollte weiterhin das flache Enrichment-Format erwarten. Falls ein Node direkt vom AI-Agent kommt, muss vorher ein Set-/Normalize-Step `output.*` nach `teaser`, `summary_long`, `category`, `tags` und `seriousness_rating` mappen.
- Der AI-Prompt greift auf `article.content_md` zu. Nach der Migration muss `Python: Finalize Article` dieses Feld weiterhin im `article` belassen.
- Der Fehlerpfad sollte kuenftig zwischen Source-Fehlern, Kandidaten-Fehlern und Detailfetch-Fehlern unterscheiden.
