# 🎴 Tazos Collection Tracker

A tiny web app to track which numbered tazos you have, how many copies,
and the condition of each copy. Runs two ways: as a fully static page (great
for **GitHub Pages**) or as a local Python app.

## Run on GitHub Pages (no install)

The app also works as a pure static site — open `index.html` and it stores your
collections in the browser (via `localStorage`), so no server is needed.

1. Push this repo to GitHub.
2. In the repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*,
   pick the `main` branch and the `/ (root)` folder, and **Save**.
4. After a minute your tracker is live at
   `https://<your-username>.github.io/<repo-name>/`.

On the first visit, the bundled collections in `collections/` are loaded into
your browser automatically (listed in `collections/manifest.json`). From then
on, every change auto-saves to that browser. Use **⬇ Export CSV** to download a
collection as a spreadsheet-friendly file.

> Note: on GitHub Pages your data lives in your browser, not in the repo — it
> is per-device and per-browser. Editing the CSV/JSON files in the repo won't
> change what an existing browser already has (clear the site's storage to
> re-seed from the bundled files).

## Run locally (Python)

**Easiest (macOS):** double-click `launch.command` in Finder.

**Or from a terminal:**
```bash
python3 server.py
```

Then open <http://localhost:8765> in your browser.
Press `Ctrl+C` in the terminal to stop.

The Python version reads and writes the JSON/CSV files in `collections/`
directly on disk (the static/Pages version cannot, since Pages has no backend).

## How to use

1. Type a **collection name** and the **total number** of tazos, then click **Set up grid**.
2. **Left-click** a tazo to mark you own it (adds one copy as **Excelente** by default).
3. **Left-click again** to add another copy (repeated tazo).
4. **Shift+Click** removes one copy.
5. **Right-click** a tazo to:
   - add a copy with a specific condition (Excelente / Bien / Maltratado / Muy Maltratado / Dañado),
   - change the condition of an existing copy,
   - remove one or all copies.
6. Switch between saved collections with the **— load saved —** dropdown.

Every change auto-saves.

## Where your data lives

Each collection is saved twice in the `collections/` folder next to the app:

- `<name>.json` — full data (source of truth, re-loadable in the app)
- `<name>.csv` — flat table: `number, count, owned, conditions`

You can open the CSV in Excel / Numbers / Google Sheets anytime.
