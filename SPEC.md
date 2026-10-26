<!--
PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
written-by: unknown (pre-provenance) | 2026-10-16 | 7c43fb7
modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE_WITH_NITS
END PROVENANCE
-->
# cite-chain: spec

Stdlib-only Python tool that walks citation chains from seed DOIs and sorts what it finds by open-access status.

## Core (module `cite_chain`, console script `cite-chain`)
- Input: seed DOIs (args or a file). Walk references (backward) and cited-by (forward) 1 or 2 hops (`--hops`, default 1, max 2), with `--max-nodes` and a relevance filter hook (keyword list).
- Sources:
  - OpenAlex (primary, `https://api.openalex.org`): works, referenced_works, cited_by via filter. API key from env `OPENALEX_API_KEY` and contact email from env `CONTACT_EMAIL`; cursor paging past page 1 only when both are set (otherwise stop at page 1 and warn).
  - Crossref (gaps, `https://api.crossref.org`): send `mailto` from `CONTACT_EMAIL` (polite pool); max 10 requests/sec, 3 concurrent.
  - Semantic Scholar (citation contexts, `https://api.semanticscholar.org/graph/v1`): optional key from env `S2_API_KEY`; 1 request/sec. Attribution required in output ("Data from Semantic Scholar"). No redistribution: its responses are cached only under the local, git-ignored cache and never written to exported files beyond IDs and our own derived flags.
  - Unpaywall (`https://api.unpaywall.org/v2/{doi}`): DOI lookup only (the search endpoint was retired Sep 18, 2026). Every call needs `email=` from `CONTACT_EMAIL`; without it, skip Unpaywall and fall back to OpenAlex OA fields.
- Dedup across sources by normalized DOI, then by normalized title plus year.
- OA routing: each work is OPEN (with best OA URL) or LIBRARY-ONLY. Non-OA works go to `LIBRARY-ONLY.csv` (full cite fields, DOI, why) for manual retrieval. No PDF downloads, no scraping.
- Outputs: `graph.json` (nodes, edges, hop), `chain.md` (map by hop), `LIBRARY-ONLY.csv`.
- Local cache `.cache/cite-chain/` (git-ignored, never committed).

## Ledger checker (sub-feature, `cite-chain ledger check LEDGER.md [--draft FILE] [--today YYYY-MM-DD]`)
- Deterministic, no model, never reads licensed text. Never edits the ledger; may print a suggested updated table to stdout (`--suggest`).
- Input: a Markdown table at a user-given path with columns `Source | Found via | ALT copy found? (URL) | Status`. Ship a synthetic example at `examples/ledger-example.md` (generic wording, invented sources and DOIs).
- Checks:
  1. Parse: pull a DOI (if any) and the title, authors and year out of the Source column.
  2. Duplicates: flag the same DOI twice, or a fuzzy title-plus-year match.
  3. Open-access lookup: rows with a DOI are looked up in Unpaywall (email from `CONTACT_EMAIL`); report `is_oa` and `best_oa_location.url` as a suggested ALT for the human to confirm. Rows without a DOI are matched on metadata in Crossref and OpenAlex to find one.
  4. Draft check: given a draft file (Markdown, or plain text exported from a word processor), report any ledger source cited in the draft that has no ALT URL and a Status other than cleared (CITED_NOT_CLEARED).
  5. Status: report empty or stale rows (the date in the Status column has passed; today comes from `--today`, default the current date).
- Output: JSON and Markdown reports, one row per source: label (`CLEARED_ALT` | `OA_CANDIDATE` | `LIBRARY_ONLY` | `DUPLICATE` | `CITED_NOT_CLEARED`), matched field, source URL and reason; empty/stale status noted in the reason.
- Tests: mocked network and synthetic rows only.

## Rules for all parts
- Deterministic only: rule-based parsing and exact or fuzzy matching against authoritative sources. No LLM or model makes any pass/fail call, and nothing calls a model API at runtime. Output is a first pass that a human verifies.
- License Apache-2.0 (LICENSE and NOTICE are already here; keep them as they are). pyproject.toml: `license = "Apache-2.0"`, requires-python >=3.11.
- Tests use pytest and must pass with this exact command run from this directory (network is off; the uv cache is pre-warmed):
  `UV_OFFLINE=1 UV_CACHE_DIR=$UVC uv run --no-project --with pytest pytest -q`
  where $UVC is the pre-warmed cache path given in the job prompt. Put `[tool.pytest.ini_options]` with `pythonpath = ["src"]` and `testpaths = ["tests"]` in pyproject.toml. Use a src/ layout.
- All network access in tests is mocked (unittest.mock on the stdlib HTTP layer). No live calls in tests or CI.
- Synthetic fixtures only (synthetic citations and DOIs; no real drafts or notes). No hostnames other than the public API hosts named here, no IPs, local paths, usernames, real emails (use `you@example.com`; contact email only from env `CONTACT_EMAIL` or a config file, never hardcoded), account details, real data or secrets.
- Tokens and contact emails come only from environment variables read at runtime. Never print, log, cache or write their values.
- The README must state that all output needs human verification before use.
- Do not copy text from The Bluebook or any licensed or library source. Do not bundle CSL styles.
- Work only inside this directory. Do not read or copy anything from other directories.
