# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | pending | DOI-less Semantic Scholar traversal regression test added with provenance block
# END PROVENANCE
from __future__ import annotations

from cite_chain.models import Work
from cite_chain.walk import walk


class SyntheticSource:
    def __init__(self, works, backward=(), forward=()):
        self.works = works
        self.backward = dict(backward)
        self.forward = dict(forward)

    def get_work(self, identifier):
        doi = identifier.removeprefix("https://doi.org/").lower()
        return self.works.get(doi)

    def references(self, work):
        return [self.works[doi] for doi in self.backward.get(work.doi, [])]

    def citations(self, work):
        return [self.works[doi] for doi in self.forward.get(work.doi, [])]


def fixture_source():
    works = {
        "10.5555/seed.1": Work("Seed methods", "10.5555/seed.1", 2024),
        "10.5555/back.1": Work("Earlier methods", "10.5555/back.1", 2023),
        "10.5555/front.1": Work("Later analysis", "10.5555/front.1", 2026),
        "10.5555/two.1": Work("Second hop methods", "10.5555/two.1", 2022),
    }
    return SyntheticSource(
        works,
        backward=(("10.5555/seed.1", ["10.5555/back.1"]),
                  ("10.5555/back.1", ["10.5555/two.1"])),
        forward=(("10.5555/seed.1", ["10.5555/front.1"]),),
    )


def test_walk_hop_limits_and_edges():
    source = fixture_source()
    one = walk(["10.5555/seed.1"], [source], hops=1)
    assert len(one.nodes) == 3
    assert max(one.hops.values()) == 1
    two = walk(["10.5555/seed.1"], [source], hops=2)
    assert len(two.nodes) == 4
    assert max(two.hops.values()) == 2
    assert {edge.relation for edge in two.edges} == {"references", "cited_by"}


def test_keyword_filter_and_max_nodes():
    source = fixture_source()
    graph = walk(["10.5555/seed.1"], [source], hops=2, max_nodes=2, keywords=("methods",))
    assert len(graph.nodes) == 2
    assert all("analysis" not in work.title.casefold() for work in graph.nodes.values())


def test_cross_source_dedup_by_doi_and_title_year():
    first = SyntheticSource({"10.5555/seed.1": Work("Same synthetic title", "10.5555/seed.1", 2024)})
    second = SyntheticSource({"10.5555/seed.1": Work("Same synthetic title", None, 2024,
                                                     source_ids={"second": "S1"})})
    graph = walk(["10.5555/seed.1"], [first, second], hops=1)
    assert len(graph.nodes) == 1
    assert graph.nodes["doi:10.5555/seed.1"].source_ids == {"second": "S1"}


def test_doi_less_neighbor_merges_into_existing_doi_record():
    source = fixture_source()
    source.forward["10.5555/seed.1"] = ["10.5555/back.1"]
    alternate = SyntheticSource(
        {"10.5555/seed.1": source.works["10.5555/seed.1"]},
        forward=(("10.5555/seed.1", [None]),),
    )
    alternate.works[None] = Work("Earlier methods", None, 2023, source_ids={"second": "S2"})
    graph = walk(["10.5555/seed.1"], [source, alternate], hops=1)
    assert len(graph.nodes) == 2
    assert graph.nodes["doi:10.5555/back.1"].source_ids["second"] == "S2"


def test_doi_less_semantic_scholar_neighbors_remain_distinct():
    source = fixture_source()
    source.forward["10.5555/seed.1"] = ["semantic-a", "semantic-b"]
    source.works["semantic-a"] = Work(
        "Same synthetic title", year=2024,
        source_ids={"semantic_scholar": "SYNTHETIC-A"},
    )
    source.works["semantic-b"] = Work(
        "Same synthetic title", year=2024,
        source_ids={"semantic_scholar": "SYNTHETIC-B"},
    )

    graph = walk(["10.5555/seed.1"], [source], hops=1)

    assert set(graph.nodes) == {
        "doi:10.5555/back.1",
        "doi:10.5555/seed.1",
        "semantic_scholar:SYNTHETIC-A",
        "semantic_scholar:SYNTHETIC-B",
    }
    assert len(graph.edges) == 3


def test_graph_output_does_not_contain_environment_values(monkeypatch):
    monkeypatch.setenv("CONTACT_EMAIL", "you@example.com")
    monkeypatch.setenv("OPENALEX_API_KEY", "synthetic-secret")
    output = str(walk(["10.5555/seed.1"], [fixture_source()]).as_dict())
    assert "you@example.com" not in output
    assert "synthetic-secret" not in output
