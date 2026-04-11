# n8n Python Runner: erlaubte Imports (`N8N_RUNNERS_EXTERNAL_ALLOW`)

## Wichtig

- Variable heißt **`N8N_RUNNERS_EXTERNAL_ALLOW`** (mit **`RUNNERS`**, Plural). `N8N_RUNNER_*` ohne **s** greift nicht.
- Die Liste ist für **Top-Level-Modulnamen** gedacht (wie nach `import x`), **nicht** für volle Pfade wie `tkcrawler.datatable`.
- Mit **`pip install -e .`** im Runner-Image (siehe `n8n/docker/Dockerfile.task-runner-python.example`) sind **`tkcrawler`** und **`crawler`** normale Site-Packages — keine `sys.path`-Tricks in den Code-Nodes, daher braucht es **kein** `N8N_RUNNERS_STDLIB_ALLOW=os,sys` mehr; Standard reicht (**`N8N_RUNNERS_STDLIB_ALLOW=`** leer bzw. Variable weglassen, je nach n8n-Default).

## Empfohlene Zeile (Runner-Container / task-runners)

```env
N8N_RUNNERS_EXTERNAL_ALLOW=tkcrawler,crawler,feedparser,trafilatura,requests,bs4,lxml,tldextract
```

- **`tkcrawler`**: Quellen-Zeile, Fetch-Dispatch, infl0-Body.
- **`crawler`**: `RssFetcher`, `HtmlFetcher`, Utils (`text_processor`, …).
- **`bs4`**: Importname von `beautifulsoup4`.

Sobald ein Code-Node wieder **`import os`** / **`import sys`** nutzt, musst du **`os,sys`** (oder `*`) in **`N8N_RUNNERS_STDLIB_ALLOW`** ergänzen.

Nur für **vertrauenswürdige** Umgebungen:

```env
N8N_RUNNERS_EXTERNAL_ALLOW=*
```

## `n8n-task-runners.json`

`env-overrides` müssen auf den **Python**-Task-Runner wirken. Nach Änderung Runner neu starten.

## Installation

Im Image (empfohlen): siehe **`n8n/docker/Dockerfile.task-runner-python.example`**.

Manuell im Container:

```bash
pip install --no-cache-dir -e /opt/TopicKnowledgeCrawler
```

(`:ro`-Mount reicht: editable install schreibt nur in `site-packages`.)
