# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | a1461ef
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE_WITH_NITS
# reviewed-by: grok-build/grok-4.7 | 2026-10-26 | APPROVE_WITH_NITS
# END PROVENANCE
"""Stable, human-readable citation graph outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .walk import Graph


def write_outputs(graph: Graph, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "graph.json").write_text(
        json.dumps(graph.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = ["# Citation chain", "", "First-pass map; verify all records before use.", ""]
    for hop in sorted(set(graph.hops.values())):
        lines.extend((f"## Hop {hop}", ""))
        for key in sorted(key for key, value in graph.hops.items() if value == hop):
            work = graph.nodes[key]
            label = work.title or work.doi or key
            year = f" ({work.year})" if work.year else ""
            doi = f" — DOI: {work.doi}" if work.doi and work.doi not in label else ""
            url = f" — {work.oa_url}" if work.access == "OPEN" else ""
            lines.append(f"- {label}{year}{doi} — **{work.access}**{url}")
        lines.append("")
    if graph.attributions:
        lines.extend(sorted(graph.attributions))
        lines.append("")
    (directory / "chain.md").write_text("\n".join(lines), encoding="utf-8")

    with (directory / "LIBRARY-ONLY.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("title", "authors", "year", "doi", "why"))
        for key in sorted(graph.nodes):
            work = graph.nodes[key]
            if work.access == "LIBRARY-ONLY":
                writer.writerow((work.title, "; ".join(work.authors), work.year or "",
                                 work.doi or "", work.oa_reason))
