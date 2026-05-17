"""Portable workflow steps used by n8n and the CLI runner."""

from tkcrawler.steps.analyze_source import analyze_source_step
from tkcrawler.steps.apply_html_analysis import apply_html_analysis_step
from tkcrawler.steps.build_ingest_body import build_ingest_body_step
from tkcrawler.steps.build_source_status_body import build_source_status_body_step
from tkcrawler.steps.derive_source_health import derive_source_health_step
from tkcrawler.steps.fetch_detail import fetch_detail_step
from tkcrawler.steps.filter_candidates import filter_candidates_step
from tkcrawler.steps.finalize_crawl_run import finalize_crawl_run_step
from tkcrawler.steps.finalize_item import finalize_item_step
from tkcrawler.steps.inspect_source_policy import inspect_source_policy_step
from tkcrawler.steps.limit_llm_items import limit_llm_items_step
from tkcrawler.steps.list_candidates import list_candidates_step
from tkcrawler.steps.normalize_source import normalize_source_step
from tkcrawler.steps.plan_dispatch import plan_dispatch_step
from tkcrawler.steps.prepare_html_analysis import prepare_html_analysis_step
from tkcrawler.steps.segment_content import segment_content_step
from tkcrawler.steps.validate_source_configuration import (
    validate_source_configuration_step,
)

STEP_REGISTRY = {
    "analyze_source": analyze_source_step,
    "apply_html_analysis": apply_html_analysis_step,
    "build_ingest_body": build_ingest_body_step,
    "build_source_status_body": build_source_status_body_step,
    "derive_source_health": derive_source_health_step,
    "filter_candidates": filter_candidates_step,
    "fetch_detail": fetch_detail_step,
    "finalize_crawl_run": finalize_crawl_run_step,
    "finalize_item": finalize_item_step,
    "inspect_source_policy": inspect_source_policy_step,
    "limit_llm_items": limit_llm_items_step,
    "list_candidates": list_candidates_step,
    "normalize_source": normalize_source_step,
    "plan_dispatch": plan_dispatch_step,
    "prepare_html_analysis": prepare_html_analysis_step,
    "segment_content": segment_content_step,
    "validate_source_configuration": validate_source_configuration_step,
}

__all__ = [
    "STEP_REGISTRY",
    "analyze_source_step",
    "apply_html_analysis_step",
    "build_ingest_body_step",
    "build_source_status_body_step",
    "derive_source_health_step",
    "filter_candidates_step",
    "fetch_detail_step",
    "finalize_crawl_run_step",
    "finalize_item_step",
    "inspect_source_policy_step",
    "limit_llm_items_step",
    "list_candidates_step",
    "normalize_source_step",
    "plan_dispatch_step",
    "prepare_html_analysis_step",
    "segment_content_step",
    "validate_source_configuration_step",
]
