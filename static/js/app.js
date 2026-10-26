/* Meteorite Vault frontend: draws the BST and talks to the Flask API. */

const SVG_NS = "http://www.w3.org/2000/svg";

const GROUP_COLORS = {
  "Iron": "#9fb3c8",
  "Stony": "#e0a96d",
  "Stony-iron": "#6fd6c0",
  "Martian": "#ff6b5b",
  "Lunar": "#c9b8ff",
};

function formatMass(kg) {
  if (kg >= 1000) return `${+(kg / 1000).toFixed(2)} t`;
  if (kg >= 1) return `${+kg.toFixed(2)} kg`;
  return `${+(kg * 1000).toFixed(0)} g`;
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ------------------------------------------------------------------ */
/* API client                                                          */
/* ------------------------------------------------------------------ */
class ApiClient {
  async request(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unexpected error");
    return data;
  }

  get(path, params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(query ? `${path}?${query}` : path);
  }

  post(path, body) { return this.request(path, { method: "POST", body: body || {} }); }
  put(path, body) { return this.request(path, { method: "PUT", body }); }
  delete(path) { return this.request(path, { method: "DELETE" }); }
}

/* ------------------------------------------------------------------ */
/* Tree renderer (SVG)                                                 */
/* ------------------------------------------------------------------ */
class TreeRenderer {
  constructor(svg, container, onSelect) {
    this.svg = svg;
    this.container = container;
    this.onSelect = onSelect;
    this.nodes = new Map();   // key -> <g>
    this.edges = new Map();   // child key -> <path>
    this.parents = new Map(); // child key -> parent key
    this.scale = 1;
    this.size = { width: 0, height: 0 };
    this.spacingX = 88;
    this.spacingY = 100;
    this.padding = 60;
    this.enablePanning();
  }

  /* In-order index gives the x position, depth gives the y position. */
  layout(root) {
    const positioned = [];
    let index = 0;
    let maxDepth = 0;
    const walk = (node, depth, parent) => {
      if (!node) return;
      walk(node.left, depth + 1, node);
      positioned.push({ node, depth, parent, x: index++ });
      maxDepth = Math.max(maxDepth, depth);
      walk(node.right, depth + 1, node);
    };
    walk(root, 0, null);
    return { positioned, count: index, maxDepth };
  }

  render(root, newKey = null) {
    this.svg.innerHTML = "";
    this.nodes.clear();
    this.edges.clear();
    this.parents.clear();
    if (!root) {
      this.size = { width: 0, height: 0 };
      return;
    }
    const { positioned, count, maxDepth } = this.layout(root);
    const point = (item) => ({
      x: this.padding + item.x * this.spacingX,
      y: this.padding + item.depth * this.spacingY,
    });
    const byKey = new Map(positioned.map((item) => [item.node.key, point(item)]));
    this.size = {
      width: this.padding * 2 + Math.max(0, count - 1) * this.spacingX,
      height: this.padding * 2 + maxDepth * this.spacingY + 20,
    };
    this.svg.setAttribute("viewBox", `0 0 ${this.size.width} ${this.size.height}`);

    const edgeLayer = this.make("g");
    const nodeLayer = this.make("g");
    this.svg.append(edgeLayer, nodeLayer);

    for (const item of positioned) {
      if (!item.parent) continue;
      const from = byKey.get(item.parent.key);
      const to = byKey.get(item.node.key);
      const midY = (from.y + to.y) / 2;
      const path = this.make("path", {
        class: "edge",
        d: `M${from.x},${from.y} C${from.x},${midY} ${to.x},${midY} ${to.x},${to.y}`,
      });
      edgeLayer.append(path);
      this.edges.set(item.node.key, path);
      this.parents.set(item.node.key, item.parent.key);

      const label = this.make("text", {
        class: "edge-label",
        x: (from.x + to.x) / 2 + (to.x < from.x ? -10 : 6),
        y: midY - 4,
      });
      label.textContent = to.x < from.x ? "<" : ">";
      edgeLayer.append(label);
    }

    for (const item of positioned) {
      const { x, y } = byKey.get(item.node.key);
      const meteorite = item.node;
      const color = GROUP_COLORS[meteorite.group] || "#ccc";
      const group = this.make("g", { class: "node", transform: `translate(${x},${y})`, tabindex: 0 });
      if (newKey !== null && meteorite.key === newKey) group.classList.add("is-new");
      const radius = item.depth === 0 ? 30 : 26;
      group.append(
        this.make("circle", { class: "halo", r: radius + 7 }),
        this.make("circle", { class: "body", r: radius, fill: color, stroke: "rgba(255,255,255,.18)" }),
      );
      const mass = this.make("text", { class: "mass", y: 4 });
      mass.textContent = formatMass(meteorite.key);
      const shortName = meteorite.name.length > 13 ? `${meteorite.name.slice(0, 12)}…` : meteorite.name;
      const nameWidth = shortName.length * 7.6 + 16;
      const nameBg = this.make("rect", {
        class: "name-bg", x: -nameWidth / 2, y: radius + 6, width: nameWidth, height: 20, rx: 10,
      });
      const name = this.make("text", { class: "name", y: radius + 20.5 });
      name.textContent = shortName;
      const title = this.make("title");
      title.textContent = `${meteorite.name} · ${formatMass(meteorite.key)} · ${meteorite.group}`;
      group.append(mass, nameBg, name, title);
      group.addEventListener("click", () => this.onSelect(meteorite.key, true));
      group.addEventListener("keydown", (event) => { if (event.key === "Enter") this.onSelect(meteorite.key, true); });
      nodeLayer.append(group);
      this.nodes.set(meteorite.key, group);
    }
    this.applyScale();
  }

  make(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
    return element;
  }

  /* ---------- Highlighting ---------- */
  clear() {
    this.svg.querySelectorAll(".order-badge").forEach((badge) => badge.remove());
    for (const node of this.nodes.values()) node.classList.remove("is-path", "is-visit", "is-result", "is-dim");
    for (const edge of this.edges.values()) edge.classList.remove("is-path");
  }

  select(key) {
    for (const [nodeKey, node] of this.nodes) node.classList.toggle("is-selected", nodeKey === key);
  }

  markPath(keys) {
    keys.forEach((key, index) => {
      this.nodes.get(key)?.classList.add("is-path");
      if (index > 0) this.edges.get(key)?.classList.add("is-path");
    });
  }

  markResults(keys, dimOthers = true) {
    const wanted = new Set(keys);
    for (const [key, node] of this.nodes) {
      if (wanted.has(key)) node.classList.add("is-result");
      else if (dimOthers) node.classList.add("is-dim");
    }
  }

  visit(key, order) {
    const node = this.nodes.get(key);
    if (!node) return;
    node.classList.add("is-visit");
    const badge = this.make("g", { class: "order-badge", transform: "translate(20,-22)" });
    const circle = this.make("circle", { r: 10 });
    const text = this.make("text", { y: 3.5 });
    text.textContent = order;
    badge.append(circle, text);
    node.append(badge);
  }

  /* ---------- Zoom & pan ---------- */
  applyScale() {
    this.svg.style.width = `${Math.max(this.size.width * this.scale, 10)}px`;
    this.svg.style.height = `${Math.max(this.size.height * this.scale, 10)}px`;
  }

  zoom(factor) {
    this.scale = Math.min(2.2, Math.max(0.35, this.scale * factor));
    this.applyScale();
  }

  fit() {
    if (!this.size.width) return;
    const box = this.container.getBoundingClientRect();
    this.scale = Math.min(1.15, (box.width - 8) / this.size.width, (box.height - 8) / this.size.height);
    this.scale = Math.max(this.scale, 0.5);
    this.applyScale();
  }

  enablePanning() {
    let start = null;
    this.container.addEventListener("pointerdown", (event) => {
      if (event.target.closest(".node")) return;
      start = { x: event.clientX, y: event.clientY, left: this.container.scrollLeft, top: this.container.scrollTop };
      this.container.classList.add("dragging");
    });
    window.addEventListener("pointermove", (event) => {
      if (!start) return;
      this.container.scrollLeft = start.left - (event.clientX - start.x);
      this.container.scrollTop = start.top - (event.clientY - start.y);
    });
    window.addEventListener("pointerup", () => {
      start = null;
      this.container.classList.remove("dragging");
    });
  }
}

/* ------------------------------------------------------------------ */
/* Output strip under the canvas                                       */
/* ------------------------------------------------------------------ */
class OutputPanel {
  constructor(onChipClick) {
    this.title = document.getElementById("output-title");
    this.meta = document.getElementById("output-meta");
    this.chips = document.getElementById("output-chips");
    this.onChipClick = onChipClick;
  }

  show(title, meta = "", items = []) {
    this.title.textContent = title;
    this.meta.textContent = meta;
    this.chips.innerHTML = "";
    items.forEach((item, index) => this.addChip(item, index + 1));
  }

  addChip(meteorite, order = null) {
    const chip = document.createElement("button");
    chip.className = "chip";
    chip.innerHTML = `${order !== null ? `<b>${order}</b>` : ""}${escapeHtml(meteorite.name)} <span class="output-meta">${formatMass(meteorite.key)}</span>`;
    chip.addEventListener("click", () => this.onChipClick(meteorite.key));
    this.chips.append(chip);
  }

  addLevel(level) {
    const tag = document.createElement("span");
    tag.className = "chip level";
    tag.textContent = `Level ${level}`;
    this.chips.append(tag);
  }
}

/* ------------------------------------------------------------------ */
/* Node inspector                                                      */
/* ------------------------------------------------------------------ */
class Inspector {
  constructor(app) {
    this.app = app;
    this.empty = document.getElementById("inspector-empty");
    this.body = document.getElementById("inspector-body");
  }

  hide() {
    this.empty.classList.remove("hidden");
    this.body.classList.add("hidden");
  }

  show(info) {
    const m = info.meteorite;
    const link = (item) => item
      ? `<span class="link" data-key="${item.key}">${escapeHtml(item.name)}</span>`
      : "—";
    const children = info.children.length ? info.children.map(link).join(", ") : "none";
    this.body.innerHTML = `
      <div class="insp-head">
        <div class="insp-dot" style="background:${GROUP_COLORS[m.group]}"></div>
        <div>
          <h2>${escapeHtml(m.name)}</h2>
          <p>${escapeHtml(m.country)} · ${m.year} · ${m.recovery}</p>
        </div>
      </div>
      <span class="role-tag role-${info.role}">${info.role} node</span>
      <div class="facts">
        <div class="fact"><small>Key (mass)</small><span>${formatMass(m.mass_kg)}</span></div>
        <div class="fact"><small>Group</small><span>${m.group}</span></div>
        <div class="fact wide"><small>Classification</small><span>${escapeHtml(m.classification || "—")}</span></div>
        <div class="fact"><small>Level</small><span>${info.level}</span></div>
        <div class="fact"><small>Degree</small><span>${info.degree}</span></div>
        <div class="fact"><small>Subtree height</small><span>${info.subtree_height}</span></div>
        <div class="fact"><small>Subtree weight</small><span>${info.subtree_weight}</span></div>
        <div class="fact"><small>Parent</small><span>${link(info.parent)}</span></div>
        <div class="fact"><small>Sibling</small><span>${link(info.sibling)}</span></div>
        <div class="fact wide"><small>Children</small><span>${children}</span></div>
        <div class="fact wide"><small>Balance factor</small><span>${info.balance_factor > 0 ? "+" : ""}${info.balance_factor}
          ${Math.abs(info.balance_factor) > 1 ? " · unbalanced" : " · balanced"}</span></div>
      </div>
      <div class="insp-actions">
        <button class="btn ghost small" id="edit-node-btn">Edit</button>
        <button class="btn danger small" id="delete-node-btn">Delete</button>
      </div>`;
    this.body.querySelectorAll(".link").forEach((element) =>
      element.addEventListener("click", () => this.app.selectNode(Number(element.dataset.key), true, true)));
    this.body.querySelector("#edit-node-btn").addEventListener("click", () => this.app.startEdit(m));
    this.body.querySelector("#delete-node-btn").addEventListener("click", () => this.app.deleteNode(m, info.degree));
    this.empty.classList.add("hidden");
    this.body.classList.remove("hidden");
  }
}

/* ------------------------------------------------------------------ */
/* Application controller                                              */
/* ------------------------------------------------------------------ */
class MeteoriteVaultApp {
  constructor() {
    this.api = new ApiClient();
    this.renderer = new TreeRenderer(
      document.getElementById("tree-svg"),
      document.getElementById("canvas"),
      (key) => this.selectNode(key, true, true),
    );
    this.output = new OutputPanel((key) => this.selectNode(key, true, true));
    this.inspector = new Inspector(this);
    this.form = document.getElementById("meteorite-form");
    this.state = null;
    this.selectedKey = null;
    this.editingKey = null;
    this.animationToken = 0;
    this.bindEvents();
    this.renderLegend();
  }

  async start() {
    this.applyState(await this.api.get("/api/state"));
    requestAnimationFrame(() => this.renderer.fit());
  }

  /* ---------- State ---------- */
  applyState(state, newKey = null) {
    this.state = state;
    this.renderer.render(state.tree, newKey);
    document.getElementById("empty-state").classList.toggle("hidden", Boolean(state.tree));
    document.getElementById("undo-btn").disabled = !state.can_undo;
    this.renderStats(state.stats);
    this.renderHistory(state.history);
    this.fillSelects();
    if (this.selectedKey !== null && this.renderer.nodes.has(this.selectedKey)) {
      this.selectNode(this.selectedKey, false);
    } else {
      this.selectedKey = null;
      this.inspector.hide();
    }
  }

  allMeteorites() {
    const result = [];
    const walk = (node) => {
      if (!node) return;
      walk(node.left);
      result.push(node);
      walk(node.right);
    };
    walk(this.state?.tree);
    return result;
  }

  renderStats(stats) {
    const cards = [
      ["Weight", stats.weight, "Number of nodes in the tree"],
      ["Height", Math.max(stats.height, 0), "Edges on the longest path from the root to a leaf"],
      ["Levels", stats.levels, "Root is level 1"],
      ["Order", stats.order, "Maximum children per node (binary tree)"],
      ["Leaves", stats.leaves, "Nodes without children"],
      ["Branches", stats.branches, "Non-root nodes with at least one child"],
      ["Balanced", stats.weight ? (stats.is_balanced ? "Yes" : "No") : "—", "Every node has |balance factor| ≤ 1", stats.is_balanced ? "good" : "bad"],
      ["Root", stats.root ? stats.root.name : "—", "First node of the tree", "small"],
      ["Lightest", stats.lightest ? formatMass(stats.lightest.key) : "—", stats.lightest ? `Minimum: ${stats.lightest.name}` : "", "small"],
      ["Heaviest", stats.heaviest ? formatMass(stats.heaviest.key) : "—", stats.heaviest ? `Maximum: ${stats.heaviest.name}` : "", "small"],
    ];
    document.getElementById("stats").innerHTML = cards.map(([label, value, help, modifier = ""]) =>
      `<div class="stat" title="${escapeHtml(help)}"><div class="label">${label}</div><div class="value ${modifier}">${escapeHtml(value)}</div></div>`
    ).join("");
  }

  renderHistory(history) {
    const list = document.getElementById("history-list");
    list.innerHTML = history.length
      ? history.map((action) => `<li>${escapeHtml(action)}</li>`).join("")
      : `<li>No changes yet</li>`;
  }

  renderLegend() {
    document.getElementById("legend").innerHTML = Object.entries(GROUP_COLORS)
      .map(([group, color]) => `<span><i style="background:${color}"></i>${group}</span>`).join("");
  }

  fillSelects() {
    const options = this.allMeteorites()
      .map((m) => `<option value="${m.key}">${escapeHtml(m.name)} · ${formatMass(m.key)}</option>`).join("");
    document.querySelectorAll(".meteorite-select").forEach((select, index) => {
      const previous = select.value;
      select.innerHTML = options;
      if (previous && select.querySelector(`option[value="${previous}"]`)) select.value = previous;
      else if (select.options.length > index) select.selectedIndex = index * Math.floor(select.options.length / 2);
    });
  }

  /* ---------- Selection ---------- */
  async selectNode(key, highlight = true, openInspector = false) {
    try {
      const info = await this.api.get(`/api/meteorites/${key}`);
      this.selectedKey = key;
      this.renderer.select(key);
      this.inspector.show(info);
      if (openInspector) this.openTab("node");
      if (highlight) {
        this.stopAnimation();
        this.renderer.clear();
        this.renderer.markPath(info.path);
        this.output.show(
          `Path to ${info.meteorite.name}`,
          `${info.path.length} node(s) from the root · level ${info.level}`,
          info.path.map((pathKey) => this.findByKey(pathKey)).filter(Boolean),
        );
      }
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  findByKey(key) {
    return this.allMeteorites().find((m) => m.key === key);
  }

  /* ---------- CRUD ---------- */
  formPayload() {
    const data = Object.fromEntries(new FormData(this.form).entries());
    data.mass_kg = Number(data.mass_kg);
    data.year = Number(data.year);
    return data;
  }

  async submitForm(event) {
    event.preventDefault();
    const payload = this.formPayload();
    try {
      const result = this.editingKey === null
        ? await this.api.post("/api/meteorites", payload)
        : await this.api.put(`/api/meteorites/${this.editingKey}`, payload);
      this.selectedKey = result.key;
      this.applyState(result.state, result.key);
      this.toast(result.message);
      this.cancelEdit();
      this.selectNode(result.key, true, true);
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  startEdit(meteorite) {
    this.editingKey = meteorite.mass_kg;
    for (const [field, value] of Object.entries(meteorite)) {
      const input = this.form.elements.namedItem(field);
      if (input) input.value = value;
    }
    document.getElementById("form-title").textContent = `Edit ${meteorite.name}`;
    document.getElementById("form-hint").textContent = "Changing the mass moves the node: it is deleted and inserted again in its new position.";
    document.getElementById("submit-btn").textContent = "Save changes";
    document.getElementById("cancel-edit-btn").classList.remove("hidden");
    this.openTab("catalog");
    this.form.elements.namedItem("name").focus();
  }

  cancelEdit() {
    this.editingKey = null;
    this.form.reset();
    document.getElementById("form-title").textContent = "Add a meteorite";
    document.getElementById("form-hint").textContent = "The mass is the key: lighter meteorites go to the left, heavier ones to the right.";
    document.getElementById("submit-btn").textContent = "Insert into tree";
    document.getElementById("cancel-edit-btn").classList.add("hidden");
  }

  async deleteNode(meteorite, degree) {
    const cases = ["it is a leaf, so it is simply detached",
      "it has one child, which takes its place",
      "it has two children, so its in-order successor replaces it"];
    if (!confirm(`Delete ${meteorite.name}?\nCase: ${cases[degree]}.`)) return;
    try {
      const result = await this.api.delete(`/api/meteorites/${meteorite.mass_kg}`);
      this.selectedKey = null;
      this.applyState(result.state);
      this.output.show("Deletion", `${result.message} · ${cases[degree]}`);
      this.toast(result.message);
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  async treeAction(path) {
    try {
      const result = await this.api.post(path);
      this.applyState(result.state);
      this.renderer.clear();
      this.output.show("Tree", result.message);
      this.toast(result.message);
      requestAnimationFrame(() => this.renderer.fit());
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  /* ---------- Queries ---------- */
  async runQuery(handler) {
    this.stopAnimation();
    this.renderer.clear();
    try {
      await handler();
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  async searchMass(mass) {
    const result = await this.api.get("/api/search", { mass });
    const steps = result.path.map((key) => this.findByKey(key));
    await this.animate(result.path, (key, index) => this.renderer.visit(key, index + 1));
    this.renderer.markPath(result.path);
    if (result.found) {
      this.renderer.markResults([result.meteorite.mass_kg], false);
      this.selectNode(result.meteorite.mass_kg, false);
    }
    this.output.show(
      result.found ? `Found ${result.meteorite.name}` : `${formatMass(Number(mass))} is not in the tree`,
      `${result.comparisons} comparison(s) out of ${this.state.stats.weight} nodes`,
      steps,
    );
  }

  async searchName(q) {
    const results = await this.api.get("/api/search/name", { q });
    this.renderer.markResults(results.map((m) => m.key));
    this.output.show(`Name contains "${q}"`, `${results.length} match(es) · full traversal needed because the key is the mass`, results);
  }

  async searchRange(min, max) {
    const results = await this.api.get("/api/range", { min, max });
    this.renderer.markResults(results.map((m) => m.key));
    const total = results.reduce((sum, m) => sum + m.key, 0);
    this.output.show(
      `Between ${formatMass(Math.min(min, max))} and ${formatMass(Math.max(min, max))}`,
      `${results.length} meteorite(s) · combined mass ${formatMass(total)}`,
      results,
    );
  }

  async searchClosest(mass) {
    const result = await this.api.get("/api/closest", { mass });
    const found = [result.floor, result.ceiling].filter(Boolean);
    this.renderer.markResults(found.map((m) => m.key));
    const describe = (label, m) => m ? `${label}: ${m.name} (${formatMass(m.key)})` : `${label}: none`;
    this.output.show(
      result.closest ? `Closest to ${formatMass(Number(mass))}: ${result.closest.name}` : "Tree is empty",
      `${describe("Floor", result.floor)} · ${describe("Ceiling", result.ceiling)}`,
      found,
    );
    if (result.closest) this.selectNode(result.closest.key, false);
  }

  async searchRank(k, order) {
    const result = await this.api.get("/api/rank", { k, order });
    this.renderer.markResults([result.key]);
    this.output.show(`#${k} ${order}: ${result.name}`, `Found with an iterative in-order walk that uses a Stack`, [result]);
    this.selectNode(result.key, false);
  }

  async searchAncestor(a, b) {
    const result = await this.api.get("/api/ancestor", { a, b });
    this.renderer.markPath(result.path_a);
    this.renderer.markPath(result.path_b);
    this.renderer.markResults([result.ancestor.key, Number(a), Number(b)]);
    this.output.show(
      `Common ancestor: ${result.ancestor.name}`,
      `${result.distance} edge(s) between both meteorites`,
      [this.findByKey(Number(a)), result.ancestor, this.findByKey(Number(b))],
    );
  }

  /* ---------- Traversals ---------- */
  async traverse(kind) {
    this.stopAnimation();
    this.renderer.clear();
    try {
      if (kind === "levels") return this.showLevels(await this.api.get("/api/levels"));
      const sequence = await this.api.get(`/api/traversal/${kind}`);
      const label = document.querySelector(`[data-kind="${kind}"] strong`).textContent;
      this.output.show(`${label} traversal`, `${sequence.length} node(s) visited`);
      await this.animate(sequence.map((m) => m.key), (key, index) => {
        this.renderer.visit(key, index + 1);
        this.output.addChip(sequence[index], index + 1);
      });
    } catch (error) {
      this.toast(error.message, true);
    }
  }

  async showLevels(levels) {
    this.output.show("Nodes by level", `${levels.length} level(s) · computed with a Queue (breadth-first)`);
    let order = 0;
    for (let i = 0; i < levels.length; i++) {
      this.output.addLevel(i + 1);
      const ok = await this.animate(levels[i].map((m) => m.key), (key, index) => {
        this.renderer.visit(key, ++order);
        this.output.addChip(levels[i][index]);
      });
      if (!ok) return;
    }
  }

  async animate(keys, step) {
    const token = ++this.animationToken;
    const delay = Number(document.getElementById("speed").value);
    for (let i = 0; i < keys.length; i++) {
      if (token !== this.animationToken) return false;
      step(keys[i], i);
      await new Promise((resolve) => setTimeout(resolve, 1320 - delay));
    }
    return true;
  }

  stopAnimation() {
    this.animationToken++;
  }

  /* ---------- UI helpers ---------- */
  openTab(name) {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${name}`));
  }

  toast(message, isError = false) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.classList.add("show");
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
  }

  bindForm(id, handler) {
    document.getElementById(id).addEventListener("submit", (event) => {
      event.preventDefault();
      const values = Object.fromEntries(new FormData(event.target).entries());
      this.runQuery(() => handler(values));
    });
  }

  bindEvents() {
    this.form.addEventListener("submit", (event) => this.submitForm(event));
    document.getElementById("cancel-edit-btn").addEventListener("click", () => this.cancelEdit());
    document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => this.openTab(tab.dataset.tab)));
    document.querySelectorAll(".traversal").forEach((button) =>
      button.addEventListener("click", () => this.traverse(button.dataset.kind)));

    document.getElementById("undo-btn").addEventListener("click", () => this.treeAction("/api/undo"));
    document.getElementById("rebalance-btn").addEventListener("click", () => this.treeAction("/api/rebalance"));
    document.getElementById("reset-btn").addEventListener("click", () => {
      if (confirm("Restore the original collection? Your changes will be lost.")) this.treeAction("/api/reset");
    });

    document.getElementById("zoom-in").addEventListener("click", () => this.renderer.zoom(1.2));
    document.getElementById("zoom-out").addEventListener("click", () => this.renderer.zoom(1 / 1.2));
    document.getElementById("zoom-fit").addEventListener("click", () => this.renderer.fit());

    this.bindForm("search-mass-form", ({ mass }) => this.searchMass(mass));
    this.bindForm("search-name-form", ({ q }) => this.searchName(q));
    this.bindForm("range-form", ({ min, max }) => this.searchRange(Number(min), Number(max)));
    this.bindForm("closest-form", ({ mass }) => this.searchClosest(mass));
    this.bindForm("rank-form", ({ k, order }) => this.searchRank(k, order));
    this.bindForm("ancestor-form", ({ a, b }) => this.searchAncestor(a, b));

    window.addEventListener("resize", () => this.renderer.fit());
  }
}

new MeteoriteVaultApp().start();
