# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

TopicKnowledgeCrawler is the crawler and preparation layer behind infl0. It discovers content from RSS, HTML and podcast sources, turns them into normalized items and prepares payloads for the infl0 reading app. See `README.md` for the full description.

All production code lives under `src/tkcrawler/`. The old `src/crawler/` package was removed.

### Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

Tests require `pytest`, `pytest-mock` and `hypothesis`. The update script installs all three.

All tests are heavily mocked — no network, no Ollama, no filesystem side-effects. The suite runs in ~2 seconds.

### Linting

```bash
ruff check src/ tests/
```

Ruff configuration lives in `pyproject.toml` under `[tool.ruff]`.

### Running the step CLI

```bash
source .venv/bin/activate
python -m tkcrawler.cli.run_step normalize_source < input.json
```

### Gotchas

- **`PYTHONPATH=src` is NOT needed** — the package is installed editable (`pip install -e .`), so `tkcrawler` resolves directly. `pytest.ini` also sets `pythonpath = src`.
- The `fuzzywuzzy` warning about `python-Levenshtein` is harmless — the pure-Python fallback is used.
- The summarizer / LLM enrichment step is handled by n8n AI nodes, not by Python. There is no LLM dependency for running tests or the crawler itself.
- `data/raw` and `data/processed` directories from the old standalone mode no longer exist. Output is sent to infl0 via API.
