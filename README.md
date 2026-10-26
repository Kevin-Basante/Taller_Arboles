# Meteorite Vault · Binary Search Tree Explorer

Data Structures workshop: **Trees**. A catalog of real meteorites stored in a
**Binary Search Tree (BST)** ordered by mass, with a Python (Flask) backend and
an HTML/CSS/JavaScript frontend that draws the tree live.

## Case study

Museums and research institutes keep collections of meteorites. Curators often
ask questions such as *"which specimens weigh between 5 kg and 800 kg?"*,
*"what is the closest specimen to 100 kg?"* or *"which is the 3rd heaviest?"*.
Using the mass as the key of a BST answers all of them by walking only the
relevant branches instead of scanning the whole collection.

The seed collection includes 19 famous meteorites, among them the Colombian
**Santa Rosa de Viterbo** (1810) and **Cali** (2007). Masses are approximate
public figures used for academic purposes.

## Tree concepts applied

| Concept (class slides) | Where it appears |
| --- | --- |
| Root, parent, child, sibling | Node inspector (Node tab) |
| Leaf and branch nodes | Stats bar and node role tag |
| Height | Edges on the longest path from the root to a leaf |
| Level | Root is level 1, shown for every node and in "Show levels" |
| Weight | Number of nodes in the tree |
| Order | 2 (binary tree) |
| Degree | Children of each node (0, 1 or 2) |
| Balance (AVL idea) | Balance factor per node, "Balanced" indicator and Rebalance |

## Operations

**Catalog:** insert, edit (if the mass changes, the node is moved), delete
(leaf / one child / two children with in-order successor), undo, reset.

**Explore:**
- Search by mass with the visited path highlighted and the number of comparisons, O(h)
- Search by name (full traversal, O(n), because the name is not the key)
- Range query (only visits branches that can contain results)
- Floor, ceiling and closest mass
- k-th lightest / k-th heaviest (iterative in-order with a Stack)
- Lowest common ancestor and distance between two nodes
- Minimum and maximum

**Traverse (animated):** in-order, reverse in-order, pre-order, post-order,
level-order (Queue) and nodes grouped by level.

**Tree maintenance:** validity check, balance check, rebalance into a minimum
height tree.

## Other data structures used

- `Stack` (linked nodes): undo history and the iterative in-order walk.
- `Queue` (linked nodes): level-order (breadth-first) traversal.

The undo history stores the **pre-order** sequence of the tree: inserting it
again rebuilds exactly the same shape.

## Project structure

```
meteorite-tree/
├── app.py                         # Flask routes (HTML page + JSON API)
├── data/meteorites.json           # Seed collection
├── meteor_tree/
│   ├── structures/
│   │   ├── node.py                # Node(key, data, left, right)
│   │   ├── binary_search_tree.py  # BinarySearchTree with all operations
│   │   ├── stack.py               # Stack (LIFO)
│   │   └── queue.py               # Queue (FIFO)
│   ├── models/meteorite.py        # Meteorite entity and validation
│   └── services/meteorite_catalog.py  # Applies the BST to the case study
├── templates/index.html           # Frontend page
├── static/css/styles.css
├── static/js/app.js               # SVG tree drawing and API calls
└── tests/test_tree.py             # Unit tests
```

## How to run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in the browser.

Run the tests:

```bash
python -m unittest discover -s tests -t .
```

## API

| Method | Route | Description |
| --- | --- | --- |
| GET | `/api/state` | Tree, statistics and history |
| POST | `/api/meteorites` | Insert a meteorite |
| PUT | `/api/meteorites/<mass>` | Edit a meteorite |
| DELETE | `/api/meteorites/<mass>` | Delete a meteorite |
| GET | `/api/meteorites/<mass>` | Node details (role, level, degree, family) |
| GET | `/api/search?mass=` | Search by key with path |
| GET | `/api/search/name?q=` | Search by name |
| GET | `/api/traversal/<kind>` | `in-order`, `reverse-in-order`, `pre-order`, `post-order`, `level-order` |
| GET | `/api/levels` | Nodes grouped by level |
| GET | `/api/range?min=&max=` | Range query |
| GET | `/api/closest?mass=` | Floor, ceiling and closest |
| GET | `/api/rank?k=&order=` | k-th lightest or heaviest |
| GET | `/api/ancestor?a=&b=` | Lowest common ancestor |
| POST | `/api/rebalance` | Rebuild a balanced tree |
| POST | `/api/undo` | Undo the last change |
| POST | `/api/reset` | Restore the seed collection |
