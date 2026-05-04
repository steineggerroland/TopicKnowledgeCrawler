# Geplante Weiterentwicklung

Diese Notiz sammelt den aktuellen Stand, das Zielbild und die offenen Entscheidungen fuer die naechste Ausbaustufe des TopicKnowledgeCrawler. Sie ist bewusst als Arbeitsdokument formuliert: genug konkret, um Implementierung zu planen, aber noch offen fuer fachliche Schaerfung.

Die uebergeordnete Zielarchitektur ist in [`TARGET_ARCHITECTURE.md`](TARGET_ARCHITECTURE.md) definiert. Dort ist auch festgehalten, dass n8n die produktive Orchestrierung bleiben darf, solange der fachliche Workflow abstrakt dokumentiert ist und die Python-Schicht entweder bewusst schlank bleibt oder ganz in n8n aufgeht.

## Ausgangslage

Der Crawler ist historisch als eigenstaendiges Projekt entstanden und wurde spaeter in eine Python-Bibliothek ueberfuehrt, damit n8n-Workflows die Fetch-Logik wiederverwenden koennen.

Aktuelle Schichten:

- `crawler`: Legacy-/Kernlogik fuer RSS, Podcast-RSS, HTML-Fetching, Source-Analyse und lokale Speicherung.
- `tkcrawler`: kleine Bibliothek fuer n8n und infl0; wandelt Data-Table-Zeilen in Sources, ruft Fetcher auf, normalisiert Crawl-Keys und baut infl0-Ingest-Payloads.
- `n8n`: Workflow-Dokumentation, Python-Code-Nodes und ein Template fuer Crawl -> LLM-Enrichment -> infl0-Ingest.

Derzeit passieren wichtige Entscheidungen erst relativ spaet im Workflow. Insbesondere werden Artikelinhalte oft schon geladen und in Markdown umgewandelt, bevor bekannt ist, ob der Artikel ueberhaupt neu, relevant alt oder erneut zu verarbeiten ist.

## Beobachtete Probleme

- RSS-Quellen koennen sehr schnell sein, wenn Feed-Eintraege direkt genug Inhalt enthalten.
- RSS-Quellen werden langsam, wenn jeder Feed-Eintrag auf eine Detailseite verweist und diese einzeln gecrawlt wird.
- Ein Podcast-RSS-Lauf kann aktuell etwa 40 Minuten dauern, wenn fuer viele Episoden Detailseiten bzw. lange Inhalte verarbeitet werden.
- Die bestehende `article_enrichment`-Skip-Logik spart LLM-Kosten, aber nicht zwingend Fetch- und Markdown-Extraktionszeit.
- Quellen haben keine expliziten Crawl-Policies, etwa Mindestabstand, Rate-Limit, maximale Eintraege pro Lauf oder Altersfenster.
- infl0 kann Quellen bereitstellen und Artikel entgegennehmen, aber der Crawl-Prozess ist noch nicht als von infl0 steuerbarer Prozess modelliert.

## Ziele

1. Quellen intelligenter und ruecksichtsvoller crawlen.
2. Teure Detailabrufe vermeiden, wenn Eintraege bereits bekannt oder zu alt sind.
3. Feed- und Artikelverarbeitung messbar schneller machen.
4. n8n als Orchestrierung behalten, aber besser mit infl0 verbinden.
5. Die Fetcher-Vertraege so erweitern, dass lokale Nutzung und n8n-Nutzung dieselbe Kernlogik teilen.
6. HTML-Quellen wieder als gleichwertigen Produktivpfad neben RSS nutzbar machen.
7. Python-Schritte in n8n kleiner schneiden, damit n8n Steuerungsentscheidungen, Status und Fehler sichtbar orchestrieren kann.

## Nicht-Ziele fuer die erste Iteration

- Kein kompletter Rewrite des Crawlers.
- Kein Wechsel weg von n8n als produktiver Orchestrierung.
- Kein neues persistentes Backend im Python-Projekt, sofern n8n Data Tables bzw. infl0 den Zustand halten koennen.
- Keine perfekte Volltext-Aktualisierung fuer alte Artikel; nach einem definierbaren Alter duerfen Aenderungen ignoriert werden.

## Zielbild

Der Crawl-Prozess soll in zwei Phasen getrennt werden:

1. Feed/List-Metadaten lesen: guenstig, schnell, mit ETag/Last-Modified wenn moeglich.
2. Detailinhalt laden: nur fuer Kandidaten, die nach Policy wirklich verarbeitet werden sollen.

Langfristig ist "Artikel" nur eine Item-Art. Die Pipeline soll auf ein allgemeineres Quellen- und Item-Modell wachsen: RSS/HTML liefern Artikel, Podcast-RSS liefert Episoden, soziale Quellen liefern Posts oder Threads, Buecher/Dokumente liefern Kapitel oder Abschnitte, Paper-Quellen liefern Paper-Hinweise oder Volltext-Segmente. Die n8n-Workflows duerfen kurzfristig weiter `article` sagen, sollten aber bei neuen Schnittstellen moeglichst in Richtung `item` generalisiert werden.

Ein Eintrag wird zum Detailabruf zugelassen, wenn mindestens eine dieser Bedingungen zutrifft:

- Er ist noch nicht bekannt.
- Er ist bekannt, aber innerhalb eines Aktualisierungsfensters, zum Beispiel sieben Tage, und der Feed deutet auf eine Aenderung hin.
- Die Quelle verlangt explizit immer einen Refresh.

Ein Eintrag wird vor dem Detailabruf uebersprungen, wenn alle diese Bedingungen zutreffen:

- stabile Artikel-ID oder Link ist bereits bekannt,
- `content_hash`/Enrichment existiert bereits oder der Workflow kann den Artikel als verarbeitet erkennen,
- `publishedAt` liegt ausserhalb des Aktualisierungsfensters,
- keine Quelle-Policy erzwingt erneutes Laden.

## Source-Policy

Quellen sollten optionale Policy-Felder bekommen. Diese koennen in `config/sources.json`, n8n `crawl_sources` oder spaeter infl0 gepflegt werden.

Vorschlag:

```json
{
  "crawl_interval_minutes": 60,
  "rate_limit_per_minute": 10,
  "max_entries_per_run": 20,
  "refresh_window_days": 7,
  "detail_fetch": "new_or_recent_changed",
  "prefer_feed_content": true,
  "timeout_seconds": 10
}
```

Semantik:

- `crawl_interval_minutes`: Mindestabstand zwischen erfolgreichen Crawls dieser Quelle.
- `rate_limit_per_minute`: Obergrenze fuer HTTP-Requests gegen dieselbe Quelle.
- `max_entries_per_run`: Schutz gegen sehr grosse Feeds.
- `refresh_window_days`: Zeitraum, in dem bekannte Eintraege erneut geprueft werden duerfen.
- `detail_fetch`: Strategie, zum Beispiel `always`, `new_only`, `new_or_recent_changed`.
- `prefer_feed_content`: wenn Feed-Inhalt ausreicht, keine Detailseite laden.
- `timeout_seconds`: HTTP-Timeout pro Request.

### Automatisch erkannte Source-Hinweise

Einige Quellen geben selbst Hinweise darauf, wie oft sie abgerufen werden sollten. Diese Hinweise sollten separat erkannt und an n8n gemeldet werden, damit der Workflow sie speichern, anzeigen und mit manuellen Policies zusammenfuehren kann.

Moegliche Signale:

- RSS/Atom `ttl`: empfohlene Cache-/Refresh-Zeit in Minuten.
- RSS `skipHours` / `skipDays`: Zeitfenster, in denen nicht gecrawlt werden soll.
- HTTP `Cache-Control`, `Expires`, `ETag`, `Last-Modified`: Caching- und Revalidierungsinformationen.
- `robots.txt` `Crawl-delay`: falls vorhanden und fuer den User-Agent relevant.
- HTTP `Retry-After`: nach 429/503 als harte Pause behandeln.
- HTML-Metadaten oder Publisher-Hinweise, sofern strukturiert erkennbar.

Prioritaet:

1. Harte technische Antworten wie `Retry-After` und 429/503 respektieren.
2. Manuell gesetzte Source-Policy darf konservativer sein als erkannte Hinweise.
3. Erkannte Hinweise duerfen nie aggressiver crawlen als globale Defaults.
4. Fehlende Hinweise fallen auf sichere Defaults zurueck.

## Neuer Fetch-Kontext

`tkcrawler.fetch.fetch_entries_for_source` sollte optional einen Kontext erhalten, den n8n aus Data Tables oder infl0 befuellt.

Beispiel:

```python
fetch_entries_for_source(
    source,
    context={
        "now": "2026-05-04T12:00:00+02:00",
        "known_article_ids": ["..."],
        "known_links": ["https://..."],
        "known_content_hashes": {"article_id": "hash"},
        "last_successful_crawl_at": "2026-05-04T10:00:00+02:00",
        "policy": {"refresh_window_days": 7}
    },
)
```

Der Kontext soll keine n8n-Abhaengigkeit in die Fetcher bringen. Er beschreibt nur, was bereits bekannt ist und welche Policy gilt.

## Interaktive n8n-Orchestrierung

Der aktuelle `code_fetch_expand.py`-Stil ist bequem, aber zu grob: Ein Python-Schritt nimmt eine Quelle, crawlt sie und gibt fertige Artikel zurueck. Fuer lange oder fragile Quellen soll n8n stattdessen mehrere kleinere Python-Schritte orchestrieren, die jeweils Steuerungsinformationen liefern.

Vorgeschlagene Python-Bausteine:

- `analyze_source`: klassifiziert URL als `rss`, `rss+podcast`, `html` oder `unknown`; erzeugt bei HTML eine Selector-Konfiguration oder einen Fehlerstatus.
- `inspect_source_policy`: liest guenstige Source-Hinweise wie RSS `ttl`, `skipHours`, HTTP-Header, robots `Crawl-delay` und gibt eine normalisierte Policy-Empfehlung zurueck.
- `plan_crawl`: kombiniert gespeicherte Policy, erkannte Hinweise, letzte Laufdaten und aktuellen Zeitpunkt; entscheidet `should_crawl`, `next_allowed_at`, `reason`.
- `list_candidates`: liest Feed oder HTML-Listing und gibt nur Metadaten/Kandidaten zurueck, noch ohne teuren Detailabruf.
- `filter_candidates`: markiert Kandidaten als `fetch`, `skip_known`, `skip_too_old`, `skip_rate_limited`, `skip_policy`.
- `fetch_detail`: laedt und extrahiert genau einen Artikel/eine Episode, damit n8n Batches, Retries und Rate-Limits granular steuern kann.
- `finalize_article`: erzeugt `content_hash`, infl0-Payload-Grunddaten und technische Metadaten.

Damit kann n8n nach jedem Schritt entscheiden:

- abbrechen, wenn die Quelle noch nicht faellig ist,
- warten oder reschedulen, wenn ein Rate-Limit greift,
- nur neue Kandidaten in kleine Batches schicken,
- Fehler pro Kandidat speichern, ohne den gesamten Quellenlauf zu verlieren,
- Crawl-Status fuer infl0 laufend aktualisieren.

Beispiel fuer `plan_crawl`-Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "should_crawl": false,
  "reason": "source_interval_not_elapsed",
  "next_allowed_at": "2026-05-04T13:00:00+02:00",
  "effective_policy": {
    "crawl_interval_minutes": 60,
    "rate_limit_per_minute": 10,
    "refresh_window_days": 7
  },
  "detected_policy": {
    "rss_ttl_minutes": 60,
    "etag": "\"abc123\"",
    "last_modified": "Mon, 04 May 2026 08:00:00 GMT"
  }
}
```

Beispiel fuer `list_candidates`-Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "source_type": "rss",
  "feed_not_modified": false,
  "candidates": [
    {
      "id": "sha256...",
      "link": "https://example.com/article",
      "title": "Article title",
      "publishedAt": "2026-05-04T09:00:00+02:00",
      "updatedAt": null,
      "has_feed_content": true
    }
  ],
  "http_cache": {
    "etag": "\"new-etag\"",
    "last_modified": "Mon, 04 May 2026 09:00:00 GMT"
  }
}
```

Dieser Zuschnitt macht Python eher zu einer Bibliothek fuer Analyse und Extraktion, waehrend n8n die Ablaufsteuerung sichtbar uebernimmt.

## Fetcher-Aenderungen

Vorab wichtig: `tkcrawler.fetch.fetch_entries_for_source` dispatcht bereits auf `html`, wenn die Source-Zeile `type: html` und eine passende `configuration`/`configuration_json` enthaelt. Der aktuell robuste Pfad ist trotzdem RSS, weil HTML-Quellen zusaetzliche Selector-Konfiguration, stabilere Vorab-IDs und bessere Fehlerdiagnose brauchen.

Perspektivisch sollten Fetcher eher als Source-Adapter verstanden werden. Ein Adapter kann Kandidaten listen, Details laden und bei langen Quellen Segmente erzeugen. RSS, HTML und Podcast sind die ersten Adapter; spaeter koennen Adapter fuer Mastodon, Dokumente oder Paper-Quellen folgen.

### RSS

Aktuell ruft `RssFetcher` fuer jeden Feed-Eintrag `HtmlFetcher.generate_markdown_from_url(entry.link)` auf. Das ist der zentrale Hebel.

Geplante Aenderungen:

- Feed-Eintraege zuerst normalisieren, deduplizieren und klassifizieren.
- `publishedAt`/`updatedAt` in echte Datumswerte parsen, soweit moeglich.
- Vor Detailabruf pruefen, ob der Eintrag bekannt und ausserhalb des Refresh-Fensters ist.
- Wenn `content` oder `summary` im Feed hochwertig genug ist, daraus Markdown erzeugen und Detailabruf vermeiden.
- Optional ETag/Last-Modified des Feeds nutzen, wenn der Aufrufer diese Werte speichert.

### Podcast-RSS

Aktuell nutzt `PodcastFetcher` primaer Feed-Inhalte (`content`, `description`, `itunes:summary`) und konvertiert diese in Markdown. Fuer Podcasts ist wichtig, alte Episoden frueh zu begrenzen.

Geplante Aenderungen:

- `publishedAt` robust aus `published`, `pubDate` und `updated` lesen.
- Standardmaessig nur neue oder kuerzlich geaenderte Episoden verarbeiten.
- `max_entries_per_run` und `refresh_window_days` respektieren.
- Optional Kapitel-/Shownotes-Links nur bei neuen Episoden nachladen.

### HTML

HTML-Quellen haben eine Listing-Seite und Detailseiten. Auch hier sollte vor dem Detailabruf entschieden werden.

Geplante Aenderungen:

- HTML als explizit unterstuetzten n8n-Pfad testen: Data-Table-Zeile -> `row_to_source` -> `HtmlFetcher` -> `finalize_entry_metadata`.
- `configuration_json` validieren und klare Fehler liefern, wenn `article_selector` oder `main_page_anchor_selector` fehlen.
- Source-Analyse stabilisieren: `SourceAnalyzer` soll bei HTML nur dann LLM-Analyse ausfuehren, wenn `configuration` fehlt.
- HTML-Analyse-Ergebnis versionieren oder mit Confidence/Fehlergrund speichern, damit defekte Selector-Konfigurationen sichtbar werden.
- Link aus dem Listing als stabile Vorab-ID verwenden.
- Bereits bekannte Links vor `extract_article_meta` und `generate_markdown_from_url` ueberspringen, sofern Policy es erlaubt.
- Optional `max_entries_per_run` auf Listing-Kandidaten anwenden.
- Optional pro Quelle definieren, ob Listing-Inhalte bereits reichen oder ob immer die Detailseite geladen werden muss.

## HTML-Quellen als Produktivpfad

HTML-Quellen unterscheiden sich von RSS-Quellen, weil die Listing-Seite selbst keine standardisierte Artikelstruktur garantiert. Darum braucht der Produktivpfad drei Bausteine:

1. Klassifikation: Ist die URL RSS, Podcast-RSS oder HTML?
2. Konfiguration: Welche CSS-Selektoren finden Artikelblöcke und Detail-Links?
3. Laufzeitvalidierung: Liefert die Konfiguration weiterhin Artikel, oder ist die Website-Struktur gebrochen?

Vorgeschlagener Data-Table-Zustand fuer HTML:

```json
{
  "type": "html",
  "configuration_json": {
    "article_selector": "article",
    "main_page_anchor_selector": "a:has(h2)"
  },
  "configuration_status": "valid",
  "configuration_checked_at": "2026-05-04T12:00:00+02:00",
  "configuration_error": null
}
```

Workflow-Idee:

- Beim Sync aus infl0 werden neue Quellen zunaechst ohne Typ oder mit `type: unknown` gespeichert.
- Ein Analyse-Schritt setzt `type`.
- Bei `type: html` erzeugt oder prueft der Analyse-Schritt `configuration_json`.
- Der Fetch-Schritt verarbeitet nur HTML-Zeilen mit gueltiger Konfiguration.
- Wenn keine Artikel gefunden werden oder Selector-Fehler auftreten, wird `configuration_status` auf `invalid` gesetzt und die Quelle nicht stillschweigend als leerer Crawl behandelt.

Offene Frage: Soll HTML-Selector-Ermittlung weiterhin ueber den bestehenden `SourceAnalyzer` laufen, oder wollen wir fuer n8n/infl0 einen separaten, strikteren Analyzer mit JSON-Schema, Confidence und Testbeispielen bauen?

## n8n Data Tables

Bestehende Tabellen:

- `crawl_sources`: was gecrawlt wird.
- `article_enrichment`: ersetzt `summary_history.json`.

Vorgeschlagene Erweiterungen fuer `crawl_sources`:

- `policy_json`: JSON mit Source-Policy.
- `detected_policy_json`: automatisch erkannte Hinweise aus Feed, HTTP und robots.
- `effective_policy_json`: zusammengefuehrte Policy, die der Workflow wirklich nutzt.
- `next_allowed_crawl_at`
- `last_crawl_started_at`
- `last_crawl_finished_at`
- `last_crawl_status`
- `last_crawl_error`
- `last_feed_etag`
- `last_feed_modified`

Vorgeschlagene Erweiterungen fuer `article_enrichment` oder eine neue Tabelle `crawl_articles`:

- `article_id`
- `crawl_key`
- `link`
- `published_at`
- `updated_at`
- `content_hash`
- `first_seen_at`
- `last_seen_at`
- `last_fetched_at`
- `last_enriched_at`

Offene Frage: Soll `article_enrichment` die technische Crawl-Historie mittragen, oder ist eine getrennte Tabelle `crawl_articles` sauberer? Eine getrennte Tabelle waere fachlich klarer, kostet aber einen weiteren Lookup im Workflow.

## infl0-Integration

Aktuell relevant:

- infl0 stellt Quellen ueber `GET /api/crawler/sources` bereit.
- TopicKnowledgeCrawler/n8n liefert Artikel ueber `POST /api/crawler/ingest` zurueck.

Ziel:

- infl0 kann einen Crawl fuer eine Quelle oder alle aktiven Quellen anstossen.
- n8n bleibt der Worker/Orchestrator und nimmt Crawl-Auftraege per Webhook entgegen.
- infl0 kann Crawl-Status anzeigen: geplant, laeuft, erfolgreich, fehlgeschlagen, zuletzt gelieferte Artikel.

Moegliche Schnittstellen:

- infl0 -> n8n: Webhook `POST /crawl/run` mit `crawl_key`, optional `force`, optional `max_entries`.
- n8n -> infl0: bestehender Ingest plus optionaler Status-Endpunkt.
- infl0 -> n8n oder eigener Store: Crawl-Run-Status abrufen.

Offene Frage: Soll infl0 nur n8n triggern, oder soll infl0 selbst eine Queue/Run-Tabelle fuehren und n8n zieht Jobs daraus?

## Implementierungsplan

### Phase 1: Messbarkeit und Vorab-Skip

- Groben Fetch-Schritt in kleinere n8n/Python-Bausteine aufteilen: Plan, Kandidatenliste, Filter, Detailfetch.
- Fetcher um optionale Policy-/Known-Kontexte erweitern.
- Vor Detailabruf bekannte alte Eintraege ueberspringen.
- n8n-Code-Node so erweitern, dass bekannte Artikelinformationen vor dem Fetch bereitgestellt werden.
- HTML-Pfad in `tkcrawler`/n8n mit Konfigurationsvalidierung und aussagekraeftigen Fehlern reaktivieren.
- Tests fuer RSS/Podcast/HTML-Skip-Entscheidungen ergaenzen.

### Phase 2: Source-Policies und Rate-Limits

- `policy_json` in `crawl_sources` dokumentieren und auswerten.
- Automatisch erkannte Source-Hinweise als `detected_policy_json` speichern.
- `effective_policy_json` aus Defaults, manueller Policy und erkannten Hinweisen berechnen.
- Mindestabstand pro Quelle respektieren.
- Einfache per-source Request-Drosselung einfuehren.
- `max_entries_per_run` implementieren.

### Phase 3: Feed-Caching und HTTP-Metadaten

- ETag/Last-Modified fuer Feeds speichern und senden.
- `304 Not Modified` als schneller No-op behandeln.
- Last-Modified/ETag optional auch fuer Detailseiten pruefen, falls praktikabel.

### Phase 4: infl0-gesteuerte Crawls

- n8n Webhook fuer Crawl-Auftrag definieren.
- infl0 kann Crawl-Auftrag senden.
- Status- und Fehler-Rueckmeldung modellieren.
- UI in infl0 kann Crawl starten und letzten Lauf anzeigen.

### Phase 5: Neue Quellenfamilien

- Generisches `item`-Modell neben dem bestehenden `article`-Format definieren.
- Source-Adapter-Konzept dokumentieren und in Code-/Node-Vertraege uebernehmen.
- Erste soziale Quelle evaluieren, zum Beispiel Mastodon.
- Dokument-Adapter fuer PDF/EPUB konzipieren: Extraktion, Segmentierung, stabile IDs, Reihenfolge.
- Paper-Quelle konzipieren: Metadaten, Relevanzfilter, vorsichtige wissenschaftliche Zusammenfassung.

## Offene Entscheidungen

- Standardwert fuer `refresh_window_days`: sieben Tage wirkt passend, muss aber pro Quelle ueberschreibbar sein.
- Reicht `article_enrichment` als einziger Artikelzustand, oder brauchen wir `crawl_articles`?
- Welche Feed-Inhalte gelten als "gut genug", um Detailseiten nicht zu laden?
- Soll `rss` automatisch zu `rss+podcast` erkannt werden, oder bleibt das eine manuelle Source-Eigenschaft?
- Soll `html` automatisch analysiert werden, oder nur nach expliziter Freigabe/Pruefung der Selector-Konfiguration?
- Wo sollen Rate-Limits technisch greifen: in Python-Fetchern, in n8n-Batches oder in beiden?
- Welche automatisch erkannten Hinweise sollen verbindlich sein, und welche nur informativ?
- Wie granular sollen n8n-Code-Nodes werden, ohne den Workflow unuebersichtlich zu machen?
- Wie viel Kontrolle soll infl0 ueber Crawl-Policies erhalten?
- Wann migrieren wir Begriffe und Schnittstellen von `article` auf ein allgemeineres `item`?
- Welche neue Quellenfamilie eignet sich als erster Proof of Concept nach RSS/HTML/Podcast?
- Wie sollen lange Quellen segmentiert werden: Kapitel, semantische Abschnitte, fixe Chunk-Groesse oder hybride Logik?

## Naechster sinnvoller Schritt

Die erste Implementierung sollte den groessten Zeitfresser direkt adressieren: bekannte und alte Feed-Eintraege vor dem Detailabruf ueberspringen. Dafuer brauchen wir einen minimalen Fetch-Kontext aus n8n, der pro Quelle bekannte `article_id`/`link`/`published_at`-Informationen liefert.
