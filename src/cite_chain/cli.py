# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE
# END PROVENANCE
"""Command-line entry point."""

from __future__ import annotations

import argparse
from datetime import date
import sys
from pathlib import Path

from .clients import CrossrefClient, OpenAlexClient, SemanticScholarClient, UnpaywallClient
from .oa import route_open_access
from .ledger import check_rows, parse_ledger, suggested_table, write_reports
from .http import JsonCache
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
    check = commands.add_parser("check", help="check a source ledger")
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
            try:
                today = date.fromisoformat(parsed.today) if parsed.today else date.today()
                rows = parse_ledger(parsed.ledger)
                draft = parsed.draft.read_text(encoding="utf-8") if parsed.draft else None
                results = check_rows(rows, today=today, draft=draft,
                                     unpaywall=UnpaywallClient(),
                                     metadata_clients=(CrossrefClient(cache=JsonCache()),
                                                       OpenAlexClient(cache=JsonCache())))
                write_reports(results)
                if parsed.suggest:
                    sys.stdout.write(suggested_table(rows, results))
                return 0
            except (OSError, UnicodeError, ValueError) as exc:
                ledger.error(str(exc))
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
