"""Bounded breadth-first citation graph traversal."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Protocol

from .models import Edge, Work, normalize_title


class Source(Protocol):
    def get_work(self, identifier: str) -> Work | None: ...
    def references(self, work: Work) -> list[Work]: ...
    def citations(self, work: Work) -> list[Work]: ...


@dataclass
class Graph:
    nodes: dict[str, Work] = field(default_factory=dict)
    hops: dict[str, int] = field(default_factory=dict)
    edges: set[Edge] = field(default_factory=set)
    attributions: set[str] = field(default_factory=set)

    def add(self, work: Work, hop: int) -> tuple[str, bool]:
        # DOI is authoritative. For DOI-less records, title plus year is the key.
        key = work.key
        if key in self.nodes:
            self.nodes[key].merge(work)
            self.hops[key] = min(self.hops[key], hop)
            return key, False
        normalized = normalize_title(work.title)
        same_metadata = next(
            (existing_key for existing_key, existing in self.nodes.items()
             if normalized and normalize_title(existing.title) == normalized and existing.year == work.year),
            None,
        )
        if same_metadata is not None:
            existing = self.nodes[same_metadata]
            existing.merge(work)
            destination = existing.key
            if destination != same_metadata:
                self.nodes.pop(same_metadata)
                old_hop = self.hops.pop(same_metadata)
                self.nodes[destination] = existing
                self.hops[destination] = min(old_hop, hop)
                self.edges = {Edge(destination if e.source == same_metadata else e.source,
                                   destination if e.target == same_metadata else e.target, e.relation)
                              for e in self.edges}
            else:
                self.hops[same_metadata] = min(self.hops[same_metadata], hop)
            return destination, False
        # A later provider may add a DOI to an existing title/year record.
        title_key = f"title:{normalize_title(work.title)}:{work.year or ''}"
        if work.doi and title_key in self.nodes:
            existing = self.nodes.pop(title_key).merge(work)
            old_hop = self.hops.pop(title_key)
            self.nodes[key] = existing
            self.hops[key] = min(old_hop, hop)
            self.edges = {Edge(key if e.source == title_key else e.source,
                               key if e.target == title_key else e.target, e.relation) for e in self.edges}
            return key, False
        self.nodes[key] = work
        self.hops[key] = hop
        return key, True

    def as_dict(self) -> dict[str, object]:
        nodes = [{**work.public_dict(), "hop": self.hops[key]}
                 for key, work in sorted(self.nodes.items())]
        edges = [{"source": e.source, "target": e.target, "relation": e.relation}
                 for e in sorted(self.edges, key=lambda x: (x.source, x.target, x.relation))]
        result: dict[str, object] = {"nodes": nodes, "edges": edges}
        if self.attributions:
            result["attributions"] = sorted(self.attributions)
        return result


def _relevant(work: Work, keywords: tuple[str, ...]) -> bool:
    if not keywords:
        return True
    haystack = f"{work.title} {work.abstract}".casefold()
    return any(keyword.casefold() in haystack for keyword in keywords)


def walk(seeds: list[str], sources: list[Source], *, hops: int = 1,
         max_nodes: int = 100, keywords: tuple[str, ...] = ()) -> Graph:
    if hops not in (1, 2):
        raise ValueError("hops must be 1 or 2")
    if max_nodes < 1:
        raise ValueError("max_nodes must be positive")
    graph = Graph()
    queue: deque[tuple[str, int]] = deque()
    for seed in seeds:
        records = [record for source in sources if (record := source.get_work(seed))]
        if not records:
            records = [Work(doi=seed)]
        first = records[0]
        for record in records[1:]:
            first.merge(record)
        key, fresh = graph.add(first, 0)
        if fresh:
            queue.append((key, 0))
        if len(graph.nodes) >= max_nodes:
            break
    expanded: set[tuple[str, int]] = set()
    while queue and len(graph.nodes) < max_nodes:
        key, hop = queue.popleft()
        if hop >= hops or (key, hop) in expanded or key not in graph.nodes:
            continue
        expanded.add((key, hop))
        current = graph.nodes[key]
        for source in sources:
            for relation, getter in (("references", source.references), ("cited_by", source.citations)):
                for neighbor in getter(current):
                    if not _relevant(neighbor, keywords):
                        continue
                    neighbor_key, fresh = graph.add(neighbor, hop + 1)
                    if relation == "references":
                        edge = Edge(key, neighbor_key, relation)
                    else:
                        edge = Edge(neighbor_key, key, relation)
                    graph.edges.add(edge)
                    if fresh and len(graph.nodes) < max_nodes:
                        queue.append((neighbor_key, hop + 1))
                    if len(graph.nodes) >= max_nodes:
                        break
                if len(graph.nodes) >= max_nodes:
                    break
            if len(graph.nodes) >= max_nodes:
                break
    if any("semantic_scholar" in work.source_ids for work in graph.nodes.values()):
        graph.attributions.add("Data from Semantic Scholar")
    return graph
