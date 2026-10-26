"""Flask entry point: serves the HTML frontend and a JSON API over the tree."""

from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, jsonify, render_template, request

from meteor_tree.models import GROUPS, RECOVERY_TYPES
from meteor_tree.services import CatalogError, MeteoriteCatalog

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
catalog = MeteoriteCatalog(seed_file=BASE_DIR / "data" / "meteorites.json")


def api_route(handler: Callable[..., Any]) -> Callable[..., Any]:
    """Turn business errors into clean JSON responses."""

    @wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return handler(*args, **kwargs)
        except (CatalogError, ValueError) as error:
            return jsonify({"error": str(error)}), 400

    return wrapper


def number_arg(name: str) -> float:
    raw = request.args.get(name, "")
    try:
        return float(raw)
    except ValueError:
        raise CatalogError(f"'{name}' must be a number") from None


def with_state(**payload: Any) -> Any:
    payload["state"] = catalog.state()
    return jsonify(payload)


@app.get("/")
def index() -> str:
    return render_template("index.html", groups=GROUPS, recovery_types=RECOVERY_TYPES)


@app.get("/api/state")
def get_state() -> Any:
    return jsonify(catalog.state())


@app.post("/api/meteorites")
@api_route
def add_meteorite() -> Any:
    meteorite = catalog.add(request.get_json(force=True))
    return with_state(message=f"{meteorite.name} added to the tree", key=meteorite.key)


@app.put("/api/meteorites/<key>")
@api_route
def edit_meteorite(key: str) -> Any:
    meteorite = catalog.edit(float(key), request.get_json(force=True))
    return with_state(message=f"{meteorite.name} updated", key=meteorite.key)


@app.delete("/api/meteorites/<key>")
@api_route
def remove_meteorite(key: str) -> Any:
    meteorite = catalog.remove(float(key))
    return with_state(message=f"{meteorite.name} removed from the tree")


@app.get("/api/meteorites/<key>")
@api_route
def describe_meteorite(key: str) -> Any:
    return jsonify(catalog.describe(float(key)))


@app.get("/api/search")
@api_route
def search() -> Any:
    return jsonify(catalog.search(number_arg("mass")))


@app.get("/api/search/name")
@api_route
def search_by_name() -> Any:
    return jsonify(catalog.search_by_name(request.args.get("q", "")))


@app.get("/api/traversal/<kind>")
@api_route
def traversal(kind: str) -> Any:
    return jsonify(catalog.traversal(kind))


@app.get("/api/levels")
def levels() -> Any:
    return jsonify(catalog.levels())


@app.get("/api/range")
@api_route
def mass_range() -> Any:
    return jsonify(catalog.mass_range(number_arg("min"), number_arg("max")))


@app.get("/api/closest")
@api_route
def closest() -> Any:
    return jsonify(catalog.closest(number_arg("mass")))


@app.get("/api/rank")
@api_route
def rank() -> Any:
    k = int(number_arg("k"))
    heaviest = request.args.get("order") == "heaviest"
    result = catalog.kth_heaviest(k) if heaviest else catalog.kth_lightest(k)
    if result is None:
        raise CatalogError(f"Position {k} is out of range")
    return jsonify(result)


@app.get("/api/ancestor")
@api_route
def common_ancestor() -> Any:
    return jsonify(catalog.common_ancestor(number_arg("a"), number_arg("b")))


@app.post("/api/rebalance")
@api_route
def rebalance() -> Any:
    heights = catalog.rebalance()
    return with_state(
        message=f"Tree rebalanced: height {heights['height_before']} -> {heights['height_after']}"
    )


@app.post("/api/undo")
@api_route
def undo() -> Any:
    action = catalog.undo()
    return with_state(message=f"Undone: {action}")


@app.post("/api/reset")
def reset() -> Any:
    catalog.reset()
    return with_state(message="Catalog restored to the original collection")


if __name__ == "__main__":
    app.run(debug=True)
