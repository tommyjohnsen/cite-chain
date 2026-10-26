<!--
PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE_WITH_NITS
END PROVENANCE
-->
# cite-chain

`cite-chain` is a small, deterministic Python tool for walking scholarly
citation links from DOI seeds. It queries public metadata APIs, deduplicates
works across providers, identifies open-access candidates, and keeps each walk
bounded by hop and node limits. It does not download PDFs or scrape websites,
and no model makes a pass/fail decision.

All output is a first pass and needs human verification before use.

## Install

Python 3.11 or newer is required. From the project directory, run:

```console
pip install .
```

## Citation-chain usage

Pass one or more seed DOIs directly:

```console
CONTACT_EMAIL=you@example.com cite-chain --hops 1 10.5555/example.1
```

Seeds can instead be listed one per line in a file with `--file`. Use
`--hops 1` or `--hops 2`, `--max-nodes` to bound the graph, and repeat
`--keyword` to retain works whose title or abstract contains any supplied
term. `--output` selects the destination directory. The command writes:

- `graph.json`, containing nodes, edges, and discovery hops;
- `chain.md`, a readable map organized by hop; and
- `LIBRARY-ONLY.csv`, containing works for which no open copy was identified.

Records are deduplicated first by normalized DOI and then by normalized title
plus year. Open-access routing checks Unpaywall when a contact email is
available and otherwise falls back to OpenAlex open-access fields.

### API configuration and terms

Credentials and contact details are read only from environment variables at
runtime and are never included in output.

- **OpenAlex:** `OPENALEX_API_KEY` supplies the optional API key and
  `CONTACT_EMAIL` supplies the contact email. Cursor paging beyond the first
  page occurs only when both are set; otherwise the tool stops after page one
  and warns.
- **Crossref:** `CONTACT_EMAIL` is sent as the `mailto` value for polite-pool
  identification. The client is limited to ten requests per second and three
  concurrent requests.
- **Semantic Scholar:** `S2_API_KEY` supplies the optional API key. Output that
  uses this source includes the required “Data from Semantic Scholar”
  attribution. Responses must not be redistributed: they are cached only in
  the local, ignored `.cache/cite-chain/` directory and are never copied into
  exports beyond identifiers and locally derived flags. The client is limited
  to one request per second.
- **Unpaywall:** `CONTACT_EMAIL` is required and is sent as the `email=` query
  parameter on every call. Only DOI lookup is used; the retired search endpoint
  is not used. Without an email, the tool skips Unpaywall and uses OpenAlex
  open-access fields.

Users are responsible for checking the current provider terms and any terms
or licenses attached to fetched metadata before using or sharing it.

## Ledger checker

Run the deterministic ledger checker with:

```console
CONTACT_EMAIL=you@example.com cite-chain ledger check LEDGER.md --draft DRAFT.md --today 2026-10-16
```

The input is a Markdown table with these exact columns:

| Source | Found via | ALT copy found? (URL) | Status |
| --- | --- | --- | --- |
| A. Example, "Synthetic Signals in Generic Systems" (2024), DOI: 10.5555/example.signal | Citation trail |  | Review by 2027-02-01 |

The checker performs five checks:

1. **Parse:** extracts any DOI and the title, authors, and year from `Source`.
2. **Duplicates:** finds repeated DOIs and fuzzy title-plus-year matches.
3. **Open access:** looks up DOI rows in Unpaywall and suggests its
   `is_oa`/`best_oa_location.url` result for human confirmation. For rows
   without a DOI, it searches Crossref and OpenAlex metadata for a match.
4. **Draft:** with `--draft`, reports a ledger source cited in the plain-text or
   Markdown draft when the row has no alternative URL and is not cleared.
5. **Status:** notes empty status cells and dates that precede `--today` (or the
   current date when `--today` is omitted).

It writes `ledger-report.json` and `ledger-report.md`, with one result per
source. Each result has a matched field, source URL, reason, and one of these
labels: `CLEARED_ALT`, `OA_CANDIDATE`, `LIBRARY_ONLY`, `DUPLICATE`, or
`CITED_NOT_CLEARED`. `--suggest` prints a proposed updated table to standard
output. The checker never edits the ledger.

A complete invented input is available at
[`examples/ledger-example.md`](examples/ledger-example.md). For example, a
repeated `10.5555/example.signal` DOI is labeled `DUPLICATE`; an open-location
match can be labeled `OA_CANDIDATE`; and a draft citation that lacks both a
cleared status and an alternative URL is labeled `CITED_NOT_CLEARED`.

## Exit codes

- `0`: the command completed and wrote its outputs.
- `2`: command-line arguments, a ledger date, or a ledger input were invalid.
- Other nonzero values indicate an unexpected I/O, network, or runtime failure.

## Limits

- Walks are limited to one or two hops and the configured maximum node count;
  relevance filtering is a simple keyword match.
- Provider coverage, metadata quality, API availability, and rate limits can
  make the graph or open-access result incomplete. OpenAlex paging is also
  limited without both its key and a contact email.
- Open-access URLs and ledger matches are candidates, not legal, bibliographic,
  or availability determinations. The tool neither retrieves restricted works
  nor validates rights to reuse fetched data.

## Dependencies and licenses

The installed application has no third-party runtime package dependencies; it
uses the Python standard library, distributed under the PSF License, which is
compatible with this project's Apache-2.0 license. Its declared build backend
is Hatchling (MIT), and its development test dependency is pytest (MIT). Both
permissive licenses allow their use to build and test an Apache-2.0 project
without changing the license of this project's code. The optional `uv` test
runner is dual-licensed under Apache-2.0 or MIT and is likewise compatible.

OpenAlex, Crossref, Semantic Scholar, and Unpaywall are external services, not
redistributed software dependencies. Their operational and data-use terms
still apply: provide the required contact information, observe the request
limits above, retain Semantic Scholar attribution, do not redistribute its
responses, and review the applicable terms and metadata licenses before reuse.

The project itself is licensed under Apache-2.0; see `LICENSE` and `NOTICE`.
