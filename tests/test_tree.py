"""Unit tests for the tree, the auxiliary structures and the catalog service."""

import unittest
from pathlib import Path

from meteor_tree.services import CatalogError, MeteoriteCatalog
from meteor_tree.structures import BinarySearchTree, DuplicateKeyError, Queue, Stack

SEED = Path(__file__).resolve().parent.parent / "data" / "meteorites.json"


def build_tree(keys):
    tree = BinarySearchTree()
    for key in keys:
        tree.insert(key, f"item-{key}")
    return tree


class StackAndQueueTest(unittest.TestCase):
    def test_stack_is_lifo(self):
        stack = Stack()
        for value in (1, 2, 3):
            stack.push(value)
        self.assertEqual([stack.pop(), stack.pop(), stack.pop()], [3, 2, 1])
        self.assertTrue(stack.is_empty())

    def test_stack_drops_oldest_when_full(self):
        stack = Stack(max_size=2)
        for value in (1, 2, 3):
            stack.push(value)
        self.assertEqual(list(stack), [3, 2])

    def test_queue_is_fifo(self):
        queue = Queue()
        for value in (1, 2, 3):
            queue.enqueue(value)
        self.assertEqual([queue.dequeue(), queue.dequeue(), queue.dequeue()], [1, 2, 3])
        self.assertTrue(queue.is_empty())


class BinarySearchTreeTest(unittest.TestCase):
    def setUp(self):
        #            50
        #        30       70
        #      20  40   60  80
        self.tree = build_tree([50, 30, 70, 20, 40, 60, 80])

    def keys(self, nodes):
        return [node.key for node in nodes]

    def test_traversals(self):
        self.assertEqual(self.keys(self.tree.in_order()), [20, 30, 40, 50, 60, 70, 80])
        self.assertEqual(self.keys(self.tree.pre_order()), [50, 30, 20, 40, 70, 60, 80])
        self.assertEqual(self.keys(self.tree.post_order()), [20, 40, 30, 60, 80, 70, 50])
        self.assertEqual(self.keys(self.tree.level_order()), [50, 30, 70, 20, 40, 60, 80])
        self.assertEqual(self.keys(self.tree.in_order(descending=True)), [80, 70, 60, 50, 40, 30, 20])

    def test_measurements(self):
        self.assertEqual(self.tree.weight, 7)
        self.assertEqual(self.tree.height(), 2)
        self.assertEqual(self.tree.level_of(50), 1)
        self.assertEqual(self.tree.level_of(60), 3)
        self.assertEqual(len(self.tree.leaves()), 4)
        self.assertEqual(len(self.tree.branches()), 2)
        self.assertTrue(self.tree.is_balanced())

    def test_duplicate_is_rejected(self):
        with self.assertRaises(DuplicateKeyError):
            self.tree.insert(40, "again")

    def test_delete_three_cases(self):
        self.tree.delete(20)  # leaf
        self.tree.insert(65, "x")
        self.tree.delete(60)  # one child
        self.tree.delete(50)  # two children, root
        self.assertEqual(self.keys(self.tree.in_order()), [30, 40, 65, 70, 80])
        self.assertEqual(self.tree.root.key, 65)
        self.assertEqual(self.tree.weight, 5)
        self.assertTrue(self.tree.is_valid())
        self.assertIsNone(self.tree.delete(999))

    def test_family(self):
        self.assertEqual(self.tree.parent_of(40).key, 30)
        self.assertEqual(self.tree.sibling_of(40).key, 20)
        self.assertIsNone(self.tree.parent_of(50))
        self.assertEqual(self.tree.lowest_common_ancestor(20, 40).key, 30)
        self.assertEqual(self.tree.lowest_common_ancestor(20, 80).key, 50)
        self.assertEqual(self.tree.distance_between(20, 80), 4)

    def test_ordered_queries(self):
        self.assertEqual(self.keys(self.tree.range_search(35, 65)), [40, 50, 60])
        self.assertEqual(self.tree.floor(55).key, 50)
        self.assertEqual(self.tree.ceiling(55).key, 60)
        self.assertEqual(self.tree.closest(57).key, 60)
        self.assertIsNone(self.tree.floor(1))
        self.assertEqual(self.tree.kth_smallest(3).key, 40)
        self.assertIsNone(self.tree.kth_smallest(8))
        self.assertEqual(self.tree.min_node().key, 20)
        self.assertEqual(self.tree.max_node().key, 80)

    def test_search_path(self):
        self.assertEqual(self.tree.search_path(60), ([50, 70, 60], True))
        self.assertEqual(self.tree.search_path(65), ([50, 70, 60], False))

    def test_rebalance_degenerate_tree(self):
        chain = build_tree(range(1, 16))
        self.assertEqual(chain.height(), 14)
        chain.rebalance()
        self.assertEqual(chain.height(), 3)
        self.assertTrue(chain.is_balanced())
        self.assertEqual(self.keys(chain.in_order()), list(range(1, 16)))


class MeteoriteCatalogTest(unittest.TestCase):
    def setUp(self):
        self.catalog = MeteoriteCatalog(seed_file=SEED)
        self.sample = {
            "name": "Test Rock", "mass_kg": 42, "country": "Colombia", "year": 2020,
            "group": "Stony", "classification": "L6", "recovery": "Fell",
        }

    def test_add_and_undo(self):
        before = self.catalog.tree.weight
        self.catalog.add(self.sample)
        self.assertEqual(self.catalog.tree.weight, before + 1)
        self.catalog.undo()
        self.assertEqual(self.catalog.tree.weight, before)
        self.assertFalse(self.catalog.tree.contains(42))

    def test_undo_restores_exact_shape(self):
        shape = [node.key for node in self.catalog.tree.pre_order()]
        self.catalog.rebalance()
        self.catalog.undo()
        self.assertEqual([node.key for node in self.catalog.tree.pre_order()], shape)

    def test_duplicate_mass_and_name(self):
        with self.assertRaises(CatalogError):
            self.catalog.add({**self.sample, "mass_kg": 2000})
        with self.assertRaises(CatalogError):
            self.catalog.add({**self.sample, "name": "allende"})

    def test_edit_with_new_mass_moves_node(self):
        record = self.catalog.describe(0.478)["meteorite"]
        self.catalog.edit(0.478, {**record, "mass_kg": 99999})
        self.assertFalse(self.catalog.tree.contains(0.478))
        self.assertEqual(self.catalog.tree.max_node().data.name, "Cali")

    def test_describe_root(self):
        info = self.catalog.describe(2000)
        self.assertEqual(info["role"], "Root")
        self.assertEqual(info["level"], 1)

    def test_invalid_payload(self):
        with self.assertRaises(ValueError):
            self.catalog.add({**self.sample, "mass_kg": -3})
        with self.assertRaises(ValueError):
            self.catalog.add({**self.sample, "group": "Plastic"})


if __name__ == "__main__":
    unittest.main()
