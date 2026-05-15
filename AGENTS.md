# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

TopicKnowledgeCrawler — a Python-based content collection and processing pipeline that crawls RSS/Atom feeds, podcast feeds, and HTML listing pages, then summarizes and categorizes content using a local Ollama LLM. See `README.md` for full details.

### Running tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

All tests are heavily mocked (no network, no Ollama, no filesystem side-effects). The full suite (128 tests) runs in ~2 seconds.

`pytest-mock` is required in addition to `requirements.txt` — the update script installs both.

### Running the standalone collector

```bash
source .venv/bin/activate
PYTHONPATH=src python src/collector.py
```

`PYTHONPATH=src` is needed outside pytest because `pytest.ini` sets `pythonpath = src` only for the test runner.

### Gotchas

- **python3.12-venv** must be installed (`apt install python3.12-venv`) before creating the virtualenv. The update script handles this.
- The `fuzzywuzzy` warning about `python-Levenshtein` is harmless — the pure-Python fallback is used.
- `tldextract` emits a `DeprecationWarning` about `registered_domain` — this is a known upstream deprecation and does not affect functionality.
- The summarizer (`src/summarizer.py`) requires a running Ollama instance with models `qwen2.5` / `qwen2.5:14b`. Tests mock Ollama, so the LLM is **not** needed for `pytest`.
- `data/raw` and `data/processed` are gitignored output directories created at runtime.
