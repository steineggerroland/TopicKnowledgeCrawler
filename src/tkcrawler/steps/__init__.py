"""Portable workflow steps used by n8n and the CLI runner."""

from tkcrawler.steps.build_ingest_body import build_ingest_body_step
from tkcrawler.steps.normalize_source import normalize_source_step
from tkcrawler.steps.plan_dispatch import plan_dispatch_step

STEP_REGISTRY = {
    "normalize_source": normalize_source_step,
    "build_ingest_body": build_ingest_body_step,
    "plan_dispatch": plan_dispatch_step,
}

__all__ = [
    "STEP_REGISTRY",
    "build_ingest_body_step",
    "normalize_source_step",
    "plan_dispatch_step",
]
