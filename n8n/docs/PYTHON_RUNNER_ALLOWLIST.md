# n8n Python Runner: erlaubte Imports (`N8N_RUNNERS_EXTERNAL_ALLOW`)

## Wichtig

- Variable heißt **`N8N_RUNNERS_EXTERNAL_ALLOW`** (mit **`RUNNERS`**, Plural). `N8N_RUNNER_*` ohne **s** greift nicht.
- Die Liste ist für **Top-Level-Modulnamen** gedacht (wie nach `import x`), **nicht** für volle Pfade wie `src.crawler.n8n_compat.datatable`.
- Lokaler Projektcode zählt als **externes** Modul nur, wenn er per **`pip install -e`** installiert ist (siehe Root-`pyproject.toml`). Dann ist das Top-Level-Modul **`src`**.

## Empfohlene Zeile (Runner-Container / task-runners)

```env
N8N_RUNNERS_STDLIB_ALLOW=os,sys
N8N_RUNNERS_EXTERNAL_ALLOW=src,feedparser,trafilatura,requests,bs4,lxml,tldextract
```

- **`src`**: nach `pip install -e /data/TopicKnowledgeCrawler` (Mount-Pfad wie in Compose).
- **`bs4`**: zu `beautifulsoup4` (Importname).
- **`lxml`**: oft indirekt nötig; sicher mit aufnehmen.

Nur für **vertrauenswürdige** Umgebungen:

```env
N8N_RUNNERS_EXTERNAL_ALLOW=*
```

## `n8n-task-runners.json`

`env-overrides` müssen auf den **Python**-Task-Runner wirken (nicht nur auf den n8n-Hauptcontainer). Nach Änderung Runner neu starten.

## Einmalig im Runner-Image / beim Start

```bash
pip install --no-cache-dir -e /data/TopicKnowledgeCrawler
```

(`:ro`-Mount reicht: editable install schreibt nur in `site-packages`.)
