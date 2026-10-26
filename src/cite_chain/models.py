# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | stable Semantic Scholar keys added with provenance block
# END PROVENANCE
"""Small provider-neutral data model."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.rstrip(".,;) ") or None


def normalize_title(value: str | None) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").casefold()))


@dataclass(slots=True)
class Work:
    title: str = ""
    doi: str | None = None
    year: int | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    source_ids: dict[str, str] = field(default_factory=dict)
    referenced_ids: list[str] = field(default_factory=list)
    cited_by_ids: list[str] = field(default_factory=list)
    is_oa: bool | None = None
    oa_url: str | None = None
    oa_source: str | None = None
    oa_reason: str = "Not checked"

    def __post_init__(self) -> None:
        self.doi = normalize_doi(self.doi)

    @property
    def key(self) -> str:
        if self.doi:
            return f"doi:{self.doi}"
        if semantic_scholar_id := self.source_ids.get("semantic_scholar"):
            return f"semantic_scholar:{semantic_scholar_id}"
        return f"title:{normalize_title(self.title)}:{self.year or ''}"

    def merge(self, other: "Work") -> "Work":
        """Merge provider records without discarding existing useful data."""
        self.doi = self.doi or other.doi
        self.title = self.title or other.title
        self.year = self.year or other.year
        self.abstract = self.abstract or other.abstract
        self.authors = list(dict.fromkeys(self.authors + other.authors))
        self.source_ids.update(other.source_ids)
        self.referenced_ids = list(dict.fromkeys(self.referenced_ids + other.referenced_ids))
        self.cited_by_ids = list(dict.fromkeys(self.cited_by_ids + other.cited_by_ids))
        if other.is_oa is True or self.is_oa is None:
            self.is_oa = other.is_oa
        self.oa_url = self.oa_url or other.oa_url
        self.oa_source = self.oa_source or other.oa_source
        if self.oa_reason == "Not checked" and other.oa_reason != "Not checked":
            self.oa_reason = other.oa_reason
        return self

    @property
    def access(self) -> str:
        return "OPEN" if self.is_oa is True and bool(self.oa_url) else "LIBRARY-ONLY"

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.key,
            "doi": self.doi,
            "title": self.title,
            "year": self.year,
            "authors": self.authors,
            "source_ids": self.source_ids,
            "access": self.access,
            "is_oa": self.is_oa,
            "oa_url": self.oa_url,
            "oa_source": self.oa_source,
            "oa_reason": self.oa_reason,
        }


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    relation: str
