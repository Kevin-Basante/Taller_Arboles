"""Binary Search Tree (order 2) with a rich set of operations.

Terminology follows the class slides:
    * Root:   first node of the tree.
    * Parent: node with at least one child.
    * Child:  node that has a parent.
    * Sibling: nodes that share the same parent.
    * Leaf:   node without children.
    * Branch: node that is not the root and has at least one child.
    * Level:  distance from the root, the root being level 1.
    * Height: length (in edges) of the longest path from the root to a leaf.
    * Weight: number of nodes in the tree.
    * Order:  maximum number of children a node may have (2 here).
    * Degree: number of children of a node.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from .node import Node
from .queue import Queue
from .stack import Stack


class DuplicateKeyError(ValueError):
    """Raised when inserting a key that already exists in the tree."""


class BinarySearchTree:
    ORDER = 2

    def __init__(self) -> None:
        self.root: Optional[Node] = None
        self._weight = 0

    # ------------------------------------------------------------------ #
    # Basic operations
    # ------------------------------------------------------------------ #
    def insert(self, key: float, data: Any) -> Node:
        """Insert a new node. Smaller keys go left, larger keys go right."""
        new_node = Node(key, data)
        if self.root is None:
            self.root = new_node
        else:
            self._insert_recursive(new_node, self.root)
        self._weight += 1
        return new_node

    def _insert_recursive(self, new_node: Node, current: Node) -> None:
        if new_node.key == current.key:
            raise DuplicateKeyError(f"Key {new_node.key} already exists")
        if new_node.key < current.key:
            if current.left is None:
                current.left = new_node
            else:
                self._insert_recursive(new_node, current.left)
        else:
            if current.right is None:
                current.right = new_node
            else:
                self._insert_recursive(new_node, current.right)

    def search(self, key: float) -> Optional[Node]:
        """Classic iterative search: O(h)."""
        current = self.root
        while current is not None:
            if key == current.key:
                return current
            current = current.left if key < current.key else current.right
        return None

    def search_path(self, key: float) -> Tuple[List[float], bool]:
        """Return every key visited while searching and whether it was found."""
        path: List[float] = []
        current = self.root
        while current is not None:
            path.append(current.key)
            if key == current.key:
                return path, True
            current = current.left if key < current.key else current.right
        return path, False

    def contains(self, key: float) -> bool:
        return self.search(key) is not None

    def update(self, key: float, data: Any) -> bool:
        """Replace the data stored under an existing key."""
        node = self.search(key)
        if node is None:
            return False
        node.data = data
        return True

    def delete(self, key: float) -> Optional[Any]:
        """Remove a node handling the three classic cases.

        1. Leaf node: simply detach it.
        2. Node with one child: the child takes its place.
        3. Node with two children: copy the in-order successor
           (minimum of the right subtree) and delete that successor.
        Returns the removed data or None if the key does not exist.
        """
        node = self.search(key)
        if node is None:
            return None
        removed_data = node.data
        self.root = self._delete_recursive(self.root, key)
        self._weight -= 1
        return removed_data

    def _delete_recursive(self, current: Optional[Node], key: float) -> Optional[Node]:
        if current is None:
            return None
        if key < current.key:
            current.left = self._delete_recursive(current.left, key)
        elif key > current.key:
            current.right = self._delete_recursive(current.right, key)
        else:
            if current.left is None:
                return current.right
            if current.right is None:
                return current.left
            successor = self._min_node(current.right)
            current.key, current.data = successor.key, successor.data
            current.right = self._delete_recursive(current.right, successor.key)
        return current

    def clear(self) -> None:
        self.root = None
        self._weight = 0

    def is_empty(self) -> bool:
        return self.root is None

    # ------------------------------------------------------------------ #
    # Traversals
    # ------------------------------------------------------------------ #
    def in_order(self, descending: bool = False) -> List[Node]:
        """Left - Root - Right (ascending) or Right - Root - Left (descending)."""
        result: List[Node] = []
        self._in_order_recursive(self.root, result, descending)
        return result

    def _in_order_recursive(self, current: Optional[Node], result: List[Node], descending: bool) -> None:
        if current is None:
            return
        first, second = (current.right, current.left) if descending else (current.left, current.right)
        self._in_order_recursive(first, result, descending)
        result.append(current)
        self._in_order_recursive(second, result, descending)

    def pre_order(self) -> List[Node]:
        """Root - Left - Right."""
        result: List[Node] = []
        self._pre_order_recursive(self.root, result)
        return result

    def _pre_order_recursive(self, current: Optional[Node], result: List[Node]) -> None:
        if current is None:
            return
        result.append(current)
        self._pre_order_recursive(current.left, result)
        self._pre_order_recursive(current.right, result)

    def post_order(self) -> List[Node]:
        """Left - Right - Root."""
        result: List[Node] = []
        self._post_order_recursive(self.root, result)
        return result

    def _post_order_recursive(self, current: Optional[Node], result: List[Node]) -> None:
        if current is None:
            return
        self._post_order_recursive(current.left, result)
        self._post_order_recursive(current.right, result)
        result.append(current)

    def level_order(self) -> List[Node]:
        """Breadth-first traversal using a Queue."""
        return [node for level in self.levels() for node in level]

    def levels(self) -> List[List[Node]]:
        """Group the nodes by level (level 1 is the root) using a Queue."""
        grouped: List[List[Node]] = []
        if self.root is None:
            return grouped
        queue = Queue()
        queue.enqueue(self.root)
        while not queue.is_empty():
            level_size = len(queue)
            current_level: List[Node] = []
            for _ in range(level_size):
                node = queue.dequeue()
                current_level.append(node)
                if node.left is not None:
                    queue.enqueue(node.left)
                if node.right is not None:
                    queue.enqueue(node.right)
            grouped.append(current_level)
        return grouped

    # ------------------------------------------------------------------ #
    # Measurements (height, level, weight, order, degree)
    # ------------------------------------------------------------------ #
    def height(self, node: Optional[Node] = None, *, from_root: bool = True) -> int:
        """Edges on the longest path down to a leaf. Empty tree: -1."""
        start = self.root if from_root and node is None else node
        return self._height_recursive(start)

    def _height_recursive(self, current: Optional[Node]) -> int:
        if current is None:
            return -1
        return 1 + max(self._height_recursive(current.left), self._height_recursive(current.right))

    def level_of(self, key: float) -> Optional[int]:
        path, found = self.search_path(key)
        return len(path) if found else None

    @property
    def weight(self) -> int:
        return self._weight

    def subtree_weight(self, node: Optional[Node]) -> int:
        if node is None:
            return 0
        return 1 + self.subtree_weight(node.left) + self.subtree_weight(node.right)

    def leaves(self) -> List[Node]:
        return [node for node in self.in_order() if node.is_leaf()]

    def branches(self) -> List[Node]:
        return [node for node in self.in_order() if node is not self.root and not node.is_leaf()]

    def max_degree(self) -> int:
        return max((node.degree for node in self.in_order()), default=0)

    # ------------------------------------------------------------------ #
    # Family relationships
    # ------------------------------------------------------------------ #
    def parent_of(self, key: float) -> Optional[Node]:
        parent: Optional[Node] = None
        current = self.root
        while current is not None and current.key != key:
            parent = current
            current = current.left if key < current.key else current.right
        return parent if current is not None else None

    def sibling_of(self, key: float) -> Optional[Node]:
        parent = self.parent_of(key)
        if parent is None:
            return None
        if parent.left is not None and parent.left.key == key:
            return parent.right
        return parent.left

    def path_from_root(self, key: float) -> List[Node]:
        nodes: List[Node] = []
        current = self.root
        while current is not None:
            nodes.append(current)
            if key == current.key:
                return nodes
            current = current.left if key < current.key else current.right
        return []

    def lowest_common_ancestor(self, key_a: float, key_b: float) -> Optional[Node]:
        """Deepest node that has both keys in its subtree."""
        if not (self.contains(key_a) and self.contains(key_b)):
            return None
        current = self.root
        while current is not None:
            if key_a < current.key and key_b < current.key:
                current = current.left
            elif key_a > current.key and key_b > current.key:
                current = current.right
            else:
                return current
        return None

    def distance_between(self, key_a: float, key_b: float) -> Optional[int]:
        """Number of edges between two nodes, going through their common ancestor."""
        ancestor = self.lowest_common_ancestor(key_a, key_b)
        if ancestor is None:
            return None
        depth_ancestor = self.level_of(ancestor.key) or 0
        return (self.level_of(key_a) or 0) + (self.level_of(key_b) or 0) - 2 * depth_ancestor

    # ------------------------------------------------------------------ #
    # Ordered queries
    # ------------------------------------------------------------------ #
    def min_node(self) -> Optional[Node]:
        return self._min_node(self.root) if self.root else None

    def max_node(self) -> Optional[Node]:
        current = self.root
        while current is not None and current.right is not None:
            current = current.right
        return current

    @staticmethod
    def _min_node(node: Node) -> Node:
        while node.left is not None:
            node = node.left
        return node

    def range_search(self, low: float, high: float) -> List[Node]:
        """All nodes with low <= key <= high, skipping subtrees out of range."""
        result: List[Node] = []
        self._range_recursive(self.root, low, high, result)
        return result

    def _range_recursive(self, current: Optional[Node], low: float, high: float, result: List[Node]) -> None:
        if current is None:
            return
        if low < current.key:
            self._range_recursive(current.left, low, high, result)
        if low <= current.key <= high:
            result.append(current)
        if current.key < high:
            self._range_recursive(current.right, low, high, result)

    def floor(self, key: float) -> Optional[Node]:
        """Largest key that is <= the given key."""
        best: Optional[Node] = None
        current = self.root
        while current is not None:
            if current.key == key:
                return current
            if current.key < key:
                best = current
                current = current.right
            else:
                current = current.left
        return best

    def ceiling(self, key: float) -> Optional[Node]:
        """Smallest key that is >= the given key."""
        best: Optional[Node] = None
        current = self.root
        while current is not None:
            if current.key == key:
                return current
            if current.key > key:
                best = current
                current = current.left
            else:
                current = current.right
        return best

    def closest(self, key: float) -> Optional[Node]:
        lower, upper = self.floor(key), self.ceiling(key)
        if lower is None:
            return upper
        if upper is None:
            return lower
        return lower if key - lower.key <= upper.key - key else upper

    def kth_smallest(self, k: int) -> Optional[Node]:
        """Iterative in-order walk with an explicit Stack, stopping at the k-th node."""
        if k < 1:
            return None
        stack = Stack()
        current = self.root
        count = 0
        while current is not None or not stack.is_empty():
            while current is not None:
                stack.push(current)
                current = current.left
            current = stack.pop()
            count += 1
            if count == k:
                return current
            current = current.right
        return None

    def filter(self, predicate: Callable[[Node], bool]) -> List[Node]:
        return [node for node in self.in_order() if predicate(node)]

    # ------------------------------------------------------------------ #
    # Balance
    # ------------------------------------------------------------------ #
    def balance_factor(self, node: Optional[Node]) -> int:
        """height(left) - height(right), the same measure used by AVL trees."""
        if node is None:
            return 0
        return self._height_recursive(node.left) - self._height_recursive(node.right)

    def is_balanced(self) -> bool:
        return self._check_balanced(self.root) != -2

    def _check_balanced(self, current: Optional[Node]) -> int:
        """Return the height of the subtree, or -2 when it is not balanced."""
        if current is None:
            return -1
        left = self._check_balanced(current.left)
        right = self._check_balanced(current.right)
        if left == -2 or right == -2 or abs(left - right) > 1:
            return -2
        return 1 + max(left, right)

    def rebalance(self) -> None:
        """Rebuild the tree with minimum height from its sorted nodes."""
        ordered = [(node.key, node.data) for node in self.in_order()]
        self.root = self._build_balanced(ordered, 0, len(ordered) - 1)

    def _build_balanced(self, items: List[Tuple[float, Any]], start: int, end: int) -> Optional[Node]:
        if start > end:
            return None
        middle = (start + end) // 2
        node = Node(*items[middle])
        node.left = self._build_balanced(items, start, middle - 1)
        node.right = self._build_balanced(items, middle + 1, end)
        return node

    def is_valid(self) -> bool:
        """Check that every node respects the BST ordering rule."""
        keys = [node.key for node in self.in_order()]
        return all(a < b for a, b in zip(keys, keys[1:]))

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #
    def to_nested(self, serializer: Callable[[Node], Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Nested dictionary representation used to draw the tree."""
        return self._to_nested_recursive(self.root, serializer)

    def _to_nested_recursive(self, current: Optional[Node], serializer: Callable[[Node], Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if current is None:
            return None
        payload = serializer(current)
        payload["left"] = self._to_nested_recursive(current.left, serializer)
        payload["right"] = self._to_nested_recursive(current.right, serializer)
        return payload
