"""CLI subprocess integration: normalize → list → filter → fetch → finalize → ingest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _run_cli_step(step: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "tkcrawler.cli.run_step", step],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["ok"] is True, result
    return result


@pytest.fixture
def rss_source():
    return {
        "crawl_key": "https://synthetic.example.com/feed.xml",
        "type": "rss",
        "url": str(FIXTURES / "synthetic_rss.xml"),
        "source_status": "ready",
    }


def test_cli_rss_flow_to_ingest_body(rss_source):
    normalized = _run_cli_step("normalize_source", {"item": rss_source})["items"][0]
    assert normalized["crawl_key"] == rss_source["crawl_key"]

    candidates = _run_cli_step("list_candidates", {"item": normalized})["items"]
    assert len(candidates) == 3
    candidate_row = candidates[0]

    filtered = _run_cli_step(
        "filter_candidates",
        {
            "item": candidate_row,
            "context": {"now": "2026-05-17T12:00:00+00:00"},
        },
    )["items"][0]
    assert filtered["candidate_decision"] == "fetch"
    filtered["prefer_feed_content"] = True
    filtered["candidate"]["has_feed_content"] = True
    filtered["candidate"]["feed_content"] = "<p>Body</p>"

    fetched = _run_cli_step(
        "fetch_detail",
        {"item": filtered, "context": {"verify": False}},
    )["items"][0]
    assert fetched["article"]["content_md"] == "# First Synthetic Article\n\nBody"

    finalized = _run_cli_step("finalize_item", {"item": fetched})["items"][0]
    assert finalized["content_hash"]

    ingest = _run_cli_step("build_ingest_body", {"item": finalized})["items"][0]
    body = ingest["infl0_ingest_body"]
    assert body["crawlKey"] == rss_source["crawl_key"]
    assert body["item_kind"] == "article"
    assert body["title"] == "First Synthetic Article"
    assert body["link"] == "https://synthetic.example.com/articles/first"
