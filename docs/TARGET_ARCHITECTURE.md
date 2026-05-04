# Zielarchitektur

Diese Notiz definiert das Ziel fuer die naechste Entwicklungsstufe des TopicKnowledgeCrawler. Der Fokus liegt nicht mehr auf einem eigenstaendigen Crawler-Produkt, sondern auf einer robusten, gut orchestrierbaren Ingestion- und Aufbereitungs-Pipeline fuer infl0.

Der konkrete Umsetzungsplan ist in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) beschrieben.

## Grundentscheidung

n8n ist aktuell die produktive Orchestrierung. Das darf so bleiben. Die Python-Schicht soll deshalb nicht kuenstlich eine vollstaendige Applikation simulieren, sondern entweder:

1. eine schlanke, gut testbare Library fuer Parsing, Normalisierung und Entscheidungslogik sein, oder
2. als separate Library ganz entfallen, wenn der Python-Code in n8n klein, explizit und wartbar bleibt.

Beide Varianten sind akzeptabel, solange der fachliche Workflow abstrakt dokumentiert ist und nicht nur als n8n-JSON existiert.

## Ziel

Wir wollen eine Pipeline, die Quellen intelligent, ruecksichtsvoll und nachvollziehbar verarbeitet:

- Quellen aus infl0 synchronisieren.
- Quellen klassifizieren: RSS, Podcast-RSS, HTML oder unbekannt.
- Perspektivisch weitere Quellenfamilien unterstuetzen: soziale Netzwerke, Dokumente, Buecher, Paper-Feeds und andere Wissensquellen.
- HTML-Quellen mit validierter Selector-Konfiguration nutzbar machen.
- Source-Hinweise erkennen: RSS `ttl`, `skipHours`, HTTP Cache-Header, `Retry-After`, optional robots `Crawl-delay`.
- Crawl-Intervalle und Rate-Limits pro Quelle respektieren.
- Vor teuren Detailabrufen entscheiden, ob ein Artikel ueberhaupt relevant ist.
- Nur neue oder sinnvoll aktualisierbare Inhalte verarbeiten.
- Lange Quellen in sinnvolle Lern- und Timeline-Happen zerlegen.
- Enrichment und Ingest weiterhin transparent ueber n8n steuern.
- infl0 kann den Crawl-Prozess perspektivisch starten und Status sehen.

## Produktvision

infl0 soll die Lese- und Lernapp fuer Nutzerinnen sein: ein kompakter Inflow, in dem alle spannenden Informationsquellen zu ihren Themen sauber aufbereitet, lernbar und erfassbar erscheinen.

Die Pipeline soll nicht nur "Artikel holen", sondern Wissensquellen in konsumierbare infl0-Items verwandeln:

- aktuelle Artikel aus RSS/Atom und HTML-Quellen,
- Podcast-Episoden und Shownotes,
- Posts oder Threads aus sozialen Netzwerken wie Mastodon,
- neue wissenschaftliche Paper oder Paper-Hinweise,
- Buecher und lange Dokumente aus PDF oder EPUB,
- spaeter weitere persoenliche oder kuratierte Wissensquellen.

Der gemeinsame Nenner ist nicht das technische Quellformat, sondern das Ziel: Nutzerinnen sollen neue Informationen effizient erfassen, wiederfinden und lernen koennen.

## Nicht-Ziel

- Kein eigenstaendiger Scheduler im Python-Projekt.
- Keine eigene Python-Datenbank, solange n8n Data Tables oder infl0 den Zustand halten.
- Kein monolithischer Python-Crawler, der n8n nur noch als Startknopf benutzt.
- Keine n8n-spezifische Fachlogik, die nicht zusaetzlich abstrakt beschrieben ist.

## Abstrakter Workflow

Der Workflow soll unabhaengig von n8n in fachliche Schritte zerlegt sein:

1. `sync_sources`: Hole Quellen aus infl0 oder einer anderen Quelle.
2. `normalize_source`: Normalisiere Felder wie `crawl_key`, `url`, `name`.
3. `analyze_source`: Bestimme `type` und ggf. HTML-Konfiguration.
4. `validate_source`: Pruefe, ob die Quelle crawlbar ist.
5. `inspect_source_policy`: Erkenne technische Crawl-Hinweise.
6. `plan_dispatch`: Entscheide, ob die Quelle jetzt gestartet werden darf.
7. `list_candidates`: Ermittle guenstig Artikel-/Episoden-Kandidaten.
8. `filter_candidates`: Entscheide vor Detailabruf, welche Kandidaten verarbeitet werden.
9. `fetch_detail`: Lade und extrahiere genau einen Artikel/eine Episode.
10. `segment_content`: Zerlege lange Inhalte optional in sinnvolle Einheiten.
11. `finalize_item`: Berechne Hashes und technische Metadaten.
12. `enrich_item`: Erzeuge Teaser, Summary, Kategorien, Tags und Rating.
13. `ingest_item`: Sende den finalen Payload an infl0.
14. `record_status`: Speichere Run-, Source- und Itemstatus.

n8n ist eine konkrete Implementierung dieser Schritte. Ein anderes System muesste dieselben Schritte und Datenvertraege nachbauen koennen.

## Quellenfamilien

Die Architektur sollte Quellenfamilien unterscheiden, weil sie unterschiedliche Kandidaten-, Fetch- und Segmentierungslogik brauchen.

### Feed- und Webquellen

Beispiele:

- RSS/Atom
- Podcast-RSS
- HTML-Listing-Seiten

Typische Einheit:

- Artikel
- Episode
- Link aus einer Listing-Seite

Besonderheiten:

- haeufige Updates,
- Rate-Limits und Cache-Header,
- alte Items koennen meist nach einem Refresh-Fenster ignoriert werden,
- Detailseiten sind oft der teuerste Schritt.

### Soziale Quellen

Beispiele:

- Mastodon-Accounts, Hashtags oder Listen,
- perspektivisch andere soziale Netzwerke, sofern API/Export/Feed verfuegbar und rechtlich/technisch sauber nutzbar.

Typische Einheit:

- Post,
- Thread,
- Link-Sammlung,
- Diskussion.

Besonderheiten:

- deutlich staerkeres Rate-Limiting,
- Duplikate und Reposts/Boosts,
- kurze Inhalte mit viel Kontextverlust,
- Thread-Zusammenfassung kann wichtiger sein als Einzelpost-Zusammenfassung.

### Dokumente und Buecher

Beispiele:

- PDF,
- EPUB,
- lange Reports,
- Whitepaper,
- Buecher.

Typische Einheit:

- Kapitel,
- Abschnitt,
- semantischer Chunk,
- Lernkarte oder Timeline-Item.

Besonderheiten:

- eine Quelle erzeugt viele infl0-Items,
- Segmentierung ist ein Kernschritt, nicht nur ein Detail,
- Fortschritt, Reihenfolge und Kontext muessen erhalten bleiben,
- Updates sind selten; wichtiger sind Idempotenz, Versionierung und Wiederaufnahme.

### Paper- und Research-Quellen

Beispiele:

- Paper-Feeds,
- Suchalerts,
- Scholar-/Preprint-Quellen, sofern verfuegbar,
- manuell gespeicherte Paper.

Typische Einheit:

- Paper-Hinweis,
- Abstract,
- Volltext-Abschnitt,
- Methoden-/Ergebnis-Zusammenfassung.

Besonderheiten:

- Metadaten sind wichtig: Autorinnen, Venue, Jahr, DOI/arXiv-ID,
- Relevanzfilter ist wichtiger als blinde Aufnahme,
- Zusammenfassung sollte wissenschaftliche Aussagen vorsichtig und nachvollziehbar darstellen.

## Einheitliches Item-Modell

Unabhaengig von der Quelle soll die Pipeline am Ende infl0-Items erzeugen. Ein Item kann ein Artikel, Post, Thread, Kapitel, Abschnitt oder Paper sein.

Gemeinsame Felder:

- `item_id`: stabile ID fuer genau dieses Item.
- `source_key`: stabile ID der Quelle.
- `source_type`: Quellenfamilie oder konkreter Typ.
- `title`
- `link` oder `origin_ref`
- `author`
- `publishedAt`
- `updatedAt`
- `content_md`
- `content_hash`
- `position`: optional fuer Reihenfolge innerhalb langer Quellen.
- `parent_item_id`: optional fuer Kapitel/Abschnitte/Threads.
- `item_kind`: `article`, `episode`, `post`, `thread`, `chapter`, `section`, `paper`, `abstract`.

Der bisherige Begriff `article` bleibt fuer RSS/HTML passend, sollte im Zielmodell aber zu `item` generalisiert werden. Die n8n-Workflows koennen intern noch `article` verwenden, solange die Abstraktion dokumentiert ist.

## Option A: Schlanke Library-Schicht

Die Library bleibt, aber sie wird bewusst klein gehalten.

Sie enthaelt:

- Datennormalisierung: `crawl_key`, Source-Zeilen, Candidate-Zeilen.
- Parser: RSS/Atom, Podcast-RSS, HTML-Listing, HTML-Detailseite.
- perspektivisch Parser/Adapter fuer soziale Quellen, Dokumente und Paper-Metadaten.
- Policy-Helfer: erkannte Hinweise normalisieren, effektive Policy berechnen, `next_allowed_crawl_at` bestimmen.
- Entscheidungsfunktionen: `should_dispatch`, `should_fetch_candidate`.
- Segmentierungshelfer fuer lange Dokumente.
- Payload-Bau: infl0-Ingest-Body.
- Tests fuer Parser, Policy und Entscheidungen.

Sie enthaelt nicht:

- n8n-Node-Ablaufsteuerung.
- Persistenzlogik fuer n8n Data Tables.
- LLM-Orchestrierung.
- lange End-to-End-Crawl-Jobs.
- eigene Scheduler- oder Queue-Logik.

Vorteile:

- Entscheidungslogik ist testbar.
- n8n-Code-Nodes bleiben klein.
- Spaeterer Wechsel auf ein anderes Orchestrierungssystem bleibt realistischer.
- Gemeinsame Logik fuer RSS, HTML und Podcast kann sauber wiederverwendet werden.

Nachteile:

- Packaging und Deployment der Library im n8n-Runner bleiben noetig.
- Es gibt weiterhin eine Grenze zwischen Workflow und Code, die gepflegt werden muss.

## Option B: Python vollstaendig in n8n

Die separate Library-Schicht faellt weg oder wird nur noch als Referenz/Archiv genutzt. Python-Code lebt direkt in n8n-Code-Nodes.

Voraussetzungen:

- Jeder Python-Node bleibt klein und hat einen klaren JSON-Vertrag.
- Gemeinsame Hilfsfunktionen werden entweder bewusst dupliziert oder als kopierbare Snippets dokumentiert.
- Der abstrakte Workflow und die Datenvertraege sind im Repo dokumentiert.
- Kritische Logik wird durch Beispiel-Inputs/-Outputs und ggf. lokale Test-Skripte abgesichert.

Vorteile:

- Weniger Deployment-Komplexitaet.
- n8n-Workflow ist die eine sichtbare Wahrheit.
- Schnelleres Iterieren direkt im produktiven Werkzeug.

Nachteile:

- Staerkere Bindung an n8n.
- Weniger klassische Unit-Testbarkeit.
- Hoeheres Risiko fuer Logikdrift zwischen Nodes.
- Wiederverwendung ausserhalb von n8n wird schwieriger.

## Entscheidungskriterium

Die Library lohnt sich nur, wenn sie echte Komplexitaet kapselt.

Behalten als schlanke Library:

- RSS/Atom-Parsing und Datumsnormalisierung.
- HTML-Extraktion und Markdown-Erzeugung.
- Candidate- und Policy-Entscheidungen.
- Hashing und infl0-Payload-Bau.

Nach n8n verschieben:

- Ablaufentscheidungen zwischen Nodes.
- Data-Table-Lookups und Upserts.
- Retry-/Batch-/Wait-Logik.
- AI-Enrichment-Orchestrierung.
- Status-Updates, sofern sie rein workflowbezogen sind.

Wenn eine Funktion keinen Test braucht, keine gemeinsame Wiederverwendung hat und direkt n8n-Felder verdrahtet, gehoert sie eher in n8n. Wenn eine Funktion Parser-/Policy-/Entscheidungslogik enthaelt, gehoert sie eher in die Library.

## Empfohlene Richtung

Kurzfristig: Option A, aber radikal schlank.

Die bestehende `tkcrawler`-Schicht wird nicht zu einer grossen App ausgebaut. Sie wird zu einem Toolkit fuer:

- `normalize_source`
- `inspect_source_policy`
- `plan_dispatch`
- `list_candidates`
- `filter_candidates`
- `fetch_detail`
- `segment_content`
- `finalize_item`
- `build_ingest_body`

n8n bleibt verantwortlich fuer:

- Trigger
- Tabellenzugriff
- Batches
- Waits und Retries
- AI-Agent
- Ingest-Aufruf
- Statusspeicherung

Mittelfristig kann nach jeder extrahierten Funktion entschieden werden, ob sie wirklich als Library-Funktion wertvoll ist. Falls nicht, darf sie wieder als n8n-Code-Node leben.

## Erfolgskriterien

- Der Crawl-Dispatcher startet nur faellige Quellen.
- Eine bekannte alte RSS-/Podcast-Episode verursacht keinen Detailabruf.
- HTML-Quellen koennen mit gueltiger Konfiguration produktiv verarbeitet werden.
- Lange Dokumente koennen in stabile, nachvollziehbare infl0-Items zerlegt werden.
- Neue Quellenfamilien koennen ueber Adapter ergaenzt werden, ohne den gesamten Workflow umzubauen.
- Rate-Limits und erkannte Source-Hinweise beeinflussen `next_allowed_crawl_at`.
- Der n8n-Workflow bleibt in kleinen, nachvollziehbaren Schritten debugbar.
- Der abstrakte Workflow ist so dokumentiert, dass er spaeter auf ein anderes Orchestrierungssystem uebertragbar waere.
