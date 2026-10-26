# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE
# END PROVENANCE
from __future__ import annotations

import csv
import json

from cite_chain.cli import ledger_parser
from cite_chain.outputs import write_outputs
from cite_chain.models import Work
from cite_chain.walk import Graph


def test_writes_declared_outputs(tmp_path):
    graph = Graph()
    graph.add(Work("Open synthetic source", "10.5555/open.1", 2024, is_oa=True,
                   oa_url="https://api.unpaywall.org/open"), 0)
    graph.add(Work("Restricted synthetic source", "10.5555/closed.1", 2023), 1)
    graph.attributions.add("Data from Semantic Scholar")

    write_outputs(graph, tmp_path)

    data = json.loads((tmp_path / "graph.json").read_text())
    assert len(data["nodes"]) == 2
    assert "Data from Semantic Scholar" in (tmp_path / "chain.md").read_text()
    rows = list(csv.DictReader((tmp_path / "LIBRARY-ONLY.csv").open()))
    assert [row["doi"] for row in rows] == ["10.5555/closed.1"]


def test_ledger_command_group_is_reserved_for_next_release():
    args = ledger_parser().parse_args([
        "check", "ledger.md", "--draft", "draft.md", "--today", "2026-10-16", "--suggest"
    ])
    assert args.ledger_command == "check"
    assert args.ledger.name == "ledger.md"
    assert args.suggest is True
