# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | focused OpenAlex and Semantic Scholar identity regression tests added with provenance block
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE
# END PROVENANCE
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import warnings

from cite_chain.clients import OpenAlexClient, SemanticScholarClient, UnpaywallClient
from cite_chain.http import JsonCache, RateLimiter


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.value).encode()


def test_openalex_stops_after_first_page_without_both_credentials():
    calls = []

    def opener(request, **_):
        calls.append(request.full_url)
        return Response({"results": [{"id": "https://api.openalex.org/W2", "title": "Synthetic result"}],
                         "meta": {"next_cursor": "next"}})

    client = OpenAlexClient(api_key="", email="", opener=opener, sleeper=lambda _: None)
    with warnings.catch_warnings(record=True) as caught:
        rows = list(client._pages({"filter": "cites:W1"}))
    assert len(rows) == len(calls) == 1
    assert "page 1" in str(caught[0].message)


def test_openalex_pages_with_key_and_email():
    calls = []

    def opener(request, **_):
        calls.append(request.full_url)
        cursor = parse_qs(urlparse(request.full_url).query)["cursor"][0]
        return Response({"results": [{"id": f"https://api.openalex.org/{cursor}"}],
                         "meta": {"next_cursor": "second" if cursor == "*" else None}})

    client = OpenAlexClient(api_key="synthetic-key", email="you@example.com", opener=opener,
                            sleeper=lambda _: None)
    assert len(list(client._pages({}))) == 2
    assert len(calls) == 2


def test_openalex_get_work_routes_openalex_ids_without_doi_prefix():
    calls = []

    def opener(request, **_):
        calls.append(request.full_url)
        return Response({"id": "https://openalex.org/W1920000001", "title": "Synthetic work"})

    client = OpenAlexClient(api_key="", email="", opener=opener, sleeper=lambda _: None)
    assert client.get_work("W1920000001").source_ids["openalex"].endswith("W1920000001")
    assert client.get_work("https://openalex.org/W1920000002") is not None
    assert [urlparse(url).path for url in calls] == [
        "/works/W1920000001",
        "/works/W1920000002",
    ]


def test_openalex_get_work_routes_only_dois_through_doi_url():
    calls = []

    def opener(request, **_):
        calls.append(request.full_url)
        return Response({"id": "https://openalex.org/W1920000003", "title": "Synthetic work"})

    client = OpenAlexClient(api_key="", email="", opener=opener, sleeper=lambda _: None)
    assert client.get_work("10.5555/synthetic.3") is not None
    assert client.get_work("synthetic-provider-id") is not None
    assert [urlparse(url).path for url in calls] == [
        "/works/https%3A%2F%2Fdoi.org%2F10.5555%2Fsynthetic.3",
        "/works/synthetic-provider-id",
    ]


def test_unpaywall_skips_without_email():
    called = False

    def opener(*_, **__):
        nonlocal called
        called = True

    assert UnpaywallClient(email="", opener=opener).lookup("10.5555/synthetic.1") is None
    assert called is False


def test_semantic_scholar_cache_excludes_key(tmp_path: Path):
    calls = []

    def opener(request, **_):
        calls.append(request.headers)
        return Response({"paperId": "S1", "title": "Cached", "externalIds": {"DOI": "10.5555/cache.1"}})

    cache = JsonCache(tmp_path)
    client = SemanticScholarClient(api_key="synthetic-secret", opener=opener, cache=cache,
                                   sleeper=lambda _: None)
    assert client.get_work("10.5555/cache.1").doi == "10.5555/cache.1"
    assert client.get_work("10.5555/cache.1").title == ""
    assert len(calls) == 1
    written = "".join(path.read_text() for path in tmp_path.rglob("*.json"))
    assert "synthetic-secret" not in written


def test_semantic_scholar_doi_less_records_have_distinct_stable_keys():
    first = SemanticScholarClient.parse({"paperId": "SYNTHETIC-A", "externalIds": {}})
    second = SemanticScholarClient.parse({"paperId": "SYNTHETIC-B", "externalIds": {}})

    assert first.key == "semantic_scholar:SYNTHETIC-A"
    assert second.key == "semantic_scholar:SYNTHETIC-B"


def test_rate_limiter_uses_injected_clock():
    now = [5.0]
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        now[0] += delay

    limiter = RateLimiter(1, clock=lambda: now[0], sleeper=sleep)
    limiter.wait()
    limiter.wait()
    assert sleeps == [1.0]
