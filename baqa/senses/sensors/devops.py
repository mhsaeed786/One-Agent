"""Sensor: Azure DevOps / Jira work items.

Dormant until BOTH conditions hold:
  1. sense permission 'devops' granted
  2. credentials present in env: AZURE_DEVOPS_ORG + AZURE_DEVOPS_PAT
     (or JIRA_BASE_URL + JIRA_EMAIL + JIRA_TOKEN)

Read-only: fetches the user's recently-updated work items and absorbs
title/state/type as experiences. Never writes to the tracker.
"""
from __future__ import annotations

import os
import time
from typing import List

from ..store import Experience


class DevOpsSensor:
    id = "devops"
    description = "Absorbs Azure DevOps / Jira work items assigned to you"

    def available(self) -> bool:
        has_ado = bool(os.getenv("AZURE_DEVOPS_ORG") and os.getenv("AZURE_DEVOPS_PAT"))
        has_jira = bool(os.getenv("JIRA_BASE_URL") and os.getenv("JIRA_TOKEN"))
        return has_ado or has_jira

    def poll(self) -> List[Experience]:
        if os.getenv("AZURE_DEVOPS_ORG") and os.getenv("AZURE_DEVOPS_PAT"):
            return self._poll_azure_devops()
        if os.getenv("JIRA_BASE_URL") and os.getenv("JIRA_TOKEN"):
            return self._poll_jira()
        return []

    def _poll_azure_devops(self) -> List[Experience]:
        import base64, json as _json
        import urllib.request

        org = os.getenv("AZURE_DEVOPS_ORG", "")
        project = os.getenv("AZURE_DEVOPS_PROJECT", "")
        pat = os.getenv("AZURE_DEVOPS_PAT", "")
        token = base64.b64encode(f":{pat}".encode()).decode()
        url = (f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql"
               f"?api-version=7.1")
        wiql = {"query": "SELECT [System.Id], [System.Title], [System.State],"
                          "[System.WorkItemType], [System.ChangedDate]"
                          " FROM WorkItems WHERE [System.AssignedTo] = @Me"
                          " ORDER BY [System.ChangedDate] DESC"}
        req = urllib.request.Request(
            url, data=_json.dumps(wiql).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Basic {token}"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _json.loads(resp.read().decode())
        except (OSError, ValueError):
            return []
        out: List[Experience] = []
        for item in data.get("workItems", [])[:50]:
            fields = item.get("fields", {})
            title = fields.get("System.Title", "")
            if not title:
                continue
            out.append(Experience(
                source="devops:ado",
                kind="work_item",
                ts=time.time(),
                title=f"[{fields.get('System.WorkItemType','?')}] {title}"[:120],
                text=f"{title} — state: {fields.get('System.State','?')}",
                uri=item.get("url", ""),
                meta={"id": item.get("id"), "state": fields.get("System.State")},
            ))
        return out

    def _poll_jira(self) -> List[Experience]:
        import json as _json
        import urllib.request

        base = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        email = os.getenv("JIRA_EMAIL", "")
        token = os.getenv("JIRA_TOKEN", "")
        import base64
        token_b64 = base64.b64encode(f"{email}:{token}".encode()).decode()
        jql = urllib.parse.quote("assignee = currentUser() ORDER BY updated DESC")
        url = f"{base}/rest/api/2/search?jql={jql}&maxResults=50"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {token_b64}",
            "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _json.loads(resp.read().decode())
        except (OSError, ValueError):
            return []
        out: List[Experience] = []
        for issue in data.get("issues", []):
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "")
            if not summary:
                continue
            out.append(Experience(
                source="devops:jira",
                kind="work_item",
                ts=time.time(),
                title=f"[{key}] {summary}"[:120],
                text=f"{summary} — state: {fields.get('status',{}).get('name','?')}",
                uri=f"{base}/browse/{key}",
                meta={"key": key},
            ))
        return out


import urllib.parse  # noqa: E402  (used by _poll_jira)
