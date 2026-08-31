"""Sensor: browser history — Chrome/Edge (URLs + titles).

Read-only. Copies the locked History DB to temp before reading.
Requires explicit permission (sense id: browser_history).
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import time
from typing import List

from ..store import Experience

HISTORY_PATHS = {
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\History"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History"),
}
MAX_ROWS = 500


def _webkit_to_epoch(ts) -> float:
    try:
        return float(ts) / 1_000_000 - 11_644_473_600
    except (TypeError, ValueError):
        return 0.0


class BrowserHistorySensor:
    id = "browser_history"
    description = "Absorbs visited URLs + page titles from Chrome/Edge history"

    def available(self) -> bool:
        return any(os.path.isfile(p) for p in HISTORY_PATHS.values())

    def poll(self) -> List[Experience]:
        out: List[Experience] = []
        for browser, path in HISTORY_PATHS.items():
            if not os.path.isfile(path):
                continue
            tmp = os.path.join(tempfile.gettempdir(), f"mind_{browser}_history.db")
            try:
                shutil.copy2(path, tmp)  # DB is locked while browser runs
                conn = sqlite3.connect(tmp)
                rows = conn.execute(
                    "SELECT url, title, last_visit_time FROM urls"
                    " ORDER BY last_visit_time DESC LIMIT ?", (MAX_ROWS,)).fetchall()
                conn.close()
            except (sqlite3.Error, OSError, PermissionError):
                continue
            for url, title, ts in rows:
                if not title or len(title) < 4:
                    continue
                out.append(Experience(
                    source=f"browser:{browser}",
                    kind="visit",
                    ts=_webkit_to_epoch(ts) or time.time(),
                    title=title[:120],
                    text=f"{title} — {url}",
                    uri=url,
                ))
        return out


class BookmarksSensor:
    id = "bookmarks"
    description = "Absorbs Chrome/Edge bookmarks"

    def available(self) -> bool:
        return any(os.path.isfile(p) for p in BOOKMARK_PATHS.values())

    def poll(self) -> List[Experience]:
        import json
        out: List[Experience] = []

        def walk(node, folder):
            if isinstance(node, dict):
                if node.get("type") == "url":
                    return [Experience(
                        source="browser:bookmarks",
                        kind="bookmark",
                        ts=time.time(),
                        title=(node.get("name") or "")[:120],
                        text=f"{node.get('name','')} — {node.get('url','')}",
                        uri=node.get("url", ""),
                        meta={"folder": folder},
                    )]
                results = []
                for child in node.get("children", []) or []:
                    results.extend(walk(child, node.get("name", folder)))
                return results
            return []

        for browser, path in BOOKMARK_PATHS.items():
            if not os.path.isfile(path):
                continue
            try:
                data = json.load(open(path, encoding="utf-8", errors="replace"))
                for root in (data.get("roots") or {}).values():
                    out.extend(walk(root, ""))
            except (OSError, json.JSONDecodeError):
                continue
        return out


BOOKMARK_PATHS = {
    "chrome": os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks"),
    "edge": os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks"),
}
