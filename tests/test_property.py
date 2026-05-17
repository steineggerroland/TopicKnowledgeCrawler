"""Property-based tests using hypothesis for pure functions."""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from tkcrawler.crawl_key import normalize_feed_url
from tkcrawler.html import HtmlFetcher
from tkcrawler.text import calculate_hash, sanitize_string


class TestNormalizeFeedUrlProperties:
    @given(path=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/-_.~"),
        min_size=1,
        max_size=50,
    ))
    @settings(max_examples=100)
    def test_output_has_no_fragment(self, path):
        url = f"https://example.com/{path}#section"
        result = normalize_feed_url(url)
        assert "#" not in result

    @given(path=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/-_.~"),
        min_size=1,
        max_size=50,
    ))
    @settings(max_examples=100)
    def test_scheme_is_lowercase(self, path):
        url = f"HTTPS://Example.COM/{path}"
        result = normalize_feed_url(url)
        assert result.startswith("https://")

    @given(path=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_.~"),
        min_size=1,
        max_size=50,
    ))
    @settings(max_examples=100)
    def test_no_trailing_slash_on_non_root(self, path):
        url = f"https://example.com/{path}/"
        result = normalize_feed_url(url)
        assert not result.endswith("/")

    def test_root_path_keeps_trailing_slash(self):
        result = normalize_feed_url("https://example.com/")
        assert result == "https://example.com/"

    @given(scheme=st.sampled_from(["ftp", "file", "mailto", "ssh"]))
    def test_rejects_non_http_schemes(self, scheme):
        with pytest.raises(ValueError, match="protocol"):
            normalize_feed_url(f"{scheme}://example.com/feed")

    def test_idempotent(self):
        url = "HTTPS://Example.com/Feed/"
        once = normalize_feed_url(url)
        twice = normalize_feed_url(once)
        assert once == twice


class TestCalculateHashProperties:
    @given(text=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_deterministic(self, text):
        assert calculate_hash(text) == calculate_hash(text)

    @given(text=st.text(min_size=0, max_size=1000))
    @settings(max_examples=100)
    def test_output_is_hex_string(self, text):
        result = calculate_hash(text)
        assert len(result) == 64
        int(result, 16)

    @given(a=st.text(min_size=1, max_size=100), b=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_different_inputs_produce_different_hashes(self, a, b):
        assume(a != b)
        assert calculate_hash(a) != calculate_hash(b)


class TestSanitizeStringProperties:
    @given(text=st.text(min_size=0, max_size=200))
    @settings(max_examples=200)
    def test_output_is_filename_safe(self, text):
        result = sanitize_string(text)
        for ch in result:
            assert ch.isalnum() or ch in ("_", ".", "-")

    @given(text=st.text(min_size=1, max_size=200))
    @settings(max_examples=100)
    def test_preserves_length(self, text):
        assert len(sanitize_string(text)) == len(text)

    def test_idempotent(self):
        text = "hello world! @#$"
        once = sanitize_string(text)
        twice = sanitize_string(once)
        assert once == twice


class TestSanitizeLinkProperties:
    TRACKING_QUERY_KEYS = frozenset(
        {"utm_source", "utm_medium", "utm_campaign", "tracking", "referrer"}
    )

    @given(path=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/-_"),
        min_size=0,
        max_size=50,
    ))
    @settings(max_examples=100)
    def test_path_segments_may_contain_tracking_like_names(self, path):
        """sanitize_link strips query keys only; path segments are left unchanged."""
        url = f"https://example.com/{path}"
        result = HtmlFetcher.sanitize_link(url)
        assert result is not None
        assert result.startswith("https://example.com/")

    @given(tracking_key=st.sampled_from(sorted(TRACKING_QUERY_KEYS)))
    @settings(max_examples=50)
    def test_strips_tracking_query_parameters(self, tracking_key):
        from urllib.parse import parse_qs, urlparse

        url = f"https://example.com/article?{tracking_key}=noise&keep=1"
        result = HtmlFetcher.sanitize_link(url)
        assert result is not None
        query = parse_qs(urlparse(result).query)
        assert tracking_key not in query
        assert "keep" in query
