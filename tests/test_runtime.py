"""Tests for tkcrawler.steps._runtime – envelope helpers and input parsing."""

from __future__ import annotations

import pytest

from tkcrawler.steps._runtime import (
    StepError,
    fail,
    ok,
    parse_json_object,
    run_safely,
    split_input,
)


class TestSplitInput:
    def test_extracts_item_and_context_from_envelope(self):
        item, ctx = split_input({"item": {"a": 1}, "context": {"now": "t"}})
        assert item == {"a": 1}
        assert ctx == {"now": "t"}

    def test_treats_raw_dict_as_item(self):
        item, ctx = split_input({"a": 1, "b": 2})
        assert item == {"a": 1, "b": 2}
        assert ctx == {}

    def test_handles_missing_item_in_envelope(self):
        item, ctx = split_input({"context": {"now": "t"}})
        assert item == {}
        assert ctx == {"now": "t"}

    def test_handles_missing_context_in_envelope(self):
        item, ctx = split_input({"item": {"a": 1}})
        assert item == {"a": 1}
        assert ctx == {}

    def test_raises_on_non_mapping_item(self):
        with pytest.raises(StepError) as exc_info:
            split_input({"item": "not_a_dict"})
        assert exc_info.value.code == "invalid_input"

    def test_raises_on_non_mapping_context(self):
        with pytest.raises(StepError) as exc_info:
            split_input({"item": {}, "context": "bad"})
        assert exc_info.value.code == "invalid_input"

    def test_returns_copies(self):
        original_item = {"key": "value"}
        item, _ = split_input({"item": original_item})
        item["key"] = "changed"
        assert original_item["key"] == "value"


class TestOk:
    def test_wraps_single_dict_in_items_list(self):
        result = ok({"a": 1})
        assert result == {"ok": True, "items": [{"a": 1}], "meta": {}}

    def test_passes_list_through(self):
        result = ok([{"a": 1}, {"b": 2}])
        assert result["items"] == [{"a": 1}, {"b": 2}]

    def test_includes_meta(self):
        result = ok({"a": 1}, meta={"count": 5})
        assert result["meta"] == {"count": 5}

    def test_empty_list(self):
        result = ok([])
        assert result == {"ok": True, "items": [], "meta": {}}


class TestFail:
    def test_basic_error(self):
        err = StepError("test_code", "test message")
        result = fail(err)
        assert result["ok"] is False
        assert result["items"] == []
        assert result["error"]["code"] == "test_code"
        assert result["error"]["message"] == "test message"

    def test_includes_details(self):
        err = StepError("code", "msg", {"field": "url"})
        result = fail(err)
        assert result["error"]["details"] == {"field": "url"}

    def test_includes_meta(self):
        err = StepError("code", "msg")
        result = fail(err, meta={"attempt": 2})
        assert result["meta"] == {"attempt": 2}


class TestParseJsonObject:
    def test_returns_empty_for_none(self):
        assert parse_json_object(None, field="x") == {}

    def test_returns_empty_for_empty_string(self):
        assert parse_json_object("", field="x") == {}

    def test_passes_through_mapping(self):
        assert parse_json_object({"a": 1}, field="x") == {"a": 1}

    def test_parses_json_string(self):
        assert parse_json_object('{"a": 1}', field="x") == {"a": 1}

    def test_raises_on_invalid_json(self):
        with pytest.raises(StepError) as exc_info:
            parse_json_object("{bad json", field="policy")
        assert exc_info.value.code == "invalid_json"
        assert "policy" in exc_info.value.message

    def test_raises_on_json_array(self):
        with pytest.raises(StepError) as exc_info:
            parse_json_object("[1, 2]", field="config")
        assert exc_info.value.code == "invalid_json"

    def test_raises_on_json_scalar(self):
        with pytest.raises(StepError) as exc_info:
            parse_json_object('"just a string"', field="f")
        assert exc_info.value.code == "invalid_json"

    def test_raises_on_non_string_non_mapping(self):
        with pytest.raises(StepError) as exc_info:
            parse_json_object(42, field="num")
        assert exc_info.value.code == "invalid_json"


class TestRunSafely:
    def test_returns_step_result(self):
        def step(payload):
            return ok({"done": True})

        result = run_safely(step, {})
        assert result["ok"] is True

    def test_catches_step_error(self):
        def step(payload):
            raise StepError("boom", "something broke")

        result = run_safely(step, {})
        assert result["ok"] is False
        assert result["error"]["code"] == "boom"

    def test_does_not_catch_other_exceptions(self):
        def step(payload):
            raise ValueError("unexpected")

        with pytest.raises(ValueError, match="unexpected"):
            run_safely(step, {})
