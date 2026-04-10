# n8n Python Runner: erlaubte Imports (`N8N_RUNNERS_EXTERNAL_ALLOW`)

## Wichtig

- Variable heißt **`N8N_RUNNERS_EXTERNAL_ALLOW`** (mit **`RUNNERS`**, Plural). `N8N_RUNNER_*` ohne **s** greift nicht.
- Die Liste ist für **Top-Level-Modulnamen** gedacht (wie nach `import x`), **nicht** für volle Pfade wie `tkcrawler.datatable`.
- Nach **`pip install -e .`** (Root-`pyproject.toml`) gibt es u. a. **`tkcrawler`** (n8n-Helfer) und **`crawler`** (Fetcher/Utils).

## Empfohlene Zeile (Runner-Container / task-runners)

```env
N8N_RUNNERS_STDLIB_ALLOW=os,sys
N8N_RUNNERS_EXTERNAL_ALLOW=tkcrawler,crawler,feedparser,trafilatura,requests,bs4,lxml,tldextract
```

- **`tkcrawler`**: Quellen-Zeile, Fetch-Dispatch, infl0-Body.
- **`crawler`**: `RssFetcher`, `HtmlFetcher`, Utils (`text_processor`, …).
- **`bs4`**: Importname von `beautifulsoup4`.

Nur für **vertrauenswürdige** Umgebungen:

```env
N8N_RUNNERS_EXTERNAL_ALLOW=*
```

## `n8n-task-runners.json`

`env-overrides` müssen auf den **Python**-Task-Runner wirken. Nach Änderung Runner neu starten.

## Installation

```bash
pip install --no-cache-dir -e /data/TopicKnowledgeCrawler
```

(`:ro`-Mount reicht: editable install schreibt nur in `site-packages`.)

Ohne pip: im Code-Node **`sys.path.insert(0, os.path.join(TOPIC_CRAWLER_ROOT, "src"))`** (steht in `n8n/python/*.py` und im Workflow-Template).
