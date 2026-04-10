# n8n Docker: TopicKnowledgeCrawler einbinden

## 1) Repo auf dem Host

```bash
cd ~
git clone <dein-repo> crawler
# oder: git pull in ~/crawler
```

## 2) `.env` neben `docker-compose.yaml`

```env
# Pfad auf dem **Host** zum geklonten Repo (Ordner mit `src/`)
CRAWLER_HOST_PATH=/home/infl0/crawler
```

## 3) Compose

Siehe [`docker-compose.server.example.yaml`](docker-compose.server.example.yaml):

- **`TOPIC_CRAWLER_ROOT=/data/TopicKnowledgeCrawler`** und **`PYTHONPATH`** im `x-shared`-Block
- **Volume** `${CRAWLER_HOST_PATH}:/data/TopicKnowledgeCrawler:ro` auf **`n8n`** und **`n8n-worker`** (Python Task Runner)

Passe deine bestehende `docker-compose.yaml` entsprechend an (oder merge per Diff).

## 4) Python-Pakete im Runner-Image

Das `:ro`-Mount liefert nur den Code; **feedparser, trafilatura, …** müssen im **Python-Runner-Image** installiert sein (`./runners` Dockerfile), z. B.:

```dockerfile
COPY crawler-requirements.txt /tmp/crawler-requirements.txt
RUN pip install --no-cache-dir -r /tmp/crawler-requirements.txt
```

wobei `crawler-requirements.txt` eine Kopie von `n8n/requirements-n8n.txt` aus diesem Repo ist (oder per `curl` beim Build).

Ohne diese Pakete schlagen Python Code Nodes mit `import feedparser` / `trafilatura` fehl.

### 4b) Projekt als Paket + Allowlist `src`

n8n erlaubt **keine** freien Imports von `PYTHONPATH` allein: `src.crawler…` muss als **installiertes** Paket erkennbar sein.

```bash
pip install --no-cache-dir -e /data/TopicKnowledgeCrawler
```

Dann **`N8N_RUNNERS_EXTERNAL_ALLOW`** mit Top-Level-Name **`src`** (nicht `src.crawler.n8n_compat…`). Details: [`docs/PYTHON_RUNNER_ALLOWLIST.md`](docs/PYTHON_RUNNER_ALLOWLIST.md).

## 5) infl0 (optional in n8n Env)

```env
INFL0_BASE_URL=https://reader.neurospicy.icu
INFL0_CRAWLER_API_KEY=<NUXT_CRAWLER_API_KEY>
```

Diese Variablen in der n8n-Compose-Umgebung setzen (oder in n8n UI unter Environment), damit der HTTP-Request-Node `{{$env.INFL0_BASE_URL}}` nutzen kann.
