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

Vor dem HTTP-Node: Body auf `{{ $json.infl0_ingest_body }}` setzen (ggf. „JSON“-Modus).

## Abhängigkeiten

Siehe `../requirements-n8n.txt` bzw. Root-`pyproject.toml` – im Runner **`pip install -e /data/TopicKnowledgeCrawler`** (empfohlen).
