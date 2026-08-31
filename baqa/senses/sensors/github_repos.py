"""Sensor: GitHub repositories — your code as knowledge.

Uses `git log` locally (no API keys needed). Absorbs recent commit subjects
from every repo under repo-audit + Documents/Migrated data.
Requires explicit permission (sense id: github_repos).
"""
from __future__ import annotations

import os
import subprocess
import time
from typing import List

from ..store import Experience

REPO_ROOTS = [
    os.path.expanduser(r"~\repo-audit"),
]
MAX_COMMITS_PER_REPO = 30


def _find_repos(root: str, depth: int = 0) -> List[str]:
    if depth > 2:
        return []
    repos = []
    try:
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isdir(os.path.join(p, ".git")):
                repos.append(p)
            elif os.path.isdir(p) and depth < 2:
                repos.extend(_find_repos(p, depth + 1))
    except (OSError, PermissionError):
        pass
    return repos


class GitHubReposSensor:
    id = "github_repos"
    description = "Absorbs recent commit history from local git repositories"

    def available(self) -> bool:
        return any(os.path.isdir(r) for r in REPO_ROOTS)

    def poll(self) -> List[Experience]:
        out: List[Experience] = []
        for root in REPO_ROOTS:
            for repo in _find_repos(root):
                try:
                    r = subprocess.run(
                        ["git", "log", "--pretty=%s|%at", f"-n{MAX_COMMITS_PER_REPO}"],
                        cwd=repo, capture_output=True, text=True, timeout=30)
                    for line in (r.stdout or "").splitlines():
                        if "|" not in line:
                            continue
                        subject, _, ts = line.rpartition("|")
                        if len(subject) < 8:
                            continue
                        try:
                            ts_f = float(ts)
                        except ValueError:
                            ts_f = time.time()
                        out.append(Experience(
                            source="github",
                            kind="commit",
                            ts=ts_f,
                            title=subject[:120],
                            text=subject,
                            uri=repo,
                            meta={"repo": os.path.basename(repo)},
                        ))
                except (subprocess.TimeoutExpired, OSError):
                    continue
        return out
