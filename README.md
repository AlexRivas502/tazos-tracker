# 🎴 Tazos Collection Tracker

A tiny local web app to track which numbered tazos you have, how many copies,
and the condition of each copy. No internet, no dependencies — just Python 3.

## Launch

**Easiest (macOS):** double-click `launch.command` in Finder.

**Or from a terminal:**
```bash
python3 server.py
```

Then open <http://localhost:8765> in your browser.
Press `Ctrl+C` in the terminal to stop.

## How to use

1. Type a **collection name** and the **total number** of tazos, then click **Set up grid**.
2. **Left-click** a tazo to mark you own it (adds one copy as **Mint** by default).
3. **Left-click again** to add another copy (repeated tazo).
4. **Shift+Click** removes one copy.
5. **Right-click** a tazo to:
   - add a copy with a specific condition (Mint / Good / Used / Damaged / Very Damaged),
   - change the condition of an existing copy,
   - remove one or all copies.
6. Switch between saved collections with the **— load saved —** dropdown.

Every change auto-saves.

## Where your data lives

Each collection is saved twice in the `collections/` folder next to the app:

- `<name>.json` — full data (source of truth, re-loadable in the app)
- `<name>.csv` — flat table: `number, count, owned, conditions`

You can open the CSV in Excel / Numbers / Google Sheets anytime.
