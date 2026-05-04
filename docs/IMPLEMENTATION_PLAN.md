# Implementierungsplan

Dieser Plan beschreibt die naechsten konkreten Schritte. Ziel ist eine schlanke Python-Step-Schicht, die sowohl von n8n-Code-Nodes als auch unabhaengig per CLI ausgefuehrt werden kann.

## Leitprinzip

Jeder fachliche Schritt bekommt:

1. eine Python-Funktion mit klaren Dict/JSON-Vertraegen,
2. optional ein kleines CLI-Modul mit stdin/stdout JSON,
3. ein n8n-Code-Node-Snippet, das nur noch Input weiterreicht und Output zurueckgibt,
4. Tests fuer die eigentliche Funktion, nicht fuer n8n.

Die n8n-Workflows bleiben die produktive Orchestrierung. Die Python-Steps sind die portable Referenzimplementierung.

## Python-Leitplanken

Das Projekt soll sich an gaengigen Python-Best-Practices orientieren. Das bestehende `src/`-Layout ist dafuer passend und soll beibehalten werden: es verhindert versehentliche Importe aus dem Working Directory und entspricht dem empfohlenen Packaging-Stil fuer installierbare Libraries.

Leitplanken fuer neue Python-Aenderungen:

- Package-Code bleibt unter `src/tkcrawler` bzw. bei Legacy-Kompatibilitaet unter `src/crawler`.
- Tests liegen unter `tests/` und testen Funktionen/Verhalten, nicht n8n-Node-Implementierungsdetails.
- Neue Step-Funktionen sind klein, typisiert und arbeiten mit `dict`/JSON-nahen Datenstrukturen.
- Seiteneffekte bleiben am Rand: CLI liest stdin/stdout, n8n liest/schreibt Items, Kernfunktionen nehmen Input entgegen und geben Output zurueck.
- Keine versteckte globale Konfiguration in Kernfunktionen; Laufzeitkontext kommt explizit ueber `context`.
- Keine n8n-spezifischen Feldzugriffe tief in Parser-/Policy-Logik; n8n-Mapping passiert in duennen Wrappern.
- Fehler werden strukturiert gemeldet, nicht nur geloggt oder als freie Strings verstreut.
- Neue Module sollen keine schwergewichtigen Imports beim Package-Import ausloesen, sofern sie nur fuer einzelne Adapter gebraucht werden.
- Bestehende Legacy-Fetcher werden nicht blind refactored; neue portable Steps duerfen sie schrittweise kapseln oder ersetzen.
- Packaging bleibt ueber `pyproject.toml`; keine parallelen Setup-Konventionen einfuehren.

Wo Python-Konventionen und n8n-Bequemlichkeit kollidieren, soll die Python-Konvention in der Library gewinnen. n8n-Code-Nodes duerfen pragmatisch bleiben, aber sie sollten moeglichst nur Step-Funktionen aufrufen.

## Zielstruktur im Code

Vorgeschlagene neue Module:

```text
src/tkcrawler/
  steps/
    __init__.py
    normalize_source.py
    analyze_source.py
    inspect_source_policy.py
    plan_dispatch.py
    list_candidates.py
    filter_candidates.py
    fetch_detail.py
    finalize_item.py
    build_ingest_body.py
  cli/
    __init__.py
    run_step.py
```

Kurzfristig koennen die CLI-Module entweder einzeln per `python -m tkcrawler.steps.normalize_source` laufen oder ueber einen gemeinsamen Runner:

```bash
python -m tkcrawler.cli.run_step normalize_source < input.json
```

## n8n-Input vs. CLI-Envelope

Es gibt zwei bewusst unterschiedliche Aufrufebenen:

1. **Core-Funktion fuer n8n:** nimmt ein einzelnes flaches n8n-Item-Payload entgegen, also genau das, was in n8n unter `$json` bzw. `item["json"]` liegt.
2. **Step-Funktion/CLI:** nimmt einen portablen Envelope entgegen, damit derselbe Schritt ausserhalb von n8n mit Kontext ausgefuehrt werden kann.

n8n-Code-Nodes sollten in der Regel die Core-Funktion nutzen:

```python
from tkcrawler.steps.plan_dispatch import plan_dispatch_item

out = []
for item in _items:
    planned = plan_dispatch_item(
        item["json"],
        {"now": _now.isoformat(), "dispatch_mode": "scheduled"},
    )
    if planned["should_dispatch"]:
        out.append({"json": planned})
return out
```

In n8n ist der Input also **nicht**:

```json
{
  "item": {
    "crawl_key": "https://example.com/feed",
    "type": "rss"
  }
}
```

sondern flach:

```json
{
  "crawl_key": "https://example.com/feed",
  "type": "rss",
  "source_status": "ready"
}
```

Der Envelope ist fuer CLI/portable Runner gedacht.

CLI-Input:

```json
{
  "item": {
    "crawl_key": "https://example.com/feed",
    "type": "rss",
    "source_status": "ready"
  },
  "context": {
    "now": "2026-05-04T12:00:00+02:00",
    "dispatch_mode": "scheduled"
  }
}
```

CLI-Output bei Erfolg:

```json
{
  "ok": true,
  "items": [
    {}
  ],
  "meta": {}
}
```

CLI-Output bei fachlichem Fehler:

```json
{
  "ok": false,
  "items": [],
  "error": {
    "code": "source_not_ready",
    "message": "Source is missing type",
    "details": {}
  },
  "meta": {}
}
```

Die Step-Funktionen tolerieren aktuell auch flache Inputs ohne Envelope, damit sie einfacher testbar und skriptbar bleiben. Fuer n8n ist aber die `*_item(...)`-Funktion der bevorzugte Weg, weil sie direkt ein n8n-kompatibles Dict fuer `{"json": ...}` liefert.

## Phase 1: Step- und CLI-Grundgeruest

Ziel: Portabilitaet herstellen, ohne die Fetcher-Logik direkt umzubauen.

Umsetzung:

- `tkcrawler.steps` Paket anlegen.
- Gemeinsame Helper fuer Envelope, JSON stdin/stdout und Fehlerformat anlegen.
- `normalize_source` als ersten Step implementieren.
- `build_ingest_body` als Step aus bestehendem `tkcrawler.infl0_payload` wrappen.
- CLI-Runner `python -m tkcrawler.cli.run_step <step>` implementieren.
- Tests fuer `normalize_source`, `build_ingest_body` und CLI-Smoke-Test.

Ergebnis:

- n8n kann den SourceAnalyzer-/Ingest-Code mittelfristig durch sehr kleine Step-Aufrufe ersetzen.
- Es gibt eine bewiesene Konvention fuer alle weiteren Steps.

## Phase 2: Dispatch-Entscheidung

Ziel: Crawl-Intervall zuerst im Dispatcher nutzbar machen.

Umsetzung:

- `plan_dispatch` implementieren.
- Inputs: Source-Zeile mit `active`, `source_status`, `type`, `configuration_status`, `effective_policy_json`, `detected_policy_json`, `next_allowed_crawl_at`, `last_crawl_status`.
- Outputs: `should_dispatch`, `dispatch_reason`, `next_allowed_crawl_at`, `effective_policy`.
- Tests fuer:
  - aktive faellige Quelle,
  - `next_allowed_crawl_at` in Zukunft,
  - HTML-Konfiguration invalid,
  - `last_crawl_status = running`,
  - manuell/force Kontext.
- n8n-Dispatch-Workflow bekommt einen Python-Step vor `Execute Workflow`.

Ergebnis:

- Der 3-Stunden-Trigger startet nicht mehr pauschal alle aktiven Quellen.
- Erste echte Source-Policy wirkt produktiv.

## Phase 3: Source-Sync entkoppeln

Ziel: Source-Sync robust machen und Analyse-Status sichtbar speichern.

Umsetzung:

- `normalize_source` im Source-Sync-Workflow nutzen.
- `analyze_source` in zwei Teile splitten:
  - guenstige Typ-Erkennung,
  - HTML-Selector-Ermittlung/Validierung.
- `validate_source` oder Teil von `analyze_source` einfuehren.
- Data-Table-Felder `source_status`, `analysis_error`, `configuration_status`, `configuration_error` nutzen.
- Deaktivierung nicht mehr gelieferter Quellen auf `last_seen_in_infl0_at` umstellen.

Ergebnis:

- infl0-Quellen werden schnell gespiegelt.
- Langsame/fehlerhafte HTML-Analyse blockiert nicht mehr den gesamten Sync.
- Der Artikel-Crawl verarbeitet nur `ready` Quellen.

## Phase 4: Candidate-First-Crawl

Ziel: teure Detailabrufe erst nach History-/Policy-Entscheidung ausfuehren.

Umsetzung:

- `list_candidates` fuer RSS und Podcast-RSS implementieren.
- HTML-Kandidaten aus Listing-Links implementieren.
- `filter_candidates` implementieren.
- n8n-Crawl-Workflow umbauen:
  - `Python: Fetch + Expand` ersetzen durch `List Candidates`,
  - History-Lookup vor Detailfetch,
  - `Filter Candidates`,
  - nur `candidate_decision = fetch` geht zu `Fetch Detail`.
- `fetch_detail` und `finalize_item` implementieren.

Ergebnis:

- Bekannte alte RSS-/Podcast-Eintraege verursachen keinen Detailabruf mehr.
- HTML-Quellen werden wieder als produktiver Pfad moeglich.

## Phase 5: Policy-Erkennung

Ziel: Quellenhinweise automatisch erkennen und in Dispatch/Crawl einbeziehen.

Umsetzung:

- `inspect_source_policy` implementieren.
- RSS `ttl`, `skipHours`, `skipDays` lesen.
- HTTP Header `Cache-Control`, `Expires`, `ETag`, `Last-Modified` erfassen.
- `Retry-After` bei Fehlern in Status/Policy ueberfuehren.
- Optional robots `Crawl-delay`.
- `detected_policy_json` und `effective_policy_json` speichern.

Ergebnis:

- Crawl-Intervalle koennen aus Quelle + manueller Policy entstehen.
- Rate-Limits und Cache-Hinweise werden nachvollziehbar.

## Phase 6: Item-Modell und neue Quellenfamilien

Ziel: Von `article` zu allgemeinerem `item` wachsen.

Umsetzung:

- `finalize_item` als kanonischen Namen etablieren, `article` als kompatiblen Alias behalten.
- `item_kind`, `parent_item_id`, `position`, `origin_ref` einfuehren.
- Einen ersten neuen Adapter auswaehlen:
  - Mastodon fuer soziale Quellen, oder
  - PDF/EPUB fuer lange Dokumente, oder
  - Paper-Feed fuer Research.
- `segment_content` fuer lange Quellen konzipieren und testen.

Ergebnis:

- infl0 kann perspektivisch nicht nur Artikel, sondern Lern-Items aus vielen Quellen aufnehmen.

## Empfohlener erster Sprint

Der erste Sprint sollte klein sein und die Architektur beweisen:

1. Step-Envelope und CLI-Runner bauen.
2. `normalize_source` implementieren.
3. `build_ingest_body` als Step wrappen.
4. `plan_dispatch` implementieren.
5. Tests fuer diese drei Steps.
6. n8n-Doku mit Beispiel-Code-Nodes aktualisieren.

Danach koennen wir den Dispatch-Workflow zuerst produktiv verbessern, bevor wir den grossen Crawl-Workflow umbauen.

## Offene Entscheidungen vor Implementierung

- CLI-Aufruf: einzelne Module pro Step oder gemeinsamer `run_step` als Einstieg?
- Soll der Envelope immer `items[]` liefern, auch wenn ein Step genau ein Item erwartet?
- Welche Default-Policy gilt ohne explizite Quelle: 3 Stunden, 6 Stunden oder source-spezifisch?
- Wie behandeln wir manuelle Dispatches: Intervall ignorieren, aber `Retry-After` respektieren?
- Wollen wir `article` im n8n-Workflow kurzfristig behalten und nur intern `item` vorbereiten?
