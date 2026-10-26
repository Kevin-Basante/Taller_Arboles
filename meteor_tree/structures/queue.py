"""Queue (FIFO) implemented with linked nodes."""

from typing import Any, Optional


class _QueueNode:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.next: Optional["_QueueNode"] = None


class Queue:
    """First In, First Out structure.

    Used by the tree for the level-order (breadth-first) traversal.
    """

    def __init__(self) -> None:
        self.first: Optional[_QueueNode] = None
        self.last: Optional[_QueueNode] = None
        self.length = 0

    def enqueue(self, value: Any) -> None:
        new_node = _QueueNode(value)
        if self.last is None:
            self.first = new_node
        else:
            self.last.next = new_node
        self.last = new_node
        self.length += 1

    def dequeue(self) -> Any:
        if self.first is None:
            raise IndexError("dequeue from an empty queue")
        value = self.first.value
        self.first = self.first.next
        if self.first is None:
            self.last = None
        self.length -= 1
        return value

    def peek(self) -> Any:
        if self.first is None:
            raise IndexError("peek from an empty queue")
        return self.first.value

    def is_empty(self) -> bool:
        return self.first is None

    def __len__(self) -> int:
        return self.length
