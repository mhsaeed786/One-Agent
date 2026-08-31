"""Sensor: web AI chats — fed by the Mind Capture browser extension.

The extension POSTs the user's prompts to POST /mind/capture. This module
owns the permission check + storage. The sense never browses on its own;
it only receives what the user explicitly sends (approval-first by design).
"""
from __future__ import annotations

import time
from typing import List

from ..store import Experience, ExperienceStore
from ..permissions import PermissionGate

SENSE_ID = "web_ai_chats"


def capture_instruction(payload: dict) -> dict:
    """Store one captured prompt from the extension. Gate-checked."""
    gate = PermissionGate()
    if gate.state(SENSE_ID) != "granted":
        return {"stored": False,
                "reason": f"sense '{SENSE_ID}' is '{gate.state(SENSE_ID)}' — grant it first"}

    text = (payload.get("text") or "").strip()
    if len(text) < 25:
        return {"stored": False, "reason": "too short"}

    tool = payload.get("tool") or "web:unknown"
    store = ExperienceStore()
    exp = Experience(
        source=f"ai_session:{tool}",
        kind=payload.get("kind") or "instruction",
        ts=time.time(),
        title=(payload.get("title") or text[:90])[:120],
        text=text[:4000],
        uri=payload.get("uri") or "",
    )
    absorbed, _ = store.absorb([exp])
    return {"stored": bool(absorbed), "sense": SENSE_ID}
