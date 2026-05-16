# Contributing

TopicKnowledgeCrawler is the portable crawler step layer behind infl0. Keep changes small, explicit and easy to run from n8n, the CLI and plain Python.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install pytest pytest-mock hypothesis ruff
```

`PYTHONPATH=src` is not required when the package is installed editable. `pytest.ini` also configures the test import path for local test runs.

## Checks

Run the same checks before opening a PR:

```bash
source .venv/bin/activate
pytest tests/ -v
ruff check src/ tests/
```

Set `TLDEXTRACT_CACHE` if your environment should avoid user-global cache writes:

```bash
TLDEXTRACT_CACHE=/tmp/tkcrawler-tldextract-cache pytest tests/ -v
```

## Code Style

- Production code lives under `src/tkcrawler/`.
- Use the portable step functions in `tkcrawler.steps` as the public workflow boundary.
- Keep n8n-specific mapping in thin wrappers or docs, not in parser or policy logic.
- Prefer typed enums from `tkcrawler.enums` over raw status strings in new code.
- Keep crawler behavior deterministic and testable. Tests should mock network, Ollama and filesystem side effects.
- Use `ruff` for import order and lint checks. The configuration lives in `pyproject.toml`.

## Adding a Step

1. Add the item-level function and envelope step function under `src/tkcrawler/steps/`.
2. Register the step in `src/tkcrawler/steps/__init__.py`.
3. Add focused tests in `tests/steps/test_steps.py` or a dedicated test module.
4. Document any new input/output contract in `docs/` or `n8n/docs/`.
5. Verify the step through the CLI:

```bash
python -m tkcrawler.cli.run_step your_step_name < input.json
```

## Pull Requests

- State whether behavior changed or the PR is a refactor only.
- Include the tests and lint command output.
- Update docs when changing workflow order, envelope shape, infl0 payloads or n8n assumptions.
- Avoid unrelated formatting churn so diffs stay reviewable.
