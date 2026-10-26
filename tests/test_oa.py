# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | a1461ef
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE
# END PROVENANCE
from cite_chain.models import Work
from cite_chain.oa import route_open_access
from cite_chain.walk import Graph


class Lookup:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def lookup(self, doi):
        self.calls.append(doi)
        return self.records.get(doi)


def test_unpaywall_result_wins_over_openalex_fields():
    graph = Graph()
    graph.add(Work("Synthetic", "10.5555/route.1", is_oa=True,
                   oa_url="https://api.openalex.org/open", oa_source="OpenAlex"), 0)
    lookup = Lookup({"10.5555/route.1": Work(
        doi="10.5555/route.1", is_oa=False, oa_source="Unpaywall"
    )})

    route_open_access(graph, lookup)

    work = graph.nodes["doi:10.5555/route.1"]
    assert work.access == "LIBRARY-ONLY"
    assert work.oa_url is None
    assert work.oa_source == "Unpaywall"
    assert work.oa_reason == "Unpaywall reports no open-access location"


def test_missing_unpaywall_record_falls_back_to_openalex():
    graph = Graph()
    graph.add(Work("Synthetic", "10.5555/route.2", is_oa=True,
                   oa_url="https://api.openalex.org/open", oa_source="OpenAlex"), 0)

    route_open_access(graph, Lookup({}))

    work = graph.nodes["doi:10.5555/route.2"]
    assert work.access == "OPEN"
    assert work.oa_source == "OpenAlex"
    assert work.oa_reason == "OpenAlex provides an open-access location"


def test_doi_less_record_is_library_only_without_lookup():
    graph = Graph()
    graph.add(Work("Identifier-free synthetic source", year=2021), 0)
    lookup = Lookup({})

    route_open_access(graph, lookup)

    work = next(iter(graph.nodes.values()))
    assert lookup.calls == []
    assert work.access == "LIBRARY-ONLY"
    assert work.oa_reason == "No verified open-access location in OpenAlex"
