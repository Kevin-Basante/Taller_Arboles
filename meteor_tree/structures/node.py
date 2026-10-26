"""Node used by the binary search tree."""

from typing import Any, Optional


class Node:
    """A single node of a binary tree.

    Each node stores a comparable key (used to order the tree), the data
    associated with that key and references to its left and right children.
    """

    def __init__(self, key: float, data: Any) -> None:
        self.key = key
        self.data = data
        self.left: Optional["Node"] = None
        self.right: Optional["Node"] = None

    @property
    def degree(self) -> int:
        """Number of children of the node (0, 1 or 2)."""
        return int(self.left is not None) + int(self.right is not None)

    def is_leaf(self) -> bool:
        return self.degree == 0

    def __repr__(self) -> str:
        return f"Node(key={self.key!r})"
