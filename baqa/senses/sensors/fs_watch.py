"""Sensor: filesystem — absorbs user documents (md, txt, py, json…) as knowledge."""
from __future__ import annotations

import glob
import os
from typing import List

from ..store import Experience

# knowledge-dense files worth absorbing
PATTERNS = ["*.md", "*.txt"]
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv", "chroma_data"}
MAX_FILES = 300
MAX_SIZE = 60_000  # chars


class FilesystemSensor:
    id = "filesystem"
    description = "Absorbs markdown/text documents from the workspace"

    def __init__(self, roots: List[str] = None):
        if roots is None:
            roots = [
                os.path.expanduser(r"~\repo-audit\One-Agent"),
                os.path.expanduser(r"~\Documents"),
            ]
        self.roots = [r for r in roots if os.path.isdir(r)]

    def available(self) -> bool:
        return bool(self.roots)

    def poll(self) -> List[Experience]:
        out: List[Experience] = []
        for root in self.roots:
            count = 0
            for pat in PATTERNS:
                for fp in glob.glob(os.path.join(root, "**", pat), recursive=True):
                    if count >= MAX_FILES:
                        break
                    if any(part in fp for part in SKIP_DIRS):
                        continue
                    try:
                        if os.path.getsize(fp) > MAX_SIZE * 4:
                            continue
                        with open(fp, encoding="utf-8", errors="replace") as f:
                            text = f.read(MAX_SIZE)
                        if len(text.strip()) < 50:
                            continue
                        out.append(Experience(
                            source="filesystem",
                            kind="document",
                            ts=os.path.getmtime(fp),
                            title=os.path.basename(fp),
                            text=text,
                            uri=fp,
                        ))
                        count += 1
                    except (OSError, PermissionError):
                        continue
        return out
