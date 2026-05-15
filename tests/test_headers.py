"""Tests for tkcrawler.steps._headers – request header construction."""

from __future__ import annotations

from tkcrawler.steps._headers import request_headers


class TestRequestHeaders:
    def test_empty_row_returns_empty(self):
        assert request_headers({}) == {}

    def test_policy_user_agent(self):
        row = {"effective_policy": {"user_agent": "CustomBot/1.0"}}
        h = request_headers(row)
        assert h["User-Agent"] == "CustomBot/1.0"

    def test_policy_contact_sets_from_and_x_infl0(self):
        row = {"effective_policy": {"contact": "admin@example.com"}}
        h = request_headers(row)
        assert h["From"] == "admin@example.com"
        assert h["X-Infl0-Contact"] == "admin@example.com"

    def test_policy_crawler_name(self):
        row = {"effective_policy": {"crawler_name": "tkcrawler"}}
        h = request_headers(row)
        assert h["X-Infl0-Crawler"] == "tkcrawler"

    def test_policy_request_headers_forwarded(self):
        row = {"effective_policy": {"request_headers": {"Accept": "text/html"}}}
        h = request_headers(row)
        assert h["Accept"] == "text/html"

    def test_context_headers_override_policy(self):
        row = {"effective_policy": {"user_agent": "Policy/1"}}
        ctx = {"headers": {"User-Agent": "Override/2"}}
        h = request_headers(row, ctx)
        assert h["User-Agent"] == "Override/2"

    def test_ignores_non_mapping_policy(self):
        row = {"effective_policy": "not a dict"}
        assert request_headers(row) == {}


class TestSelectUserAgent:
    def test_user_agents_list_rotation(self):
        row = {
            "crawl_key": "https://example.com/feed",
            "effective_policy": {"user_agents": ["Bot/A", "Bot/B", "Bot/C"]},
        }
        h = request_headers(row)
        assert h["User-Agent"] in {"Bot/A", "Bot/B", "Bot/C"}

    def test_user_agents_deterministic_per_crawl_key(self):
        row = {
            "crawl_key": "https://example.com/feed",
            "effective_policy": {"user_agents": ["Bot/A", "Bot/B"]},
        }
        h1 = request_headers(row)
        h2 = request_headers(row)
        assert h1["User-Agent"] == h2["User-Agent"]

    def test_different_crawl_keys_may_pick_different_agents(self):
        agents = ["Bot/A", "Bot/B", "Bot/C", "Bot/D"]
        results = set()
        for i in range(20):
            row = {
                "crawl_key": f"https://example.com/feed-{i}",
                "effective_policy": {"user_agents": agents},
            }
            results.add(request_headers(row)["User-Agent"])
        assert len(results) > 1

    def test_empty_user_agents_list(self):
        row = {"effective_policy": {"user_agents": []}}
        assert "User-Agent" not in request_headers(row)

    def test_user_agents_with_falsy_entries(self):
        row = {
            "crawl_key": "https://x.com",
            "effective_policy": {"user_agents": [None, "", "Bot/Valid"]},
        }
        h = request_headers(row)
        assert h["User-Agent"] == "Bot/Valid"

    def test_user_agent_takes_precedence_over_user_agents(self):
        row = {
            "effective_policy": {
                "user_agent": "Primary/1",
                "user_agents": ["Fallback/A"],
            },
        }
        h = request_headers(row)
        assert h["User-Agent"] == "Primary/1"
