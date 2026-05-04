"""Portable workflow steps used by n8n and the CLI runner."""

from tkcrawler.steps.build_ingest_body import build_ingest_body_step
from tkcrawler.steps.filter_candidates import filter_candidates_step
from tkcrawler.steps.fetch_detail import fetch_detail_step
from tkcrawler.steps.finalize_item import finalize_item_step
from tkcrawler.steps.list_candidates import list_candidates_step
from tkcrawler.steps.normalize_source import normalize_source_step
from tkcrawler.steps.plan_dispatch import plan_dispatch_step

STEP_REGISTRY = {
    "normalize_source": normalize_source_step,
    "build_ingest_body": build_ingest_body_step,
    "filter_candidates": filter_candidates_step,
    "fetch_detail": fetch_detail_step,
    "finalize_item": finalize_item_step,
    "list_candidates": list_candidates_step,
    "plan_dispatch": plan_dispatch_step,
}

__all__ = [
    "STEP_REGISTRY",
    "build_ingest_body_step",
    "filter_candidates_step",
    "fetch_detail_step",
    "finalize_item_step",
    "list_candidates_step",
    "normalize_source_step",
    "plan_dispatch_step",
]
