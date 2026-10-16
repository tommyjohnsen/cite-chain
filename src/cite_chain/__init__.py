"""Citation graph clients and traversal."""

from .models import Edge, Work
from .walk import Graph, walk

__all__ = ["Edge", "Graph", "Work", "walk"]
__version__ = "0.1.0"

