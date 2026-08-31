"""Senses — sensor base class and registry."""
from __future__ import annotations

import os
import glob
from typing import List, Optional

from .store import Experience


class Sensor:
    """A sense. Polls a source and yields Experiences."""
    id: str = "sensor"
    description: str = ""

    def available(self) -> bool:
        return True

    def poll(self) -> List[Experience]:
        raise NotImplementedError


SENSOR_DIRS = {
    # local AI session stores discovered on this PC
    "hermes": [
        os.path.expanduser(r"~\session-migration-backup-20260822\converted-for-hermes"),
    ],
    "claude_code": [os.path.expanduser(r"~\.claude\projects")],
    "codex": [os.path.expanduser(r"~\.codex\sessions")],
    "goose": [
        os.path.expandvars(r"%APPDATA%\Block\goose\data\sessions"),
    ],
}


def discover_sensors() -> List[Sensor]:
    from .sensors import local_sessions, fs_watch, browser, github_repos

    sensors: List[Sensor] = []
    for cls in (local_sessions.LocalSessionSensor, fs_watch.FilesystemSensor,
                browser.BrowserHistorySensor, browser.BookmarksSensor,
                github_repos.GitHubReposSensor):
        try:
            s = cls()
            if s.available():
                sensors.append(s)
        except Exception:
            pass
    return sensors
