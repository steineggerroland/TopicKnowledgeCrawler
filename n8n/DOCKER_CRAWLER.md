# Python Runner Setup

The recommended setup is a custom Python task runner image that installs TopicKnowledgeCrawler with `pip install -e`.

## Custom Image

Build from the repository root:

```bash
docker build -f n8n/docker/Dockerfile.task-runner-python.example -t n8n-runner-python:local .
```

Then configure the Python task runner service to use `n8n-runner-python:local`.

The image copies or clones the repository and installs the package into the runner environment. This is more reliable than only mounting the repository read-only.

## Volume Mount Alternative

A volume mount can still be useful during development:

```env
CRAWLER_HOST_PATH=/home/<user>/crawler
```

The mounted path should point to the repository root, the directory that contains `src/`.

Even with a mount, dependencies must exist in the Python runner image. Use the custom image above or install the dependencies listed in `n8n/requirements-n8n.txt`.

## Allowlist

See `docs/PYTHON_RUNNER_ALLOWLIST.md` for the required `N8N_RUNNERS_EXTERNAL_ALLOW` setting.
