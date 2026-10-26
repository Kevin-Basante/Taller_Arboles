"""Application service that applies the binary search tree to a meteorite catalog."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import GROUPS, Meteorite
from ..structures import BinarySearchTree, DuplicateKeyError, Node, Stack


class CatalogError(ValueError):
    """Business rule violation reported back to the user."""


class MeteoriteCatalog:
    """Meteorite collection stored in a BST ordered by mass (kg).

    Every mutation pushes a snapshot onto an undo Stack. A snapshot is the
    pre-order list of the tree: inserting it again rebuilds the exact same
    shape, which is a nice property of pre-order traversal.
    """

    HISTORY_LIMIT = 30

    def __init__(self, seed_file: Optional[Path] = None) -> None:
        self.tree = BinarySearchTree()
        self.history = Stack(max_size=self.HISTORY_LIMIT)
        self.seed_file = seed_file
        if seed_file is not None:
            self.load_seed()

    # ------------------------------------------------------------------ #
    # Persistence helpers
    # ------------------------------------------------------------------ #
    def load_seed(self) -> None:
        self.tree.clear()
        self.history.clear()
        if self.seed_file is None or not self.seed_file.exists():
            return
        with self.seed_file.open(encoding="utf-8") as handle:
            for record in json.load(handle):
                meteorite = Meteorite.from_dict(record)
                self.tree.insert(meteorite.key, meteorite)

    def _snapshot(self) -> List[Dict[str, Any]]:
        return [node.data.to_dict() for node in self.tree.pre_order()]

    def _restore(self, snapshot: List[Dict[str, Any]]) -> None:
        self.tree.clear()
        for record in snapshot:
            meteorite = Meteorite.from_dict(record)
            self.tree.insert(meteorite.key, meteorite)

    def _remember(self, action: str) -> None:
        self.history.push({"action": action, "snapshot": self._snapshot()})

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #
    def add(self, payload: Dict[str, Any]) -> Meteorite:
        meteorite = Meteorite.from_dict(payload)
        self._ensure_unique_name(meteorite.name)
        if self.tree.contains(meteorite.key):
            raise CatalogError(f"A meteorite with mass {meteorite.mass_kg} kg already exists")
        self._remember(f"Added {meteorite.name}")
        try:
            self.tree.insert(meteorite.key, meteorite)
        except DuplicateKeyError as error:
            self.history.pop()
            raise CatalogError(str(error)) from None
        return meteorite

    def edit(self, key: float, payload: Dict[str, Any]) -> Meteorite:
        node = self._require(key)
        updated = Meteorite.from_dict(payload)
        self._ensure_unique_name(updated.name, ignore_key=key)
        if updated.key != key and self.tree.contains(updated.key):
            raise CatalogError(f"A meteorite with mass {updated.mass_kg} kg already exists")
        self._remember(f"Edited {node.data.name}")
        if updated.key == key:
            self.tree.update(key, updated)
        else:
            # The key changed, so the node must move to a new position.
            self.tree.delete(key)
            self.tree.insert(updated.key, updated)
        return updated

    def remove(self, key: float) -> Meteorite:
        node = self._require(key)
        case = {0: "leaf", 1: "one child", 2: "two children"}[node.degree]
        self._remember(f"Removed {node.data.name} ({case})")
        return self.tree.delete(key)

    def rebalance(self) -> Dict[str, int]:
        before = self.tree.height()
        self._remember("Rebalanced tree")
        self.tree.rebalance()
        return {"height_before": before, "height_after": self.tree.height()}

    def undo(self) -> str:
        if self.history.is_empty():
            raise CatalogError("Nothing to undo")
        entry = self.history.pop()
        self._restore(entry["snapshot"])
        return entry["action"]

    def reset(self) -> None:
        self.load_seed()

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    def search(self, mass: float) -> Dict[str, Any]:
        path, found = self.tree.search_path(mass)
        node = self.tree.search(mass) if found else None
        return {
            "found": found,
            "path": path,
            "comparisons": len(path),
            "meteorite": node.data.to_dict() if node else None,
        }

    def search_by_name(self, text: str) -> List[Dict[str, Any]]:
        """Name is not the ordering key, so a full traversal is required: O(n)."""
        needle = text.strip().lower()
        return self._serialize(self.tree.filter(lambda node: needle in node.data.name.lower()))

    def traversal(self, kind: str) -> List[Dict[str, Any]]:
        strategies = {
            "in-order": lambda: self.tree.in_order(),
            "reverse-in-order": lambda: self.tree.in_order(descending=True),
            "pre-order": self.tree.pre_order,
            "post-order": self.tree.post_order,
            "level-order": self.tree.level_order,
        }
        if kind not in strategies:
            raise CatalogError(f"Unknown traversal '{kind}'")
        return self._serialize(strategies[kind]())

    def levels(self) -> List[List[Dict[str, Any]]]:
        return [self._serialize(level) for level in self.tree.levels()]

    def mass_range(self, low: float, high: float) -> List[Dict[str, Any]]:
        if low > high:
            low, high = high, low
        return self._serialize(self.tree.range_search(low, high))

    def closest(self, mass: float) -> Dict[str, Any]:
        return {
            "floor": self._serialize_one(self.tree.floor(mass)),
            "ceiling": self._serialize_one(self.tree.ceiling(mass)),
            "closest": self._serialize_one(self.tree.closest(mass)),
        }

    def kth_lightest(self, k: int) -> Optional[Dict[str, Any]]:
        return self._serialize_one(self.tree.kth_smallest(k))

    def kth_heaviest(self, k: int) -> Optional[Dict[str, Any]]:
        return self._serialize_one(self.tree.kth_smallest(self.tree.weight - k + 1))

    def common_ancestor(self, key_a: float, key_b: float) -> Dict[str, Any]:
        self._require(key_a)
        self._require(key_b)
        ancestor = self.tree.lowest_common_ancestor(key_a, key_b)
        return {
            "ancestor": self._serialize_one(ancestor),
            "distance": self.tree.distance_between(key_a, key_b),
            "path_a": [node.key for node in self.tree.path_from_root(key_a)],
            "path_b": [node.key for node in self.tree.path_from_root(key_b)],
        }

    def describe(self, key: float) -> Dict[str, Any]:
        """Every tree concept from the slides applied to one node."""
        node = self._require(key)
        parent = self.tree.parent_of(key)
        sibling = self.tree.sibling_of(key)
        if node is self.tree.root:
            role = "Root"
        elif node.is_leaf():
            role = "Leaf"
        else:
            role = "Branch"
        return {
            "meteorite": node.data.to_dict(),
            "role": role,
            "level": self.tree.level_of(key),
            "degree": node.degree,
            "parent": self._serialize_one(parent),
            "sibling": self._serialize_one(sibling),
            "children": self._serialize([child for child in (node.left, node.right) if child]),
            "subtree_height": self.tree.height(node, from_root=False),
            "subtree_weight": self.tree.subtree_weight(node),
            "balance_factor": self.tree.balance_factor(node),
            "path": [step.key for step in self.tree.path_from_root(key)],
        }

    def statistics(self) -> Dict[str, Any]:
        tree = self.tree
        nodes = tree.in_order()
        lightest, heaviest = tree.min_node(), tree.max_node()
        total_mass = sum(node.key for node in nodes)
        groups = Counter(node.data.group for node in nodes)
        return {
            "weight": tree.weight,
            "height": tree.height(),
            "levels": len(tree.levels()),
            "order": tree.ORDER,
            "max_degree": tree.max_degree(),
            "leaves": len(tree.leaves()),
            "branches": len(tree.branches()),
            "is_balanced": tree.is_balanced(),
            "is_valid": tree.is_valid(),
            "root": self._serialize_one(tree.root),
            "lightest": self._serialize_one(lightest),
            "heaviest": self._serialize_one(heaviest),
            "total_mass_kg": round(total_mass, 3),
            "groups": {group: groups.get(group, 0) for group in GROUPS},
            "fell": sum(1 for node in nodes if node.data.recovery == "Fell"),
            "found": sum(1 for node in nodes if node.data.recovery == "Found"),
        }

    def state(self) -> Dict[str, Any]:
        """Everything the frontend needs to redraw itself."""
        return {
            "tree": self.tree.to_nested(self._node_view),
            "stats": self.statistics(),
            "can_undo": not self.history.is_empty(),
            "history": [entry["action"] for entry in self.history],
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _require(self, key: float) -> Node:
        node = self.tree.search(key)
        if node is None:
            raise CatalogError(f"No meteorite with mass {key} kg")
        return node

    def _ensure_unique_name(self, name: str, ignore_key: Optional[float] = None) -> None:
        for node in self.tree.filter(lambda item: item.data.name.lower() == name.lower()):
            if node.key != ignore_key:
                raise CatalogError(f"'{name}' is already in the catalog")

    def _node_view(self, node: Node) -> Dict[str, Any]:
        view = node.data.to_dict()
        view["key"] = node.key
        view["degree"] = node.degree
        view["balance_factor"] = self.tree.balance_factor(node)
        return view

    @staticmethod
    def _serialize_one(node: Optional[Node]) -> Optional[Dict[str, Any]]:
        if node is None:
            return None
        payload = node.data.to_dict()
        payload["key"] = node.key
        return payload

    def _serialize(self, nodes: List[Node]) -> List[Dict[str, Any]]:
        return [self._serialize_one(node) for node in nodes]
