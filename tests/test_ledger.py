from __future__ import annotations

from datetime import date
import json

from cite_chain import cli
from cite_chain.ledger import (check_rows, parse_ledger, suggested_table,
                               write_reports)
from cite_chain.models import Work


TABLE = """\
| Source | Found via | ALT copy found? (URL) | Status |
| --- | --- | --- | --- |
{rows}
"""


class OaLookup:
    def __init__(self, values=None):
        self.values = values or {}
        self.calls = []

    def lookup(self, doi):
        self.calls.append(doi)
        return self.values.get(doi)


class MetadataSearch:
    def __init__(self, values=()):
        self.values = list(values)
        self.calls = []

    def search(self, title, *, limit=5):
        self.calls.append((title, limit))
        return self.values


def load(tmp_path, rows):
    path = tmp_path / "ledger.md"
    path.write_text(TABLE.format(rows=rows), encoding="utf-8")
    return path, parse_ledger(path)


def check(rows, *, lookup=None, searches=(), draft=None, today=date(2026, 10, 16)):
    return check_rows(rows, today=today, draft=draft,
                      unpaywall=lookup or OaLookup(), metadata_clients=tuple(searches))


def test_parse_extracts_source_fields(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Invented Source Title" (2024), DOI: 10.5555/parse.1 | Trail |  | Review |')
    assert rows[0].title == "Invented Source Title"
    assert rows[0].authors == ["A. Example"]
    assert rows[0].year == 2024
    assert rows[0].doi == "10.5555/parse.1"


def test_cleared_alt_label(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Open Placeholder" (2024) | Trail | https://api.openalex.org/W1 | Cleared |')
    result = check(rows)[0]
    assert result.label == "CLEARED_ALT"
    assert result.source_url == "https://api.openalex.org/W1"


def test_oa_candidate_label_and_suggestion(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Candidate Placeholder" (2024), DOI: 10.5555/open.2 | Trail |  | Review |')
    lookup = OaLookup({"10.5555/open.2": Work(
        doi="10.5555/open.2", is_oa=True, oa_url="https://api.unpaywall.org/open.2")})
    results = check(rows, lookup=lookup)
    assert results[0].label == "OA_CANDIDATE"
    assert results[0].is_oa is True
    assert "https://api.unpaywall.org/open.2" in suggested_table(rows, results)


def test_library_only_label(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Closed Placeholder" (2024), DOI: 10.5555/closed.2 | Trail |  | Review |')
    lookup = OaLookup({"10.5555/closed.2": Work(doi="10.5555/closed.2", is_oa=False)})
    result = check(rows, lookup=lookup)[0]
    assert result.label == "LIBRARY_ONLY"
    assert result.is_oa is False


def test_duplicate_doi_and_fuzzy_title_year(tmp_path):
    _, rows = load(tmp_path, "\n".join((
        '| A. Example, "Repeated Synthetic Finding" (2024), DOI: 10.5555/dupe.1 | Trail |  | Review |',
        '| B. Example, "Other Wording" (2023), DOI: 10.5555/dupe.1 | Trail |  | Review |',
        '| C. Example, "Repeated Synthetic Findings" (2024) | Trail |  | Review |',
    )))
    results = check(rows)
    assert results[1].label == "DUPLICATE"
    assert results[2].label == "DUPLICATE"


def test_cited_not_cleared_label(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Draft Citation Placeholder" (2024), DOI: 10.5555/draft.1 | Trail |  | Review |')
    result = check(rows, draft="Discussion citing DOI 10.5555/draft.1.")[0]
    assert result.label == "CITED_NOT_CLEARED"


def test_empty_and_stale_status_are_in_reason(tmp_path):
    _, rows = load(tmp_path, "\n".join((
        '| A. Example, "Empty Status" (2024) | Trail |  |  |',
        '| B. Example, "Stale Status" (2023) | Trail |  | Review by 2026-01-02 |',
    )))
    results = check(rows)
    assert "status is empty" in results[0].reason
    assert "status is stale" in results[1].reason


def test_without_doi_matches_crossref_or_openalex_metadata(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Metadata Match Placeholder" (2024) | Trail |  | Review |')
    search = MetadataSearch([Work("Metadata Match Placeholder", "10.5555/match.1", 2024)])
    result = check(rows, searches=(search,))[0]
    assert result.matched_field == "title+year"
    assert result.source_url == "https://doi.org/10.5555/match.1"
    assert search.calls == [("Metadata Match Placeholder", 5)]


def test_reports_are_json_and_markdown(tmp_path):
    _, rows = load(tmp_path,
        '| A. Example, "Report Placeholder" (2024) | Trail |  | Review |')
    write_reports(check(rows), tmp_path)
    payload = json.loads((tmp_path / "ledger-report.json").read_text(encoding="utf-8"))
    assert payload["results"][0]["label"] == "LIBRARY_ONLY"
    assert "| Row | Source | Label |" in (tmp_path / "ledger-report.md").read_text(encoding="utf-8")


def test_ledger_is_unchanged_after_run(tmp_path):
    path, rows = load(tmp_path,
        '| A. Example, "Unchanged Placeholder" (2024), DOI: 10.5555/safe.1 | Trail |  | Review |')
    before = path.read_bytes()
    results = check(rows, lookup=OaLookup({"10.5555/safe.1": Work(
        doi="10.5555/safe.1", is_oa=True, oa_url="https://api.unpaywall.org/safe.1")}))
    write_reports(results, tmp_path)
    suggested_table(rows, results)
    assert path.read_bytes() == before


def test_cli_run_leaves_ledger_unchanged(tmp_path, monkeypatch):
    path, _ = load(tmp_path,
        '| A. Example, "Command Placeholder" (2024), DOI: 10.5555/command.1 | Trail |  | Review |')
    before = path.read_bytes()

    class CliLookup(OaLookup):
        def __init__(self):
            super().__init__({"10.5555/command.1": Work(
                doi="10.5555/command.1", is_oa=True,
                oa_url="https://api.unpaywall.org/command.1")})

    class CliSearch(MetadataSearch):
        def __init__(self, **_):
            super().__init__()

    monkeypatch.setattr(cli, "UnpaywallClient", CliLookup)
    monkeypatch.setattr(cli, "CrossrefClient", CliSearch)
    monkeypatch.setattr(cli, "OpenAlexClient", CliSearch)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["ledger", "check", str(path), "--today", "2026-10-16"]) == 0
    assert path.read_bytes() == before
    assert (tmp_path / "ledger-report.json").is_file()
