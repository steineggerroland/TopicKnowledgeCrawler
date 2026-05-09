# Crawl-Dispatch-Workflow

Diese Notiz bezieht sich auf den n8n-Workflow, der aktive Quellen aus `Infl0-crawl-sources` liest und fuer jede Quelle den eigentlichen Crawl-Workflow `infl0 - Process source, discover articles -> infl0` ausfuehrt.

## Aktueller Ablauf

1. Manual Trigger oder Schedule Trigger alle drei Stunden.
2. `Merge Triggers`.
3. `Get row(s)`: liest alle Quellen mit `active = true`, sortiert nach `updatedAt ASC`.
4. `Execute Workflow`: ruft pro Item den Crawl-Workflow im Modus `each` auf.

## Rolle im Gesamtsystem

Dieser Workflow ist der Dispatcher. Er sollte langfristig entscheiden, welche Quellen jetzt wirklich laufen duerfen. Der eigentliche Crawl-Workflow sollte weiterhin eine einzelne Quelle verarbeiten.

Damit ergibt sich diese Arbeitsteilung:

- Source-Sync-Workflow: haelt `crawl_sources` aktuell und analysiert Quellen.
- Crawl-Dispatch-Workflow: waehlt faellige Quellen aus und startet einzelne Crawls.
- Crawl-Workflow: verarbeitet eine Quelle, listet Kandidaten, fetched Details, enriched und sendet an infl0.

## Problem im aktuellen Ablauf

Der aktuelle Filter `active = true` reicht nicht mehr, sobald Quellen eigene Crawl-Intervalle, Rate-Limits oder erkannte Source-Hinweise haben.

Wenn der Dispatcher alle aktiven Quellen alle drei Stunden startet:

- werden Quellen mit laengeren Intervallen zu oft gecrawlt,
- werden Quellen mit `Retry-After` oder Rate-Limit trotzdem wieder gestartet,
- wird `rss ttl` / `skipHours` / `skipDays` nicht respektiert,
- laufen HTML-Quellen eventuell trotz `configuration_invalid`,
- blockieren langsame Quellen weiterhin regelmaessig den Workflow.

## Zielstruktur

Der Dispatcher sollte nur Quellen starten, die faellig und crawlbar sind.

Minimaler Data-Table-Filter:

- `active = true`
- `source_status = ready`
- `next_allowed_crawl_at` ist leer oder `<= now`

Zusaetzlich in n8n oder Python pruefen:

- `type` ist `rss`, `rss+podcast` oder `html`
- bei `type = html`: `configuration_status = valid`
- `last_crawl_status` ist nicht `running` oder der Lauf ist als stale erkannt
- optional: `subscriber_count > 0`

## Empfohlene Node-Kette

1. Manual Trigger, Webhook Trigger oder Schedule Trigger.
2. `Set Dispatch Context`: setzt `dispatch_mode` (`scheduled`, `manual`, `force`) und `dispatch_started_at`.
3. `Get row(s)`: grober Filter auf `active = true`.
4. `Python: Inspect Source Policy`: liest guenstige Source-Hinweise wie
   RSS `ttl`, HTTP Cache-Header und `Retry-After`.
5. `Data Table: Update Detected Policy`: speichert die erkannten Hinweise.
6. `Python: Plan Dispatch`: prueft pro Quelle Policy, Status und Faelligkeit.
7. `IF should_dispatch`.
8. `Data Table: Mark Crawl Started`: setzt `last_crawl_started_at`, `last_crawl_status = running`.
9. `Execute Workflow`: ruft Crawl-Workflow pro Quelle auf.
10. `Data Table: Mark Crawl Finished`: setzt `last_crawl_finished_at`, `last_crawl_status`, `last_crawl_error`, `next_allowed_crawl_at`.

Bei `manual` oder `force` kann `Python: Plan Dispatch` die Intervallpruefung ueberschreiben, sollte aber harte Limits wie `Retry-After` weiterhin respektieren, sofern nicht explizit anders gewuenscht.

Wichtig fuer die Verdrahtung: Der Child-Crawl-Workflow sollte das geplante Item aus `Python: Plan Dispatch` bzw. dem True-Branch des IF bekommen, nicht den Output des Data-Table-Update-Nodes. Der Update-Node kann Felder verlieren oder anders formatieren. Wenn `Execute Workflow` hinter dem Update-Node haengt, fehlen im Child leicht Felder wie `dispatch_reason` oder `effective_policy`. Besser:

- IF True -> `Data Table: Mark Crawl Started`
- IF True -> `Execute Workflow`

oder alternativ nach dem Update die geplanten Felder wieder per Merge/Set aus dem IF-Input herstellen.

## `Python: Inspect Source Policy`

Input: Source-Zeile aus `crawl_sources`.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "detected_policy_json": "{\"http_status\":200,\"rss_ttl_minutes\":60,\"etag\":\"...\"}",
  "detected_policy_checked_at": "2026-05-09T12:00:00+00:00",
  "detected_policy_error": null
}
```

Der Step trifft keine Dispatch-Entscheidung. Er erkennt nur Hinweise:

- HTTP Status
- `ETag`
- `Last-Modified`
- `Cache-Control` und `max-age`
- `Expires`
- `Retry-After`
- RSS/Atom `ttl`

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.inspect_source_policy import inspect_source_policy_item

now = datetime.now(timezone.utc).isoformat()
verify = "/etc/ssl/certs/ca-certificates.crt"

out = []
for item in _items:
    out.append(
        {
            "json": inspect_source_policy_item(
                item["json"],
                {"now": now, "verify": verify, "timeout_seconds": 10},
            )
        }
    )
return out
```

Empfohlenes Data-Table-Update danach:

- Filter: `crawl_key = {{$json.crawl_key}}`
- `detected_policy_json = {{$json.detected_policy_json}}`
- `detected_policy_checked_at = {{$json.detected_policy_checked_at}}`
- `detected_policy_error = {{$json.detected_policy_error}}`

## `Python: Plan Dispatch`

Input: Source-Zeile aus `crawl_sources`.

Output:

```json
{
  "crawl_key": "https://example.com/feed.xml",
  "should_dispatch": true,
  "dispatch_reason": "due",
  "next_allowed_crawl_at": "2026-05-04T15:00:00+02:00",
  "effective_policy": {
    "crawl_interval_minutes": 180,
    "rate_limit_per_minute": 10,
    "refresh_window_days": 7
  }
}
```

Moegliche `dispatch_reason`-Werte:

- `due`
- `manual_force`
- `not_due`
- `inactive`
- `source_not_ready`
- `html_configuration_invalid`
- `rate_limited`
- `retry_after_active`
- `already_running`

## Intervall-Logik

Die Intervall-Entscheidung sollte aus `effective_policy_json`, `detected_policy_json`, `last_crawl_finished_at` und `next_allowed_crawl_at` entstehen.

Prioritaet:

1. Wenn `next_allowed_crawl_at` in der Zukunft liegt: nicht dispatchen.
2. Wenn ein hartes `Retry-After` aktiv ist: nicht dispatchen.
3. Wenn `source_status != ready`: nicht dispatchen.
4. Wenn HTML-Konfiguration fehlt oder invalid ist: nicht dispatchen.
5. Wenn `last_crawl_status = running` und nicht stale: nicht dispatchen.
6. Sonst dispatchen, wenn das effektive Intervall abgelaufen ist.

`next_allowed_crawl_at` sollte nach jedem Crawl neu berechnet werden:

- erfolgreiche Quelle: `last_crawl_finished_at + crawl_interval_minutes`
- 429/503 mit `Retry-After`: `now + retry_after`
- Fehler ohne Retry-After: kurzer Backoff, zum Beispiel 15 bis 60 Minuten
- manuell gesetzte Policy darf konservativer sein als automatisch erkannte Hinweise

## Auswirkungen auf den Crawl-Workflow

Der Crawl-Workflow bekommt im Normalfall bereits ein von `Python: Plan Dispatch` geplantes Item. Wenn er vom Dispatcher gestartet wird, sollte er nicht direkt erneut `plan_dispatch` ausfuehren, nachdem `next_allowed_crawl_at` und `last_crawl_status` bereits geschrieben wurden. Sonst kann der Child-Workflow entweder faelschlich `not_due` werden oder, bei erzwungenem Re-Check, `dispatch_reason = manual_force` erzeugen.

Empfohlen:

- Dispatcher filtert und markiert Runs.
- Child-Crawl-Workflow startet direkt mit `List Candidates`, wenn `should_dispatch = true` bereits vorhanden ist.
- Fuer direkte manuelle Child-Starts sollte ein separater kleiner Guard genutzt werden, der nur Pflichtfelder validiert (`crawl_key`, `url`, `type`), aber nicht erneut `next_allowed_crawl_at` berechnet.

Diese Trennung verhindert, dass der Dispatcher-Entscheid im Child versehentlich ueberschrieben wird.

## Crawl-Abschluss aus Aggregates

Wenn der Child-Crawl-Workflow seine Endpfade aggregiert, kann ein letzter Python-Step daraus den Source-Update-Payload bauen. Erwartete Aggregate-Felder:

- `candidateCount`
- `skipped` oder `skippedCandidates`
- `fetchErrorred` oder `fetchErrored`
- `unchanged`
- `processed`
- `llmFailed`

Die Felder duerfen Arrays oder bereits Zahlen sein.

Empfohlene n8n-Verdrahtung:

- Direkt nach `List Candidates` die Kandidaten zaehlen und `candidateCount` bis
  zum Abschlussflow mitgeben.
- Kandidaten mit `candidate_decision != fetch` in einen eigenen Abschlusszweig
  fuehren und als `skipped` aggregieren.
- Wenn `List Candidates` keine Items erzeugt, trotzdem ein Abschluss-Item mit
  `crawl_key` und `candidateCount = 0` erzeugen. Sonst hat n8n kein Item mehr,
  das den Crawl erfolgreich abschliessen kann.
- Der bisherige `if fetch`-False-Branch sollte daher nicht leer bleiben,
  sondern in ein skipped/no-fetch Aggregat laufen.

n8n Native-Python:

```python
from datetime import datetime, timezone

from tkcrawler.steps.finalize_crawl_run import finalize_crawl_run_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    out.append({"json": finalize_crawl_run_item(item["json"], {"now": now})})
return out
```

Der Step setzt:

```json
{
  "last_crawl_status": "success|partial_failed|failed",
  "last_crawl_finished_at": "2026-05-08T12:00:00+00:00",
  "last_crawl_error": null,
  "crawl_total_count": 12,
  "crawl_candidate_count": 12,
  "crawl_skipped_count": 0,
  "crawl_fetch_error_count": 0,
  "crawl_unchanged_count": 7,
  "crawl_processed_count": 5,
  "crawl_llm_failed_count": 0,
  "last_crawl_result_json": "{\"total_count\":12,...}",
  "consecutive_error_count": 0
}
```

Status-Regeln:

- `success`: keine Fetch- oder LLM-Fehler.
- `partial_failed`: mindestens ein Erfolg (`processed` oder `unchanged`) und mindestens ein Fehler.
- `failed`: Fehler, aber keine erfolgreichen Items.

Empfohlenes Data-Table-Update in `crawl_sources`:

- Filter: `crawl_key = {{$json.crawl_key}}`
- `last_crawl_status = {{$json.last_crawl_status}}`
- `last_crawl_finished_at = {{$json.last_crawl_finished_at}}`
- `last_crawl_error = {{$json.last_crawl_error}}`
- `last_crawl_result_json = {{$json.last_crawl_result_json}}`
- `crawl_total_count = {{$json.crawl_total_count}}`
- optional `crawl_candidate_count = {{$json.crawl_candidate_count}}`
- optional `crawl_skipped_count = {{$json.crawl_skipped_count}}`
- `crawl_fetch_error_count = {{$json.crawl_fetch_error_count}}`
- `crawl_unchanged_count = {{$json.crawl_unchanged_count}}`
- `crawl_processed_count = {{$json.crawl_processed_count}}`
- `crawl_llm_failed_count = {{$json.crawl_llm_failed_count}}`
- `consecutive_error_count = {{$json.consecutive_error_count}}`
- optional `last_successful_crawl_at = {{$json.last_successful_crawl_at}}`

## Tabellenerweiterungen

Der Dispatcher braucht diese Felder in `crawl_sources`:

- `effective_policy_json`
- `detected_policy_json`
- `next_allowed_crawl_at`
- `last_crawl_started_at`
- `last_crawl_finished_at`
- `last_crawl_status`
- `last_crawl_error`
- `last_dispatch_reason`

Optional:

- `crawl_running_since`
- `last_successful_crawl_at`
- `consecutive_error_count`
- `last_http_status`
- `crawl_candidate_count`
- `crawl_skipped_count`

## Kurzfristige Migration

Als erster kleiner Schritt reicht:

1. `next_allowed_crawl_at` als Spalte anlegen.
2. Im `Get row(s)`-Ergebnis einen Python-Filter `should_dispatch` einfuegen.
3. Nur `should_dispatch = true` an `Execute Workflow` weitergeben.
4. Nach dem Crawl `next_allowed_crawl_at` anhand eines Default-Intervalls setzen.

Danach koennen Source-Policy, erkannte RSS-/HTTP-Hinweise und Backoff schrittweise dazukommen.
