"""Command-line entry point."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .clients import CrossrefClient, OpenAlexClient, SemanticScholarClient, UnpaywallClient
from .walk import walk


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="cite-chain")
    result.add_argument("doi", nargs="*")
    result.add_argument("--file", type=Path, help="file containing one seed DOI per line")
    result.add_argument("--hops", type=int, choices=(1, 2), default=1)
    result.add_argument("--max-nodes", type=int, default=100)
    result.add_argument("--keyword", action="append", default=[])
    result.add_argument("--output", type=Path, default=Path("."))
    return result


def _write_outputs(graph, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "graph.json").write_text(json.dumps(graph.as_dict(), indent=2) + "\n", encoding="utf-8")
    lines = ["# Citation chain", "", "First-pass map; verify all records before use.", ""]
    for hop in sorted(set(graph.hops.values())):
        lines.extend((f"## Hop {hop}", ""))
        for key in sorted(key for key, value in graph.hops.items() if value == hop):
            work = graph.nodes[key]
            suffix = f" ({work.year})" if work.year else ""
            lines.append(f"- {work.title or work.doi or key}{suffix}")
        lines.append("")
    if graph.attributions:
        lines.extend(sorted(graph.attributions))
        lines.append("")
    (directory / "chain.md").write_text("\n".join(lines), encoding="utf-8")
    with (directory / "LIBRARY-ONLY.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("title", "authors", "year", "doi", "why"))
        for work in sorted(graph.nodes.values(), key=lambda item: item.key):
            if work.is_oa is not True:
                writer.writerow((work.title, "; ".join(work.authors), work.year or "", work.doi or "",
                                 "No verified open-access location"))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    seeds = list(args.doi)
    if args.file:
        seeds.extend(line.strip() for line in args.file.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#"))
    if not seeds:
        parser().error("provide at least one DOI or --file")
    graph = walk(seeds, [OpenAlexClient(), CrossrefClient(), SemanticScholarClient()],
                 hops=args.hops, max_nodes=args.max_nodes, keywords=tuple(args.keyword))
    unpaywall = UnpaywallClient()
    for work in graph.nodes.values():
        if work.doi and (oa := unpaywall.lookup(work.doi)):
            work.merge(oa)
    _write_outputs(graph, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
