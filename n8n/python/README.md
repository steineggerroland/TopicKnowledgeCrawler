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
    if planned["should_dispatch"]:
        out.append({"json": planned})
return out
```

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
