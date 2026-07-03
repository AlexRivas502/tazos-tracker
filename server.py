#!/usr/bin/env python3
"""
Tazos Collection Tracker — tiny local web app.

Run:  python3 server.py
Then open http://localhost:8765 in your browser.

Collections are saved as both JSON and CSV files in the ./collections folder
next to this script. No external dependencies — uses only the standard library.
"""

import json
import csv
import io
import os
import re
import http.server
import socketserver
import urllib.parse

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "collections")
CONDITIONS = ["Mint", "Good", "Used", "Damaged", "Very Damaged"]

os.makedirs(DATA_DIR, exist_ok=True)


def safe_name(name):
    """Turn a collection name into a safe filename slug."""
    slug = re.sub(r"[^A-Za-z0-9_\- ]+", "", name).strip()
    slug = re.sub(r"\s+", "_", slug)
    return slug or "collection"


def json_path(name):
    return os.path.join(DATA_DIR, safe_name(name) + ".json")


def csv_path(name):
    return os.path.join(DATA_DIR, safe_name(name) + ".csv")


def save_collection(data):
    """Persist a collection to JSON and CSV. Returns the saved data."""
    name = data.get("name", "collection")

    # JSON — the full source of truth
    with open(json_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # CSV — flat, one row per tazo (numbered first, then custom labels)
    total = int(data.get("total", 0))
    items = data.get("items", {})
    extras = data.get("extras", [])
    with open(csv_path(name), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "count", "owned", "conditions"])
        labels = [str(n) for n in range(1, total + 1)] + [str(e) for e in extras]
        for label in labels:
            item = items.get(label, {})
            count = int(item.get("count", 0))
            conds = item.get("conditions", [])
            writer.writerow([
                label,
                count,
                "yes" if count > 0 else "no",
                "; ".join(conds),
            ])
    return data


def list_collections():
    out = []
    for fn in sorted(os.listdir(DATA_DIR)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(DATA_DIR, fn), encoding="utf-8") as f:
                    d = json.load(f)
                out.append({"name": d.get("name", fn[:-5]), "total": d.get("total", 0)})
            except Exception:
                pass
    return out


def load_collection(name):
    p = json_path(name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def delete_collection(name):
    """Remove the JSON and CSV files for a collection. Returns True if anything was removed."""
    removed = False
    for p in (json_path(name), csv_path(name)):
        if os.path.exists(p):
            os.remove(p)
            removed = True
    return removed


def rename_collection(old_name, new_name):
    """Rename a collection. Loads the old data, writes it under the new name, and
    removes the old files if the slug actually changed. Returns the saved data."""
    data = load_collection(old_name)
    if data is None:
        return None
    data["name"] = new_name
    save_collection(data)
    if safe_name(old_name) != safe_name(new_name):
        delete_collection(old_name)
    return data


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._send(200, INDEX_HTML, "text/html")
            return

        if path == "/api/collections":
            self._send(200, list_collections())
            return

        if path == "/api/collection":
            qs = urllib.parse.parse_qs(parsed.query)
            name = qs.get("name", [""])[0]
            data = load_collection(name)
            if data is None:
                self._send(404, {"error": "not found"})
            else:
                self._send(200, data)
            return

        self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/save":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except Exception:
                self._send(400, {"error": "bad json"})
                return
            saved = save_collection(data)
            self._send(200, {"ok": True, "saved": saved.get("name")})
            return

        if parsed.path == "/api/delete":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except Exception:
                self._send(400, {"error": "bad json"})
                return
            removed = delete_collection(data.get("name", ""))
            self._send(200, {"ok": removed})
            return

        if parsed.path == "/api/rename":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except Exception:
                self._send(400, {"error": "bad json"})
                return
            old = (data.get("old") or "").strip()
            new = (data.get("new") or "").strip()
            if not new:
                self._send(400, {"error": "empty name"})
                return
            result = rename_collection(old, new)
            if result is None:
                self._send(404, {"error": "not found"})
            else:
                self._send(200, {"ok": True, "name": result.get("name")})
            return

        self._send(404, {"error": "not found"})


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tazos Collection Tracker</title>
<style>
  :root {
    --bg: #0f1419;
    --panel: #1a212b;
    --border: #2a3441;
    --accent: #ffb300;
    --owned: #2e7d32;
    --owned-bright: #43a047;
    --text: #e6edf3;
    --muted: #8b98a5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, system-ui, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    min-height: 100vh;
  }

  /* ---- sidebar: the list of collections ---- */
  aside {
    width: 250px;
    flex: 0 0 250px;
    background: var(--panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    height: 100vh;
    position: sticky;
    top: 0;
  }
  aside .side-head {
    padding: 16px 16px 10px;
    border-bottom: 1px solid var(--border);
  }
  aside .side-head h1 { font-size: 17px; margin: 0 0 12px; color: var(--accent); }
  .collections { flex: 1; overflow-y: auto; padding: 8px; }
  .col-item {
    padding: 10px 12px;
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 4px;
    border: 1px solid transparent;
  }
  .col-item:hover { background: #243140; }
  .col-item.active { background: #243140; border-color: var(--accent); }
  .col-item .cname { font-size: 14px; font-weight: 600; }
  .col-item .cmeta { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .col-empty { color: var(--muted); font-size: 13px; padding: 12px; text-align: center; }

  .container { flex: 1; min-width: 0; display: flex; flex-direction: column; }

  header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--panel);
    position: sticky; top: 0; z-index: 10;
    display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  }
  h1 { font-size: 18px; margin: 0 12px 0 0; color: var(--accent); }
  label { font-size: 13px; color: var(--muted); }
  input, select, button {
    font: inherit;
    background: #0f1620;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 10px;
  }
  input[type=number] { width: 90px; }
  button {
    cursor: pointer;
    background: #243140;
  }
  button:hover { background: #2e3d4f; }
  button.primary { background: var(--accent); color: #1a1200; border-color: var(--accent); font-weight: 600; }
  button.primary:hover { filter: brightness(1.08); }
  button.block { display: block; width: 100%; text-align: center; }
  button.danger-btn { color: #ff7b72; }
  button.danger-btn:hover { background: #3a2422; }
  .stats { margin-left: auto; font-size: 13px; color: var(--muted); }
  .stats b { color: var(--text); }
  .save-status { font-size: 12px; color: var(--owned-bright); min-width: 90px; }

  main { padding: 16px 20px 60px; flex: 1; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(78px, 1fr));
    gap: 8px;
  }
  .cell {
    position: relative;
    aspect-ratio: 1 / 1;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--panel);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    user-select: none;
    transition: transform .05s, background .12s;
  }
  .cell:hover { border-color: var(--accent); }
  .cell:active { transform: scale(.95); }
  .cell.owned {
    background: var(--owned);
    border-color: var(--owned-bright);
  }
  .cell .num { font-size: 18px; font-weight: 700; }
  .cell.owned .num { color: #fff; }
  .cell .count {
    position: absolute; top: 4px; right: 6px;
    font-size: 11px; font-weight: 700;
    background: var(--accent); color: #1a1200;
    border-radius: 10px; padding: 1px 6px;
    min-width: 18px; text-align: center;
  }
  .cell .conds {
    font-size: 9px; color: rgba(255,255,255,.85);
    text-align: center; line-height: 1.1; margin-top: 3px;
    max-width: 100%; padding: 0 3px; overflow: hidden;
  }
  .empty-msg { color: var(--muted); padding: 40px 0; text-align: center; }

  /* custom (non-numbered) tazos */
  .cell.custom { border-style: dashed; }
  .cell.custom:not(.owned) { background: #161e29; }
  .cell .tag {
    position: absolute; top: 4px; left: 6px;
    font-size: 8px; text-transform: uppercase; letter-spacing: .04em;
    color: var(--accent); opacity: .85;
  }
  .cell.owned .tag { color: #fff; }

  /* context menu */
  .menu {
    position: fixed; z-index: 100;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(0,0,0,.5);
    padding: 6px; min-width: 180px;
    display: none;
  }
  .menu.show { display: block; }
  .menu .mtitle { font-size: 11px; color: var(--muted); padding: 4px 8px; }
  .menu button {
    display: block; width: 100%; text-align: left;
    border: none; background: transparent; padding: 8px 10px; border-radius: 6px;
  }
  .menu button:hover { background: #2e3d4f; }
  .menu .sep { height: 1px; background: var(--border); margin: 5px 4px; }
  .menu button.danger { color: #ff7b72; }
  .legend { font-size: 12px; color: var(--muted); margin: 4px 0 14px; }
  .legend code { background: #0f1620; padding: 1px 6px; border-radius: 5px; color: var(--text); }
</style>
</head>
<body>
<aside>
  <div class="side-head">
    <h1>🎴 Tazos Tracker</h1>
    <button id="newBtn" class="primary block">＋ New collection</button>
  </div>
  <div id="collections" class="collections"></div>
</aside>

<div class="container">
<header>
  <label>Collection
    <input id="name" type="text" placeholder="e.g. Pokémon 2000" value="My Collection" style="width:180px">
  </label>
  <label>Total
    <input id="total" type="number" min="1" max="2000" value="50">
  </label>
  <button id="apply" class="primary">Set up grid</button>
  <button id="addCustomBtn">＋ Add custom tazo</button>
  <button id="renameBtn">Rename</button>
  <button id="deleteBtn" class="danger-btn">Delete</button>
  <div class="stats" id="stats"></div>
  <span class="save-status" id="saveStatus"></span>
</header>

<main>
  <div class="legend">
    Left-click a tazo to add one (defaults to <b>Mint</b>). Click again to add another copy.
    Right-click to set the condition of a copy, remove a copy, or <b>reset the number</b> if you clicked it by accident. <code>Shift+Click</code> removes one copy.
  </div>
  <div id="grid" class="grid"></div>
  <div id="emptyMsg" class="empty-msg">Set a total number above and click “Set up grid”, or use “＋ Add custom tazo”.</div>
</main>
</div>

<div id="menu" class="menu"></div>

<script>
const CONDITIONS = ["Mint", "Good", "Used", "Damaged", "Very Damaged"];
let state = { name: "My Collection", total: 0, items: {}, extras: [] };
let saveTimer = null;

const $ = id => document.getElementById(id);

function item(n) {
  const k = String(n);
  if (!state.items[k]) state.items[k] = { count: 0, conditions: [] };
  return state.items[k];
}

function addCopy(n, condition = "Mint") {
  const it = item(n);
  it.count += 1;
  it.conditions.push(condition);
  render(); scheduleSave();
}

function removeCopy(n, idx = -1) {
  const it = item(n);
  if (it.count <= 0) return;
  it.count -= 1;
  if (idx >= 0 && idx < it.conditions.length) it.conditions.splice(idx, 1);
  else it.conditions.pop();
  render(); scheduleSave();
}

function setCondition(n, idx, condition) {
  const it = item(n);
  if (idx >= 0 && idx < it.conditions.length) it.conditions[idx] = condition;
  render(); scheduleSave();
}

function render() {
  const grid = $("grid");
  grid.innerHTML = "";
  if (!state.extras) state.extras = [];
  const hasContent = state.total > 0 || state.extras.length > 0;
  if (!hasContent) { $("emptyMsg").style.display = "block"; updateStats(); return; }
  $("emptyMsg").style.display = "none";

  // numbered tazos first
  for (let n = 1; n <= state.total; n++) {
    grid.appendChild(buildCell(String(n), false));
  }
  // then custom labels
  state.extras.forEach(label => {
    grid.appendChild(buildCell(String(label), true));
  });
  updateStats();
}

function buildCell(key, isCustom) {
  const it = item(key);
  const cell = document.createElement("div");
  cell.className = "cell" + (it.count > 0 ? " owned" : "") + (isCustom ? " custom" : "");
  const numSpan = document.createElement("span");
  numSpan.className = "num";
  numSpan.textContent = key;  // textContent → safe for any custom label

  cell.innerHTML =
    (it.count > 0 ? `<span class="count">${it.count}</span>` : "") +
    (isCustom ? `<span class="tag">custom</span>` : "");
  cell.appendChild(numSpan);
  if (it.conditions.length) {
    const cs = document.createElement("span");
    cs.className = "conds";
    cs.textContent = condSummary(it.conditions);
    cell.appendChild(cs);
  }

  cell.addEventListener("click", (e) => {
    if (e.shiftKey) removeCopy(key);
    else addCopy(key);
  });
  cell.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    openMenu(e, key, isCustom);
  });
  return cell;
}

function condSummary(conds) {
  // compact like: Mint×2, Good
  const order = {};
  conds.forEach(c => order[c] = (order[c] || 0) + 1);
  return Object.entries(order)
    .map(([c, k]) => k > 1 ? `${c}×${k}` : c)
    .join(", ");
}

function updateStats() {
  const keys = [];
  for (let n = 1; n <= state.total; n++) keys.push(String(n));
  (state.extras || []).forEach(l => keys.push(String(l)));

  let owned = 0, copies = 0;
  keys.forEach(k => {
    const it = state.items[k];
    if (it && it.count > 0) { owned++; copies += it.count; }
  });
  const totalSlots = keys.length;
  const missing = totalSlots - owned;
  const extraNote = (state.extras && state.extras.length)
    ? ` &nbsp;·&nbsp; incl. ${state.extras.length} custom` : "";
  $("stats").innerHTML = totalSlots
    ? `Owned <b>${owned}</b> / ${totalSlots} &nbsp;·&nbsp; Missing <b>${missing}</b> &nbsp;·&nbsp; Total copies <b>${copies}</b>${extraNote}`
    : "";
}

/* ---- context menu ---- */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function openMenu(e, n, isCustom = false) {
  const it = item(n);
  const menu = $("menu");
  const label = escapeHtml(n);
  let html = `<div class="mtitle">Tazo ${label} — add a copy as:</div>`;
  CONDITIONS.forEach(c => {
    html += `<button data-act="add" data-cond="${c}">＋ ${c}</button>`;
  });
  if (it.count > 0) {
    html += `<div class="sep"></div><div class="mtitle">Existing copies (click to change condition):</div>`;
    it.conditions.forEach((c, i) => {
      html += `<button data-act="edit" data-idx="${i}">#${i + 1}: ${c} ▾</button>`;
    });
    html += `<div class="sep"></div>`;
    html += `<button class="danger" data-act="removeone">－ Remove one copy</button>`;
  }
  html += `<div class="sep"></div>`;
  html += `<button class="danger" data-act="reset">↺ Reset this tazo (clear all copies)</button>`;
  if (isCustom) {
    html += `<button class="danger" data-act="deletecustom">🗑 Delete this custom tazo</button>`;
  }
  menu.innerHTML = html;
  menu.classList.add("show");
  positionMenu(e.clientX, e.clientY);

  menu.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const act = btn.dataset.act;
      if (act === "add") { addCopy(n, btn.dataset.cond); closeMenu(); }
      else if (act === "removeone") { removeCopy(n); closeMenu(); }
      else if (act === "reset") {
        const k = String(n); state.items[k] = { count: 0, conditions: [] };
        render(); scheduleSave(); closeMenu();
      }
      else if (act === "deletecustom") {
        deleteCustom(n); closeMenu();
      }
      else if (act === "edit") {
        const idx = parseInt(btn.dataset.idx, 10);
        openCondPicker(ev, n, idx);
      }
    });
  });
}

function openCondPicker(e, n, idx) {
  const menu = $("menu");
  let html = `<div class="mtitle">Tazo ${escapeHtml(n)}, copy #${idx + 1} → set condition:</div>`;
  CONDITIONS.forEach(c => {
    html += `<button data-cond="${c}">${c}</button>`;
  });
  html += `<div class="sep"></div><button class="danger" data-remove="1">－ Remove this copy</button>`;
  menu.innerHTML = html;
  positionMenu(e.clientX, e.clientY);
  menu.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      if (btn.dataset.remove) removeCopy(n, idx);
      else setCondition(n, idx, btn.dataset.cond);
      closeMenu();
    });
  });
}

function positionMenu(x, y) {
  const menu = $("menu");
  const w = menu.offsetWidth, h = menu.offsetHeight;
  menu.style.left = Math.min(x, window.innerWidth - w - 8) + "px";
  menu.style.top = Math.min(y, window.innerHeight - h - 8) + "px";
}
function closeMenu() { $("menu").classList.remove("show"); }
document.addEventListener("click", closeMenu);
document.addEventListener("scroll", closeMenu, true);

/* ---- custom tazos (labels outside the 1..total range, e.g. 0, A, Special) ---- */
function addCustom() {
  if (!state.extras) state.extras = [];
  const raw = prompt("Label for the custom tazo (e.g. 0, A, B, Special):", "");
  if (raw === null) return;
  const label = raw.trim();
  if (!label) return;

  // reject collisions with an existing numbered slot or an existing custom label
  const asNum = Number(label);
  if (Number.isInteger(asNum) && asNum >= 1 && asNum <= state.total) {
    alert(`“${label}” is already a numbered tazo (1–${state.total}).`);
    return;
  }
  if (state.extras.some(e => String(e) === label)) {
    alert(`“${label}” already exists as a custom tazo.`);
    return;
  }

  state.extras.push(label);
  item(label); // ensure an entry exists
  render();
  scheduleSave();
}

function deleteCustom(label) {
  if (!confirm(`Delete custom tazo “${label}” and all its copies?`)) return;
  state.extras = (state.extras || []).filter(e => String(e) !== String(label));
  delete state.items[String(label)];
  render();
  scheduleSave();
}

/* ---- collections sidebar & multi-collection management ---- */
let allCollections = [];

async function refreshList() {
  const res = await fetch("/api/collections");
  allCollections = await res.json();
  renderSidebar();
}

function renderSidebar() {
  const box = $("collections");
  box.innerHTML = "";
  if (!allCollections.length) {
    box.innerHTML = '<div class="col-empty">No collections yet.<br>Click “New collection”.</div>';
    return;
  }
  allCollections.forEach(c => {
    const div = document.createElement("div");
    div.className = "col-item" + (c.name === state.name ? " active" : "");
    div.innerHTML = `<div class="cname"></div><div class="cmeta">${c.total} tazos</div>`;
    div.querySelector(".cname").textContent = c.name;  // safe text
    div.addEventListener("click", () => {
      if (c.name !== state.name) loadCollection(c.name);
    });
    box.appendChild(div);
  });
}

async function loadCollection(name) {
  const res = await fetch("/api/collection?name=" + encodeURIComponent(name));
  if (!res.ok) return;
  state = await res.json();
  if (!state.items) state.items = {};
  if (!state.extras) state.extras = [];
  $("name").value = state.name;
  $("total").value = state.total;
  render();
  renderSidebar();
}

function newCollection() {
  const name = prompt("Name for the new collection:", "New Collection");
  if (name === null) return;
  const total = parseInt(prompt("How many tazos in this collection?", "50"), 10);
  state = { name: name.trim() || "New Collection", total: (total > 0 ? total : 0), items: {}, extras: [] };
  $("name").value = state.name;
  $("total").value = state.total;
  render();
  save().then(refreshList);
}

async function renameCollection() {
  const newName = prompt("Rename collection:", state.name);
  if (newName === null) return;
  const trimmed = newName.trim();
  if (!trimmed || trimmed === state.name) return;
  const oldName = state.name;
  await fetch("/api/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old: oldName, new: trimmed }),
  });
  state.name = trimmed;
  $("name").value = trimmed;
  await refreshList();
}

async function deleteCollection() {
  if (!confirm(`Delete collection “${state.name}”?\nThis removes its JSON and CSV files. This cannot be undone.`)) return;
  await fetch("/api/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: state.name }),
  });
  await refreshList();
  // switch to another collection, or a blank one
  if (allCollections.length) {
    loadCollection(allCollections[0].name);
  } else {
    state = { name: "My Collection", total: 0, items: {}, extras: [] };
    $("name").value = state.name;
    $("total").value = state.total;
    render();
    renderSidebar();
  }
}

/* ---- persistence ---- */
function scheduleSave() {
  $("saveStatus").textContent = "saving…";
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => save().then(refreshList), 400);
}
async function save() {
  state.name = $("name").value.trim() || "My Collection";
  try {
    await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });
    const t = new Date().toLocaleTimeString();
    $("saveStatus").textContent = "saved ✓ " + t;
  } catch (err) {
    $("saveStatus").textContent = "save failed ✗";
  }
}

/* ---- setup ---- */
$("apply").addEventListener("click", () => {
  const total = parseInt($("total").value, 10) || 0;
  state.name = $("name").value.trim() || "My Collection";
  state.total = total;
  render();
  scheduleSave();
});

$("name").addEventListener("change", scheduleSave);
$("newBtn").addEventListener("click", newCollection);
$("addCustomBtn").addEventListener("click", addCustom);
$("renameBtn").addEventListener("click", renameCollection);
$("deleteBtn").addEventListener("click", deleteCollection);

/* on first load: open the most recent collection if any exist */
(async function init() {
  await refreshList();
  if (allCollections.length) {
    await loadCollection(allCollections[0].name);
  } else {
    render();
  }
})();
</script>
</body>
</html>
"""


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}"
        print("=" * 52)
        print("  🎴  Tazos Collection Tracker is running")
        print(f"  Open:  {url}")
        print(f"  Files saved to: {DATA_DIR}")
        print("  Press Ctrl+C to stop.")
        print("=" * 52)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
