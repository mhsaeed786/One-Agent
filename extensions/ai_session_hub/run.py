#!/usr/bin/env python3
"""AI Session Hub — Entry point.

Usage:
    python run.py --sync          # Run incremental sync
    python run.py --sync-all      # Force full re-sync
    python run.py --serve         # Start web server
    python run.py --serve --sync  # Sync then serve
"""

import argparse
import os
import sys

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def init_db():
    """Create the database and apply schema if needed."""
    import sqlite3
    from config import DB_PATH, SCHEMA_PATH

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Register tools
    from config import TOOL_CONFIGS
    for name, cfg in TOOL_CONFIGS.items():
        conn.execute(
            """INSERT OR IGNORE INTO tools (name, display_name, adapter_class, data_path, enabled)
               VALUES (?, ?, ?, ?, ?)""",
            (name, cfg["display_name"], cfg["adapter_class"], cfg["data_path"], int(cfg["enabled"])),
        )
    conn.commit()
    conn.close()
    print(f"[init] Database ready at {DB_PATH}")


def run_sync(force_full=False):
    """Run the sync engine."""
    from sync.engine import SyncEngine

    engine = SyncEngine(force_full=force_full)
    results = engine.run_all()
    print("\n=== Sync Results ===")
    for tool, stats in results.items():
        status = stats.get("status", "unknown")
        found = stats.get("found", 0)
        new = stats.get("new", 0)
        updated = stats.get("updated", 0)
        print(f"  {tool}: {status} | found={found} new={new} updated={updated}")
    print("====================\n")


def run_server():
    """Start the Flask web server."""
    from web.app import create_app
    from config import WEB_HOST, WEB_PORT

    app = create_app()
    print(f"[serve] AI Session Hub running at http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)


def main():
    parser = argparse.ArgumentParser(description="AI Session Hub")
    parser.add_argument("--sync", action="store_true", help="Run incremental sync")
    parser.add_argument("--sync-all", action="store_true", help="Force full re-sync")
    parser.add_argument("--serve", action="store_true", help="Start web server")
    args = parser.parse_args()

    if not args.sync and not args.sync_all and not args.serve:
        parser.print_help()
        sys.exit(1)

    init_db()

    if args.sync_all:
        run_sync(force_full=True)
    elif args.sync:
        run_sync(force_full=False)

    if args.serve:
        run_server()


if __name__ == "__main__":
    main()
