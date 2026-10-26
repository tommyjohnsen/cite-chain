# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | a1461ef
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | pending | provenance block added
# END PROVENANCE
"""Deterministic open-access routing."""

from __future__ import annotations

from typing import Protocol

from .models import Work
from .walk import Graph


class OALookup(Protocol):
    def lookup(self, doi: str) -> Work | None: ...


def _use_openalex(work: Work) -> None:
    if work.is_oa is True and work.oa_url:
        work.oa_source = "OpenAlex"
        work.oa_reason = "OpenAlex provides an open-access location"
        return
    work.is_oa = False
    work.oa_url = None
    work.oa_source = "OpenAlex" if work.oa_source == "OpenAlex" else None
    work.oa_reason = "No verified open-access location in OpenAlex"


def route_open_access(graph: Graph, unpaywall: OALookup) -> None:
    """Classify every node, preferring a returned Unpaywall DOI record."""
    for key in sorted(graph.nodes):
        work = graph.nodes[key]
        result = unpaywall.lookup(work.doi) if work.doi else None
        if result is None:
            _use_openalex(work)
        elif result.is_oa is True and result.oa_url:
            work.is_oa = True
            work.oa_url = result.oa_url
            work.oa_source = "Unpaywall"
            work.oa_reason = "Unpaywall provides an open-access location"
        else:
            work.is_oa = False
            work.oa_url = None
            work.oa_source = "Unpaywall"
            work.oa_reason = "Unpaywall reports no open-access location"
