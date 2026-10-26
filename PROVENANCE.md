# Provenance

Generated from `.provenance/ledger.jsonl` by the operator tool; do not edit by hand. The ledger is the record of truth; per-file `PROVENANCE` headers mirror it, and the ledger wins on any disagreement.

Each ledger line is one JSON object with `path`, `blob`, `event` (`written` or `reviewed`), `by` (seat/model, or `unknown (pre-provenance)` for history whose author is not recorded), `date`, and either `commit` (written) or `verdict`, `head` and `record` (reviewed). Verdicts are `APPROVE`, `APPROVE_WITH_NITS` or `REJECT`.

`blob` is the git blob SHA-1 of the file after removing its PROVENANCE header block: the lines from the `PROVENANCE` line through the `END PROVENANCE` line inclusive, plus a directly enclosing `<!--` / `-->` line pair. A review applies only while the file's current `blob` equals the reviewed one; any content change makes it stale. A release needs current reviews from claude-code and grok-build; an author never reviews its own work.

Files tracked: 26 (excluding this summary and `.provenance/`). Inline headers: 21. Ledger-only: 5. Written entries current: 26/26. Current reviews: claude-code 26, grok-build 26. Current REJECTs: 0.

| path | header | written-by (current content) | claude-code | grok-build |
|---|---|---|---|---|
| `.github/workflows/test.yml` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `.gitignore` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `LICENSE` | ledger | unknown (pre-provenance) | APPROVE | APPROVE |
| `NOTICE` | ledger | unknown (pre-provenance) | APPROVE | APPROVE |
| `README.md` | inline | unknown (pre-provenance) | APPROVE_WITH_NITS | APPROVE_WITH_NITS |
| `SPEC.md` | inline | unknown (pre-provenance) | APPROVE_WITH_NITS | APPROVE_WITH_NITS |
| `examples/ledger-example.md` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `pyproject.toml` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `src/cite_chain/__init__.py` | inline | codex/gpt-5.6-sol | APPROVE_WITH_NITS | APPROVE_WITH_NITS |
| `src/cite_chain/cli.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `src/cite_chain/clients.py` | inline | codex/gpt-5.6-sol | APPROVE_WITH_NITS | APPROVE |
| `src/cite_chain/http.py` | inline | codex/gpt-5.6-sol | APPROVE_WITH_NITS | APPROVE_WITH_NITS |
| `src/cite_chain/ledger.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE_WITH_NITS |
| `src/cite_chain/models.py` | inline | codex/gpt-5.6-sol | APPROVE | APPROVE |
| `src/cite_chain/oa.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `src/cite_chain/outputs.py` | inline | unknown (pre-provenance) | APPROVE_WITH_NITS | APPROVE_WITH_NITS |
| `src/cite_chain/walk.py` | inline | codex/gpt-5.6-sol | APPROVE | APPROVE |
| `tests/golden/LIBRARY-ONLY.csv` | ledger | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/golden/chain.md` | ledger | unknown (pre-provenance) | APPROVE | APPROVE_WITH_NITS |
| `tests/golden/graph.json` | ledger | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/test_cli.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/test_clients.py` | inline | codex/gpt-5.6-sol | APPROVE | APPROVE |
| `tests/test_ledger.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/test_oa.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/test_outputs_golden.py` | inline | unknown (pre-provenance) | APPROVE | APPROVE |
| `tests/test_walk.py` | inline | codex/gpt-5.6-sol | APPROVE | APPROVE |
