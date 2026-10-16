# cite-chain

`cite-chain` is a small, dependency-free Python tool for walking scholarly
citation links from one or more DOI seeds. It queries public metadata APIs,
deduplicates records across providers, and keeps the walk bounded by hop and
node limits.

```console
CONTACT_EMAIL=you@example.com cite-chain --hops 1 10.5555/example.1
```

Use `--keyword` more than once to retain records whose title or abstract
contains at least one requested term. Seeds may also be supplied one per line
with `--file`. The command writes `graph.json`, `chain.md`, and
`LIBRARY-ONLY.csv` to the selected output directory. API credentials and contact details are read only
from `OPENALEX_API_KEY`, `S2_API_KEY`, and `CONTACT_EMAIL`; they are never
included in output. Semantic Scholar responses remain in the local
`.cache/cite-chain/` cache, while exported graph data contains only normalized
metadata and identifiers. Open-access routing checks Unpaywall first when a
contact email is available, then uses OpenAlex OA fields as its fallback.

The `cite-chain ledger` command group is reserved for the ledger checker in a
later release.

All output is a first pass and needs human verification before use.
