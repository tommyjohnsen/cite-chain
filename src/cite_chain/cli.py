"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .clients import CrossrefClient, OpenAlexClient, SemanticScholarClient, UnpaywallClient
from .oa import route_open_access
from .outputs import write_outputs
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


def ledger_parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="cite-chain ledger")
    commands = result.add_subparsers(dest="ledger_command", title="commands")
    check = commands.add_parser("check", help="reserved for the ledger checker")
    check.add_argument("ledger", type=Path)
    check.add_argument("--draft", type=Path)
    check.add_argument("--today")
    check.add_argument("--suggest", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "ledger":
        ledger = ledger_parser()
        parsed = ledger.parse_args(arguments[1:])
        if parsed.ledger_command == "check":
            ledger.error("the ledger checker is not available in this release")
        ledger.print_help()
        return 0
    args = parser().parse_args(arguments)
    seeds = list(args.doi)
    if args.file:
        seeds.extend(line.strip() for line in args.file.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#"))
    if not seeds:
        parser().error("provide at least one DOI or --file")
    graph = walk(seeds, [OpenAlexClient(), CrossrefClient(), SemanticScholarClient()],
                 hops=args.hops, max_nodes=args.max_nodes, keywords=tuple(args.keyword))
    route_open_access(graph, UnpaywallClient())
    write_outputs(graph, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
