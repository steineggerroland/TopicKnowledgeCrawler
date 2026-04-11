# n8n Docker: TopicKnowledgeCrawler einbinden

## Empfohlen: Projekt im Python-Runner-Image (`pip install -e`)

Damit entfällt manuelles `git clone` auf dem Host für den Runner. Baue ein eigenes Image aus diesem Repo:

```bash
cd /path/to/TopicKnowledgeCrawler
docker build -f n8n/docker/Dockerfile.task-runner-python.example -t n8n-runner-python:local .
```

In Compose den **Python-Task-Runner** (bzw. den Service, der `n8nio/runners` nutzt) auf **`n8n-runner-python:local`** umstellen. Das Image kopiert `pyproject.toml`, `README.md` und `src/` nach `/opt/TopicKnowledgeCrawler` und führt **`uv pip install -e /opt/TopicKnowledgeCrawler`** aus.

Optional: Im Dockerfile die auskommentierte **`git clone`**-Variante nutzen (`TKCRAWLER_GIT_URL` / `TKCRAWLER_GIT_REF`), wenn du beim Build aus einem Remote ziehen willst statt `COPY`.

Allowlists und Variablen: [`docs/PYTHON_RUNNER_ALLOWLIST.md`](docs/PYTHON_RUNNER_ALLOWLIST.md). Beispiel-`n8n-task-runners.json`: [`docker/n8n-task-runners.example.json`](docker/n8n-task-runners.example.json).

## Alternative: Repo per Volume auf dem Host (Dev / schnelle Iteration)

### 1) Repo auf dem Host

```bash
cd ~
git clone <dein-repo> crawler
# oder: git pull in ~/crawler
```

### 2) `.env` neben `docker-compose.yaml`

```env
# Pfad auf dem **Host** zum geklonten Repo (Ordner mit `src/`)
CRAWLER_HOST_PATH=/home/infl0/crawler
```

### 3) Compose

Siehe [`docker-compose.server.example.yaml`](docker-compose.server.example.yaml):

- **`TOPIC_CRAWLER_ROOT=/data/TopicKnowledgeCrawler`** (Repo-Root)
- **Volume** `${CRAWLER_HOST_PATH}:/data/TopicKnowledgeCrawler:ro` auf **`n8n`** und **`n8n-worker`** (Python Task Runner)

Passe deine bestehende `docker-compose.yaml` entsprechend an (oder merge per Diff).

### 4) Pakete im Runner-Image

Auch bei Volume-Mount müssen Abhängigkeiten im **Python-Runner-Image** installiert sein. Am einfahren: eigenes Image wie oben bauen **oder** im Runner-Dockerfile weiterhin `uv pip install …` / `pip install -e` nutzen (siehe `n8n/docker/Dockerfile.task-runner-python.example`).

### 5) infl0 (optional in n8n Env)

```env
INFL0_BASE_URL=https://reader.neurospicy.icu
INFL0_CRAWLER_API_KEY=<NUXT_CRAWLER_API_KEY>
```

Diese Variablen in der n8n-Compose-Umgebung setzen (oder in n8n UI unter Environment), damit der HTTP-Request-Node `{{$env.INFL0_BASE_URL}}` nutzen kann.
