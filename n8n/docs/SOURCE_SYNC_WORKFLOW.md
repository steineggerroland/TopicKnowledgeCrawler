# Source-Sync und SourceAnalyzer-Workflow

Diese Notiz bezieht sich auf den aktuellen n8n-Workflow, der infl0-Quellen ueber `GET /api/crawler/sources` synchronisiert, alle vorhandenen `crawl_sources` kurz deaktiviert, die infl0-Liste splittet, per Python analysiert und anschliessend in `Infl0-crawl-sources` upsertet.

## Aktueller Ablauf

1. Manual Trigger oder Schedule Trigger.
2. `Update row(s)`: setzt bestehende Quellen auf `active = false`.
3. HTTP Request an `https://reader.neurospicy.icu/api/crawler/sources`.
4. `Split Out`: splittet `body.sources`.
5. JavaScript-Code-Node: gibt das `source`-Objekt als Item weiter.
6. Python-Code-Node: normalisiert `url`/`feedUrl`, `name`/`displayTitle`, `crawl_key`/`crawlKey`, klassifiziert per `SourceAnalyzer` und erzeugt bei HTML `configuration_json`.
7. `Upsert row(s)`: schreibt `name`, `type`, `url`, `crawl_key`, `configuration_json`, `active = true`.

## Was daran gut ist

- Der Sync trennt Quellenverwaltung von Artikel-Crawl.
- infl0 bleibt die fuehrende Quelle fuer abonnierte Feeds.
- Quellen, die nicht mehr von infl0 geliefert werden, koennen durch das vorherige `active = false` deaktiviert werden.
- Der Python-Node akzeptiert sowohl infl0-Felder (`feedUrl`, `crawlKey`, `displayTitle`) als auch Data-Table-Felder (`url`, `crawl_key`, `name`).
- HTML-Konfiguration kann beim Sync entstehen, also bevor der eigentliche Crawl startet.

## Risiken im aktuellen Workflow

- Der HTTP-Node ist als `POST /api/crawler/ingest` benannt, ruft aber `GET /api/crawler/sources` auf. Das ist nur Naming, aber spaeter beim Debugging verwirrend.
- `Upsert row(s)` filtert aktuell mit `={{ $json.crawlKey }}`. Der Python-Node normalisiert aber primaer nach `crawl_key`. Der Filter sollte auf `={{ $json.crawl_key || $json.crawlKey }}` oder konsequent `crawl_key` umgestellt werden.
- `Update row(s)` deaktiviert vor dem Sync pauschal Quellen. Wenn der infl0-Request oder die Analyse danach teilweise fehlschlaegt, koennen Quellen faelschlich inaktiv bleiben.
- Analyse und Upsert sind gekoppelt: wenn die LLM-basierte HTML-Analyse langsam ist oder fehlschlaegt, wird auch die reine Source-Synchronisation langsamer oder unvollstaendig.
- Der Analyse-Status wird nicht explizit gespeichert. Eine Quelle ohne `type` oder ohne HTML-Konfiguration sieht aehnlich aus wie eine Quelle, die noch nicht analysiert wurde.
- Bei HTML gibt es keinen sichtbaren Unterschied zwischen "keine Artikel gefunden", "Selector kaputt", "LLM konnte nicht analysieren" und "Quelle ist wirklich leer".

## Zielstruktur

Der Source-Sync sollte in zwei getrennte Phasen zerlegt werden:

1. **Spiegeln:** infl0-Quellen schnell und robust in `crawl_sources` uebernehmen.
2. **Analysieren:** nur neue, geaenderte oder unvollstaendige Quellen klassifizieren und konfigurieren.

Empfohlene Node-Kette:

1. Trigger.
2. `GET /api/crawler/sources`.
3. `Split sources`.
4. `Python: Normalize Source Row`.
5. `Data Table: Upsert Source Shell`.
6. `Data Table: Get Sources Needing Analysis`.
7. `Split in Batches`.
8. `Python: Analyze Source Type`.
9. `IF type == html and configuration missing`.
10. `Python or AI: Analyze HTML Selectors`.
11. `Python: Validate Source Configuration`.
12. `Data Table: Update Analysis Status`.
13. Optional: `Data Table: Deactivate Missing Sources` erst nach erfolgreichem Sync.

So bleibt die Source-Liste auch dann aktuell, wenn einzelne HTML-Analysen scheitern.

## Empfohlene Felder fuer `crawl_sources`

Neben den bestehenden Feldern:

- `name`
- `type`
- `url`
- `configuration_json`
- `crawl_key`
- `active`

sollten fuer die Analyse hinzukommen:

- `source_status`: `new`, `ready`, `needs_analysis`, `analysis_failed`, `configuration_invalid`, `inactive`.
- `analysis_error`: letzter Analysefehler als Text.
- `analysis_checked_at`: wann Typ/Konfiguration zuletzt geprueft wurden.
- `configuration_status`: `missing`, `valid`, `invalid`, `generated`.
- `configuration_error`: letzter Selector-/Validierungsfehler.
- `source_fingerprint`: Hash aus URL und ggf. relevanten Analyse-Eingaben, um erneute Analyse nur bei Aenderung auszufuehren.
- `subscriber_count`: aus infl0, falls geliefert.
- `last_seen_in_infl0_at`: wann die Quelle zuletzt von infl0 geliefert wurde.

## Python-Node-Vertraege

### `Python: Normalize Source Row`

Input: infl0-Source.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "url": "https://example.com/feed.xml",
  "name": "Example Feed",
  "subscriber_count": 3,
  "active": true,
  "source_status": "needs_analysis"
}
```

Dieser Schritt sollte keine Netzwerkrequests machen.

### `Python: Analyze Source Type`

Input: normalisierte Source-Zeile.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "type": "rss",
  "analysis_checked_at": "2026-05-04T12:00:00+02:00",
  "source_status": "ready",
  "analysis_error": null,
  "detected_content_type": "application/rss+xml"
}
```

Dieser Schritt sollte nur die Source-URL selbst pruefen. Bei HTML sollte er `type = html` setzen, aber die Selector-Ermittlung kann ein eigener Schritt sein.

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.analyze_source import analyze_source_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    out.append({"json": analyze_source_item(item["json"], {"now": now})})
return out
```

### `Python: Prepare HTML Analysis`

Input: HTML-Source ohne gueltige Konfiguration.

Output:

```json
{
  "crawl_key": "https://example.com/articles",
  "type": "html",
  "source_status": "needs_analysis",
  "configuration_status": "missing",
  "html_analysis_prompt": "Analyze this HTML listing page...",
  "html_analysis_input": "<html>..."
}
```

Dieser Schritt laedt die Listing-Seite, entfernt sehr laute HTML-Teile wie `script`/`style` und baut ein Prompt-Feld. Er ruft kein LLM auf.

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.prepare_html_analysis import prepare_html_analysis_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    out.append(
        {
            "json": prepare_html_analysis_item(
                item["json"],
                {"now": now, "max_html_chars": 30000},
            )
        }
    )
return out
```

### `n8n LLM: Analyze HTML Selectors`

Input: `html_analysis_prompt` aus dem vorherigen Python-Step.

Output des LLM sollte JSON sein:

```json
{
  "article_selector": "article",
  "main_page_anchor_selector": "a:has(h2)",
  "confidence": "high",
  "notes": "The listing contains repeated article cards."
}
```

Die Modellwahl, Prompt-Varianten und Vergleichstests bleiben bewusst in n8n. Fuer Modellvergleiche kann derselbe `html_analysis_prompt` parallel an mehrere LLM-Nodes gehen.

### `Python: Apply HTML Analysis`

Input: Source-Zeile plus LLM-Output, zum Beispiel als `output`, `html_analysis_result`, `text` oder `response`.

Output:

```json
{
  "crawl_key": "https://example.com/articles",
  "configuration_json": "{\"article_selector\":\"article\",\"main_page_anchor_selector\":\"a:has(h2)\"}",
  "configuration_status": "generated",
  "configuration_error": null
}
```

Dieser Schritt parst nur das LLM-Ergebnis und erzeugt daraus `configuration_json`. Die eigentliche Validierung passiert im naechsten Schritt.

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.apply_html_analysis import apply_html_analysis_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    out.append({"json": apply_html_analysis_item(item["json"], {"now": now})})
return out
```

### `Python: Validate Source Configuration`

Input: Source mit `type` und ggf. `configuration_json`.

Output:

```json
{
  "crawl_key": "https://example.com/articles",
  "source_status": "ready",
  "configuration_status": "valid",
  "configuration_error": null,
  "sample_candidate_count": 5
}
```

Bei HTML sollte die Validierung nur die Listing-Seite und Kandidaten-Links pruefen, aber noch keine Detailseiten extrahieren.

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.validate_source_configuration import validate_source_configuration_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    out.append(
        {
            "json": validate_source_configuration_item(
                item["json"],
                {"now": now, "sample_candidate_limit": 5},
            )
        }
    )
return out
```

## Deaktivierung nicht mehr gelieferter Quellen

Der aktuelle Ansatz `alle inactive -> gelieferte active` ist einfach, aber riskant bei Teilfehlern. Robuster waere:

1. Sync-Lauf-ID oder `sync_started_at` erzeugen.
2. Jede von infl0 gelieferte Quelle mit `last_seen_in_infl0_at = sync_started_at` upserten.
3. Erst nach erfolgreichem Durchlauf Quellen deaktivieren, deren `last_seen_in_infl0_at` aelter als der aktuelle Lauf ist.

Damit deaktiviert ein fehlgeschlagener HTTP-Request nicht versehentlich alle Quellen.

## Beziehung zum Artikel-Crawl

Der Artikel-Crawl sollte nur Quellen verarbeiten, die diese Bedingungen erfuellen:

- `active = true`
- `source_status = ready`
- `type` ist `rss`, `rss+podcast` oder `html`
- bei `type = html`: `configuration_status = valid`

Quellen mit `needs_analysis`, `analysis_failed` oder `configuration_invalid` sollten sichtbar bleiben, aber nicht in den teuren Crawl laufen.
