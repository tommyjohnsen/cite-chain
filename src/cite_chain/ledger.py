# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | 4cb39b9
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# END PROVENANCE
"""Deterministic checks for a Markdown source ledger."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
from typing import Protocol

from .models import Work, normalize_doi, normalize_title


HEADERS = ("Source", "Found via", "ALT copy found? (URL)", "Status")
DOI_RE = re.compile(r"(?i)(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:a-z0-9]+)")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
URL_RE = re.compile(r"https?://[^\s<>|]+", re.I)
DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")


class MetadataClient(Protocol):
    def search(self, title: str, *, limit: int = 5) -> list[Work]: ...


class OaClient(Protocol):
    def lookup(self, doi: str) -> Work | None: ...


@dataclass(slots=True)
class LedgerRow:
    source: str
    found_via: str
    alt: str
    status: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None


@dataclass(slots=True)
class CheckResult:
    row: int
    source: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    label: str
    matched_field: str
    source_url: str | None
    is_oa: bool | None
    reason: str


def _cells(line: str) -> list[str]:
    """Split a Markdown table row while respecting escaped pipes."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith(r"\|"):
        line = line[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_source(value: str) -> tuple[str, list[str], int | None, str | None]:
    """Extract common citation fields without interpreting licensed text."""
    doi_match = DOI_RE.search(value)
    doi = normalize_doi(doi_match.group(1)) if doi_match else None
    year_match = YEAR_RE.search(DOI_RE.sub("", value))
    year = int(year_match.group(1)) if year_match else None

    quoted = re.search(r"[\"“]([^\"”]+)[\"”]", value)
    if quoted:
        title = quoted.group(1).strip(" .,;")
        prefix = value[:quoted.start()].strip(" .,;()")
    else:
        clean = DOI_RE.sub("", value)
        clean = re.sub(r"(?i)https?://\S+", "", clean)
        clean = YEAR_RE.sub("", clean)
        clean = re.sub(r"\(\s*\)", "", clean).strip(" .,;-")
        parts = [part.strip(" .,;()") for part in re.split(r"\.\s+", clean) if part.strip(" .,;()")]
        if len(parts) >= 2:
            prefix, title = parts[0], max(parts[1:], key=len)
        else:
            comma = [part.strip() for part in clean.split(",") if part.strip()]
            prefix = comma[0] if len(comma) > 1 else ""
            title = max(comma[1:], key=len) if len(comma) > 1 else clean
    authors = [part.strip() for part in re.split(r"\s*(?:;|\band\b|&)\s*", prefix, flags=re.I)
               if part.strip()]
    return title.strip(" .,;"), authors, year, doi


def parse_ledger(path: Path) -> list[LedgerRow]:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        cells = _cells(line)
        if tuple(cell.casefold() for cell in cells) == tuple(x.casefold() for x in HEADERS):
            if index + 1 >= len(lines) or not _is_separator(_cells(lines[index + 1])):
                raise ValueError("ledger table header must be followed by a Markdown separator row")
            rows: list[LedgerRow] = []
            for candidate in lines[index + 2:]:
                if not candidate.strip():
                    if rows:
                        break
                    continue
                values = _cells(candidate)
                if len(values) != len(HEADERS):
                    if rows:
                        break
                    continue
                title, authors, year, doi = parse_source(values[0])
                rows.append(LedgerRow(*values, title, authors, year, doi))
            return rows
    raise ValueError("ledger must contain columns: " + " | ".join(HEADERS))


def _similar(left: str, right: str) -> bool:
    left_n, right_n = normalize_title(left), normalize_title(right)
    if not left_n or not right_n:
        return False
    if left_n == right_n:
        return True
    return SequenceMatcher(None, left_n, right_n, autojunk=False).ratio() >= 0.9


def _alt_url(value: str) -> str | None:
    match = URL_RE.search(value)
    return match.group(0).rstrip(".,;)") if match else None


def _is_cleared(status: str) -> bool:
    return bool(re.search(r"\bcleared\b", status, re.I))


def _status_note(status: str, today: date) -> str | None:
    if not status.strip():
        return "status is empty"
    dates: list[date] = []
    for raw in DATE_RE.findall(status):
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError:
            continue
    if dates and min(dates) < today:
        return f"status is stale (date {min(dates).isoformat()} has passed)"
    return None


def _cited(row: LedgerRow, draft: str) -> bool:
    folded = draft.casefold()
    if row.doi and row.doi in folded:
        return True
    title = normalize_title(row.title)
    if title and title in normalize_title(draft):
        return True
    if row.year:
        for author in row.authors:
            words = re.findall(r"[a-z0-9]+", author.casefold())
            if words and re.search(rf"\b{re.escape(words[-1])}\b[^\n]{{0,40}}\b{row.year}\b", folded):
                return True
    return False


def _match_metadata(row: LedgerRow, clients: tuple[MetadataClient, ...]) -> tuple[Work | None, str]:
    best: Work | None = None
    best_score = -1.0
    for client in clients:
        for work in client.search(row.title, limit=5):
            if row.year is not None and work.year is not None and row.year != work.year:
                continue
            left, right = normalize_title(row.title), normalize_title(work.title)
            score = SequenceMatcher(None, left, right, autojunk=False).ratio() if left and right else 0.0
            if score >= 0.9 and (score > best_score or
                                 (score == best_score and work.oa_url and not (best and best.oa_url))):
                best, best_score = work, score
    return best, "title+year" if best else "none"


def check_rows(rows: list[LedgerRow], *, today: date, draft: str | None,
               unpaywall: OaClient, metadata_clients: tuple[MetadataClient, ...]) -> list[CheckResult]:
    results: list[CheckResult] = []
    seen_doi: dict[str, int] = {}
    seen_titles: list[tuple[str, int | None, int]] = []
    for number, row in enumerate(rows, start=1):
        duplicate_of: int | None = None
        if row.doi and row.doi in seen_doi:
            duplicate_of = seen_doi[row.doi]
        elif row.year is not None:
            for title, year, earlier in seen_titles:
                if year == row.year and _similar(title, row.title):
                    duplicate_of = earlier
                    break
        if row.doi:
            seen_doi.setdefault(row.doi, number)
        seen_titles.append((row.title, row.year, number))

        alt = _alt_url(row.alt)
        matched = "doi" if row.doi else "none"
        candidate: Work | None = None
        lookup_error: str | None = None
        try:
            if row.doi:
                candidate = unpaywall.lookup(row.doi)
            elif row.title:
                candidate, matched = _match_metadata(row, metadata_clients)
        except Exception as exc:
            lookup_error = f"metadata lookup failed ({type(exc).__name__})"

        candidate_url = candidate.oa_url if candidate else None
        metadata_url = None
        if candidate:
            metadata_url = (candidate_url or
                            (f"https://doi.org/{candidate.doi}" if candidate.doi else None) or
                            candidate.source_ids.get("openalex"))
        source_url = alt or metadata_url or (f"https://doi.org/{row.doi}" if row.doi else None)
        cited_uncleared = bool(draft is not None and _cited(row, draft) and not alt and not _is_cleared(row.status))
        if duplicate_of is not None:
            label, reason = "DUPLICATE", f"duplicates row {duplicate_of}"
        elif cited_uncleared:
            label, reason = "CITED_NOT_CLEARED", "source appears in draft without an ALT URL or cleared status"
        elif alt:
            label, reason = "CLEARED_ALT", "ledger contains an ALT URL for human confirmation"
        elif candidate_url and (candidate.is_oa is not False):
            label, reason = "OA_CANDIDATE", "authoritative metadata suggests an open-access URL for human confirmation"
        else:
            label = "LIBRARY_ONLY"
            if row.doi and candidate and candidate.is_oa is False:
                reason = "Unpaywall reports no open-access location"
            elif not row.doi and candidate:
                reason = "metadata match found, but no verified open-access URL"
            elif row.doi and candidate is None:
                reason = "no Unpaywall record available"
            else:
                reason = "no authoritative metadata match or verified open-access URL"
        note = _status_note(row.status, today)
        details = [reason]
        if lookup_error:
            details.append(lookup_error)
        if note:
            details.append(note)
        results.append(CheckResult(number, row.source, row.title, row.authors, row.year, row.doi,
                                   label, matched, source_url,
                                   candidate.is_oa if candidate else None, "; ".join(details)))
    return results


def write_reports(results: list[CheckResult], directory: Path = Path(".")) -> None:
    payload = {"generated_by": "cite-chain ledger check", "results": [asdict(item) for item in results]}
    (directory / "ledger-report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = ["# Ledger check", "", "First-pass results; verify every record before use.", "",
             "| Row | Source | Label | Matched field | Is OA | Source URL | Reason |",
             "| ---: | --- | --- | --- | --- | --- | --- |"]
    for item in results:
        is_oa = "true" if item.is_oa is True else "false" if item.is_oa is False else "unknown"
        values = (str(item.row), item.source, item.label, item.matched_field, is_oa,
                  item.source_url or "", item.reason)
        lines.append("| " + " | ".join(value.replace("|", r"\|").replace("\n", " ") for value in values) + " |")
    (directory / "ledger-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def suggested_table(rows: list[LedgerRow], results: list[CheckResult]) -> str:
    lines = ["| " + " | ".join(HEADERS) + " |", "| --- | --- | --- | --- |"]
    for row, result in zip(rows, results, strict=True):
        alt = row.alt
        if not _alt_url(alt) and result.label == "OA_CANDIDATE" and result.source_url:
            alt = result.source_url
        values = (row.source, row.found_via, alt, row.status)
        lines.append("| " + " | ".join(value.replace("|", r"\|").replace("\n", " ") for value in values) + " |")
    return "\n".join(lines) + "\n"
