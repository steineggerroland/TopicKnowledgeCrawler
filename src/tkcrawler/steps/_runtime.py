"""Backward-compatible re-export from tkcrawler._runtime."""

from tkcrawler._runtime import (
    StepError,
    fail,
    ok,
    parse_json_object,
    run_safely,
    split_input,
)

__all__ = [
    "StepError",
    "fail",
    "ok",
    "parse_json_object",
    "run_safely",
    "split_input",
]
