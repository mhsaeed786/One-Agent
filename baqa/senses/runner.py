"""Action Runner — executes approved proposals.

Safety model:
- A proposal only reaches the runner after the user explicitly approved it.
- Actions are registered handlers; each handler is report-first: it produces
  a report the user reads, and performs writes only within its approved scope.
- Unknown actions are never executed.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict

logger = logging.getLogger("mind.runner")

# action name -> callable() -> report dict
ACTIONS: Dict[str, Callable[[], dict]] = {}


def action(name: str):
    def deco(fn):
        ACTIONS[name] = fn
        return fn
    return deco


def register_approved(proposal: dict) -> dict:
    """An approved proposal becomes a scheduled registration.

    The action must exist in the registry; otherwise it stays approved-but-
    dormant and appears in /mind/proposals?status=approved as awaiting-impl.
    """
    name = proposal.get("action", "")
    if name in ACTIONS:
        try:
            report = ACTIONS[name]()
            return {"registered": True, "executed": True, "report": report}
        except Exception as e:
            return {"registered": True, "executed": False, "error": str(e)[:200]}
    return {"registered": True, "executed": False,
            "note": f"action '{name}' not yet implemented; approved and queued"}


# ── Built-in actions (report-first) ─────────────────────────────────────

@action("repo_hygiene")
def repo_hygiene() -> dict:
    """Read-only scan: unpushed commits, dirty worktrees across known repos."""
    import subprocess, os
    repos_root = os.path.expanduser("~\\repo-audit")
    report = {"repos": []}
    if not os.path.isdir(repos_root):
        return {"error": "no repo-audit dir"}
    for name in os.listdir(repos_root):
        path = os.path.join(repos_root, name)
        git = os.path.join(path, ".git")
        if not os.path.isdir(git):
            continue
        entry = {"repo": name}
        try:
            st = subprocess.run(["git", "status", "-sb"], cwd=path,
                                capture_output=True, text=True, timeout=30)
            entry["status"] = (st.stdout or "").strip().splitlines()[0][:80] if st.stdout else ""
            dirty = len((st.stdout or "").strip().splitlines()) - 1
            entry["dirty_files"] = max(dirty, 0)
        except Exception as e:
            entry["error"] = str(e)[:100]
        report["repos"].append(entry)
    return report


@action("session_digest")
def session_digest() -> dict:
    """Digest new AI-session instructions into a knowledge-base file."""
    import os
    from .store import ExperienceStore
    store = ExperienceStore()
    exps = store.recent(50, source="ai_session:hermes")
    kb_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kb")
    os.makedirs(kb_dir, exist_ok=True)
    out = os.path.join(kb_dir, "session_digest_latest.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Session Digest (latest 50 Hermes instructions)\n\n")
        for e in exps:
            f.write(f"- {e['title'][:120]}\n")
    return {"digest_file": out, "instructions": len(exps)}


@action("teams_scrape_merge")
def teams_scrape_merge() -> dict:
    """Placeholder until the Teams sense is wired; reports instead of scraping."""
    return {"note": "Teams sense not yet permissioned; approve the teams sense first",
            "status": "awaiting_permission"}


@action("fhir_audit")
def fhir_audit() -> dict:
    """Placeholder: runs only after the FHIR server sense is permissioned."""
    return {"note": "FHIR sense not yet permissioned; grant permission first",
            "status": "awaiting_permission"}
