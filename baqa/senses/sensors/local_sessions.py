"""Sensor: local AI session chats (Hermes, Claude Code, Codex…).

Reads real session transcripts on this PC and absorbs user instructions
as experiences. This is how the Mind learns what you've asked every AI
on this machine, forever.
"""
from __future__ import annotations

import glob
import json
import os
from typing import List

from ..store import Experience
from .. import SENSOR_DIRS


class LocalSessionSensor:
    id = "ai_sessions"
    description = "Absorbs user instructions from local AI session transcripts"

    def available(self) -> bool:
        return any(os.path.isdir(p) for paths in SENSOR_DIRS.values() for p in paths)

    def poll(self) -> List[Experience]:
        experiences: List[Experience] = []
        for tool, paths in SENSOR_DIRS.items():
            for base in paths:
                if not os.path.isdir(base):
                    continue
                for fp in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True)[:200]:
                    experiences.extend(self._absorb_jsonl(fp, tool))
        return experiences

    def _absorb_jsonl(self, path: str, tool: str) -> List[Experience]:
        out: List[Experience] = []
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    role, content, ts = self._extract_message(obj)
                    if role != "user":
                        continue
                    text = self._flatten(content)
                    if len(text) < 25:  # skip "continue", "ok", etc.
                        continue
                    out.append(Experience(
                        source=f"ai_session:{tool}",
                        kind="instruction",
                        ts=self._parse_ts(ts, path),
                        title=text[:90],
                        text=text[:4000],
                        uri=path,
                    ))
        except (OSError, PermissionError):
            pass
        return out

    @staticmethod
    def _parse_ts(ts, path: str) -> float:
        """Parse epoch floats or ISO-8601 strings; fall back to file mtime."""
        if ts is None:
            return os.path.getmtime(path)
        if isinstance(ts, (int, float)):
            return float(ts)
        try:
            from datetime import datetime, timezone
            s = str(ts).replace("Z", "+00:00")
            return datetime.fromisoformat(s).timestamp()
        except ValueError:
            return os.path.getmtime(path)

    @staticmethod
    def _extract_message(obj: dict):
        """Handle Claude Code, Codex rollout, and generic jsonl shapes."""
        # claude code: {"type":"user","message":{"role":"user","content":[...]}, "timestamp":...}
        if obj.get("type") == "user" and isinstance(obj.get("message"), dict):
            m = obj["message"]
            return m.get("role"), m.get("content"), obj.get("timestamp")
        # codex rollout: {"type":"response_item","payload":{"type":"message","role":"user","content":[...]}, "timestamp":...}
        if obj.get("type") == "response_item" and isinstance(obj.get("payload"), dict):
            p = obj["payload"]
            if p.get("type") == "message":
                return p.get("role"), p.get("content"), obj.get("timestamp")
        # generic: {"role":"user","content":...}
        return obj.get("role"), obj.get("content"), obj.get("timestamp")

    @staticmethod
    def _flatten(content) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict) and c.get("type") in ("text", "input_text"):
                    parts.append(c.get("text", ""))
                elif isinstance(c, str):
                    parts.append(c)
            return " ".join(parts).strip()
        return ""
