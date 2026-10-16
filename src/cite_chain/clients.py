"""Clients for authoritative scholarly metadata services."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import os
import threading
import time
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import urlopen
import warnings

from .http import JsonCache, RateLimiter, get_json
from .models import Work, normalize_doi


def _year(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class OpenAlexClient:
    base_url = "https://api.openalex.org"

    def __init__(self, *, api_key: str | None = None, email: str | None = None,
                 opener: Callable[..., Any] = urlopen,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENALEX_API_KEY")
        self.email = email if email is not None else os.getenv("CONTACT_EMAIL")
        self.opener = opener
        self.limiter = RateLimiter(10, clock=clock, sleeper=sleeper)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        if self.email:
            clean["mailto"] = self.email
        if self.api_key:
            clean["api_key"] = self.api_key
        self.limiter.wait()
        return get_json(f"{self.base_url}{path}?{urlencode(clean)}", opener=self.opener)

    @staticmethod
    def parse(item: dict[str, Any]) -> Work:
        is_oa = (item.get("open_access") or {}).get("is_oa")
        location = ((item.get("best_oa_location") or item.get("primary_location"))
                    if is_oa is True else {}) or {}
        return Work(
            title=item.get("title") or "", doi=item.get("doi"),
            year=_year(item.get("publication_year")),
            authors=[x.get("author", {}).get("display_name", "") for x in item.get("authorships", []) if x.get("author")],
            source_ids={"openalex": item["id"]} if item.get("id") else {},
            referenced_ids=list(item.get("referenced_works") or []),
            is_oa=is_oa,
            oa_url=location.get("landing_page_url") or location.get("pdf_url"),
            oa_source="OpenAlex" if is_oa is not None else None,
        )

    def get_work(self, identifier: str) -> Work | None:
        ident = f"https://doi.org/{normalize_doi(identifier)}" if normalize_doi(identifier) else identifier
        try:
            return self.parse(self._request(f"/works/{quote(ident, safe='')}"))
        except Exception as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise

    def _pages(self, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
        cursor: str | None = "*"
        first = True
        while cursor:
            page = self._request("/works", {**params, "cursor": cursor, "per-page": 200})
            yield from page.get("results", [])
            cursor = (page.get("meta") or {}).get("next_cursor")
            if first and cursor and not (self.api_key and self.email):
                warnings.warn("OpenAlex paging stopped after page 1: API key and contact email are required", stacklevel=2)
                return
            first = False

    def references(self, work: Work) -> list[Work]:
        found = []
        for ident in work.referenced_ids:
            item = self.get_work(ident)
            if item:
                found.append(item)
        return found

    def citations(self, work: Work) -> list[Work]:
        ident = work.source_ids.get("openalex")
        if not ident:
            return []
        return [self.parse(x) for x in self._pages({"filter": f"cites:{ident.rsplit('/', 1)[-1]}"})]


class CrossrefClient:
    base_url = "https://api.crossref.org"

    def __init__(self, *, email: str | None = None, opener: Callable[..., Any] = urlopen,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.email = email if email is not None else os.getenv("CONTACT_EMAIL")
        self.opener = opener
        self.limiter = RateLimiter(10, clock=clock, sleeper=sleeper)
        self.concurrent = threading.BoundedSemaphore(3)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        clean = dict(params or {})
        if self.email:
            clean["mailto"] = self.email
        self.limiter.wait()
        with self.concurrent:
            return get_json(f"{self.base_url}{path}?{urlencode(clean)}", opener=self.opener)

    @staticmethod
    def parse(item: dict[str, Any]) -> Work:
        dates = item.get("published-print") or item.get("published-online") or item.get("issued") or {}
        parts = dates.get("date-parts") or []
        authors = [" ".join(filter(None, (a.get("given"), a.get("family")))) for a in item.get("author", [])]
        return Work(title=(item.get("title") or [""])[0], doi=item.get("DOI"),
                    year=_year(parts[0][0]) if parts and parts[0] else None,
                    authors=authors, source_ids={"crossref": item["DOI"]} if item.get("DOI") else {},
                    referenced_ids=[r["DOI"] for r in item.get("reference", []) if r.get("DOI")])

    def get_work(self, identifier: str) -> Work | None:
        doi = normalize_doi(identifier)
        if not doi:
            return None
        try:
            return self.parse(self._request(f"/works/{quote(doi, safe='')}" ).get("message", {}))
        except Exception as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise

    def references(self, work: Work) -> list[Work]:
        result = []
        for ident in work.referenced_ids:
            item = self.get_work(ident)
            if item:
                result.append(item)
        return result

    def citations(self, work: Work) -> list[Work]:
        if not work.doi:
            return []
        data = self._request("/works", {"filter": f"reference:{work.doi}", "rows": 1000})
        return [self.parse(x) for x in data.get("message", {}).get("items", [])]


class SemanticScholarClient:
    base_url = "https://api.semanticscholar.org/graph/v1"
    attribution = "Data from Semantic Scholar"

    def __init__(self, *, api_key: str | None = None, opener: Callable[..., Any] = urlopen,
                 cache: JsonCache | None = None, clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("S2_API_KEY")
        self.opener = opener
        self.cache = cache or JsonCache()
        self.limiter = RateLimiter(1, clock=clock, sleeper=sleeper)

    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode(params)}"
        cached = self.cache.get("semantic-scholar", url)
        if cached is not None:
            return cached
        self.limiter.wait()
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        value = get_json(url, headers=headers, opener=self.opener)
        self.cache.put("semantic-scholar", url, value)
        return value

    @staticmethod
    def parse(item: dict[str, Any]) -> Work:
        external = item.get("externalIds") or {}
        # Provider metadata stays in its local cache. Exports may contain only
        # identifiers and flags derived by this package.
        return Work(doi=external.get("DOI"),
                    source_ids={"semantic_scholar": item["paperId"]} if item.get("paperId") else {})

    def get_work(self, identifier: str) -> Work | None:
        doi = normalize_doi(identifier)
        paper_id = f"DOI:{doi}" if doi else identifier
        try:
            data = self._request(f"/paper/{quote(paper_id, safe=':')}", {"fields": "paperId,externalIds"})
            return self.parse(data)
        except Exception as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise

    def _links(self, work: Work, relation: str) -> list[Work]:
        ident = work.source_ids.get("semantic_scholar") or (f"DOI:{work.doi}" if work.doi else None)
        if not ident:
            return []
        data = self._request(f"/paper/{quote(ident, safe=':')}/{relation}",
                             {"fields": "paperId,externalIds", "limit": 1000})
        side = "citedPaper" if relation == "references" else "citingPaper"
        return [self.parse(row[side]) for row in data.get("data", []) if row.get(side)]

    def references(self, work: Work) -> list[Work]:
        return self._links(work, "references")

    def citations(self, work: Work) -> list[Work]:
        return self._links(work, "citations")


class UnpaywallClient:
    base_url = "https://api.unpaywall.org/v2"

    def __init__(self, *, email: str | None = None, opener: Callable[..., Any] = urlopen,
                 clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.email = email if email is not None else os.getenv("CONTACT_EMAIL")
        self.opener = opener
        self.limiter = RateLimiter(10, clock=clock, sleeper=sleeper)

    def lookup(self, doi: str) -> Work | None:
        normalized = normalize_doi(doi)
        if not self.email or not normalized:
            return None
        self.limiter.wait()
        try:
            data = get_json(f"{self.base_url}/{quote(normalized, safe='')}?{urlencode({'email': self.email})}", opener=self.opener)
        except Exception as exc:
            if getattr(exc, "code", None) == 404:
                return None
            raise
        best = data.get("best_oa_location") or {}
        return Work(title=data.get("title") or "", doi=data.get("doi") or normalized,
                    year=_year(data.get("year")), is_oa=bool(data.get("is_oa")),
                    oa_url=(best.get("url_for_landing_page") or best.get("url_for_pdf")
                            or best.get("url")), oa_source="Unpaywall")
