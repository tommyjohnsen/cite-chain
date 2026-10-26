# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | a1461ef
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# END PROVENANCE
from pathlib import Path

from cite_chain.models import Edge, Work
from cite_chain.outputs import write_outputs
from cite_chain.walk import Graph


GOLDEN = Path(__file__).with_name("golden")


def test_each_output_matches_golden_file(tmp_path):
    graph = Graph()
    open_key, _ = graph.add(Work(
        "Open synthetic source", "10.5555/open.1", 2024, ["A. Example"],
        is_oa=True, oa_url="https://api.unpaywall.org/open", oa_source="Unpaywall",
        oa_reason="Unpaywall provides an open-access location",
    ), 0)
    closed_key, _ = graph.add(Work(
        "Restricted synthetic source", "10.5555/closed.1", 2023, ["B. Example"],
        is_oa=False, oa_source="Unpaywall",
        oa_reason="Unpaywall reports no open-access location",
    ), 1)
    graph.edges.add(Edge(open_key, closed_key, "references"))
    graph.attributions.add("Data from Semantic Scholar")

    write_outputs(graph, tmp_path)

    for name in ("graph.json", "chain.md", "LIBRARY-ONLY.csv"):
        assert (tmp_path / name).read_bytes() == (GOLDEN / name).read_bytes()
