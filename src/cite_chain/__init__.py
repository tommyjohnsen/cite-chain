# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | pending | provenance block added
# END PROVENANCE
"""Citation graph clients and traversal."""

from .models import Edge, Work
from .walk import Graph, walk

__all__ = ["Edge", "Graph", "Work", "walk"]
__version__ = "0.1.0"
