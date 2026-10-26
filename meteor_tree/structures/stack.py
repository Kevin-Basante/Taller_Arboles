"""Stack (LIFO) implemented with linked nodes."""

from typing import Any, Iterator, Optional


class _StackNode:
    def __init__(self, value: Any, next_node: Optional["_StackNode"] = None) -> None:
        self.value = value
        self.next = next_node


class Stack:
    """Last In, First Out structure.

    Used by the tree for the iterative in-order walk (k-th smallest) and by
    the catalog to keep the undo history.
    """

    def __init__(self, max_size: Optional[int] = None) -> None:
        self.top: Optional[_StackNode] = None
        self.length = 0
        self.max_size = max_size

    def push(self, value: Any) -> None:
        self.top = _StackNode(value, self.top)
        self.length += 1
        if self.max_size is not None and self.length > self.max_size:
            self._drop_bottom()

    def pop(self) -> Any:
        if self.top is None:
            raise IndexError("pop from an empty stack")
        value = self.top.value
        self.top = self.top.next
        self.length -= 1
        return value

    def peek(self) -> Any:
        if self.top is None:
            raise IndexError("peek from an empty stack")
        return self.top.value

    def is_empty(self) -> bool:
        return self.top is None

    def clear(self) -> None:
        self.top = None
        self.length = 0

    def _drop_bottom(self) -> None:
        """Remove the oldest element so the stack never exceeds max_size."""
        current = self.top
        while current is not None and current.next is not None and current.next.next is not None:
            current = current.next
        if current is not None:
            current.next = None
            self.length -= 1

    def __len__(self) -> int:
        return self.length

    def __iter__(self) -> Iterator[Any]:
        current = self.top
        while current is not None:
            yield current.value
            current = current.next
