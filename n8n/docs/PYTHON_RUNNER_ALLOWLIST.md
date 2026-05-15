# n8n Python Runner Allowlist

## Important

- The variable is `N8N_RUNNERS_EXTERNAL_ALLOW` with plural `RUNNERS`.
- The list contains top-level module names, not full import paths.
- With `pip install -e .` in the runner image, `tkcrawler` is a normal site package. Code nodes do not need `sys.path` changes.

## Recommended Setting

```env
N8N_RUNNERS_EXTERNAL_ALLOW=tkcrawler,feedparser,trafilatura,requests,bs4,lxml,tldextract
```

- `tkcrawler`: source rows, source analysis, dispatch, candidate listing, detail fetch, finalization and infl0 payloads.
- `bs4`: import name for `beautifulsoup4`.

If a Code node imports standard-library modules such as `os` or `sys`, add them to `N8N_RUNNERS_STDLIB_ALLOW` according to your runner policy.

Only for trusted environments:

```env
N8N_RUNNERS_EXTERNAL_ALLOW=*
```

## `n8n-task-runners.json`

`env-overrides` must apply to the Python task runner. Restart the runner after changes.

## Installation

Recommended: use `n8n/docker/Dockerfile.task-runner-python.example`.

Manual install inside the container:

```bash
pip install --no-cache-dir -e /opt/TopicKnowledgeCrawler
```
