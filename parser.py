"""Parse Kaner et al. taxonomy from Markdown into a navigable tree."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from slugify import slugify


class TaxonomyNode:
    def __init__(
        self,
        *,
        node_id: str,
        name: str,
        level: int,
        description: str = "",
        parent_id: Optional[str] = None,
    ) -> None:
        self.id = node_id
        self.name = name
        self.level = level
        self.description = description.strip()
        self.parent_id = parent_id
        self.children: list[str] = []

    def to_dict(self, include_children: bool = True) -> dict:
        result = {
            "id": self.id,
            "name": self.name,
            "level": self.level,
            "description": self.description,
            "parent_id": self.parent_id,
        }
        if include_children:
            result["children"] = self.children
        return result


class KanerTaxonomy:
    def __init__(self, md_path: Path) -> None:
        self.nodes: dict[str, TaxonomyNode] = {}
        self.root_ids: list[str] = []
        self._parse(md_path)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        # The detailed content begins at the first H1 heading.
        h1_match = re.search(r"^# ", text, re.MULTILINE)
        if not h1_match:
            raise ValueError("No H1 heading found in the taxonomy file.")
        content = text[h1_match.start():]

        # Split into (heading_level, heading_text, body_text) tuples.
        pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(content))

        # We track id-collision counts so duplicate names get unique slugs.
        slug_counts: dict[str, int] = {}

        def make_id(name: str) -> str:
            base = slugify(name)
            if base not in slug_counts:
                slug_counts[base] = 0
                return base
            slug_counts[base] += 1
            return f"{base}-{slug_counts[base]}"

        # Stack holds (level, node_id) for the currently open ancestors.
        stack: list[tuple[int, str]] = []

        for i, m in enumerate(matches):
            level = len(m.group(1))
            name = m.group(2).strip()

            # Collect body text between this heading and the next.
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            description = content[body_start:body_end].strip()
            # Remove sub-heading markup that leaked into description (shouldn't
            # happen, but belt-and-suspenders).
            description = re.sub(r"^#{1,4}\s+.+$", "", description, flags=re.MULTILINE).strip()

            node_id = make_id(name)

            # Determine parent: pop stack entries deeper-or-equal to current level.
            while stack and stack[-1][0] >= level:
                stack.pop()

            parent_id = stack[-1][1] if stack else None

            node = TaxonomyNode(
                node_id=node_id,
                name=name,
                level=level,
                description=description,
                parent_id=parent_id,
            )
            self.nodes[node_id] = node

            if parent_id:
                self.nodes[parent_id].children.append(node_id)
            else:
                self.root_ids.append(node_id)

            stack.append((level, node_id))

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get(self, node_id: str) -> Optional[TaxonomyNode]:
        return self.nodes.get(node_id)

    def roots(self) -> list[TaxonomyNode]:
        return [self.nodes[nid] for nid in self.root_ids]

    def subtree(self, node_id: str) -> Optional[dict]:
        node = self.nodes.get(node_id)
        if node is None:
            return None
        result = node.to_dict()
        result["children"] = [self.subtree(cid) for cid in node.children]
        return result

    def flat_list(self) -> list[TaxonomyNode]:
        return list(self.nodes.values())

    def leaves(self) -> list[TaxonomyNode]:
        return [n for n in self.nodes.values() if not n.children]

    def path_to(self, node_id: str) -> list[TaxonomyNode]:
        """Return ancestor chain from root to the given node (inclusive)."""
        node = self.nodes.get(node_id)
        if node is None:
            return []
        chain: list[TaxonomyNode] = []
        current: Optional[TaxonomyNode] = node
        while current:
            chain.append(current)
            current = self.nodes.get(current.parent_id) if current.parent_id else None
        chain.reverse()
        return chain

    def search(self, query: str) -> list[TaxonomyNode]:
        q = query.lower()
        return [
            n
            for n in self.nodes.values()
            if q in n.name.lower() or q in n.description.lower()
        ]

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_node(
        self,
        name: str,
        description: str = "",
        parent_id: Optional[str] = None,
    ) -> TaxonomyNode:
        if parent_id is not None and parent_id not in self.nodes:
            raise KeyError(f"Parent node '{parent_id}' not found.")

        level = (self.nodes[parent_id].level + 1) if parent_id else 1

        base = slugify(name)
        node_id, counter = base, 1
        while node_id in self.nodes:
            node_id = f"{base}-{counter}"
            counter += 1

        node = TaxonomyNode(
            node_id=node_id,
            name=name,
            level=level,
            description=description,
            parent_id=parent_id,
        )
        self.nodes[node_id] = node

        if parent_id:
            self.nodes[parent_id].children.append(node_id)
        else:
            self.root_ids.append(node_id)

        return node

    def update_node(
        self,
        node_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[TaxonomyNode]:
        node = self.nodes.get(node_id)
        if node is None:
            return None
        if name is not None:
            node.name = name
        if description is not None:
            node.description = description
        return node
