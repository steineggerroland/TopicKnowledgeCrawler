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
4. `Python: Plan Dispatch`: prueft pro Quelle Policy, Status und Faelligkeit.
5. `IF should_dispatch`.
6. `Data Table: Mark Crawl Started`: setzt `last_crawl_started_at`, `last_crawl_status = running`.
7. `Execute Workflow`: ruft Crawl-Workflow pro Quelle auf.
8. `Data Table: Mark Crawl Finished`: setzt `last_crawl_finished_at`, `last_crawl_status`, `last_crawl_error`, `next_allowed_crawl_at`.

Bei `manual` oder `force` kann `Python: Plan Dispatch` die Intervallpruefung ueberschreiben, sollte aber harte Limits wie `Retry-After` weiterhin respektieren, sofern nicht explizit anders gewuenscht.

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

Der Crawl-Workflow sollte weiterhin robust sein, falls er direkt gestartet wird. Er darf also nicht allein dem Dispatcher vertrauen.

Empfohlen:

- Dispatcher filtert grob und markiert Runs.
- Crawl-Workflow fuehrt am Anfang nochmals `plan_crawl` aus.
- Wenn `should_crawl = false`, beendet der Crawl-Workflow schnell und schreibt Status/Grund zurueck.

Diese doppelte Pruefung verhindert Fehlstarts durch manuelle Ausfuehrung oder veraltete Queue-Items.

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

## Kurzfristige Migration

Als erster kleiner Schritt reicht:

1. `next_allowed_crawl_at` als Spalte anlegen.
2. Im `Get row(s)`-Ergebnis einen Python-Filter `should_dispatch` einfuegen.
3. Nur `should_dispatch = true` an `Execute Workflow` weitergeben.
4. Nach dem Crawl `next_allowed_crawl_at` anhand eines Default-Intervalls setzen.

Danach koennen Source-Policy, erkannte RSS-/HTTP-Hinweise und Backoff schrittweise dazukommen.
