# Python-Skripte für n8n Code Nodes

Jede Datei ist so gedacht, dass du den **Inhalt** (ohne führende Kommentare optional) in einen **Python Code**-Node kopierst – oder das Repo mountest und `Path(__file__)` durch einen festen Pfad zu deinem Clone ersetzt.

## Pfade

Setze **`TOPIC_CRAWLER_ROOT`** auf das **Repository-Root** (enthält `src/tkcrawler` und `src/crawler`). Die Skripte hängen zusätzlich `…/src` an `sys.path`. Mit **`pip install -e .`** im Container ist `PYTHONPATH` optional. Beispiel Docker:

```yaml
environment:
  TOPIC_CRAWLER_ROOT: /data/TopicKnowledgeCrawler
volumes:
  - /opt/TopicKnowledgeCrawler:/data/TopicKnowledgeCrawler:ro
```

Die Skripte nutzen standardmäßig `/data/TopicKnowledgeCrawler`, falls die Variable fehlt.

## Dateien

| Datei | Rolle |
|--------|--------|
| `code_normalize_crawl_key.py` | Nur `crawl_key` aus `url` berechnen (infl0-kompatibel). |
| `code_analyze_source_row.py` | Wie `SourceAnalyzer`: `type` rss/html + bei HTML `configuration_json` (LLM). |
| `code_fetch_expand.py` | Quelle → n Artikel (RSS/HTML/Podcast). |
| `code_merge_enrichment_for_infl0.py` | `article` + optionale LLM-Felder → `infl0_ingest_body`. |

Geplante Aufteilung des groben Fetch-Schritts: siehe [`../docs/CURRENT_WORKFLOW_MIGRATION.md`](../docs/CURRENT_WORKFLOW_MIGRATION.md). Dort sind die kuenftigen Node-Vertraege fuer `analyze_source`, `inspect_source_policy`, `plan_crawl`, `list_candidates`, `filter_candidates`, `fetch_detail` und `finalize_article` beschrieben.

## Portable Steps

Neue portable Steps liegen unter `tkcrawler.steps` und koennen sowohl in n8n als auch per CLI genutzt werden:

```bash
python -m tkcrawler.cli.run_step normalize_source < input.json
python -m tkcrawler.cli.run_step plan_dispatch < input.json
python -m tkcrawler.cli.run_step list_candidates < input.json
python -m tkcrawler.cli.run_step filter_candidates < input.json
python -m tkcrawler.cli.run_step fetch_detail < input.json
python -m tkcrawler.cli.run_step finalize_item < input.json
python -m tkcrawler.cli.run_step limit_llm_items < input.json
python -m tkcrawler.cli.run_step build_ingest_body < input.json
```

Wichtig: In n8n werden die `*_item(...)`-Funktionen genutzt. Sie bekommen direkt `item["json"]`, also das flache Payload aus `$json`. Der portable Envelope mit `{ "item": ..., "context": ... }` ist fuer CLI/Runner gedacht, nicht fuer normale n8n-Code-Nodes.

n8n-Code-Node-Beispiel fuer `normalize_source`:

```python
from tkcrawler.steps.normalize_source import normalize_source_item

out = []
for item in _items:
    out.append({"json": normalize_source_item(item["json"])})
return out
```

n8n-Code-Node-Beispiel fuer den Dispatch-Workflow:

```python
from datetime import datetime, timezone

from tkcrawler.steps.plan_dispatch import plan_dispatch_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    planned = plan_dispatch_item(
        item["json"],
        {"now": now, "dispatch_mode": "scheduled"},
    )
    out.append({"json": planned})
return out
```

Danach in n8n per IF auf `{{ $json.should_dispatch }}` verzweigen. Wenn der Python-Node bereits filtert, gibt er bei lauter `not_due`-Quellen `[]` zurueck und der Workflow endet ohne False-Branch.

n8n-Code-Node-Beispiel fuer `List Candidates V2` im Child-Crawl-Workflow:

```python
from tkcrawler.steps.list_candidates import list_candidates_items

out = []
for item in _items:
    for candidate in list_candidates_items(item["json"]):
        out.append({"json": candidate})
return out
```

Dieser Step liest RSS/Podcast-RSS und gibt Kandidaten zurueck, ohne Artikel-Detailseiten zu laden.

n8n-Code-Node-Beispiel fuer `Filter Candidates V2` nach History-Lookup/Merge:

```python
from datetime import datetime, timezone

from tkcrawler.steps.filter_candidates import filter_candidate_item

now = datetime.now(timezone.utc).isoformat()
out = []
for item in _items:
    filtered = filter_candidate_item(item["json"], {"now": now})
    out.append({"json": filtered})
return out
```

Danach per IF auf `{{ $json.candidate_decision === "fetch" }}` verzweigen. `skip_too_old` bleibt sichtbar im False-Branch und verursacht keinen Detailabruf.

n8n-Code-Node-Beispiel fuer `Fetch Detail V2` nach `candidate_decision == fetch`:

```python
from tkcrawler.steps.fetch_detail import fetch_detail_item

verify = "/etc/ssl/certs/ca-certificates.crt"
out = []
for item in _items:
    try:
        out.append({"json": fetch_detail_item(item["json"], {"verify": verify})})
    except Exception as exc:
        j = dict(item["json"])
        j["fetch_detail_error"] = str(exc)
        j["candidate_decision"] = "fetch_failed"
        out.append({"json": j})
return out
```

Dieser Step laedt fuer RSS-Artikel die Detailseite und erzeugt `article.content_md`. Bei Podcast-RSS bevorzugt er vorhandene Feed-/Shownotes-Inhalte.

n8n-Code-Node-Beispiel fuer `Finalize Item V2` nach erfolgreichem Detailfetch:

```python
from tkcrawler.steps.finalize_item import finalize_item

out = []
for item in _items:
    out.append({"json": finalize_item(item["json"])})
return out
```

Dieser Step ergaenzt `content_hash`, `source_type` und `tld` am `article` und setzt `content_hash` auch flach auf dem n8n-Item. Danach kann der bestehende History-/LLM-Pfad genutzt werden.

n8n-Code-Node-Beispiel fuer `Limit LLM Items V2` direkt vor dem AI-Agent-Branch:

```python
from tkcrawler.steps.limit_llm_items import limit_llm_items

out = []
for limited in limit_llm_items(_items and [item["json"] for item in _items] or []):
    out.append({"json": limited})
return out
```

Der Step liest `effective_policy.max_llm_items_per_run` pro Quelle. Danach per IF auf `{{ $json.llm_decision === "process" }}` verzweigen. Ueberschuessige Items bekommen `llm_decision = "skip_run_limit"` und koennen ohne LLM gespeichert oder fuer spaetere Laeufe sichtbar gehalten werden.

n8n-Code-Node-Beispiel fuer `build_ingest_body` mit flachem Enrichment-Format:

```python
from tkcrawler.steps.build_ingest_body import build_ingest_body_item

out = []
for item in _items:
    out.append({"json": build_ingest_body_item(item["json"])})
return out
```

Vor dem HTTP-Node: Body auf `{{ $json.infl0_ingest_body }}` setzen (ggf. „JSON“-Modus).

## Abhängigkeiten

Siehe `../requirements-n8n.txt` bzw. Root-`pyproject.toml` – im Runner **`pip install -e /data/TopicKnowledgeCrawler`** (empfohlen).
